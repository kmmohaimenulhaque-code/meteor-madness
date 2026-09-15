"""
Shared Gemini 3.8 Flash client (google-genai SDK).

Canonical call pattern:

  response = client.models.generate_content(
      model="gemini-3.8-flash",
      contents=prompt,
      config=types.GenerateContentConfig(
          thinking_level="medium",
          max_output_tokens=2000,
      ),
  )
"""
from __future__ import annotations

import os
from typing import Any

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
DEFAULT_MAX_OUTPUT_TOKENS = int(os.getenv("GEMINI_MAX_OUTPUT_TOKENS", "2000"))
DEFAULT_THINKING_LEVEL = os.getenv("GEMINI_THINKING_LEVEL", "medium")


def _build_config(
    *,
    system_instruction: str | None = None,
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
    thinking_level: str = DEFAULT_THINKING_LEVEL,
    response_mime_type: str | None = None,
):
    from google.genai import types

    kwargs: dict[str, Any] = {
        "thinking_level": thinking_level,
        "max_output_tokens": max_output_tokens,
    }
    if system_instruction:
        kwargs["system_instruction"] = system_instruction
    if response_mime_type:
        kwargs["response_mime_type"] = response_mime_type

    try:
        return types.GenerateContentConfig(**kwargs)
    except TypeError:
        # Older SDK builds may nest thinking under thinking_config
        kwargs.pop("thinking_level", None)
        try:
            kwargs["thinking_config"] = types.ThinkingConfig(
                thinking_level=thinking_level
            )
        except Exception:
            pass
        return types.GenerateContentConfig(**kwargs)


def generate_content(
    *,
    contents: Any,
    api_key: str,
    system_instruction: str | None = None,
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
    thinking_level: str = DEFAULT_THINKING_LEVEL,
    response_mime_type: str | None = None,
    model: str | None = None,
) -> str | None:
    """
    Call Gemini via google.genai Client.

    `contents` may be a string, a list of Content, or multi-turn history.
    Returns response text or None on failure.
    """
    try:
        from google import genai
    except ImportError:
        return None

    model_id = model or GEMINI_MODEL
    try:
        client = genai.Client(api_key=api_key)
        config = _build_config(
            system_instruction=system_instruction,
            max_output_tokens=max_output_tokens,
            thinking_level=thinking_level,
            response_mime_type=response_mime_type,
        )
        response = client.models.generate_content(
            model=model_id,
            contents=contents,
            config=config,
        )
        text = getattr(response, "text", None)
        if text and str(text).strip():
            return str(text).strip()
        # Fallback: stitch parts
        candidates = getattr(response, "candidates", None) or []
        if not candidates:
            return None
        content = getattr(candidates[0], "content", None)
        parts = getattr(content, "parts", None) or []
        joined = "".join(
            str(getattr(p, "text", "") or "") for p in parts
        ).strip()
        return joined or None
    except Exception:
        return None


def build_chat_contents(
    history: list[dict[str, str]],
    user_message: str,
) -> list[Any]:
    """
    Proper multi-turn conversation state for generate_content.

    Roles: user | model (Gemini SDK convention).
    """
    from google.genai import types

    contents: list[Any] = []
    for item in history[-12:]:
        role_raw = (item.get("role") or "user").lower()
        if role_raw in ("assistant", "model"):
            role = "model"
        else:
            role = "user"
        text = (item.get("content") or "").strip()
        if not text:
            continue
        contents.append(
            types.Content(
                role=role,
                parts=[types.Part.from_text(text=text)],
            )
        )

    contents.append(
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=user_message)],
        )
    )
    return contents
