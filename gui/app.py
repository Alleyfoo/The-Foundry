"""
Main application — DAW-style 4-panel Tkinter GUI.
Layout ported from Agentic-midi-generator/vibechords_studio.py PanedWindow pattern.
"""

from __future__ import annotations

import json
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from typing import Any

from gui.theme import (
    configure_dark_theme, BG, BG_PANEL, FG, FG_DIM, FG_ACCENT,
    ACCENT_GREEN, ACCENT_RED, ACCENT_ORANGE, ACCENT_BLUE, ACCENT_TEAL,
    FONT, FONT_BOLD, FONT_SMALL, FONT_MONO, FONT_HEADER,
    CANVAS_BG, BORDER,
)
from gui.panels import build_panel_a, build_panel_b, build_panel_c, build_panel_d


class App:
    """The-spring main application with DAW-style 4-panel layout.

    Layout:
        ┌────────────────┬────────────────┐
        │  Panel A       │  Panel B       │
        │  Schema &      │  Views &       │
        │  Source Data    │  Transform     │
        ├────────────────┼────────────────┤
        │  Panel C       │  Panel D       │
        │  Agents &      │  Validation &  │
        │  Shadow Log    │  Judge         │
        └────────────────┴────────────────┘
    """

    PANEL_NAMES = {"panel_a", "panel_b", "panel_c", "panel_d"}

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("The-spring \u2014 Schema Map System")
        self.root.minsize(1200, 700)

        self.style = configure_dark_theme(self.root)
        self._maximized_id: str | None = None
        self._pipeline_result = None

        # --- Toolbar ---
        self.toolbar = self._build_toolbar()
        self.toolbar.pack(fill=tk.X)

        # --- Main content: PanedWindow layout ---
        # Vertical split: top half / bottom half
        self.main_pane = ttk.PanedWindow(self.root, orient=tk.VERTICAL)
        self.main_pane.pack(fill=tk.BOTH, expand=True)

        # Top: horizontal split (Panel A | Panel B)
        self.top_pane = ttk.PanedWindow(self.main_pane, orient=tk.HORIZONTAL)
        self.main_pane.add(self.top_pane, weight=1)

        # Bottom: horizontal split (Panel C | Panel D)
        self.bottom_pane = ttk.PanedWindow(self.main_pane, orient=tk.HORIZONTAL)
        self.main_pane.add(self.bottom_pane, weight=1)

        # Build panels
        self.panel_a = build_panel_a(self.top_pane, on_maximize=lambda: self._toggle_maximize("panel_a"))
        self.top_pane.add(self.panel_a, weight=1)

        self.panel_b = build_panel_b(self.top_pane, on_maximize=lambda: self._toggle_maximize("panel_b"))
        self.top_pane.add(self.panel_b, weight=1)

        self.panel_c = build_panel_c(self.bottom_pane, on_maximize=lambda: self._toggle_maximize("panel_c"))
        self.bottom_pane.add(self.panel_c, weight=1)

        self.panel_d = build_panel_d(self.bottom_pane, on_maximize=lambda: self._toggle_maximize("panel_d"))
        self.bottom_pane.add(self.panel_d, weight=1)

        # --- Status bar ---
        self.status_bar = ttk.Frame(self.root, style="Status.TFrame", padding=(10, 3))
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        self.status_label = ttk.Label(self.status_bar, text="Ready", style="Status.TLabel")
        self.status_label.pack(side=tk.LEFT)
        self.drift_label = ttk.Label(self.status_bar, text="Drift: --", style="Status.TLabel")
        self.drift_label.pack(side=tk.RIGHT)
        self.run_label = ttk.Label(self.status_bar, text="Run: --", style="Status.TLabel")
        self.run_label.pack(side=tk.RIGHT, padx=(0, 20))

        # Center/maximize window
        self._center_window()

    def _build_toolbar(self) -> ttk.Frame:
        """Build the top toolbar."""
        toolbar = ttk.Frame(self.root, style="Toolbar.TFrame", padding=(10, 5))

        ttk.Label(toolbar, text="The-spring", font=FONT_HEADER,
                  foreground=FG_ACCENT, background="#3c3c3c").pack(side=tk.LEFT, padx=(0, 20))

        ttk.Button(
            toolbar, text="  RUN PIPELINE  ", style="Accent.TButton",
            command=self._on_run_pipeline,
        ).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(
            toolbar, text="Load Data", style="Toolbar.TButton",
            command=self._on_load_data,
        ).pack(side=tk.LEFT, padx=4)

        ttk.Button(
            toolbar, text="Refresh", style="Toolbar.TButton",
            command=self._on_refresh,
        ).pack(side=tk.LEFT, padx=4)

        ttk.Separator(toolbar, orient="vertical").pack(side=tk.LEFT, fill=tk.Y, padx=8, pady=2)

        # LLM status
        ttk.Label(toolbar, text="LLM:", style="Toolbar.TLabel").pack(side=tk.LEFT)
        self._llm_status = ttk.Label(toolbar, text="not checked", style="Toolbar.TLabel", foreground=FG_DIM)
        self._llm_status.pack(side=tk.LEFT, padx=(4, 12))

        ttk.Button(
            toolbar, text="Check Ollama", style="Toolbar.TButton",
            command=self._check_ollama,
        ).pack(side=tk.LEFT, padx=4)

        return toolbar

    # ------------------------------------------------------------------
    # Panel maximize / restore
    # ------------------------------------------------------------------
    def _toggle_maximize(self, panel_id: str) -> None:
        if self._maximized_id == panel_id:
            self._restore()
        else:
            self._maximize(panel_id)

    def _maximize(self, panel_id: str) -> None:
        """Maximize a single panel to fill the entire content area."""
        self._maximized_id = panel_id
        panels = {
            "panel_a": (self.panel_a, self.top_pane),
            "panel_b": (self.panel_b, self.top_pane),
            "panel_c": (self.panel_c, self.bottom_pane),
            "panel_d": (self.panel_d, self.bottom_pane),
        }

        # Hide all panels except the target
        for pid, (panel, pane) in panels.items():
            if pid != panel_id:
                try:
                    pane.forget(panel)
                except Exception:
                    pass

        # Hide the non-target pane
        target_panel, target_pane = panels[panel_id]
        other_pane = self.bottom_pane if target_pane == self.top_pane else self.top_pane
        try:
            self.main_pane.forget(other_pane)
        except Exception:
            pass

        self._set_status(f"Maximized: {panel_id}")

    def _restore(self) -> None:
        """Restore all panels to the 4-panel layout."""
        self._maximized_id = None

        # Re-add all panes
        try:
            self.main_pane.forget(self.top_pane)
        except Exception:
            pass
        try:
            self.main_pane.forget(self.bottom_pane)
        except Exception:
            pass

        self.main_pane.add(self.top_pane, weight=1)
        self.main_pane.add(self.bottom_pane, weight=1)

        # Re-add all panels
        try:
            self.top_pane.forget(self.panel_a)
        except Exception:
            pass
        try:
            self.top_pane.forget(self.panel_b)
        except Exception:
            pass
        try:
            self.bottom_pane.forget(self.panel_c)
        except Exception:
            pass
        try:
            self.bottom_pane.forget(self.panel_d)
        except Exception:
            pass

        self.top_pane.add(self.panel_a, weight=1)
        self.top_pane.add(self.panel_b, weight=1)
        self.bottom_pane.add(self.panel_c, weight=1)
        self.bottom_pane.add(self.panel_d, weight=1)

        self._set_status("Layout restored")

    # ------------------------------------------------------------------
    # Toolbar actions
    # ------------------------------------------------------------------
    def _on_load_data(self) -> None:
        """Load source data and schemas into the GUI."""
        self._set_status("Loading data...")
        try:
            self._load_source_data()
            self._load_field_matrix()
            self._load_source_schema()
            self._set_status("Data loaded successfully")
        except Exception as e:
            self._flash_status(f"Load failed: {e}", ACCENT_RED)

    def _on_refresh(self) -> None:
        """Refresh all panels from the latest pipeline run."""
        self._on_load_data()
        if self._pipeline_result:
            self._populate_results(self._pipeline_result)

    def _on_run_pipeline(self) -> None:
        """Run the full pipeline in a background thread."""
        self._set_status("Running pipeline...")
        self.root.update_idletasks()

        def _run():
            try:
                from runtime.puhemies import Puhemies
                orchestrator = Puhemies(base_dir=".")
                ctx = orchestrator.run_pipeline()
                self._pipeline_result = {
                    "ctx": ctx,
                    "shadow": orchestrator.shadow,
                    "store": orchestrator.store,
                }
                self.root.after(0, lambda: self._on_pipeline_complete(ctx, orchestrator))
            except Exception as e:
                self.root.after(0, lambda: self._flash_status(f"Pipeline error: {e}", ACCENT_RED))

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()

    def _on_pipeline_complete(self, ctx, orchestrator) -> None:
        """Update GUI after pipeline completes (called on main thread)."""
        self._on_load_data()

        result = {
            "ctx": ctx,
            "shadow": orchestrator.shadow,
            "store": orchestrator.store,
        }
        self._populate_results(result)

        if ctx.status == "completed":
            self._flash_status(f"Pipeline completed: {ctx.run_id}", ACCENT_GREEN)
        else:
            self._flash_status(f"Pipeline {ctx.status}: {ctx.error}", ACCENT_RED)

        self.run_label.config(text=f"Run: {ctx.run_id}")
        self.drift_label.config(text=f"Drift: {orchestrator.shadow.drift_score:.4f}")

    def _populate_results(self, result: dict) -> None:
        """Populate all panels with pipeline results."""
        ctx = result["ctx"]
        shadow = result["shadow"]
        store = result["store"]

        # Panel C: Shadow log
        self._populate_shadow_log(shadow)
        self._populate_drift_metrics(shadow)

        # Panel D: Validation & Judge
        self._populate_validation(ctx, store)
        self._populate_judge(ctx, store)
        self._populate_coverage(ctx, store)

        # Panel B: View data
        self._populate_view_data(ctx, store)
        self._populate_transform_plans(ctx, store)

    def _check_ollama(self) -> None:
        """Check if Ollama is available."""
        from runtime.llm_client import LLMClient
        client = LLMClient()
        if client.is_available():
            models = client.list_models()
            self._llm_status.config(text=f"OK ({len(models)} models)", foreground=ACCENT_GREEN)
        else:
            self._llm_status.config(text="not available", foreground=ACCENT_RED)

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------
    def _load_source_data(self) -> None:
        """Load products into Panel A tree."""
        data_path = Path("data/products.json")
        if not data_path.exists():
            return

        data = json.loads(data_path.read_text(encoding="utf-8"))
        products = data.get("products", []) if isinstance(data, dict) else data

        tree = self.panel_a._products_tree
        for item in tree.get_children():
            tree.delete(item)

        for p in products:
            size = f"{p.get('diameter_mm', '')}\u00d7{p.get('length_mm', '')}"
            tree.insert("", tk.END, values=(
                p.get("product_code", ""),
                p.get("product_family", ""),
                p.get("description", ""),
                p.get("material", ""),
                size,
                p.get("grade", ""),
                f"{p.get('unit_price_eur', 0):.2f}",
            ))

        self.panel_a._stats_label.config(
            text=f"{len(products)} products loaded from {data_path}",
            foreground=ACCENT_GREEN,
        )

    def _load_field_matrix(self) -> None:
        """Load field matrix into Panel A."""
        from runtime.transform import compute_field_matrix, load_view_schemas
        from runtime.schema_validator import load_schema

        try:
            source_schema = load_schema("schema/source_schema.json")
            view_schemas = load_view_schemas("schema/views")
            matrix = compute_field_matrix(source_schema, view_schemas)
        except Exception:
            return

        tree = self.panel_a._matrix_tree
        for item in tree.get_children():
            tree.delete(item)

        for row in matrix:
            tree.insert("", tk.END, values=(
                row["field"],
                row["type"] if isinstance(row["type"], str) else str(row["type"]),
                "\u2713" if row.get("in_customer", False) else "",
                "\u2713" if row.get("in_sales", False) else "",
                "\u2713" if row.get("in_engineer", False) else "",
                "\u2713" if row.get("in_management", False) else "",
                row.get("view_count", 0),
            ))

    def _load_source_schema(self) -> None:
        """Load source schema into Panel A."""
        schema_path = Path("schema/source_schema.json")
        if not schema_path.exists():
            return

        text_widget = self.panel_a._schema_text
        text_widget.configure(state=tk.NORMAL)
        text_widget.delete("1.0", tk.END)
        text_widget.insert("1.0", schema_path.read_text(encoding="utf-8"))
        text_widget.configure(state=tk.DISABLED)

    # ------------------------------------------------------------------
    # Results population
    # ------------------------------------------------------------------
    def _populate_shadow_log(self, shadow) -> None:
        """Populate Panel C shadow log."""
        tree = self.panel_c._log_tree
        for item in tree.get_children():
            tree.delete(item)

        for entry in shadow.entries:
            time_str = entry.timestamp.split("T")[-1][:8] if "T" in entry.timestamp else entry.timestamp
            detail_str = json.dumps(entry.detail, default=str)[:200] if entry.detail else ""
            tree.insert("", tk.END, values=(
                time_str, entry.agent_name, entry.event_type, detail_str
            ))

    def _populate_drift_metrics(self, shadow) -> None:
        """Populate Panel C drift metrics."""
        metrics = shadow.metrics
        labels = self.panel_c._metric_labels

        labels["drift_score"].config(
            text=f"{metrics.drift_score:.4f}",
            foreground=ACCENT_GREEN if metrics.drift_score < 0.3 else
                       ACCENT_ORANGE if metrics.drift_score < 0.6 else ACCENT_RED,
        )
        labels["total_events"].config(text=str(metrics.total_events))
        labels["error_count"].config(
            text=str(metrics.error_count),
            foreground=ACCENT_RED if metrics.error_count > 0 else FG,
        )
        labels["format_violations"].config(text=str(metrics.format_violations))
        labels["schema_mismatches"].config(text=str(metrics.schema_mismatches))
        labels["revision_count"].config(text=str(metrics.revision_count))

        # Draw drift gauge on canvas
        canvas = self.panel_c._drift_canvas
        canvas.delete("all")
        w = canvas.winfo_width() or 400
        h = canvas.winfo_height() or 120

        # Background bar
        bar_y = h // 2
        bar_h = 20
        canvas.create_rectangle(20, bar_y - bar_h, w - 20, bar_y + bar_h,
                                fill="#2a2a2a", outline=BORDER)

        # Drift fill
        score = metrics.drift_score
        fill_w = int((w - 40) * score)
        color = ACCENT_GREEN if score < 0.3 else ACCENT_ORANGE if score < 0.6 else ACCENT_RED
        if fill_w > 0:
            canvas.create_rectangle(20, bar_y - bar_h, 20 + fill_w, bar_y + bar_h,
                                    fill=color, outline="")

        # Labels
        canvas.create_text(w // 2, bar_y - bar_h - 15,
                          text=f"Drift Score: {score:.4f}", fill=FG, font=FONT_BOLD)
        canvas.create_text(25, bar_y + bar_h + 15,
                          text="0.0", fill=FG_DIM, font=FONT_SMALL, anchor="w")
        canvas.create_text(w - 25, bar_y + bar_h + 15,
                          text="1.0", fill=FG_DIM, font=FONT_SMALL, anchor="e")

    def _populate_validation(self, ctx, store) -> None:
        """Populate Panel D validation results."""
        tree = self.panel_d._val_tree
        for item in tree.get_children():
            tree.delete(item)

        detail_text = self.panel_d._detail_text
        detail_text.configure(state=tk.NORMAL)
        detail_text.delete("1.0", tk.END)

        for artifact_key in store.list_artifacts(ctx.run_id):
            if not artifact_key.startswith("validation_"):
                continue
            try:
                report = store.read_json(ctx.run_id, artifact_key)
                source = artifact_key.replace("validation_", "").replace(".json", "")
                status = "\u2713 Valid" if report.get("is_valid", True) else "\u2717 Invalid"
                tree.insert("", tk.END, values=(
                    source,
                    report.get("total_records", 0),
                    report.get("valid_records", 0),
                    report.get("violation_count", 0),
                    status,
                ))

                # Add violations to detail text
                violations = report.get("violations", [])
                if violations:
                    detail_text.insert(tk.END, f"\n--- {source} ---\n")
                    for v in violations[:10]:
                        detail_text.insert(tk.END,
                            f"  [{v.get('severity', 'error')}] {v.get('field', '?')}: "
                            f"{v.get('message', '?')} (record: {v.get('product_code', '?')})\n"
                        )
            except Exception:
                pass

        detail_text.configure(state=tk.DISABLED)

    def _populate_judge(self, ctx, store) -> None:
        """Populate Panel D judge decisions."""
        tree = self.panel_d._judge_tree
        for item in tree.get_children():
            tree.delete(item)

        for artifact_key in store.list_artifacts(ctx.run_id):
            if not artifact_key.startswith("judge_"):
                continue
            try:
                decision = store.read_json(ctx.run_id, artifact_key)
                target = artifact_key.replace("judge_", "").replace(".json", "")
                tree.insert("", tk.END, values=(
                    target,
                    decision.get("verdict", "?"),
                    f"{decision.get('confidence', 0):.0%}",
                    "; ".join(decision.get("gate_violations", []))[:100],
                    "; ".join(decision.get("suggestions", []))[:100],
                ))
            except Exception:
                pass

    def _populate_coverage(self, ctx, store) -> None:
        """Populate Panel D view coverage."""
        text_widget = self.panel_d._coverage_text
        text_widget.configure(state=tk.NORMAL)
        text_widget.delete("1.0", tk.END)

        try:
            coverage = store.read_json(ctx.run_id, "view_coverage.json")
            text_widget.insert(tk.END, json.dumps(coverage, indent=2))
        except Exception:
            text_widget.insert(tk.END, "No coverage data available")

        text_widget.configure(state=tk.DISABLED)

    def _populate_view_data(self, ctx, store) -> None:
        """Populate Panel B view tabs with actual data."""
        for view_name, tree in self.panel_b._view_trees.items():
            # Clear existing
            for item in tree.get_children():
                tree.delete(item)
            tree["columns"] = ()

            try:
                view_data = store.read_json(ctx.run_id, f"view_{view_name}.json")
                if not view_data:
                    continue

                # Set up columns from first record
                cols = list(view_data[0].keys())[:10]  # Limit columns for readability
                tree["columns"] = cols
                for col in cols:
                    tree.heading(col, text=col.replace("_", " ").title())
                    tree.column(col, width=100, minwidth=60)

                # Insert rows
                for record in view_data:
                    values = []
                    for col in cols:
                        v = record.get(col, "")
                        if isinstance(v, list):
                            v = ", ".join(str(x) for x in v)
                        values.append(str(v)[:50])
                    tree.insert("", tk.END, values=values)

                stats = self.panel_b._view_stats.get(view_name)
                if stats:
                    stats.config(
                        text=f"{len(view_data)} records, {len(cols)} fields",
                        foreground=ACCENT_GREEN,
                    )
            except Exception:
                pass

    def _populate_transform_plans(self, ctx, store) -> None:
        """Populate Panel B transform plans tab."""
        text_widget = self.panel_b._plans_text
        text_widget.configure(state=tk.NORMAL)
        text_widget.delete("1.0", tk.END)

        try:
            plans = store.read_json(ctx.run_id, "transform_plans.json")
            text_widget.insert(tk.END, json.dumps(plans, indent=2))
        except Exception:
            text_widget.insert(tk.END, "No transform plans available (run pipeline first)")

        text_widget.configure(state=tk.DISABLED)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _set_status(self, text: str) -> None:
        self.status_label.config(text=text, foreground=FG_DIM)

    def _flash_status(self, text: str, color: str = FG_ACCENT) -> None:
        self.status_label.config(text=text, foreground=color)
        self.root.after(5000, lambda: self.status_label.config(foreground=FG_DIM))

    def _center_window(self) -> None:
        self.root.update_idletasks()
        try:
            self.root.state("zoomed")
        except tk.TclError:
            screen_w = self.root.winfo_screenwidth()
            screen_h = self.root.winfo_screenheight()
            self.root.geometry(f"{screen_w}x{screen_h}+0+0")

    def run(self) -> None:
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        # Auto-load data on startup
        self.root.after(100, self._on_load_data)
        self.root.mainloop()

    def _on_close(self) -> None:
        self.root.destroy()
