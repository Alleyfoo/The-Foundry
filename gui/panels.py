"""
Four-panel GUI builders for The-spring.
Panel layout ported from Agentic-midi-generator/vibechords_studio.py DAW-style pattern.

Panel A (top-left):  Schema & Source — source data, schema overview, field matrix
Panel B (top-right): Views & Transform — 4 view tabs, transform plans
Panel C (bottom-left): Agents & Shadow — agent activity log, shadow metrics, drift
Panel D (bottom-right): Validation & Judge — validation reports, judge decisions
"""

from __future__ import annotations

import json
import tkinter as tk
from tkinter import ttk
from typing import Any

from gui.theme import (
    BG_PANEL, BG_WIDGET, FG, FG_DIM, FG_ACCENT,
    ACCENT_GREEN, ACCENT_RED, ACCENT_ORANGE, ACCENT_TEAL,
    FONT, FONT_BOLD, FONT_SMALL, FONT_MONO, FONT_HEADER,
    CANVAS_BG, BORDER,
)


# ═══════════════════════════════════════════════════════════════════════════
# PANEL A — Schema & Source Data (top-left)
# ═══════════════════════════════════════════════════════════════════════════

def build_panel_a(parent: tk.Widget, on_maximize=None) -> ttk.Frame:
    """Build the Schema & Source Data panel."""
    frame = ttk.Frame(parent, padding=6)

    # Header
    hdr = ttk.Frame(frame)
    hdr.pack(fill=tk.X, pady=(0, 6))
    ttk.Label(hdr, text="Schema & Source Data", style="PanelHeader.TLabel").pack(side=tk.LEFT)
    if on_maximize:
        ttk.Button(hdr, text="\u26f6", style="Max.TButton", command=on_maximize).pack(side=tk.RIGHT)

    # Notebook with tabs
    notebook = ttk.Notebook(frame)
    notebook.pack(fill=tk.BOTH, expand=True)

    # Tab 1: Products table
    products_tab = ttk.Frame(notebook, padding=4)
    notebook.add(products_tab, text="Products")

    # Stats bar
    stats_frame = ttk.Frame(products_tab)
    stats_frame.pack(fill=tk.X, pady=(0, 4))
    frame._stats_label = ttk.Label(stats_frame, text="No data loaded", foreground=FG_DIM, font=FONT_SMALL)
    frame._stats_label.pack(side=tk.LEFT)

    # Products treeview
    columns = ("code", "family", "description", "material", "size", "grade", "price")
    tree = ttk.Treeview(products_tab, columns=columns, show="headings", height=12)
    tree.heading("code", text="Code")
    tree.heading("family", text="Family")
    tree.heading("description", text="Description")
    tree.heading("material", text="Material")
    tree.heading("size", text="Size (mm)")
    tree.heading("grade", text="Grade")
    tree.heading("price", text="Price (EUR)")

    tree.column("code", width=130, minwidth=100)
    tree.column("family", width=120, minwidth=80)
    tree.column("description", width=250, minwidth=150)
    tree.column("material", width=100, minwidth=80)
    tree.column("size", width=80, minwidth=60)
    tree.column("grade", width=60, minwidth=50)
    tree.column("price", width=80, minwidth=60)

    scrollbar = ttk.Scrollbar(products_tab, orient=tk.VERTICAL, command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    frame._products_tree = tree

    # Tab 2: Field Matrix
    matrix_tab = ttk.Frame(notebook, padding=4)
    notebook.add(matrix_tab, text="Field Matrix")

    matrix_cols = ("field", "type", "customer", "sales", "engineer", "management", "views")
    matrix_tree = ttk.Treeview(matrix_tab, columns=matrix_cols, show="headings", height=15)
    matrix_tree.heading("field", text="Field")
    matrix_tree.heading("type", text="Type")
    matrix_tree.heading("customer", text="Customer")
    matrix_tree.heading("sales", text="Sales")
    matrix_tree.heading("engineer", text="Engineer")
    matrix_tree.heading("management", text="Mgmt")
    matrix_tree.heading("views", text="#Views")

    matrix_tree.column("field", width=160, minwidth=120)
    matrix_tree.column("type", width=80, minwidth=60)
    matrix_tree.column("customer", width=70, minwidth=50)
    matrix_tree.column("sales", width=70, minwidth=50)
    matrix_tree.column("engineer", width=70, minwidth=50)
    matrix_tree.column("management", width=70, minwidth=50)
    matrix_tree.column("views", width=50, minwidth=40)

    m_scroll = ttk.Scrollbar(matrix_tab, orient=tk.VERTICAL, command=matrix_tree.yview)
    matrix_tree.configure(yscrollcommand=m_scroll.set)
    matrix_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    m_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    frame._matrix_tree = matrix_tree

    # Tab 3: Source Schema
    schema_tab = ttk.Frame(notebook, padding=4)
    notebook.add(schema_tab, text="Source Schema")

    schema_text = tk.Text(
        schema_tab, wrap=tk.WORD, font=FONT_MONO,
        bg=BG_WIDGET, fg=FG, insertbackground=FG,
        relief="flat", borderwidth=0,
    )
    schema_scroll = ttk.Scrollbar(schema_tab, orient=tk.VERTICAL, command=schema_text.yview)
    schema_text.configure(yscrollcommand=schema_scroll.set)
    schema_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    schema_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    frame._schema_text = schema_text

    return frame


# ═══════════════════════════════════════════════════════════════════════════
# PANEL B — Views & Transform (top-right)
# ═══════════════════════════════════════════════════════════════════════════

def build_panel_b(parent: tk.Widget, on_maximize=None) -> ttk.Frame:
    """Build the Views & Transform panel."""
    frame = ttk.Frame(parent, padding=6)

    # Header
    hdr = ttk.Frame(frame)
    hdr.pack(fill=tk.X, pady=(0, 6))
    ttk.Label(hdr, text="Views & Transform", style="PanelHeader.TLabel").pack(side=tk.LEFT)
    if on_maximize:
        ttk.Button(hdr, text="\u26f6", style="Max.TButton", command=on_maximize).pack(side=tk.RIGHT)

    # Notebook with one tab per view
    notebook = ttk.Notebook(frame)
    notebook.pack(fill=tk.BOTH, expand=True)

    frame._view_trees = {}
    frame._view_stats = {}

    for view_name in ("customer", "sales", "engineer", "management"):
        tab = ttk.Frame(notebook, padding=4)
        notebook.add(tab, text=view_name.title())

        # Stats
        stats = ttk.Label(tab, text="No data", foreground=FG_DIM, font=FONT_SMALL)
        stats.pack(fill=tk.X, pady=(0, 4))
        frame._view_stats[view_name] = stats

        # View treeview — columns will be populated dynamically
        tree = ttk.Treeview(tab, show="headings", height=12)
        v_scroll = ttk.Scrollbar(tab, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=v_scroll.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        frame._view_trees[view_name] = tree

    # Transform plans tab
    plans_tab = ttk.Frame(notebook, padding=4)
    notebook.add(plans_tab, text="Transform Plans")

    plans_text = tk.Text(
        plans_tab, wrap=tk.WORD, font=FONT_MONO,
        bg=BG_WIDGET, fg=FG, insertbackground=FG,
        relief="flat", borderwidth=0,
    )
    plans_scroll = ttk.Scrollbar(plans_tab, orient=tk.VERTICAL, command=plans_text.yview)
    plans_text.configure(yscrollcommand=plans_scroll.set)
    plans_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    plans_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    frame._plans_text = plans_text

    return frame


# ═══════════════════════════════════════════════════════════════════════════
# PANEL C — Agents & Shadow (bottom-left)
# ═══════════════════════════════════════════════════════════════════════════

def build_panel_c(parent: tk.Widget, on_maximize=None) -> ttk.Frame:
    """Build the Agents & Shadow panel."""
    frame = ttk.Frame(parent, padding=6)

    # Header
    hdr = ttk.Frame(frame)
    hdr.pack(fill=tk.X, pady=(0, 6))
    ttk.Label(hdr, text="Agents & Shadow Log", style="PanelHeader.TLabel").pack(side=tk.LEFT)
    if on_maximize:
        ttk.Button(hdr, text="\u26f6", style="Max.TButton", command=on_maximize).pack(side=tk.RIGHT)

    notebook = ttk.Notebook(frame)
    notebook.pack(fill=tk.BOTH, expand=True)

    # Tab 1: Shadow Log
    log_tab = ttk.Frame(notebook, padding=4)
    notebook.add(log_tab, text="Shadow Log")

    log_cols = ("time", "agent", "event", "detail")
    log_tree = ttk.Treeview(log_tab, columns=log_cols, show="headings", height=10)
    log_tree.heading("time", text="Time")
    log_tree.heading("agent", text="Agent")
    log_tree.heading("event", text="Event")
    log_tree.heading("detail", text="Detail")

    log_tree.column("time", width=80, minwidth=70)
    log_tree.column("agent", width=100, minwidth=80)
    log_tree.column("event", width=120, minwidth=80)
    log_tree.column("detail", width=300, minwidth=150)

    l_scroll = ttk.Scrollbar(log_tab, orient=tk.VERTICAL, command=log_tree.yview)
    log_tree.configure(yscrollcommand=l_scroll.set)
    log_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    l_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    frame._log_tree = log_tree

    # Tab 2: Drift Metrics
    drift_tab = ttk.Frame(notebook, padding=4)
    notebook.add(drift_tab, text="Drift Metrics")

    # Drift score canvas
    drift_canvas = tk.Canvas(drift_tab, height=120, bg=CANVAS_BG, highlightthickness=0)
    drift_canvas.pack(fill=tk.BOTH, expand=True, pady=(0, 6))
    frame._drift_canvas = drift_canvas

    # Metrics labels
    metrics_frame = ttk.LabelFrame(drift_tab, text="Current Metrics", padding=6)
    metrics_frame.pack(fill=tk.X)

    frame._metric_labels = {}
    for metric in ("drift_score", "total_events", "error_count",
                    "format_violations", "schema_mismatches", "revision_count"):
        row = ttk.Frame(metrics_frame)
        row.pack(fill=tk.X, pady=1)
        ttk.Label(row, text=f"{metric.replace('_', ' ').title()}:", width=20, font=FONT_BOLD).pack(side=tk.LEFT)
        lbl = ttk.Label(row, text="0", font=FONT_MONO)
        lbl.pack(side=tk.LEFT)
        frame._metric_labels[metric] = lbl

    # Tab 3: Agent Network
    network_tab = ttk.Frame(notebook, padding=4)
    notebook.add(network_tab, text="Agent Network")

    network_text = tk.Text(
        network_tab, wrap=tk.WORD, font=FONT_MONO,
        bg=BG_WIDGET, fg=FG, insertbackground=FG,
        relief="flat", borderwidth=0, height=15,
    )
    network_text.pack(fill=tk.BOTH, expand=True)
    network_text.insert("1.0", _AGENT_NETWORK_DIAGRAM)
    network_text.configure(state=tk.DISABLED)
    frame._network_text = network_text

    return frame


# ═══════════════════════════════════════════════════════════════════════════
# PANEL D — Validation & Judge (bottom-right)
# ═══════════════════════════════════════════════════════════════════════════

def build_panel_d(parent: tk.Widget, on_maximize=None) -> ttk.Frame:
    """Build the Validation & Judge panel."""
    frame = ttk.Frame(parent, padding=6)

    # Header
    hdr = ttk.Frame(frame)
    hdr.pack(fill=tk.X, pady=(0, 6))
    ttk.Label(hdr, text="Validation & Judge", style="PanelHeader.TLabel").pack(side=tk.LEFT)
    if on_maximize:
        ttk.Button(hdr, text="\u26f6", style="Max.TButton", command=on_maximize).pack(side=tk.RIGHT)

    notebook = ttk.Notebook(frame)
    notebook.pack(fill=tk.BOTH, expand=True)

    # Tab 1: Validation Report
    val_tab = ttk.Frame(notebook, padding=4)
    notebook.add(val_tab, text="Validation")

    val_cols = ("source", "records", "valid", "violations", "status")
    val_tree = ttk.Treeview(val_tab, columns=val_cols, show="headings", height=8)
    val_tree.heading("source", text="Source")
    val_tree.heading("records", text="Records")
    val_tree.heading("valid", text="Valid")
    val_tree.heading("violations", text="Violations")
    val_tree.heading("status", text="Status")

    val_tree.column("source", width=130, minwidth=100)
    val_tree.column("records", width=70, minwidth=50)
    val_tree.column("valid", width=70, minwidth=50)
    val_tree.column("violations", width=80, minwidth=60)
    val_tree.column("status", width=80, minwidth=60)

    v_scroll = ttk.Scrollbar(val_tab, orient=tk.VERTICAL, command=val_tree.yview)
    val_tree.configure(yscrollcommand=v_scroll.set)
    val_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    frame._val_tree = val_tree

    # Tab 2: Judge Decisions
    judge_tab = ttk.Frame(notebook, padding=4)
    notebook.add(judge_tab, text="Judge")

    judge_cols = ("target", "verdict", "confidence", "violations", "suggestions")
    judge_tree = ttk.Treeview(judge_tab, columns=judge_cols, show="headings", height=8)
    judge_tree.heading("target", text="Target")
    judge_tree.heading("verdict", text="Verdict")
    judge_tree.heading("confidence", text="Confidence")
    judge_tree.heading("violations", text="Gate Violations")
    judge_tree.heading("suggestions", text="Suggestions")

    judge_tree.column("target", width=120, minwidth=80)
    judge_tree.column("verdict", width=80, minwidth=60)
    judge_tree.column("confidence", width=80, minwidth=60)
    judge_tree.column("violations", width=200, minwidth=100)
    judge_tree.column("suggestions", width=200, minwidth=100)

    j_scroll = ttk.Scrollbar(judge_tab, orient=tk.VERTICAL, command=judge_tree.yview)
    judge_tree.configure(yscrollcommand=j_scroll.set)
    judge_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    j_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    frame._judge_tree = judge_tree

    # Tab 3: Violation Details
    detail_tab = ttk.Frame(notebook, padding=4)
    notebook.add(detail_tab, text="Details")

    detail_text = tk.Text(
        detail_tab, wrap=tk.WORD, font=FONT_MONO,
        bg=BG_WIDGET, fg=FG, insertbackground=FG,
        relief="flat", borderwidth=0,
    )
    d_scroll = ttk.Scrollbar(detail_tab, orient=tk.VERTICAL, command=detail_text.yview)
    detail_text.configure(yscrollcommand=d_scroll.set)
    detail_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    d_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    frame._detail_text = detail_text

    # Tab 4: View Coverage
    coverage_tab = ttk.Frame(notebook, padding=4)
    notebook.add(coverage_tab, text="Coverage")

    coverage_text = tk.Text(
        coverage_tab, wrap=tk.WORD, font=FONT_MONO,
        bg=BG_WIDGET, fg=FG, insertbackground=FG,
        relief="flat", borderwidth=0,
    )
    c_scroll = ttk.Scrollbar(coverage_tab, orient=tk.VERTICAL, command=coverage_text.yview)
    coverage_text.configure(yscrollcommand=c_scroll.set)
    coverage_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    c_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    frame._coverage_text = coverage_text

    return frame


# ---------------------------------------------------------------------------
# Agent network diagram
# ---------------------------------------------------------------------------
_AGENT_NETWORK_DIAGRAM = """\
  THE-SPRING AGENT NETWORK
  ========================

  [User] --> [Puhemies (Orchestrator)]
                    |
        +-----------+-----------+
        |           |           |
  [Schema      [Transform  [Data
   Validator]   Agent]      Janitor]
        |           |           |
        +-----------+-----------+
                    |
              [Judge Agent]
              (healing-by-deepening)
                    |
            +-------+-------+
            |               |
      [ACCEPT]         [REVISE] --> loop back
                            |
                      [ESCALATE] --> human

  [Shadow Agent] ---- observes ALL above ---- [JSONL log]
  [Learning Agent] -- reads shadow, improves over time

  Agents communicate via structured JSON contracts.
  Agents exchange artifact keys, not payloads.
  Shadow never intervenes — pure observer.
"""
