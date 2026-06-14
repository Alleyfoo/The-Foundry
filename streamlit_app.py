"""
The Foundry — Streamlit web frontend.

Turning incoming business chaos into trusted, structured change.

A thin shell over the runtime. Objects live in a SQLite system of record; you can
drop in raw inputs (intake), drive them through the spine (activate → submit →
approve → commit), and watch the analysis update. Users see simple views; the
system sees governed change.

    streamlit run streamlit_app.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from runtime.foundry import Foundry, load_objects
from runtime.system_of_record import SystemOfRecord
from runtime.actions import intake, triage_text, available_actions, apply_action

BASE_DIR = Path(__file__).resolve().parent

BOX_ICON = {"create": "➕", "modify": "✏️", "plan": "📅", "control": "🛡️", "reference": "📄"}
STATE_ICON = {"active": "🟢", "pending": "🟡", "blocked": "🔴", "draft": "⚪", "retired": "⚫"}
COMMIT_ICON = {"proposal": "💡", "workflow": "⚙️", "truth": "🔒"}
SOURCES = ["form", "email", "pdf", "excel", "chat", "api"]

OBJ_COLS = ["object_id", "object_type", "title", "box", "stream",
            "owner_team", "state", "commitment", "confidence", "aging_days"]


# ----------------------------------------------------------------------
@st.cache_resource
def get_sor() -> SystemOfRecord:
    """One system-of-record per server, seeded from the object file."""
    sor = SystemOfRecord(str(BASE_DIR / "artifacts" / "foundry.db"))
    sor.seed_if_empty(load_objects(str(BASE_DIR / "data" / "objects.json")))
    return sor


def refresh(sor: SystemOfRecord) -> None:
    """Re-run the pipeline over the live system-of-record state."""
    st.session_state["result"] = Foundry(base_dir=str(BASE_DIR)).run(objects=sor.all_objects())


def to_df(records, columns=None) -> pd.DataFrame:
    """Arrow-safe DataFrame: stringify any nested cell (lists/dicts)."""
    df = pd.DataFrame(records)
    if columns:
        df = df[[c for c in columns if c in df.columns]]
    for col in df.columns:
        if df[col].map(lambda v: isinstance(v, (list, dict))).any():
            df[col] = df[col].map(
                lambda v: ", ".join(map(str, v)) if isinstance(v, list)
                else json.dumps(v, default=str) if isinstance(v, dict) else v
            )
    return df


# ----------------------------------------------------------------------
st.set_page_config(page_title="The Foundry", page_icon="🔥", layout="wide")
sor = get_sor()
if "result" not in st.session_state:
    refresh(sor)

st.title("🔥 The Foundry")
st.markdown(
    "**Turning incoming business chaos into trusted, structured change.** "
    "Org charts show hierarchy. The Foundry shows the organisation through *access* — "
    "who can act on what, as objects flow from chaos toward trusted truth."
)

with st.sidebar:
    st.header("The Foundry")
    st.caption("Documents are inputs, not the truth. The truth is the structured record.")
    if st.button("🔄  Re-run pipeline", width="stretch"):
        refresh(sor)
    if st.button("♻️  Reset to seed", width="stretch"):
        sor.reset(load_objects(str(BASE_DIR / "data" / "objects.json")))
        refresh(sor)
        st.toast("Reset to seed objects.")
    st.divider()
    st.markdown(
        "**The spine**\n\n"
        "Inputs → Triage → Five Boxes → Impact → Approval → Commit\n\n"
        "_Users see tools. The system sees governed change._"
    )

result = st.session_state["result"]
objects = result["objects"]
obj_by_id = {o["object_id"]: o for o in objects}
roles = result["roles"]
access = roles["access_model"]

# Top metrics
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Objects in flight", len(result["in_flight"]))
c2.metric("Committed truth 🔒", len(result["committed"]))
c3.metric("Bottlenecks 🔴", len(result["bottlenecks"]))
c4.metric("Access mismatches", len(result["mismatches"]))
c5.metric("Needs a human", sum(1 for t in result["triage"] if t["needs_human"]))

tabs = st.tabs([
    "Intake", "Actions", "The Story", "The Five Boxes", "Governance Map",
    "Bottlenecks & Aging", "Access Mismatches", "Monitoring Lenses", "Audit Trail",
])

# --- Intake (drop in chaos) ---
with tabs[0]:
    st.subheader("Intake — drop in chaos, watch it get sorted")
    st.caption("Triage reads the input, sorts it into one of the five boxes, and gives it a confidence.")
    raw = st.text_area("Raw input", placeholder="e.g. Customer Acme wants a waterproof handle variant")
    if raw.strip():
        preview = triage_text(raw)
        st.info(f"Preview → box **{BOX_ICON.get(preview['box'],'')} {preview['box']}** · "
                f"stream **{preview['stream']}** · confidence **{preview['confidence']}**")
    src = st.selectbox("Source", SOURCES)
    if st.button("🔥 Forge into an object", type="primary", disabled=not raw.strip()):
        obj = intake(sor, raw, src)
        refresh(sor)
        st.success(f"Created **{obj['object_id']}** → box `{obj['box']}`, "
                   f"stream `{obj['stream']}`, confidence {obj['confidence']}, state `draft`.")

# --- Actions (drive the spine) ---
with tabs[1]:
    st.subheader("Drive an object through the spine")
    st.caption("Approve / reject are Control actions — only a control-authorised role may do them.")
    actor = st.selectbox("Acting as role", [r["role"] for r in roles["roles"]], index=2)
    ids = [o["object_id"] for o in objects]
    sel = st.selectbox(
        "Object", ids,
        format_func=lambda i: (f"{i} — {obj_by_id[i]['title'][:50]} ({obj_by_id[i]['state']})"
                               if i in obj_by_id else i),
    )
    obj = obj_by_id.get(sel)
    if obj:
        st.markdown(
            f"{STATE_ICON.get(obj['state'],'')} **{obj['state']}** · "
            f"{COMMIT_ICON.get(obj['commitment'],'')} {obj['commitment']} · "
            f"box `{obj['box']}` · owner **{obj['owner_team']}** · "
            f"approver **{obj.get('approver_role') or '—'}** · "
            f"SoR `{obj.get('system_of_record_ref') or '—'}`"
        )
        acts = available_actions(obj)
        if not acts:
            st.info("No actions available — this object is in a terminal state.")
        else:
            cols = st.columns(len(acts))
            for col, act in zip(cols, acts):
                if col.button(act, key=f"act_{act}", width="stretch"):
                    r = apply_action(sor, sel, act, actor, access)
                    refresh(sor)
                    (st.success if r["ok"] else st.error)(r["message"])
                    st.rerun()

# --- The Story (org chart through access) ---
with tabs[2]:
    st.subheader("An org chart shows titles. The Foundry shows access.")
    st.markdown(
        "Different roles have different *gravity* across the five boxes. The level "
        "isn't a title — it's **which governed box you can act in.**"
    )
    role_rows = [
        {"Level": r["level"], "Role": r["role"],
         "Dominant box": r["dominant_box"], "Responsibility": r["responsibility"]}
        for r in sorted(roles["roles"], key=lambda r: -r["level"])
    ]
    st.table(pd.DataFrame(role_rows))
    st.markdown("**Who can act in each box** (access ≠ title):")
    acc_rows = [
        {"Box": f"{BOX_ICON.get(b,'')} {b}", "Primary owner": v["primary"],
         "Also touches": ", ".join(v["also"]) or "—"}
        for b, v in access["box_access"].items()
    ]
    st.table(pd.DataFrame(acc_rows))
    for p in roles["principles"]:
        st.markdown(f"- {p}")

# --- The Five Boxes ---
with tabs[3]:
    st.subheader("The Foundry sorts incoming reality into five governed action families")
    st.caption(result["boxes"]["tagline"])
    cols = st.columns(5)
    for col, box in zip(cols, result["boxes"]["boxes"]):
        in_box = [o for o in objects if o["box"] == box["id"]]
        with col:
            st.markdown(f"### {BOX_ICON.get(box['id'],'')} {box['name']}")
            st.caption(box["meaning"])
            st.metric("objects", len(in_box))
            for o in in_box:
                st.markdown(
                    f"{STATE_ICON.get(o['state'],'')} **{o['object_id']}** "
                    f"{COMMIT_ICON.get(o['commitment'],'')}<br>"
                    f"<span style='font-size:0.8em'>{o['title'][:40]}</span>",
                    unsafe_allow_html=True,
                )
    st.divider()
    st.markdown("**Triage** — how sure the Foundry is about each object:")
    st.dataframe(to_df(result["triage"]), width="stretch", height=300)

# --- Governance Map (streams) ---
with tabs[4]:
    st.subheader("Who owns reality, what is flowing, and where it gets stuck")
    for stream in ["customer", "item", "supplier"]:
        in_stream = [o for o in objects if o["stream"] == stream]
        st.markdown(f"#### {stream.title()} stream  ·  {len(in_stream)} objects")
        if in_stream:
            st.dataframe(to_df(in_stream, OBJ_COLS), width="stretch",
                         height=min(40 + 35 * len(in_stream), 340))

# --- Bottlenecks & Aging ---
with tabs[5]:
    st.subheader("Better visibility of bottlenecks and aging work")
    bn = result["bottlenecks"]
    if not bn:
        st.success("No bottlenecks. Everything is flowing.")
    else:
        st.markdown(f"**{len(bn)}** objects are stuck or aging:")
        for b in bn:
            colour = "🔴" if b["reason"] == "blocked" else "🟡"
            st.markdown(
                f"{colour} **{b['object_id']}** — {b['title']}  \n"
                f"owner **{b['owner_team']}** · state `{b['state']}` · "
                f"aging **{b['aging_days']}d** · downstream impact: {b['downstream_count']}"
            )

# --- Access Mismatches ---
with tabs[6]:
    st.subheader("Where access and responsibility disagree, the Foundry exposes it")
    st.caption("Access is a claim about responsibility. The system does not paper over the gap.")
    ms = result["mismatches"]
    if not ms:
        st.success("No access mismatches detected.")
    else:
        label = {
            "approval_without_authority": "🛡️ Approval without authority",
            "ownership_without_flow": "🔴 Ownership without flow (blocked)",
            "editable_without_approver": "✏️ Editable without a declared approver",
            "low_confidence_truth": "🔒 Committed as truth at low confidence",
        }
        for m in ms:
            o = obj_by_id.get(m["object_id"], {})
            st.markdown(
                f"**{label.get(m['type'], m['type'])}** — `{m['object_id']}` "
                f"({o.get('title','')})  \n{m['detail']}"
            )

# --- Monitoring Lenses ---
with tabs[7]:
    st.subheader("Same objects, different maps")
    st.caption("Customer · Sales · Product · Operations · Finance — each lens shows what that function owns.")
    lens_tabs = st.tabs([l.title() for l in result["lenses"]])
    for lt, (lens, ids) in zip(lens_tabs, result["lenses"].items()):
        with lt:
            rows = [obj_by_id[i] for i in ids if i in obj_by_id]
            if rows:
                st.dataframe(to_df(rows, OBJ_COLS), width="stretch", height=320)
            else:
                st.info("No objects in this lens.")

# --- Audit Trail ---
with tabs[8]:
    st.subheader("The invisible eye — every step, logged")
    st.caption("Trusted outcomes: traceable, compliant, auditable.")
    st.markdown("**System-of-record events** (intake, actions, commits):")
    events = sor.events()
    if events:
        ev = pd.DataFrame(events)[["ts", "object_id", "action", "from_state", "to_state", "actor_role", "note"]]
        ev["ts"] = ev["ts"].map(lambda t: t.split("T")[-1][:8] if isinstance(t, str) and "T" in t else t)
        st.dataframe(ev, width="stretch", height=300)
    else:
        st.info("No events yet.")
    st.markdown("**Pipeline shadow log** (this run):")
    st.json(result["metrics"])
