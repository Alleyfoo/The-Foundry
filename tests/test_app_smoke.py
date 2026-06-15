"""Smoke test: the Streamlit app renders without raising.

AppTest executes the real render path (a headless boot does not), so this catches
the kind of render-time error a plain import check would miss.
"""

from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "streamlit_app.py")


def test_app_renders_without_error():
    at = AppTest.from_file(APP, default_timeout=120).run()
    assert not at.exception
