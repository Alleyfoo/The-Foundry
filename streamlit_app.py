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
import ui

BASE_DIR = Path(__file__).resolve().parent

BOX_ICON = {"create": "➕", "modify": "✏️", "plan": "📅", "control": "🛡️", "reference": "📄"}
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
ui.inject_css()
sor = get_sor()
if "result" not in st.session_state:
    refresh(sor)

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
        "**Three lenses on one truth**\n\n"
        "🗺️ Map · 🛡️ Coverage · 🔀 Flow\n\n"
        "_Users see tools. The system sees governed change._"
    )

result = st.session_state["result"]
objects = result["objects"]
obj_by_id = {o["object_id"]: o for o in objects}
roles = result["roles"]
access = roles["access_model"]

# Hero + the spine (deck screen 1)
ui.section_header("The Foundry", "Turning incoming business chaos into trusted, structured change.")
needs_human = sum(1 for t in result["triage"] if t["needs_human"])
spine_badges = ["", "", "", "", "", ""]
spine_badges[1] = ui.badge(f"{needs_human} need a human", "#7c3aed", "#efe7fb")
spine_badges[3] = ui.badge(f"{len(result['bottlenecks'])} bottlenecks", ui.RED, "#fde8e8")
spine_badges[5] = ui.badge(f"{len(result['committed'])} committed", ui.GREEN, "#e3f6ec")
ui.spine(spine_badges)
st.caption("Users see tools. The system sees governed change.")

(tab_scenario, tab_intake, tab_objects, tab_story, tab_boxes, tab_map, tab_coverage,
 tab_bottlenecks, tab_impact, tab_mismatch, tab_lenses, tab_audit) = st.tabs([
    "▶ Scenario", "Intake", "Objects", "The Story", "The Five Boxes", "Governance Map",
    "Coverage", "Bottlenecks & Aging", "Impact & Approvals", "Access Mismatches",
    "Monitoring Lenses", "Audit Trail",
])

# --- Scenario (guided narrative walkthrough) ---
with tab_scenario:
    ui.section_header(
        "Meridian Industrial onboards a new product",
        "Watch one real change travel the spine — from a customer email to trusted SAP truth.")
    st.markdown(
        "**The story.** Nordic Health Oy signals they'd pay for a *waterproof carrying "
        "handle*. Sales raises a request to create the new variant in SAP. But the item "
        "is missing its weight and HS code, and the pricing approval has been **stuck for "
        "7 days**. Here is the change, and the Foundry governing it to trusted truth."
    )
    chain_ids = ["OBJ-I001", "OBJ-I002", "OBJ-I003", "OBJ-I004", "OBJ-I005"]
    item_chain = [obj_by_id[i] for i in chain_ids if i in obj_by_id]
    ui.stream_flow("item", "The change: new variant → SAP", item_chain)

    sap_master = obj_by_id.get("OBJ-I005", {})
    if sap_master.get("commitment") == "truth":
        st.success(f"✅ The new variant is now **trusted truth** in SAP "
                   f"(`{sap_master.get('system_of_record_ref')}`). The bottleneck is cleared.")
    else:
        st.markdown(
            "**What the Foundry caught on this chain:**\n"
            "- 🔴 **Bottleneck** — `OBJ-I004` pricing approval, blocked 7 days.\n"
            "- 🛡️ **Access mismatch** — `OBJ-I003` validation check is routed to *Product "
            "Data*, who isn't authorised to act in Control.")
        SCENARIO = [
            ("OBJ-I004", "unblock", "Manager", "Manager clears the stuck pricing approval"),
            ("OBJ-I005", "activate", "SAP Owner", "SAP Owner opens the item record"),
            ("OBJ-I005", "submit", "SAP Owner", "Submitted for approval"),
            ("OBJ-I005", "approve", "Manager", "Manager approves — authorised for Control"),
            ("OBJ-I005", "commit", "SAP Owner", "Committed to trusted truth in SAP"),
        ]
        if st.button("▶  Play the resolution", type="primary"):
            log = []
            for oid, act, actor, note in SCENARIO:
                r = apply_action(sor, oid, act, actor, access)
                log.append(f"{'✅' if r['ok'] else '⚠️'} {note} — {r['message']}")
            refresh(sor)
            st.session_state["scenario_log"] = log
            st.rerun()
    if st.session_state.get("scenario_log"):
        st.markdown("**Resolution:**")
        for line in st.session_state["scenario_log"]:
            st.markdown(f"- {line}")
        st.caption("Use **Reset to seed** in the sidebar to replay.")

# --- Intake (drop in chaos) ---
with tab_intake:
    ui.section_header(
        "Intake",
        "Drop in chaos, watch it get sorted — triage reads the input, sorts it into one "
        "of the five boxes, and gives it a confidence.")
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

# --- Objects (the cockpit: click a classifier, inspect + drive it) ---
with tab_objects:
    ui.section_header(
        "Object Explorer",
        "Every type is a classifier. Filter or search, then click a row to inspect the "
        "object's mapping, state, and connections — and drive it through the spine.")

    f1, f2, f3, f4 = st.columns(4)
    box_f = f1.selectbox("Box", ["All", "create", "modify", "plan", "control", "reference"])
    stream_f = f2.selectbox("Stream", ["All", "customer", "item", "supplier"])
    state_f = f3.selectbox("Status", ["All", "active", "pending", "blocked", "draft", "retired"])
    commit_f = f4.selectbox("Commitment", ["All", "proposal", "workflow", "truth"])
    search = st.text_input("Search", placeholder="title or object id")

    filtered = [
        o for o in objects
        if (box_f == "All" or o["box"] == box_f)
        and (stream_f == "All" or o["stream"] == stream_f)
        and (state_f == "All" or o["state"] == state_f)
        and (commit_f == "All" or o["commitment"] == commit_f)
        and (not search or search.lower() in (o["title"] + o["object_id"]).lower())
    ]

    left, right = st.columns([0.56, 0.44])
    with left:
        st.caption(f"{len(filtered)} objects — click a row to inspect")
        df = to_df(filtered, ["object_id", "object_type", "box", "state",
                              "commitment", "owner_team", "aging_days"])
        event = st.dataframe(df, width="stretch", height=460, hide_index=True,
                             on_select="rerun", selection_mode="single-row", key="obj_tbl")
        if event.selection.rows:
            st.session_state["selected_id"] = filtered[event.selection.rows[0]]["object_id"]

    with right:
        sid = st.session_state.get("selected_id")
        if sid and sid in obj_by_id:
            ui.object_detail(obj_by_id[sid], obj_by_id)
            obj = obj_by_id[sid]
            actor = st.selectbox("Acting as role", [r["role"] for r in roles["roles"]],
                                 index=2, key="det_actor")
            acts = available_actions(obj)
            if acts:
                cols = st.columns(min(len(acts), 4))
                for i, act in enumerate(acts):
                    if cols[i % 4].button(act, key=f"det_{act}", width="stretch"):
                        r = apply_action(sor, sid, act, actor, access)
                        refresh(sor)
                        (st.success if r["ok"] else st.error)(r["message"])
                        st.rerun()
            else:
                st.caption("Terminal state — no actions available.")
        else:
            st.info("⬅ Select an object to open its detail panel.")

# --- The Story (org chart through access) ---
with tab_story:
    ui.section_header(
        "Roles and Ownership",
        "An org chart shows titles. The Foundry shows access — different roles have "
        "different gravity across the boxes.")
    ui.role_ladder(roles)
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
with tab_boxes:
    ui.section_header(
        "The Five Boxes",
        "The Foundry sorts incoming reality into a small number of governed action families.")
    ui.five_boxes(result["boxes"], objects)
    st.caption(result["boxes"]["tagline"])
    st.markdown("**Triage** — how sure the Foundry is about each object:")
    st.dataframe(to_df(result["triage"]), width="stretch", height=300)

# --- Governance Map (streams) ---
with tab_map:
    ui.section_header("Object Governance Map",
                      "Who owns reality, what is flowing, and where it gets stuck.")
    labels = {"customer": "1. Customer Stream", "item": "2. Item Stream",
              "supplier": "3. Supplier / Reference Stream"}
    for stream in ["customer", "item", "supplier"]:
        in_stream = [o for o in objects if o["stream"] == stream]
        if in_stream:
            ui.stream_flow(stream, labels[stream], in_stream)
    afterlife = [o for o in objects if o.get("lifecycle", "none") != "none"]
    if afterlife:
        st.markdown("#### Lifecycle / afterlife")
        st.caption("How objects leave: end-of-life, scrap, replacement-linked, archived.")
        st.dataframe(
            to_df(afterlife, ["object_id", "title", "lifecycle", "state", "owner_team"]),
            width="stretch", height=min(40 + 35 * len(afterlife), 240),
        )

# --- Coverage (which areas are governed, and how well) ---
with tab_coverage:
    ui.section_header("Governance Coverage",
                      "Which areas are covered by which functions — and where the "
                      "checks and balances have gaps.")
    cov = result["coverage"]
    g, a, rd = cov["summary"]["green"], cov["summary"]["amber"], cov["summary"]["red"]
    st.markdown(
        f'<span class="fdy-badge" style="color:{ui.GREEN};background:#e8f7ee">{g} covered</span> '
        f'<span class="fdy-badge" style="color:{ui.ORANGE};background:#fdeede">{a} weak</span> '
        f'<span class="fdy-badge" style="color:{ui.RED};background:#fde8e8">{rd} gap</span>'
        '&nbsp;&nbsp;<span style="color:#7a899c;font-size:.8rem">'
        'green = owned + approved, no mismatch · amber = weak (missing approver or stuck) · '
        'red = a segregation-of-duties gap</span>',
        unsafe_allow_html=True,
    )
    ui.coverage_grid(cov)
    st.markdown("**How each function covers its areas:**")
    ui.coverage_functions(cov["by_function"])

# --- Bottlenecks & Aging ---
with tab_bottlenecks:
    ui.section_header("Bottlenecks & Aging",
                      "Better visibility of where work is stuck and aging — an owner is "
                      "accountable, but it cannot move.")
    bn = result["bottlenecks"]
    if not bn:
        st.success("No bottlenecks. Everything is flowing.")
    else:
        ui.bottleneck_cards(bn)

# --- Impact & Approvals ---
with tab_impact:
    ui.section_header("Impact & approval routing")
    st.caption("Route by confidence, risk, and ownership. Urgency changes priority, not truthfulness.")
    st.markdown("**Pending approvals**")
    if result["approvals"]:
        st.dataframe(
            to_df(result["approvals"],
                  ["object_id", "title", "box", "routed_to", "confidence",
                   "risk", "priority", "recommendation"]),
            width="stretch",
        )
    else:
        st.success("Nothing awaiting approval.")
    st.markdown("**Impact statements** (highest risk first)")
    order = {"high": 0, "medium": 1, "low": 2}
    imp_sorted = sorted(result["impact"], key=lambda i: order[i["risk"]])
    st.dataframe(
        to_df(imp_sorted,
              ["object_id", "box", "risk", "affects_truth", "downstream_count", "statement"]),
        width="stretch", height=360,
    )

# --- Access Mismatches ---
with tab_mismatch:
    ui.section_header(
        "Access Mismatches",
        "Where access and responsibility disagree, the Foundry exposes it — access is a "
        "claim about responsibility, and the system does not paper over the gap.")
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

# --- Monitoring Lenses (the mapmaker idea) ---
with tab_lenses:
    ui.section_header(
        "Monitoring Lenses — everyone gets their own map",
        "Data is the territory. One source of truth; each function travels it with a "
        "different map drawn for what it needs to see.")
    lens_tabs = st.tabs([l.title() for l in result["lenses"]])
    for lt, (lens, ids) in zip(lens_tabs, result["lenses"].items()):
        with lt:
            rows = [obj_by_id[i] for i in ids if i in obj_by_id]
            if rows:
                st.dataframe(to_df(rows, OBJ_COLS), width="stretch", height=320)
            else:
                st.info("No objects in this lens.")

# --- Audit Trail ---
with tab_audit:
    ui.section_header(
        "Audit Trail",
        "The invisible eye — every step logged. Trusted outcomes: traceable, "
        "compliant, auditable.")
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
