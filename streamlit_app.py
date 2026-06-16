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

from streamlit_agraph import agraph, Node, Edge, Config

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


def select_from_click(clicked: str, detector_key: str) -> None:
    """Set the shared selection only when a component reports a NEW click.

    Components return their last value on every rerun, so we de-dup per source to
    avoid one view overriding a selection made in another.
    """
    if clicked and clicked != st.session_state.get(f"_last_{detector_key}"):
        st.session_state[f"_last_{detector_key}"] = clicked
        st.session_state["selected_id"] = clicked


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

(tab_universe, tab_scenario, tab_objects, tab_map, tab_ownership,
 tab_coverage, tab_risk, tab_model) = st.tabs([
    "🌌 Signal Universe", "▶ Scenario", "Objects", "Governance Map", "Ownership",
    "Coverage", "Bottlenecks & Risk", "Model & Audit",
])
# Consolidated layout: several sub-views render into shared tabs. Entering a tab
# context more than once appends content, so the old per-view blocks still work.
tab_intake = tab_objects
tab_mismatch = tab_coverage
tab_bottlenecks = tab_impact = tab_risk
tab_story = tab_boxes = tab_lenses = tab_audit = tab_model

# Domains group the owning teams into the three ownership super-groups.
DOMAINS = [
    ("Sales Domain", "👥", ["Sales"]),
    ("Product & Ops Domain", "📦", ["Product Manager", "Product Data", "Product Owner",
                                    "Operations", "Suppliers", "Research", "Production"]),
    ("Governance Domain", "🛡️", ["Pricing", "Finance", "Manager", "SAP Owner", "Records Owner"]),
]

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
    ui.flow_legend()
    ui.flow_row("The change: new variant → SAP", item_chain)

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

    # --- Second story: the catch. Approval without authority. ---
    st.divider()
    ui.section_header(
        "A supplier price change — the catch",
        "The same spine, run on a different change. This one is stopped before it can "
        "become truth, because the person approving it isn't allowed to.")
    st.markdown(
        "**The story.** A supplier emails a new price list. Most systems would route it "
        "to whoever owns pricing and let them push it through. The Foundry routes it the "
        "same way — and then checks one more thing: *is the approver actually authorised "
        "to make this a governed truth?*")

    # A transient change — never written to the system of record. It exists only to be
    # run through the real detection engine, so the flag below is genuine, not narrated.
    px1 = {
        "object_id": "OBJ-PX1",
        "object_type": "Price Change",
        "world": "outside",
        "title": "Acme Brackets — new price list (rev C)",
        "box": "modify",
        "stream": "supplier",
        "owner_team": "Pricing",
        "state": "pending",
        "commitment": "workflow",
        "confidence": 0.55,
        "aging_days": 0,
        "approver_role": "Pricing",
        "source_input": "email",
        "lifecycle": "none",
        "evidence": ["email:acme-pricelist-revC.pdf"],
        "downstream": [],
        "system_of_record_ref": None,
    }

    if st.button("▶  Run the supplier price change", type="primary", key="px_run"):
        st.session_state["px_played"] = True

    if st.session_state.get("px_played"):
        # Run the transient object through the real engine — same code as the live pipeline.
        flags = Foundry(base_dir=str(BASE_DIR))._detect_mismatches(
            [px1], result["boxes"], access["box_access"])
        authority_flag = next(
            (f for f in flags if f["type"] == "approval_without_authority"), None)
        ctrl = access["box_access"].get("control", {})
        authorised = [ctrl.get("primary"), *ctrl.get("also", [])]

        beats = [
            ("📧", "A supplier sends a new price list by email.",
             "`email:acme-pricelist-revC.pdf` — Acme Brackets, rev C."),
            ("🔥", "The system extracts a price change object.",
             f"`{px1['object_id']}` · *{px1['title']}*"),
            ("✏️", "It is routed into **modify**.",
             "Not a new record — a change to existing reality."),
            ("⚠️", "It affects live product / pricing truth.",
             "`modify` is a truth-touching box. This is governed change, not a note."),
            ("👤", f"It has an owner — **{px1['owner_team']}**.",
             "Someone is accountable for the change."),
            ("🛡️", f"It needs an approver — routed to **{px1['approver_role']}**.",
             "Nothing touching truth moves without a named approver."),
            ("🚫", f"The approver lacks control authority.",
             f"Only {', '.join(authorised)} can act in Control. "
             f"**{px1['approver_role']}** cannot."),
            ("🔴", "The Foundry flags: **approval without authority**.",
             authority_flag["detail"] if authority_flag else "(no flag)"),
            ("✋", "Nothing is committed.",
             "The change is held in flight. No silent write to the system of record."),
        ]
        for icon, head, detail in beats:
            st.markdown(f"{icon}  **{head}**  \n&nbsp;&nbsp;&nbsp;{detail}")

        if authority_flag:
            st.error(
                "🛡️ **Approval without authority.** "
                f"`{px1['object_id']}` would change pricing truth, but its approver "
                f"(*{px1['approver_role']}*) is not authorised to act in Control. "
                "The change is **not committed** — it is routed to someone who can "
                "actually own that decision.")
        st.caption(
            "This is the difference. Process tools ask *where work moves*. The Foundry "
            "also asks *whether the people moving it are allowed to make it true.*")

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

# --- Governance Map (the signal / flow view) ---
FLOWS = [
    ("1. Customer Signal Flow", ["OBJ-C001", "OBJ-C002", "OBJ-C003", "OBJ-C004", "OBJ-C005"]),
    ("2. Item Creation Flow", ["OBJ-I001", "OBJ-I002", "OBJ-I003", "OBJ-I004", "OBJ-I005"]),
    ("3. Supplier / Reference Flow", ["OBJ-S001", "OBJ-S002", "OBJ-S003", "OBJ-X001", "OBJ-S004"]),
    ("4. Price Flow", ["OBJ-P001", "OBJ-P002", "OBJ-P003", "OBJ-P004"]),
    ("5. Product Creation Flow", ["OBJ-N001", "OBJ-N002", "OBJ-N003", "OBJ-A001"]),
]
with tab_map:
    ui.section_header("Object Governance Map",
                      "Who owns reality, what is flowing, and where it gets stuck — "
                      "click a node to inspect it.")
    ui.flow_legend()
    for title, ids in FLOWS:
        nodes = [obj_by_id[i] for i in ids if i in obj_by_id]
        if not nodes:
            continue
        ui.flow_row(title, nodes)
        cols = st.columns(len(nodes))
        for c, o in zip(cols, nodes):
            if c.button(f"🔍 {o['object_id']}", key=f"flow_{o['object_id']}", width="stretch"):
                st.session_state["selected_id"] = o["object_id"]
                st.rerun()

    sid = st.session_state.get("selected_id")
    if sid and sid in obj_by_id:
        st.divider()
        ui.object_detail(obj_by_id[sid], obj_by_id)

    afterlife = [o for o in objects if o.get("lifecycle", "none") != "none"]
    if afterlife:
        st.markdown("#### Lifecycle / afterlife")
        st.caption("How objects leave: end-of-life, scrap, replacement-linked, archived.")
        st.dataframe(
            to_df(afterlife, ["object_id", "title", "lifecycle", "state", "owner_team"]),
            width="stretch", height=min(40 + 35 * len(afterlife), 240),
        )

# --- Signal Universe (the centerpiece: interactive graph + docked detail) ---
with tab_universe:
    ui.section_header("Signal Universe",
                      "Every governed object and how it connects — click a node to inspect it. "
                      "Fill = box, border = status, arrows = downstream impact.")
    ui.universe_legend()
    graph_col, detail_col = st.columns([2, 1])
    with graph_col:
        ids = {o["object_id"] for o in objects}
        nodes = [
            Node(id=o["object_id"], label=o["object_type"], title=o["object_id"],
                 shape="dot", size=16, borderWidth=3,
                 color={"background": ui.BOX_TINT.get(o["box"], "#eef2f7"),
                        "border": ui.STATE_COLOR.get(o["state"], ui.MUTED)})
            for o in objects
        ]
        edges = [
            Edge(source=o["object_id"], target=d,
                 color=ui.STATE_COLOR.get(obj_by_id[d]["state"], "#cbd5e1"))
            for o in objects for d in o.get("downstream", []) if d in ids
        ]
        cfg = Config(width=720, height=560, directed=True, physics=True,
                     nodeHighlightBehavior=True, highlightColor="#2563c9")
        clicked = agraph(nodes=nodes, edges=edges, config=cfg)
        select_from_click(clicked, "universe")
    with detail_col:
        usid = st.session_state.get("selected_id")
        if usid and usid in obj_by_id:
            ui.object_detail(obj_by_id[usid], obj_by_id)
        else:
            st.info("⬅ Click a node to open its detail panel.")

# --- Ownership View (objects grouped by the domain that owns them) ---
with tab_ownership:
    ui.section_header("Ownership View",
                      "Every object grouped by the domain that owns it — who is "
                      "accountable for what. Click a node to inspect it.")
    dom_cols = st.columns(3)
    for col, (name, icon, teams) in zip(dom_cols, DOMAINS):
        with col:
            members = [o for o in objects if o["owner_team"] in teams]
            st.markdown(
                f'<div class="fdy-domhead"><b>{icon} {name}</b>'
                f'<span class="cnt">{len(members)} items</span></div>',
                unsafe_allow_html=True,
            )
            for o in members:
                st.markdown(ui.object_card(o), unsafe_allow_html=True)
                if st.button(f"🔍 {o['object_id']}", key=f"own_{o['object_id']}", width="stretch"):
                    st.session_state["selected_id"] = o["object_id"]
                    st.rerun()
    osid = st.session_state.get("selected_id")
    if osid and osid in obj_by_id:
        st.divider()
        ui.object_detail(obj_by_id[osid], obj_by_id)

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
