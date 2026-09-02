from abc import ABC, abstractmethod
import json
import logging
from typing import Optional
import urllib.request
import urllib.error

from app.config import settings

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """Abstract interface for pluggable LLM explanation providers."""

    @abstractmethod
    def generate(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        """Generate response text given prompt and system instruction."""
        pass


class DeterministicFallbackProvider(LLMProvider):
    """Zero-dependency deterministic provider used as reliable default and fallback."""

    def generate(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        # Returns empty to trigger deterministic template generation in explanation_agent
        return ""


class GeminiRESTProvider(LLMProvider):
    """Direct REST integration for Gemini models without extra heavy dependencies."""

    def __init__(self, api_key: str, model: str = "gemini-1.5-flash") -> None:
        self.api_key = api_key.strip()
        self.model = model.strip()

    def generate(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        if not self.api_key:
            return ""

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}

        payload = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json",
            },
        }

        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        try:
            req_data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=req_data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=10) as response:
                resp_json = json.loads(response.read().decode("utf-8"))
                candidates = resp_json.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        return parts[0].get("text", "")
        except Exception as e:
            logger.warning("Gemini REST LLM generation failed or timed out: %s. Falling back to deterministic mode.", type(e).__name__)

        return ""


def get_llm_provider() -> LLMProvider:
    """Factory to retrieve the configured LLM provider."""
    provider_name = settings.LLM_PROVIDER.lower().strip()
    api_key = settings.LLM_API_KEY.strip()

    if (provider_name in ["gemini", "google"]) and api_key:
        return GeminiRESTProvider(api_key=api_key, model=settings.LLM_MODEL)

    return DeterministicFallbackProvider()
