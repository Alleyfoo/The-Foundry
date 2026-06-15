"""
The Foundry — UI theme and components.

Matches the designer's light-theme mockup: Archivo display type, navy/orange
palette, white cards, status colours (flowing green / pending amber / blocked red
/ signal blue). Pure presentation; all data comes from the runtime.
"""

from __future__ import annotations

import html
from typing import Any

import streamlit as st

# --- Design tokens (from the mockup) ------------------------------------------
NAVY = "#0f2a4d"
BLUE = "#2563c9"
ORANGE = "#e8732a"
MUTED = "#5b6b7f"
GREEN = "#2fa86a"
AMBER = "#f1a73b"
RED = "#e5484d"
TEAL = "#0f8a8a"

BOX_COLOR = {"create": BLUE, "modify": TEAL, "plan": AMBER, "control": RED, "reference": ORANGE}
BOX_TINT = {"create": "#e7f0fb", "modify": "#dff3f3", "plan": "#fdeede",
            "control": "#fde8e8", "reference": "#fdeede"}
STATE_COLOR = {"active": GREEN, "pending": AMBER, "blocked": RED, "draft": "#94a3b8", "retired": MUTED}
STATE_LABEL = {"active": "flowing", "pending": "pending", "blocked": "stuck",
               "draft": "draft", "retired": "retired"}

# Minimal inline line-icons (stroke = currentColor).
ICONS = {
    "inbox": '<path d="M3 12h4l2 3h6l2-3h4M3 12V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v7M3 12v5a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-5"/>',
    "funnel": '<path d="M3 4h18l-7 8v6l-4 2v-8z"/>',
    "boxes": '<path d="M3 7l9-4 9 4-9 4z"/><path d="M3 7v10l9 4 9-4V7"/><path d="M12 11v10"/>',
    "search": '<circle cx="11" cy="11" r="7"/><path d="M21 21l-4-4"/>',
    "nodes": '<circle cx="6" cy="12" r="2"/><circle cx="18" cy="6" r="2"/><circle cx="18" cy="18" r="2"/><path d="M8 12l8-5M8 12l8 5"/>',
    "database": '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5"/><path d="M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3"/>',
    "create": '<rect x="4" y="4" width="16" height="16" rx="3"/><path d="M12 8v8M8 12h8"/>',
    "modify": '<path d="M4 20l4-1 10-10-3-3L5 16z"/><path d="M14 6l3 3"/>',
    "plan": '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 9h18M8 3v4M16 3v4"/>',
    "control": '<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/><path d="M9 12l2 2 4-4"/>',
    "reference": '<path d="M6 3h9l3 3v15H6z"/><path d="M9 9h6M9 13h6M9 17h4"/>',
}


def _svg(name: str, color: str, size: int = 26) -> str:
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
            f'stroke="{color}" stroke-width="1.7" stroke-linecap="round" '
            f'stroke-linejoin="round">{ICONS.get(name, "")}</svg>')


def _e(s: Any) -> str:
    return html.escape(str(s))


# --- Global CSS ---------------------------------------------------------------
def inject_css() -> None:
    st.markdown(
        """
<style>
@import url('https://fonts.googleapis.com/css2?family=Archivo:wght@400;600;700;800&display=swap');

html, body, [class*="css"], .stMarkdown, p, span, div { font-family: 'Archivo', system-ui, sans-serif; }
h1, h2, h3, h4 { font-family: 'Archivo', system-ui, sans-serif; font-weight: 800; color: #0f2a4d; letter-spacing: -0.01em; }
#MainMenu, footer, header [data-testid="stToolbar"] { visibility: hidden; }
.block-container { padding-top: 2.2rem; max-width: 1180px; }

/* Section header with the orange accent bar */
.fdy-head { border-left: 5px solid #e8732a; padding-left: 16px; margin: 4px 0 22px; }
.fdy-head h2 { font-size: 2.0rem; margin: 0; }
.fdy-head p { color: #5b6b7f; margin: 4px 0 0; font-size: 1.0rem; }

/* Generic card + badges */
.fdy-card { background:#fff; border:1px solid #e2e9f3; border-radius:14px;
            box-shadow:0 1px 2px rgba(15,42,77,.04); padding:18px; }
.fdy-badge { font-family:ui-monospace,monospace; font-size:.66rem; letter-spacing:.04em;
             padding:3px 8px; border-radius:6px; text-transform:uppercase; white-space:nowrap; }
.fdy-id { font-family:ui-monospace,monospace; font-size:.7rem; color:#94a3b8; }

/* Spine */
.fdy-spine { display:flex; align-items:flex-start; gap:2px; flex-wrap:nowrap; justify-content:center;
             overflow-x:auto; margin:6px 0 10px; }
.fdy-step { display:flex; flex-direction:column; align-items:center; width:118px; flex:none; text-align:center; }
.fdy-circle { width:58px; height:58px; border-radius:50%; background:#e7f0fb; display:flex;
              align-items:center; justify-content:center; margin-bottom:10px; }
.fdy-pill { background:#0f2a4d; color:#fff; font-weight:700; font-size:.82rem; padding:5px 14px; border-radius:7px; }
.fdy-step small { color:#5b6b7f; font-size:.72rem; display:block; margin-top:8px; line-height:1.25; }
.fdy-arrow { color:#94a3b8; font-size:1.3rem; padding-top:20px; }

/* Five boxes */
.fdy-box { background:#fff; border:1px solid #e2e9f3; border-top:4px solid var(--bc); border-radius:14px;
           padding:18px 16px; text-align:center; height:100%; }
.fdy-box .ic { width:54px; height:54px; border-radius:50%; background:var(--bt); display:flex;
               align-items:center; justify-content:center; margin:0 auto 12px; }
.fdy-box h3 { margin:.2rem 0; font-size:1.25rem; }
.fdy-box .mean { color:#3c4b60; font-size:.84rem; min-height:34px; }
.fdy-box .ex { color:#7a899c; font-size:.76rem; margin-top:8px; }
.fdy-box .cnt { font-size:2rem; font-weight:800; color:var(--bc); margin-top:6px; }

/* Role ladder */
.fdy-role { display:flex; align-items:center; gap:16px; background:#fff; border:1px solid #e9eef6;
            border-radius:12px; padding:12px 16px; margin-bottom:10px; }
.fdy-lvl { width:34px; height:34px; border-radius:50%; background:#2563c9; color:#fff; font-weight:800;
           display:flex; align-items:center; justify-content:center; flex:none; }
.fdy-role .nm { font-weight:700; color:#0f2a4d; min-width:190px; }
.fdy-zone { background:#eef5fd; border:1px solid #d9e7f8; border-radius:8px; padding:6px 14px; text-align:center; min-width:150px; }
.fdy-zone .z1 { color:#7a899c; font-size:.66rem; text-transform:uppercase; letter-spacing:.04em; }
.fdy-zone .z2 { color:#2563c9; font-weight:800; }
.fdy-role .resp { color:#5b6b7f; font-size:.9rem; }

/* Stream flow */
.fdy-stream { background:var(--sb); border:1px solid var(--sbd); border-radius:14px; padding:14px;
              margin-bottom:16px; display:flex; align-items:center; gap:6px; overflow-x:auto; }
.fdy-stream .slab { font-weight:800; color:var(--sc); min-width:120px; line-height:1.15; }
.fdy-node { background:#fff; border:1px solid #e2e9f3; border-left:3px solid var(--nc); border-radius:10px;
            padding:10px 12px; min-width:150px; }
.fdy-node .tag { background:#eef5fd; color:#4a6391; font-family:ui-monospace,monospace; font-size:.6rem;
                 padding:2px 6px; border-radius:5px; text-transform:uppercase; }
.fdy-node .nt { font-weight:700; color:#0f2a4d; font-size:.9rem; margin-top:6px; }
.fdy-node .ns { color:#7a899c; font-size:.74rem; }
.fdy-flowarrow { font-size:1.2rem; flex:none; }

/* Bottleneck cards */
.fdy-bn { background:#fff; border:1px solid #e9eef6; border-left:5px solid var(--bnc); border-radius:12px; padding:16px; }
.fdy-bn .top { display:flex; align-items:center; justify-content:space-between; }
.fdy-bn .dot { width:22px; height:22px; border-radius:50%; background:var(--bnc); color:#fff;
               display:inline-flex; align-items:center; justify-content:center; font-size:.7rem; }
.fdy-bn h4 { margin:10px 0 4px; font-size:1.05rem; }
.fdy-bn .meta { color:#5b6b7f; font-size:.82rem; }
.fdy-agewrap { height:8px; background:#eef2f7; border-radius:5px; margin:10px 0 6px; overflow:hidden; }
.fdy-agebar { height:8px; border-radius:5px; background:linear-gradient(90deg,#f1a73b,var(--bnc)); }

/* Coverage grid */
.fdy-cov { display:flex; flex-direction:column; gap:6px; margin:8px 0 4px; }
.fdy-covrow { display:flex; gap:6px; align-items:stretch; }
.fdy-covlabel { width:96px; flex:none; font-weight:800; color:#0f2a4d; display:flex; align-items:center; font-size:.85rem; }
.fdy-covhead { flex:1; text-align:center; font-weight:700; color:#5b6b7f; font-size:.66rem; text-transform:uppercase; letter-spacing:.03em; }
.fdy-covcell { flex:1; min-height:60px; border:1px solid; border-radius:9px; padding:7px 6px; text-align:center;
               display:flex; flex-direction:column; justify-content:center; }
.fdy-covcell .n { font-weight:800; font-size:1.15rem; }
.fdy-covcell .own { color:#5b6b7f; font-size:.6rem; margin-top:3px; line-height:1.15; }
.cov-flag { font-family:ui-monospace,monospace; font-size:.62rem; }

/* Object detail panel */
.fdy-det { background:#fff; border:1px solid #e2e9f3; border-radius:14px; padding:18px; }
.fdy-det h2 { margin:.15rem 0 .3rem; font-size:1.4rem; }
.fdy-detgrid { display:grid; grid-template-columns:1fr 1fr; gap:8px; margin:8px 0; }
.fdy-detbox { background:#f6f8fb; border:1px solid #eef2f7; border-radius:9px; padding:7px 10px; }
.fdy-detbox .k { color:#7a899c; font-size:.6rem; text-transform:uppercase; letter-spacing:.03em; }
.fdy-detbox .v { color:#0f2a4d; font-weight:700; font-size:.88rem; }
.fdy-detsec { font-weight:800; color:#0f2a4d; margin:15px 0 6px; font-size:.78rem;
              text-transform:uppercase; letter-spacing:.04em; }
.fdy-detrow { display:flex; justify-content:space-between; gap:12px; padding:6px 0;
              border-bottom:1px solid #f0f3f8; font-size:.84rem; }
.fdy-detrow .lbl { color:#7a899c; flex:none; }
.fdy-detrow .val { color:#0f2a4d; text-align:right; }

/* Flow view */
.fdy-flegend { display:inline-flex; flex-wrap:wrap; gap:22px; background:#f6f8fb; border:1px solid #eef2f7;
               border-radius:12px; padding:11px 18px; margin:4px 0 14px; font-size:.76rem; color:#5b6b7f; }
.fdy-flegend b { color:#0f2a4d; }
.fdy-flabel { font-size:.66rem; font-weight:800; color:#5b6b7f; letter-spacing:.06em; margin:12px 0 4px; }
.fdy-flow { display:flex; align-items:stretch; gap:1px; overflow-x:auto; padding:4px 2px 10px; }
.fdy-fcard { background:#fff; border:1px solid #e2e9f3; border-top:3px solid var(--sc); border-radius:10px;
             padding:10px 12px; min-width:172px; flex:none; }
.fdy-fcard.blocked { border:1px solid #e5484d; box-shadow:0 0 0 2px #fde8e8; }
.fc-top { display:flex; justify-content:space-between; align-items:center; gap:8px; }
.fc-type { font-weight:800; color:#0f2a4d; font-size:.86rem; }
.fc-title { color:#5b6b7f; font-size:.76rem; margin:2px 0 6px; }
.fc-rows > div { display:flex; justify-content:space-between; padding:2px 0; font-size:.72rem; color:#7a899c; }
.fc-edge { display:flex; align-items:center; padding:0 3px; font-size:1.2rem; flex:none; }
</style>
        """,
        unsafe_allow_html=True,
    )


def section_header(title: str, subtitle: str = "") -> None:
    st.markdown(
        f'<div class="fdy-head"><h2>{_e(title)}</h2>'
        f'{f"<p>{_e(subtitle)}</p>" if subtitle else ""}</div>',
        unsafe_allow_html=True,
    )


def badge(text: str, color: str, bg: str) -> str:
    return f'<span class="fdy-badge" style="color:{color};background:{bg}">{_e(text)}</span>'


# --- The spine ----------------------------------------------------------------
def spine(metrics: list[tuple[str, str, str]]) -> None:
    """metrics: list of (label, sub, badge_html) for the six steps."""
    steps = [
        ("inbox", "Inputs", "Email, PDF, Excel, chat, form, API"),
        ("funnel", "Triage", "What is it? What does it affect? How sure?"),
        ("boxes", "Five Boxes", "Create, Modify, Plan, Control, Reference"),
        ("search", "Impact", "Changes, risks, downstream effects"),
        ("nodes", "Approval", "Route by confidence, risk, ownership"),
        ("database", "Commit", "Write to system of record + audit"),
    ]
    parts = ['<div class="fdy-spine">']
    for i, (icon, label, sub) in enumerate(steps):
        extra = metrics[i] if i < len(metrics) else ""
        parts.append(
            f'<div class="fdy-step"><div class="fdy-circle">{_svg(icon, BLUE)}</div>'
            f'<div class="fdy-pill">{label}</div><small>{sub}</small>'
            f'<div style="margin-top:8px">{extra}</div></div>'
        )
        if i < len(steps) - 1:
            parts.append('<div class="fdy-arrow">→</div>')
    parts.append('</div>')
    st.markdown("".join(parts), unsafe_allow_html=True)


# --- Five boxes ---------------------------------------------------------------
def five_boxes(boxes: dict[str, Any], objects: list[dict[str, Any]]) -> None:
    cols = st.columns(5)
    for col, box in zip(cols, boxes["boxes"]):
        bid = box["id"]
        n = sum(1 for o in objects if o["box"] == bid)
        bc, bt = BOX_COLOR[bid], BOX_TINT[bid]
        tag = "TOUCHES LIVE TRUTH" if box.get("touches_live_truth") else "NO LIVE CHANGE"
        tagbg = "#fdeede" if box.get("touches_live_truth") else "#eef2f7"
        tagcol = ORANGE if box.get("touches_live_truth") else MUTED
        with col:
            st.markdown(
                f'<div class="fdy-box" style="--bc:{bc};--bt:{bt}">'
                f'<div class="ic">{_svg(bid, bc, 24)}</div>'
                f'<h3>{_e(box["name"])}</h3>'
                f'<div class="mean">{_e(box["meaning"])}</div>'
                f'<div class="ex"><b style="color:{BLUE}">Examples:</b> {_e(", ".join(box["examples"]))}</div>'
                f'<div class="cnt">{n}</div>'
                f'<div style="color:#7a899c;font-size:.7rem;margin-bottom:8px">in flight</div>'
                f'{badge(tag, tagcol, tagbg)}</div>',
                unsafe_allow_html=True,
            )


# --- Role ladder --------------------------------------------------------------
def role_ladder(roles: dict[str, Any]) -> None:
    for r in sorted(roles["roles"], key=lambda r: -r["level"]):
        st.markdown(
            f'<div class="fdy-role"><div class="fdy-lvl">{r["level"]}</div>'
            f'<div class="nm">{_e(r["role"])}</div>'
            f'<div class="fdy-zone"><div class="z1">Dominant zone</div>'
            f'<div class="z2">{_e(r["dominant_box"].replace("_", " ").title())}</div></div>'
            f'<div class="resp">{_e(r["responsibility"])}</div></div>',
            unsafe_allow_html=True,
        )


# --- Object detail panel ---
_COMMIT_TINT = {"proposal": ("#fdeede", ORANGE), "workflow": ("#eef5fd", BLUE),
                "truth": ("#e8f7ee", GREEN)}


def object_detail(obj: dict[str, Any], obj_by_id: dict[str, dict[str, Any]]) -> None:
    """The cockpit detail panel for one object — its mapping, state, and connections."""
    box = obj["box"]
    bc = BOX_COLOR.get(box, NAVY)
    sc = STATE_COLOR.get(obj["state"], MUTED)
    cbg, cfg = _COMMIT_TINT.get(obj["commitment"], ("#eef2f7", MUTED))

    outs = [obj_by_id[d]["title"] for d in obj.get("downstream", []) if d in obj_by_id]
    ins = obj.get("evidence", [])
    sor_ref = obj.get("system_of_record_ref")
    path = (f"Locked as truth in SAP ({sor_ref})." if sor_ref
            else "Will lock as truth in SAP once committed.")

    def row(lbl, val):
        return f'<div class="fdy-detrow"><span class="lbl">{_e(lbl)}</span><span class="val">{val}</span></div>'

    def cell(k, v):
        return f'<div class="fdy-detbox"><div class="k">{_e(k)}</div><div class="v">{_e(v)}</div></div>'

    h = ['<div class="fdy-det">']
    h.append(
        f'<div style="display:flex;justify-content:space-between;align-items:center">'
        f'{badge(obj["object_type"], MUTED, "#eef2f7")}'
        f'{badge(obj["commitment"], cfg, cbg)}</div>'
    )
    h.append(f'<h2>{_e(obj["title"])}</h2>')
    h.append(
        f'<div style="margin-bottom:4px"><span style="color:{sc};font-weight:700">'
        f'{_e(STATE_LABEL.get(obj["state"], obj["state"]))}</span> · '
        f'Owner <b>{_e(obj["owner_team"])}</b> · <span class="fdy-id">{_e(obj["object_id"])}</span></div>'
    )
    h.append('<div class="fdy-detsec">Ontology mapping</div>')
    h.append(
        f'<div class="fdy-detbox">User sees <b>{_e(obj["object_type"])}</b> &nbsp;→&nbsp; '
        f'system sees box {badge(box, bc, "#eef2f7")}</div>'
    )
    h.append('<div class="fdy-detsec">Operational state</div><div class="fdy-detgrid">')
    h.append(cell("Stream", obj["stream"]))
    h.append(cell("World", obj["world"]))
    h.append(cell("Created", obj.get("created_at", "—")))
    h.append(cell("Last update", obj.get("updated_at", "—")))
    h.append(cell("Time in stage", f'{obj.get("aging_days", 0)} days'))
    h.append(cell("Confidence", obj.get("confidence", "—")))
    h.append(cell("Approver", obj.get("approver_role") or "—"))
    h.append(cell("Commitment", obj["commitment"]))
    h.append('</div>')
    h.append('<div class="fdy-detsec">Inputs &amp; outputs</div>')
    h.append(row("Inputs (evidence)", _e(", ".join(ins)) if ins else "—"))
    h.append(row("Outputs (downstream)", _e(", ".join(outs)) if outs else "<i>Unreached</i>"))
    h.append('<div class="fdy-detsec">Lifecycle &amp; afterlife</div>')
    h.append(
        f'<div class="fdy-detbox">Path: {_e(path)}<br>'
        f'Lifecycle: <b>{_e(obj.get("lifecycle", "none"))}</b></div>'
    )
    h.append('</div>')
    st.markdown("".join(h), unsafe_allow_html=True)


# --- Coverage grid ---
_COV_COLOR = {"green": ("#e8f7ee", GREEN), "amber": ("#fdeede", ORANGE),
              "red": ("#fde8e8", RED), "empty": ("#f6f8fb", "#dbe3ee")}


def coverage_grid(coverage: dict[str, Any]) -> None:
    boxes = coverage["boxes"]
    cells = {(c["stream"], c["box"]): c for c in coverage["matrix"]}
    h = ['<div class="fdy-cov">', '<div class="fdy-covrow"><div class="fdy-covlabel"></div>']
    for b in boxes:
        h.append(f'<div class="fdy-covhead">{_e(b)}</div>')
    h.append('</div>')
    for s in coverage["streams"]:
        h.append(f'<div class="fdy-covrow"><div class="fdy-covlabel">{_e(s)}</div>')
        for b in boxes:
            c = cells[(s, b)]
            bg, fg = _COV_COLOR[c["status"]]
            if c["status"] == "empty":
                inner = '<div style="color:#cbd5e1">—</div>'
            else:
                flag = (f' <span class="cov-flag" style="color:{fg}">!{c["mismatch_count"]}</span>'
                        if c["mismatch_count"] else '')
                inner = (f'<div class="n" style="color:{fg}">{c["count"]}{flag}</div>'
                         f'<div class="own">{_e(", ".join(c["owners"]))[:24]}</div>')
            h.append(f'<div class="fdy-covcell" style="background:{bg};border-color:{fg}">{inner}</div>')
        h.append('</div>')
    h.append('</div>')
    st.markdown("".join(h), unsafe_allow_html=True)


def coverage_functions(by_function: list[dict[str, Any]]) -> None:
    """How each function covers the boxes it owns."""
    for f in by_function:
        col = RED if f["mismatches"] else GREEN
        flag = (f'<span style="color:{RED};font-weight:700">⚠ {f["mismatches"]} mismatch</span>'
                if f["mismatches"] else f'<span style="color:{GREEN}">✓ clean</span>')
        chips = " ".join(
            f'<span class="fdy-badge" style="color:{BOX_COLOR.get(b, NAVY)};background:#eef2f7">{_e(b)}</span>'
            for b in f["boxes"])
        st.markdown(
            f'<div class="fdy-role" style="border-left:4px solid {col}">'
            f'<div class="nm">{_e(f["owner_team"])}</div>'
            f'<div style="flex:1">{chips}</div>'
            f'<div class="resp">{f["objects"]} objects · {flag}</div></div>',
            unsafe_allow_html=True,
        )


# --- Flow view (the signal / governance map) ---
def flow_legend() -> None:
    st.markdown(
        '<div class="fdy-flegend">'
        f'<span><b>Status:</b></span>'
        f'<span>● <span style="color:{GREEN}">flowing</span></span>'
        f'<span>● <span style="color:{AMBER}">pending</span></span>'
        f'<span>● <span style="color:{RED}">blocked</span></span>'
        f'<span>&nbsp;|&nbsp;<b>Edges:</b></span>'
        f'<span style="color:{GREEN}">⇢ signal</span>'
        f'<span style="color:#94a3b8">→ workflow</span>'
        f'<span style="color:#cbd5e1">→ unreached</span>'
        '</div>',
        unsafe_allow_html=True,
    )


def _edge_type(cur: dict[str, Any], nxt: dict[str, Any]) -> str:
    if cur.get("state") == "blocked" or nxt.get("state") in ("draft", "retired"):
        return "unreached"
    if nxt.get("object_type") == "Signal" or nxt.get("box") == "plan" or cur.get("object_type") == "Signal":
        return "signal"
    return "workflow"


def flow_row(title: str, nodes: list[dict[str, Any]]) -> None:
    """A named flow: rich object cards connected by status-typed edges."""
    edge_col = {"signal": GREEN, "workflow": "#94a3b8", "unreached": "#cbd5e1"}
    edge_glyph = {"signal": "⇢", "workflow": "→", "unreached": "→"}
    h = [f'<div class="fdy-flabel">{_e(title.upper())}</div>', '<div class="fdy-flow">']
    for i, o in enumerate(nodes):
        sc = STATE_COLOR.get(o["state"], MUTED)
        cbg, cfg = _COMMIT_TINT.get(o["commitment"], ("#eef2f7", MUTED))
        blocked = "blocked" if o["state"] == "blocked" else ""
        h.append(
            f'<div class="fdy-fcard {blocked}" style="--sc:{sc}">'
            f'<div class="fc-top"><span class="fc-type">{_e(o["object_type"])}</span>'
            f'{badge(o["commitment"], cfg, cbg)}</div>'
            f'<div class="fc-title">{_e(o["title"][:26])}</div>'
            f'<div class="fc-rows">'
            f'<div><span>Owner</span><b style="color:#0f2a4d">{_e(o["owner_team"])}</b></div>'
            f'<div><span>Status</span><b style="color:{sc}">{_e(STATE_LABEL.get(o["state"], o["state"]))}</b></div>'
            f'<div><span>Box</span>{badge(o["box"], BOX_COLOR.get(o["box"], NAVY), "#eef2f7")}</div>'
            f'</div></div>'
        )
        if i < len(nodes) - 1:
            et = _edge_type(o, nodes[i + 1])
            h.append(f'<span class="fc-edge" style="color:{edge_col[et]}">{edge_glyph[et]}</span>')
    h.append('</div>')
    st.markdown("".join(h), unsafe_allow_html=True)


# --- Bottleneck cards ---------------------------------------------------------
def bottleneck_cards(bottlenecks: list[dict[str, Any]]) -> None:
    cols = st.columns(2)
    for i, b in enumerate(bottlenecks):
        bnc = RED if b["reason"] == "blocked" else AMBER
        label = "BLOCKED" if b["reason"] == "blocked" else "PENDING"
        pct = min(100, b["aging_days"] / 10 * 100)
        with cols[i % 2]:
            st.markdown(
                f'<div class="fdy-bn" style="--bnc:{bnc};margin-bottom:16px">'
                f'<div class="top"><span><span class="dot">!</span> '
                f'<span class="fdy-id">{_e(b["object_id"])}</span></span>'
                f'{badge(label, bnc, "#fde8e8" if b["reason"]=="blocked" else "#fdeede")}</div>'
                f'<h4>{_e(b["title"])}</h4>'
                f'<div class="meta">owner <b>{_e(b["owner_team"])}</b> · state {_e(b["state"])}</div>'
                f'<div style="display:flex;justify-content:space-between;font-size:.75rem;color:#7a899c;margin-top:10px">'
                f'<span>Aging</span><span style="color:{bnc};font-weight:700">{b["aging_days"]} days</span></div>'
                f'<div class="fdy-agewrap"><div class="fdy-agebar" style="width:{pct}%"></div></div>'
                f'<div class="meta">downstream impact: <b>{b["downstream_count"]} object(s)</b></div></div>',
                unsafe_allow_html=True,
            )
