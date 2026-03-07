"""
LLM client for Ollama (local-first inference).
Ported from agent-learning/app/utils/llm_client.py.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import urllib.request
import urllib.error

logger = logging.getLogger(__name__)


class LLMClient:
    """Client for Ollama HTTP API.

    Supports real inference via Ollama and a mock mode for testing.
    Default model: llama3 (fits RTX 4070 12GB VRAM).
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3",
        mock: bool = False,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.mock = mock
        self._mock_responses: list[str] = []

    def set_mock_responses(self, responses: list[str]) -> None:
        """Set canned responses for mock mode."""
        self._mock_responses = list(responses)

    def generate(self, prompt: str, system: str = "", temperature: float = 0.3) -> str:
        """Generate a completion from the LLM."""
        if self.mock:
            return self._mock_generate(prompt)

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if system:
            payload["system"] = system

        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                f"{self.base_url}/api/generate",
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return result.get("response", "")
        except urllib.error.URLError as e:
            logger.error(f"Ollama connection failed: {e}")
            return f"[LLM_ERROR] Connection failed: {e}"
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return f"[LLM_ERROR] {e}"

    def generate_json(
        self, prompt: str, system: str = "", temperature: float = 0.1
    ) -> dict[str, Any]:
        """Generate and parse a JSON response from the LLM."""
        if system:
            system += "\n\nRespond ONLY with valid JSON. No markdown, no explanation."
        else:
            system = "Respond ONLY with valid JSON. No markdown, no explanation."

        raw = self.generate(prompt, system=system, temperature=temperature)

        # Try to extract JSON from the response
        raw = raw.strip()
        if raw.startswith("```"):
            # Strip markdown code fences
            lines = raw.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            raw = "\n".join(lines).strip()

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            # Try to find JSON object in the response
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start >= 0 and end > start:
                try:
                    return json.loads(raw[start:end])
                except json.JSONDecodeError:
                    pass
            logger.warning(f"Failed to parse LLM JSON response: {raw[:200]}")
            return {"error": "json_parse_failed", "raw": raw[:500]}

    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
    ) -> str:
        """Chat completion using Ollama's chat endpoint."""
        if self.mock:
            prompt = messages[-1].get("content", "") if messages else ""
            return self._mock_generate(prompt)

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        }

        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                f"{self.base_url}/api/chat",
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return result.get("message", {}).get("content", "")
        except urllib.error.URLError as e:
            logger.error(f"Ollama chat failed: {e}")
            return f"[LLM_ERROR] Connection failed: {e}"
        except Exception as e:
            logger.error(f"LLM chat failed: {e}")
            return f"[LLM_ERROR] {e}"

    def is_available(self) -> bool:
        """Check if Ollama is reachable."""
        try:
            req = urllib.request.Request(f"{self.base_url}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status == 200
        except Exception:
            return False

    def list_models(self) -> list[str]:
        """List available models on the Ollama server."""
        try:
            req = urllib.request.Request(f"{self.base_url}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return [m.get("name", "") for m in data.get("models", [])]
        except Exception:
            return []

    def _mock_generate(self, prompt: str) -> str:
        if self._mock_responses:
            return self._mock_responses.pop(0)
        return '{"status": "mock_response", "note": "No mock responses configured"}'
