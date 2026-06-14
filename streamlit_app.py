"""
The Foundry — Streamlit web frontend.

Turning incoming business chaos into trusted, structured change.

A thin shell over runtime/foundry.py. Users see simple views; the system sees
governed change. Run with:

    streamlit run streamlit_app.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from runtime.foundry import Foundry

BASE_DIR = Path(__file__).resolve().parent

BOX_ICON = {"create": "➕", "modify": "✏️", "plan": "📅", "control": "🛡️", "reference": "📄"}
STATE_ICON = {"active": "🟢", "pending": "🟡", "blocked": "🔴", "draft": "⚪", "retired": "⚫"}
COMMIT_ICON = {"proposal": "💡", "workflow": "⚙️", "truth": "🔒"}


# ----------------------------------------------------------------------
def run_foundry() -> dict:
    return Foundry(base_dir=str(BASE_DIR)).run()


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


OBJ_COLS = ["object_id", "object_type", "title", "box", "stream",
            "owner_team", "state", "commitment", "confidence", "aging_days"]


# ----------------------------------------------------------------------
st.set_page_config(page_title="The Foundry", page_icon="🔥", layout="wide")

st.title("🔥 The Foundry")
st.markdown(
    "**Turning incoming business chaos into trusted, structured change.** "
    "Org charts show hierarchy. The Foundry shows the organisation through *access* — "
    "who can act on what, as objects flow from chaos toward trusted truth."
)

with st.sidebar:
    st.header("The Foundry")
    st.caption("Documents are inputs, not the truth. The truth is the structured record.")
    if st.button("🔥  Run the Foundry", type="primary", width="stretch"):
        with st.spinner("Intake → triage → impact → approval → commit …"):
            st.session_state["result"] = run_foundry()
    st.divider()
    st.markdown(
        "**The spine**\n\n"
        "Inputs → Triage → Five Boxes → Impact → Approval → Commit\n\n"
        "_Users see tools. The system sees governed change._"
    )

result = st.session_state.get("result")
if result is None:
    st.info("Press **🔥 Run the Foundry** in the sidebar to forge the object set into governed change.")
    st.stop()

objects = result["objects"]
obj_by_id = {o["object_id"]: o for o in objects}

# Top metrics
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Objects in flight", len(result["in_flight"]))
c2.metric("Committed truth 🔒", len(result["committed"]))
c3.metric("Bottlenecks 🔴", len(result["bottlenecks"]))
c4.metric("Access mismatches", len(result["mismatches"]),
          delta=None if not result["mismatches"] else "exposed", delta_color="inverse")
c5.metric("Needs a human", sum(1 for t in result["triage"] if t["needs_human"]))

tabs = st.tabs([
    "The Story", "The Five Boxes", "Governance Map",
    "Bottlenecks & Aging", "Access Mismatches", "Monitoring Lenses", "Audit Trail",
])

# --- The Story (org chart through access) ---
with tabs[0]:
    st.subheader("An org chart shows titles. The Foundry shows access.")
    st.markdown(
        "Different roles have different *gravity* across the five boxes. The level "
        "isn't a title — it's **which governed box you can act in.**"
    )
    roles = result["roles"]
    role_rows = [
        {"Level": r["level"], "Role": r["role"],
         "Dominant box": r["dominant_box"], "Responsibility": r["responsibility"]}
        for r in sorted(roles["roles"], key=lambda r: -r["level"])
    ]
    st.table(pd.DataFrame(role_rows))
    st.markdown("**Who can act in each box** (access ≠ title):")
    access = roles["access_model"]["box_access"]
    acc_rows = [
        {"Box": f"{BOX_ICON.get(b,'')} {b}", "Primary owner": v["primary"],
         "Also touches": ", ".join(v["also"]) or "—"}
        for b, v in access.items()
    ]
    st.table(pd.DataFrame(acc_rows))
    for p in roles["principles"]:
        st.markdown(f"- {p}")

# --- The Five Boxes ---
with tabs[1]:
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
                    f"<span style='font-size:0.8em'>{o['title']}</span>",
                    unsafe_allow_html=True,
                )
    st.divider()
    st.markdown("**Triage** — how sure the Foundry is about each object:")
    st.dataframe(to_df(result["triage"]), width="stretch", height=300)

# --- Governance Map (streams) ---
with tabs[2]:
    st.subheader("Who owns reality, what is flowing, and where it gets stuck")
    for stream in ["customer", "item", "supplier"]:
        in_stream = [o for o in objects if o["stream"] == stream]
        st.markdown(f"#### {stream.title()} stream  ·  {len(in_stream)} objects")
        st.dataframe(to_df(in_stream, OBJ_COLS), width="stretch",
                     height=min(40 + 35 * len(in_stream), 340))

# --- Bottlenecks & Aging ---
with tabs[3]:
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

# --- Access Mismatches (the payoff) ---
with tabs[4]:
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
with tabs[5]:
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
with tabs[6]:
    st.subheader("The invisible eye — every step, logged")
    st.caption("Trusted outcomes: traceable, compliant, auditable. No opinions, no intervention.")
    st.json(result["metrics"])
    log = result["store"].read_shadow(result["run_id"])
    if log:
        df = pd.DataFrame([
            {
                "time": e.get("timestamp", "").split("T")[-1][:8],
                "agent": e.get("agent_name", ""),
                "event": e.get("event_type", ""),
                "detail": json.dumps(e.get("detail", {}), default=str)[:160],
            }
            for e in log
        ])
        st.dataframe(df, width="stretch", height=380)
