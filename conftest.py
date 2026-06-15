"""Make the repo root importable so tests can `import runtime`, `ui`, etc."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
