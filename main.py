"""
The-spring — Schema Map System
Entry point for the Tkinter GUI application.
"""

import sys
import traceback
import tkinter as tk
from tkinter import messagebox


def main():
    """Launch The-spring with top-level error handling."""
    try:
        from gui.app import App
        App().run()
    except Exception:
        err = traceback.format_exc()
        print(err, file=sys.stderr)
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(
                "The-spring — Startup Error",
                f"An unexpected error occurred:\n\n{err[-800:]}",
            )
            root.destroy()
        except Exception:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()
