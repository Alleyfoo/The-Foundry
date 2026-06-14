"""
The Spring — Streamlit web frontend.

A thin shell over the existing runtime. It changes NO runtime code: it calls the
same Puhemies orchestrator the Tkinter GUI calls, and re-renders the four maps
(source, views, validation/judge, shadow) for the web.

    streamlit run streamlit_app.py

The pipeline is fully self-contained (standard-library runtime, rule-based judge,
schema-driven transforms). No Ollama or cloud LLM is needed to run it.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from runtime.puhemies import Puhemies

BASE_DIR = Path(__file__).resolve().parent

VIEW_NAMES = ["customer", "sales", "engineer", "management"]
VIEW_BLURB = {
    "customer": "Plain-language specs. No internal codes, no pricing. The map a buyer travels.",
    "sales": "Inventory, lead times, pricing tiers, margin. The map a deal travels.",
    "engineer": "Full precision, standards, tolerances, version history. The map a design travels.",
    "management": "Aggregates, coverage gaps, exception flags. The map a decision travels.",
}


# ----------------------------------------------------------------------
# Pipeline execution (cached per session)
# ----------------------------------------------------------------------
def run_pipeline() -> dict:
    """Run the full Puhemies pipeline and capture handles for rendering."""
    orchestrator = Puhemies(base_dir=str(BASE_DIR))
    ctx = orchestrator.run_pipeline()
    return {
        "run_id": ctx.run_id,
        "status": ctx.status,
        "error": ctx.error,
        "store": orchestrator.store,
        "shadow": orchestrator.shadow,
        "drift_score": orchestrator.shadow.drift_score,
        "metrics": orchestrator.shadow.summary(),
    }


def read_artifact(store, run_id: str, key: str):
    """Read a JSON artifact, returning None instead of raising if absent."""
    try:
        return store.read_json(run_id, key)
    except Exception:
        return None


# ----------------------------------------------------------------------
# Page setup
# ----------------------------------------------------------------------
st.set_page_config(
    page_title="The Spring — Access-First Product Data",
    page_icon="🪤",
    layout="wide",
)

st.title("The Spring")
st.markdown(
    "**An access-first model for product data responsibility.** "
    "Org charts show hierarchy. Access maps show how work actually happens."
)

# Sidebar — run control + the thesis
with st.sidebar:
    st.header("Pipeline")
    st.caption(
        "One source of truth → four maps, each drawn for a different traveller. "
        "The data does not change. The maps do."
    )
    if st.button("▶  Run pipeline", type="primary", use_container_width=True):
        with st.spinner("Running schema → validate → transform → judge …"):
            st.session_state["result"] = run_pipeline()

    st.divider()
    st.markdown(
        "- A title says what someone is **called**.\n"
        "- Access shows what they can **affect**.\n"
        "- Responsibility should be **explicit** wherever access exists.\n\n"
        "Access is a *claim* about responsibility. When the two disagree, the "
        "system should expose the mismatch — it should not paper over it."
    )

result = st.session_state.get("result")

if result is None:
    st.info("Press **▶ Run pipeline** in the sidebar to generate the four maps from the source data.")
    st.stop()

# ----------------------------------------------------------------------
# Run status banner
# ----------------------------------------------------------------------
store = result["store"]
run_id = result["run_id"]

if result["status"] == "completed":
    st.success(f"Pipeline completed · run `{run_id}`")
elif result["status"] == "failed":
    st.error(f"Pipeline failed · {result['error']}")
else:
    st.warning(f"Pipeline status: {result['status']}")

m = result["metrics"]
c1, c2, c3, c4 = st.columns(4)
c1.metric("Drift score", f"{result['drift_score']:.4f}")
c2.metric("Events logged", m.get("total_events", 0))
c3.metric("Errors", m.get("error_count", 0))
c4.metric("Revisions", m.get("revision_count", 0))

# ----------------------------------------------------------------------
# Tabs — the four maps + the model
# ----------------------------------------------------------------------
tab_views, tab_source, tab_valid, tab_shadow, tab_model = st.tabs(
    ["Four Views", "Source & Schema", "Validation & Judge", "Shadow Log", "Access Model"]
)

# --- Four Views ---
with tab_views:
    st.subheader("One source, four maps")
    view_tabs = st.tabs([v.title() for v in VIEW_NAMES])
    for view_name, vt in zip(VIEW_NAMES, view_tabs):
        with vt:
            st.caption(VIEW_BLURB[view_name])
            data = read_artifact(store, run_id, f"view_{view_name}.json")
            report = read_artifact(store, run_id, f"validation_{view_name}.json")
            if report:
                ok = report.get("is_valid", False)
                st.markdown(
                    f"{'✅' if ok else '❌'} "
                    f"{report.get('valid_records', 0)}/{report.get('total_records', 0)} "
                    f"records valid · {report.get('violation_count', 0)} violations"
                )
            if data:
                st.dataframe(pd.DataFrame(data), use_container_width=True, height=420)
            else:
                st.info("No data for this view.")

# --- Source & Schema ---
with tab_source:
    st.subheader("Source of truth")
    products_path = BASE_DIR / "data" / "products.json"
    if products_path.exists():
        raw = json.loads(products_path.read_text(encoding="utf-8"))
        products = raw.get("products", raw) if isinstance(raw, dict) else raw
        st.caption(f"{len(products)} products · the single source the maps are drawn from")
        st.dataframe(pd.DataFrame(products), use_container_width=True, height=360)

    matrix = read_artifact(store, run_id, "field_matrix.json")
    if matrix:
        st.subheader("Field coverage matrix")
        st.caption("Which source field appears in which view — what each traveller is allowed to see.")
        st.dataframe(pd.DataFrame(matrix), use_container_width=True, height=360)

    schema_path = BASE_DIR / "schema" / "source_schema.json"
    if schema_path.exists():
        with st.expander("Source schema (JSON)"):
            st.json(json.loads(schema_path.read_text(encoding="utf-8")))

# --- Validation & Judge ---
with tab_valid:
    st.subheader("Validation")
    rows = []
    for key in store.list_artifacts(run_id):
        if key.startswith("validation_"):
            r = read_artifact(store, run_id, key)
            if r:
                rows.append({
                    "target": key.replace("validation_", "").replace(".json", ""),
                    "total": r.get("total_records", 0),
                    "valid": r.get("valid_records", 0),
                    "violations": r.get("violation_count", 0),
                    "is_valid": r.get("is_valid", False),
                })
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True)

    st.subheader("Judge decisions")
    jrows = []
    for key in store.list_artifacts(run_id):
        if key.startswith("judge_"):
            d = read_artifact(store, run_id, key)
            if d:
                jrows.append({
                    "target": key.replace("judge_", "").replace(".json", ""),
                    "verdict": d.get("verdict", "?"),
                    "confidence": d.get("confidence", 0),
                    "gate_violations": "; ".join(d.get("gate_violations", [])),
                    "suggestions": "; ".join(d.get("suggestions", [])),
                })
    if jrows:
        st.dataframe(pd.DataFrame(jrows), use_container_width=True)

    coverage = read_artifact(store, run_id, "view_coverage.json")
    if coverage:
        with st.expander("View coverage detail"):
            st.json(coverage)

# --- Shadow Log ---
with tab_shadow:
    st.subheader("The invisible eye")
    st.caption("Every event, logged. No opinions, no intervention — the evidence layer.")
    entries = read_artifact(store, run_id, "shadow_summary.json")
    if entries:
        st.json(entries)
    log = store.read_shadow(run_id) if hasattr(store, "read_shadow") else []
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
        st.dataframe(df, use_container_width=True, height=420)

# --- Access Model ---
with tab_model:
    st.subheader("Access maps, not org charts")
    st.markdown(
        "Most systems describe people through job titles. Day-to-day data work "
        "happens through **access**: who can see a field, who can change it, who "
        "approves it, who maintains it, and who is accountable when it is wrong.\n\n"
        "The Spring records **permission** and **responsibility** separately, so "
        "they can be compared. The mismatches it is built to expose:"
    )
    st.table(pd.DataFrame([
        {"Mismatch": "Access without responsibility", "Meaning": "Someone can change it, but no one owns it."},
        {"Mismatch": "Responsibility without access", "Meaning": "Someone is accountable but cannot act."},
        {"Mismatch": "Approval without evidence", "Meaning": "A sign-off with no record behind it."},
        {"Mismatch": "Ownership without visibility", "Meaning": "An owner who cannot see the object's state."},
        {"Mismatch": "Editable field without owner", "Meaning": "Change is possible; ownership is blank."},
        {"Mismatch": "High-risk field without review", "Meaning": "Can cause harm; nothing schedules a look."},
    ]))
    st.caption("Full definitions in docs/access_model.md.")
