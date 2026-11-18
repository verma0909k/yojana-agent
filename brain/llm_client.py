"""LLM Client wrapper supporting Google Gemini, Anthropic Claude, and structured Pydantic output."""

from dataclasses import dataclass
import json
import os
import re
from typing import Any, Optional, TypeVar
from pydantic import BaseModel
from shared.config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL, GOOGLE_API_KEY, GEMINI_MODEL

T = TypeVar("T", bound=BaseModel)


class LLMUnavailableError(Exception):
    """Raised when no LLM provider is available or when an LLM call fails."""
    pass


@dataclass
class LLMResult:
    """Structured result returned by LLMClient.generate."""
    ok: bool
    text: str = ""
    error: Optional[str] = None
    provider: str = ""


def extract_json_object(text: str) -> dict[str, Any]:
    """Extracts first valid JSON object from LLM response text, stripping markdown fences."""
    cleaned = text.strip()
    # Remove markdown code block markers
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Fallback regex search for outer {...}
        match = re.search(r"(\{.*\})", cleaned, flags=re.DOTALL)
        if match:
            return json.loads(match.group(1))
        raise


class LLMClient:
    """Provides a typed interface for LLM completions via Gemini or Anthropic SDK with structured output support."""

    def __init__(
        self,
        gemini_model: Optional[str] = None,
        anthropic_model: Optional[str] = None,
        google_key: Optional[str] = None,
        anthropic_key: Optional[str] = None,
    ):
        self.google_key = google_key if google_key is not None else (GOOGLE_API_KEY or os.getenv("GOOGLE_API_KEY", ""))
        self.anthropic_key = anthropic_key if anthropic_key is not None else (ANTHROPIC_API_KEY or os.getenv("ANTHROPIC_API_KEY", ""))
        self.gemini_model = gemini_model if gemini_model is not None else (GEMINI_MODEL or os.getenv("GEMINI_MODEL", ""))
        self.anthropic_model = anthropic_model if anthropic_model is not None else (ANTHROPIC_MODEL or os.getenv("ANTHROPIC_MODEL", ""))

    def is_available(self) -> bool:
        """Returns True if at least one LLM provider has both API key and valid model configured."""
        has_gemini = bool(self.google_key and self.gemini_model and self.gemini_model != "not configured")
        has_anthropic = bool(self.anthropic_key and self.anthropic_model and self.anthropic_model != "not configured")
        return has_gemini or has_anthropic

    @property
    def configured_provider(self) -> str:
        if self.google_key and self.gemini_model:
            return "gemini"
        if self.anthropic_key and self.anthropic_model:
            return "anthropic"
        return "not configured"

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        raise_on_error: bool = False,
    ) -> LLMResult:
        """Generates text using the configured provider.

        Never returns prompt as output.
        Raises LLMUnavailableError if no provider is configured.
        Returns LLMResult with error details or raises LLMUnavailableError on provider failure.
        """
        if not self.is_available():
            raise LLMUnavailableError(
                f"LLM provider not configured. Gemini model: {self.gemini_model or 'not configured'}, "
                f"Anthropic model: {self.anthropic_model or 'not configured'}."
            )

        # 1. Try Gemini if configured
        if self.google_key and self.gemini_model:
            provider = "gemini"
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
                llm = ChatGoogleGenerativeAI(model=self.gemini_model, google_api_key=self.google_key)
                messages = []
                if system_prompt:
                    messages.append(("system", system_prompt))
                messages.append(("user", prompt))
                response = llm.invoke(messages)
                text = str(response.content) if hasattr(response, "content") else str(response)
                return LLMResult(ok=True, text=text, error=None, provider=provider)
            except Exception as e:
                if raise_on_error:
                    raise LLMUnavailableError(f"Gemini API failure: {e}") from e
                return LLMResult(ok=False, text="", error=str(e), provider=provider)

        # 2. Try Anthropic if configured
        if self.anthropic_key and self.anthropic_model:
            provider = "anthropic"
            try:
                import anthropic
                client = anthropic.Anthropic(api_key=self.anthropic_key)
                kwargs = {
                    "model": self.anthropic_model,
                    "max_tokens": 1024,
                    "messages": [{"role": "user", "content": prompt}],
                }
                if system_prompt:
                    kwargs["system"] = system_prompt
                message = client.messages.create(**kwargs)
                text = message.content[0].text if message.content else ""
                return LLMResult(ok=True, text=text, error=None, provider=provider)
            except Exception as e:
                if raise_on_error:
                    raise LLMUnavailableError(f"Anthropic API failure: {e}") from e
                return LLMResult(ok=False, text="", error=str(e), provider=provider)

        raise LLMUnavailableError("No LLM provider available.")

    def generate_structured(
        self,
        prompt: str,
        schema_class: type[T],
        system_prompt: Optional[str] = None,
        raise_on_error: bool = False,
    ) -> tuple[Optional[T], LLMResult]:
        """Generates structured output validated against a Pydantic model schema.

        Returns (validated_model_instance, raw_llm_result).
        Never returns hallucinated mock data if the provider is unavailable.
        """
        schema_json = json.dumps(schema_class.model_json_schema(), indent=2)
        instruction = (
            f"You are a strict JSON generator. Your output MUST be a single valid JSON object adhering strictly "
            f"to this JSON schema:\n{schema_json}\n"
            f"Do NOT include markdown formatting like ```json or explanation text. Output raw JSON only."
        )

        full_system = f"{system_prompt}\n\n{instruction}" if system_prompt else instruction
        llm_res = self.generate(prompt=prompt, system_prompt=full_system, raise_on_error=raise_on_error)

        if not llm_res.ok:
            return None, llm_res

        try:
            data = extract_json_object(llm_res.text)
            instance = schema_class.model_validate(data)
            return instance, llm_res
        except Exception as e:
            parse_error = f"Structured schema validation failed for {schema_class.__name__}: {e}"
            if raise_on_error:
                raise LLMUnavailableError(parse_error) from e
            return None, LLMResult(
                ok=False,
                text=llm_res.text,
                error=parse_error,
                provider=llm_res.provider
            )
