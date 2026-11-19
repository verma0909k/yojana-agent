"""LLM Client wrapper supporting Google Gemini, Anthropic Claude, structured Pydantic output,
multimodal vision parsing, prompt caching, and privacy-preserving Aadhaar masking.
"""

from dataclasses import dataclass
import base64
import hashlib
import json
import os
import re
import sqlite3
import time
from typing import Any, Optional, TypeVar
from pydantic import BaseModel
from shared.config import (
    ANTHROPIC_API_KEY,
    ANTHROPIC_MODEL,
    GOOGLE_API_KEY,
    GEMINI_MODEL,
    LLM_CACHE_DB,
)

T = TypeVar("T", bound=BaseModel)


class LLMUnavailableError(Exception):
    """Raised when no LLM provider is available or when an LLM call fails."""
    pass


@dataclass
class LLMResult:
    """Structured result returned by LLMClient.generate and vision methods."""
    ok: bool
    text: str = ""
    error: Optional[str] = None
    provider: str = ""


def mask_aadhaar(text: str) -> str:
    """Masks 12-digit Indian Aadhaar numbers to the last 4 digits (e.g. XXXX-XXXX-1234).
    Protects privacy across all prompts, logs, and stored outputs.
    """
    if not text:
        return text

    # Pattern for 12 digits formatted as XXXX XXXX XXXX or XXXX-XXXX-XXXX
    text = re.sub(
        r'\b(\d{4})[\s-](\d{4})[\s-](\d{4})\b',
        r'XXXX-XXXX-\3',
        text
    )
    # Pattern for 12 continuous digits
    text = re.sub(
        r'\b\d{8}(\d{4})\b',
        r'XXXX-XXXX-\1',
        text
    )
    return text


def extract_json_object(text: str) -> dict[str, Any]:
    """Extracts first valid JSON object from LLM response text, stripping markdown fences."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"(\{.*\})", cleaned, flags=re.DOTALL)
        if match:
            return json.loads(match.group(1))
        raise


class LLMCache:
    """Persistent SQLite cache storing prompt hash to response mapping."""

    def __init__(self, db_path=LLM_CACHE_DB):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS llm_cache (
                        prompt_hash TEXT PRIMARY KEY,
                        provider TEXT,
                        model TEXT,
                        response_text TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                conn.commit()
        except Exception:
            pass

    def get(self, prompt_hash: str) -> Optional[str]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.execute("SELECT response_text FROM llm_cache WHERE prompt_hash = ?", (prompt_hash,))
                row = cur.fetchone()
                return row[0] if row else None
        except Exception:
            return None

    def set(self, prompt_hash: str, provider: str, model: str, response_text: str):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO llm_cache (prompt_hash, provider, model, response_text) VALUES (?, ?, ?, ?)",
                    (prompt_hash, provider, model, response_text),
                )
                conn.commit()
        except Exception:
            pass


class LLMClient:
    """Provides a typed interface for text & vision LLM completions via Gemini or Anthropic SDK
    with structured Pydantic output, offline caching, and retry backoff.
    """

    def __init__(
        self,
        gemini_model: Optional[str] = None,
        anthropic_model: Optional[str] = None,
        google_key: Optional[str] = None,
        anthropic_key: Optional[str] = None,
        use_cache: bool = True,
    ):
        self.google_key = google_key if google_key is not None else (GOOGLE_API_KEY or os.getenv("GOOGLE_API_KEY", ""))
        self.anthropic_key = anthropic_key if anthropic_key is not None else (ANTHROPIC_API_KEY or os.getenv("ANTHROPIC_API_KEY", ""))
        self.gemini_model = gemini_model if gemini_model is not None else (GEMINI_MODEL or os.getenv("GEMINI_MODEL", ""))
        self.anthropic_model = anthropic_model if anthropic_model is not None else (ANTHROPIC_MODEL or os.getenv("ANTHROPIC_MODEL", ""))
        self.use_cache = use_cache
        self.cache = LLMCache() if use_cache else None

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

    def _hash_key(self, *parts: str) -> str:
        h = hashlib.sha256()
        for p in parts:
            h.update(str(p).encode("utf-8"))
        return h.hexdigest()

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        raise_on_error: bool = False,
    ) -> LLMResult:
        """Generates text using the configured provider with prompt caching & backoff."""
        if not self.is_available():
            err_msg = (
                f"LLM provider not configured. Gemini model: {self.gemini_model or 'not configured'}, "
                f"Anthropic model: {self.anthropic_model or 'not configured'}."
            )
            if raise_on_error:
                raise LLMUnavailableError(err_msg)
            return LLMResult(ok=False, text="", error=err_msg, provider="none")

        # Privacy: mask any Aadhaar numbers before prompt leaves
        safe_prompt = mask_aadhaar(prompt)
        safe_sys = mask_aadhaar(system_prompt or "")

        # Check Cache
        provider = self.configured_provider
        model_name = self.gemini_model if provider == "gemini" else self.anthropic_model
        cache_key = self._hash_key("text", provider, model_name, safe_prompt, safe_sys)

        if self.use_cache and self.cache:
            cached = self.cache.get(cache_key)
            if cached:
                return LLMResult(ok=True, text=cached, error=None, provider=f"{provider}-cache")

        # 1. Try Gemini
        if self.google_key and self.gemini_model:
            for attempt in range(2):
                try:
                    from langchain_google_genai import ChatGoogleGenerativeAI
                    llm = ChatGoogleGenerativeAI(model=self.gemini_model, google_api_key=self.google_key)
                    messages = []
                    if safe_sys:
                        messages.append(("system", safe_sys))
                    messages.append(("user", safe_prompt))
                    response = llm.invoke(messages)

                    if hasattr(response, "content") and isinstance(response.content, list):
                        text = "".join(part.get("text", "") if isinstance(part, dict) else str(part) for part in response.content)
                    elif hasattr(response, "content"):
                        text = str(response.content)
                    else:
                        text = str(response)

                    if self.use_cache and self.cache:
                        self.cache.set(cache_key, "gemini", self.gemini_model, text)

                    return LLMResult(ok=True, text=text, error=None, provider="gemini")
                except Exception as e:
                    err_str = str(e).lower()
                    if ("429" in err_str or "resourceexhausted" in err_str) and attempt == 0:
                        time.sleep(2)
                        continue
                    if raise_on_error and not (self.anthropic_key and self.anthropic_model):
                        raise LLMUnavailableError(f"Gemini API failure: {e}") from e
                    # Fallback to Anthropic if available
                    break

        # 2. Try Anthropic
        if self.anthropic_key and self.anthropic_model:
            for attempt in range(2):
                try:
                    import anthropic
                    client = anthropic.Anthropic(api_key=self.anthropic_key)
                    kwargs = {
                        "model": self.anthropic_model,
                        "max_tokens": 1024,
                        "messages": [{"role": "user", "content": safe_prompt}],
                    }
                    if safe_sys:
                        kwargs["system"] = safe_sys
                    message = client.messages.create(**kwargs)
                    text = message.content[0].text if message.content else ""

                    if self.use_cache and self.cache:
                        self.cache.set(cache_key, "anthropic", self.anthropic_model, text)

                    return LLMResult(ok=True, text=text, error=None, provider="anthropic")
                except Exception as e:
                    err_str = str(e).lower()
                    if "429" in err_str and attempt == 0:
                        time.sleep(2)
                        continue
                    if raise_on_error:
                        raise LLMUnavailableError(f"Anthropic API failure: {e}") from e
                    return LLMResult(ok=False, text="", error=str(e), provider="anthropic")

        raise LLMUnavailableError("No LLM provider available.")

    def generate_structured(
        self,
        prompt: str,
        schema_class: type[T],
        system_prompt: Optional[str] = None,
        raise_on_error: bool = False,
    ) -> tuple[Optional[T], LLMResult]:
        """Generates structured output validated against a Pydantic model schema."""
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
                provider=llm_res.provider,
            )

    def generate_vision_structured(
        self,
        image_bytes: bytes,
        mime_type: str,
        prompt: str,
        schema_class: type[T],
        system_prompt: Optional[str] = None,
        raise_on_error: bool = False,
    ) -> tuple[Optional[T], LLMResult]:
        """Generates structured output directly from image bytes using Gemini or Anthropic vision."""
        if not self.is_available():
            raise LLMUnavailableError("LLM provider not configured for vision.")

        schema_json = json.dumps(schema_class.model_json_schema(), indent=2)
        schema_instruction = (
            f"Analyze the provided document image carefully. Extract all text and demographic data into strict JSON "
            f"matching this schema:\n{schema_json}\n"
            f"Mask any 12-digit Aadhaar number to only the last 4 digits (e.g. 'id_last4': '1234'). "
            f"Do NOT include markdown code fences like ```json. Output raw JSON only."
        )

        safe_prompt = mask_aadhaar(prompt)
        combined_prompt = f"{safe_prompt}\n\n{schema_instruction}"
        full_sys = mask_aadhaar(system_prompt or "")

        provider = self.configured_provider
        model_name = self.gemini_model if provider == "gemini" else self.anthropic_model
        img_hash = hashlib.sha256(image_bytes).hexdigest()
        cache_key = self._hash_key("vision", provider, model_name, img_hash, combined_prompt)

        if self.use_cache and self.cache:
            cached = self.cache.get(cache_key)
            if cached:
                try:
                    data = extract_json_object(cached)
                    instance = schema_class.model_validate(data)
                    return instance, LLMResult(ok=True, text=cached, provider=f"{provider}-cache")
                except Exception:
                    pass

        # 1. Try Gemini Vision
        if self.google_key and self.gemini_model:
            for attempt in range(2):
                try:
                    from google import genai
                    from google.genai import types
                    client = genai.Client(api_key=self.google_key)
                    contents = [
                        types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                        combined_prompt,
                    ]
                    config = types.GenerateContentConfig(
                        system_instruction=full_sys if full_sys else None
                    )
                    resp = client.models.generate_content(
                        model=self.gemini_model,
                        contents=contents,
                        config=config,
                    )
                    text = resp.text or ""
                    data = extract_json_object(text)
                    instance = schema_class.model_validate(data)

                    if self.use_cache and self.cache:
                        self.cache.set(cache_key, "gemini", self.gemini_model, text)

                    return instance, LLMResult(ok=True, text=text, provider="gemini")
                except Exception as e:
                    err_str = str(e).lower()
                    if ("429" in err_str or "resourceexhausted" in err_str) and attempt == 0:
                        time.sleep(2)
                        continue
                    if not (self.anthropic_key and self.anthropic_model):
                        if raise_on_error:
                            raise LLMUnavailableError(f"Gemini vision error: {e}") from e
                        return None, LLMResult(ok=False, text="", error=str(e), provider="gemini")
                    break

        # 2. Try Anthropic Vision
        if self.anthropic_key and self.anthropic_model:
            for attempt in range(2):
                try:
                    import anthropic
                    client = anthropic.Anthropic(api_key=self.anthropic_key)
                    b64_img = base64.b64encode(image_bytes).decode("utf-8")
                    messages = [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": mime_type,
                                        "data": b64_img,
                                    },
                                },
                                {"type": "text", "text": combined_prompt},
                            ],
                        }
                    ]
                    kwargs = {
                        "model": self.anthropic_model,
                        "max_tokens": 1500,
                        "messages": messages,
                    }
                    if full_sys:
                        kwargs["system"] = full_sys
                    msg = client.messages.create(**kwargs)
                    text = msg.content[0].text if msg.content else ""
                    data = extract_json_object(text)
                    instance = schema_class.model_validate(data)

                    if self.use_cache and self.cache:
                        self.cache.set(cache_key, "anthropic", self.anthropic_model, text)

                    return instance, LLMResult(ok=True, text=text, provider="anthropic")
                except Exception as e:
                    err_str = str(e).lower()
                    if "429" in err_str and attempt == 0:
                        time.sleep(2)
                        continue
                    if raise_on_error:
                        raise LLMUnavailableError(f"Anthropic vision error: {e}") from e
                    return None, LLMResult(ok=False, text="", error=str(e), provider="anthropic")

        raise LLMUnavailableError("No vision-capable LLM provider available.")
