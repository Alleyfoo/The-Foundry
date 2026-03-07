"""
Artifact store for managing run artifacts.
Ported from Data-agents-demo/runtime/artifact_store.py — local-first implementation only.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


class ArtifactStore:
    """Local filesystem artifact store.

    Artifacts are stored under: artifacts/<run_id>/<artifact_key>
    Shadow logs are appended to: artifacts/<run_id>/shadow.jsonl
    """

    def __init__(self, base_dir: str = "artifacts"):
        self._base = Path(base_dir)
        self._base.mkdir(parents=True, exist_ok=True)

    def run_dir(self, run_id: str) -> Path:
        d = self._base / run_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def write_json(self, run_id: str, key: str, data: Any) -> str:
        """Write a JSON artifact. Returns the artifact path."""
        path = self.run_dir(run_id) / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        return str(path)

    def read_json(self, run_id: str, key: str) -> Any:
        """Read a JSON artifact."""
        path = self.run_dir(run_id) / key
        if not path.exists():
            raise FileNotFoundError(f"Artifact not found: {path}")
        return json.loads(path.read_text(encoding="utf-8"))

    def write_text(self, run_id: str, key: str, text: str) -> str:
        """Write a text artifact. Returns the artifact path."""
        path = self.run_dir(run_id) / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return str(path)

    def read_text(self, run_id: str, key: str) -> str:
        """Read a text artifact."""
        path = self.run_dir(run_id) / key
        if not path.exists():
            raise FileNotFoundError(f"Artifact not found: {path}")
        return path.read_text(encoding="utf-8")

    def append_shadow(self, run_id: str, entry: dict) -> None:
        """Append a JSONL entry to the shadow log."""
        path = self.run_dir(run_id) / "shadow.jsonl"
        line = json.dumps(entry, default=str) + "\n"
        with open(path, "a", encoding="utf-8") as f:
            f.write(line)

    def read_shadow(self, run_id: str) -> list[dict]:
        """Read all shadow log entries."""
        path = self.run_dir(run_id) / "shadow.jsonl"
        if not path.exists():
            return []
        entries = []
        for line in path.read_text(encoding="utf-8").strip().split("\n"):
            if line.strip():
                entries.append(json.loads(line))
        return entries

    def exists(self, run_id: str, key: str) -> bool:
        return (self.run_dir(run_id) / key).exists()

    def list_artifacts(self, run_id: str) -> list[str]:
        """List all artifact keys in a run."""
        d = self.run_dir(run_id)
        if not d.exists():
            return []
        return [str(p.relative_to(d)) for p in d.rglob("*") if p.is_file()]

    def list_runs(self) -> list[str]:
        """List all run IDs."""
        if not self._base.exists():
            return []
        return sorted(
            [d.name for d in self._base.iterdir() if d.is_dir()],
            reverse=True,
        )

    def artifact_uri(self, run_id: str, key: str) -> str:
        """Generate a URI for an artifact."""
        return f"local://{self._base}/{run_id}/{key}"

    def save_manifest(self, run_id: str) -> str:
        """Save a manifest of all artifacts in a run."""
        artifacts = self.list_artifacts(run_id)
        manifest = {
            "run_id": run_id,
            "timestamp": datetime.utcnow().isoformat(),
            "artifact_count": len(artifacts),
            "artifacts": {
                key: {
                    "uri": self.artifact_uri(run_id, key),
                    "size_bytes": (self.run_dir(run_id) / key).stat().st_size,
                }
                for key in artifacts
            },
        }
        return self.write_json(run_id, "manifest.json", manifest)
