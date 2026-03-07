"""
Dark theme configuration for The-spring GUI.
Ported from Agentic-midi-generator/vibechords_studio.py color palette and configure_dark_theme().
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

# ---------------------------------------------------------------------------
# Color Palette (dark theme)
# ---------------------------------------------------------------------------
BG = "#1e1e1e"
BG_PANEL = "#2b2b2b"
BG_WIDGET = "#333333"
BG_HEADER = "#3c3c3c"
FG = "#e0e0e0"
FG_DIM = "#888888"
FG_ACCENT = "#4a90d9"
FG_ACCENT2 = "#c0c0c0"
BORDER = "#444444"
BTN_BG = "#3a3a3a"
BTN_ACTIVE = "#4a4a4a"
CANVAS_BG = "#222222"

ACCENT_BLUE = "#4a90d9"
ACCENT_GREEN = "#5cb85c"
ACCENT_RED = "#d9534f"
ACCENT_ORANGE = "#f0ad4e"
ACCENT_TEAL = "#5bc0de"
ACCENT_PURPLE = "#9b59b6"

# ---------------------------------------------------------------------------
# Fonts
# ---------------------------------------------------------------------------
FONT = ("Segoe UI", 10)
FONT_BOLD = ("Segoe UI", 10, "bold")
FONT_SMALL = ("Segoe UI", 9)
FONT_HEADER = ("Segoe UI", 11, "bold")
FONT_MONO = ("Consolas", 9)


def configure_dark_theme(root: tk.Tk) -> ttk.Style:
    """Apply dark theme to the entire application."""
    style = ttk.Style(root)
    style.theme_use("clam")

    style.configure(
        ".", background=BG_PANEL, foreground=FG, font=FONT,
        borderwidth=0, focuscolor=FG_ACCENT,
    )
    style.configure("TFrame", background=BG_PANEL)
    style.configure("TLabel", background=BG_PANEL, foreground=FG, font=FONT)
    style.configure(
        "TLabelframe", background=BG_PANEL, foreground=FG_ACCENT,
        font=FONT_BOLD, borderwidth=1, relief="groove",
    )
    style.configure("TLabelframe.Label", background=BG_PANEL, foreground=FG_ACCENT, font=FONT_BOLD)
    style.configure(
        "TButton", background=BTN_BG, foreground=FG, font=FONT,
        padding=(8, 3), borderwidth=1, relief="flat",
    )
    style.map(
        "TButton",
        background=[("active", BTN_ACTIVE), ("pressed", FG_ACCENT)],
        foreground=[("active", FG), ("pressed", "#ffffff")],
    )
    style.configure(
        "Accent.TButton", background=FG_ACCENT, foreground="#ffffff",
        font=FONT_BOLD, padding=(12, 4),
    )
    style.map("Accent.TButton", background=[("active", "#5aa0e9"), ("pressed", "#3a70b9")])
    style.configure(
        "TEntry", fieldbackground=BG_WIDGET, foreground=FG,
        insertcolor=FG, borderwidth=1, relief="solid",
    )
    style.configure(
        "TSpinbox", fieldbackground=BG_WIDGET, foreground=FG,
        arrowcolor=FG, borderwidth=1,
    )
    style.configure(
        "TCombobox", fieldbackground=BG_WIDGET, foreground=FG,
        arrowcolor=FG, borderwidth=1,
    )
    style.map("TCombobox",
              fieldbackground=[("readonly", BG_WIDGET)],
              foreground=[("readonly", FG)])
    style.configure("TCheckbutton", background=BG_PANEL, foreground=FG, font=FONT)
    style.map("TCheckbutton", background=[("active", BG_PANEL)])
    style.configure("TNotebook", background=BG, borderwidth=0)
    style.configure("TNotebook.Tab", background=BTN_BG, foreground=FG, font=FONT, padding=(10, 3))
    style.map("TNotebook.Tab",
              background=[("selected", BG_PANEL)],
              foreground=[("selected", FG_ACCENT)])
    style.configure(
        "Treeview", background=BG_WIDGET, foreground=FG,
        fieldbackground=BG_WIDGET, font=FONT_SMALL, rowheight=22,
    )
    style.configure("Treeview.Heading", background=BG_HEADER, foreground=FG, font=FONT_BOLD)
    style.map("Treeview",
              background=[("selected", FG_ACCENT)],
              foreground=[("selected", "#ffffff")])
    style.configure("TSeparator", background=BORDER)
    style.configure("Toolbar.TFrame", background=BG_HEADER)
    style.configure("Toolbar.TLabel", background=BG_HEADER, foreground=FG, font=FONT)
    style.configure(
        "Toolbar.TButton", background="#4a4a4a", foreground=FG, font=FONT, padding=(8, 3),
    )
    style.map("Toolbar.TButton", background=[("active", "#5a5a5a")])
    style.configure("Status.TFrame", background="#1a1a1a")
    style.configure("Status.TLabel", background="#1a1a1a", foreground=FG_DIM, font=FONT_SMALL)
    style.configure("PanelHeader.TLabel", background=BG_PANEL, foreground=FG_ACCENT, font=FONT_HEADER)
    style.configure(
        "Max.TButton", background=BG_PANEL, foreground=FG_DIM,
        font=("Segoe UI", 12), padding=(2, 0), borderwidth=0, relief="flat",
    )
    style.map("Max.TButton", foreground=[("active", FG_ACCENT)], background=[("active", BG_PANEL)])
    style.configure(
        "Restore.TButton", background=ACCENT_BLUE, foreground="#ffffff",
        font=("Segoe UI", 10, "bold"), padding=(10, 4),
    )
    style.map("Restore.TButton", background=[("active", "#5aa0e9")])
    style.configure("Vertical.TScrollbar", background=BTN_BG, troughcolor=BG_WIDGET, arrowcolor=FG, borderwidth=0)
    style.configure("Horizontal.TScrollbar", background=BTN_BG, troughcolor=BG_WIDGET, arrowcolor=FG, borderwidth=0)

    # Tag styles for treeview
    style.configure("valid.Treeview", foreground=ACCENT_GREEN)
    style.configure("error.Treeview", foreground=ACCENT_RED)
    style.configure("warning.Treeview", foreground=ACCENT_ORANGE)

    root.configure(bg=BG)
    root.option_add("*TCombobox*Listbox.background", BG_WIDGET)
    root.option_add("*TCombobox*Listbox.foreground", FG)
    root.option_add("*TCombobox*Listbox.selectBackground", FG_ACCENT)
    root.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")

    return style
