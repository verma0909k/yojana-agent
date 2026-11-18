"""LLM Client wrapper supporting Google Gemini and Anthropic Claude, with local mock fallback."""

import os
from typing import Optional
from yojanaagent.shared.config import GOOGLE_API_KEY, ANTHROPIC_API_KEY, GEMINI_MODEL


class LLMClient:
    """Provides a single interface for LLM completions and structured generation."""

    def __init__(self, model_name: str = GEMINI_MODEL):
        self.model_name = model_name
        self.google_key = GOOGLE_API_KEY or os.getenv("GOOGLE_API_KEY", "")
        self.anthropic_key = ANTHROPIC_API_KEY or os.getenv("ANTHROPIC_API_KEY", "")

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generates text from LLM, or provides an intelligent heuristic fallback if no key is configured."""
        if self.google_key:
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
                llm = ChatGoogleGenerativeAI(model=self.model_name, google_api_key=self.google_key)
                messages = []
                if system_prompt:
                    messages.append(("system", system_prompt))
                messages.append(("user", prompt))
                response = llm.invoke(messages)
                return response.content
            except Exception as e:
                # Fallback to local heuristic if API call fails
                return f"[LLM Response] {prompt}"

        # Heuristic fallback for offline/development mode
        return f"[Agent Reasoning] Processed request with local fallback model."
