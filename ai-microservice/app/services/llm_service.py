"""Shim hexagonal: re-exporta desde infrastructure.llm.llm_adapter."""
from app.infrastructure.llm.llm_adapter import (  # noqa: F401
    SYSTEM_PROMPT,
    generate_insights,
    _llm_mock,
    _build_user_prompt,
    _llm_google,
    _llm_ollama,
    llm_adapter,
)
