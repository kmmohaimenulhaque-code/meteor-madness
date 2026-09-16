"""
Shared Gemini client (google-genai SDK).

Supports:
- normal text generation
- multi-turn chat history
- native Gemini function/tool calling

The tool functions are executed by the application through the
google-genai SDK. The model never directly accesses the filesystem,
database, or backend internals.
"""

from __future__ import annotations

import os
from typing import Any, Callable


GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.8-flash",
)

DEFAULT_MAX_OUTPUT_TOKENS = int(
    os.getenv("GEMINI_MAX_OUTPUT_TOKENS", "2000")
)

DEFAULT_THINKING_LEVEL = os.getenv(
    "GEMINI_THINKING_LEVEL",
    "medium",
)


def _build_config(
    *,
    system_instruction: str | None = None,
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
    thinking_level: str = DEFAULT_THINKING_LEVEL,
    response_mime_type: str | None = None,
    tools: list[Any] | None = None,
):
    """
    Build GenerateContentConfig.

    `tools` may contain normal Gemini function declarations or
    Python callables. The google-genai SDK can automatically turn
    Python callables into function declarations and handle the
    function-call -> function-response loop.
    """

    from google.genai import types

    kwargs: dict[str, Any] = {
        "max_output_tokens": max_output_tokens,
    }

    if system_instruction:
        kwargs["system_instruction"] = system_instruction

    if response_mime_type:
        kwargs["response_mime_type"] = response_mime_type

    if tools:
        kwargs["tools"] = tools

    # Gemini SDK versions have changed the location/name of the
    # thinking configuration. Try the current form first.
    try:
        kwargs["thinking_level"] = thinking_level
        return types.GenerateContentConfig(**kwargs)

    except TypeError:
        kwargs.pop("thinking_level", None)

    # Older/newer SDK compatibility.
    try:
        kwargs["thinking_config"] = types.ThinkingConfig(
            thinking_level=thinking_level
        )
    except Exception:
        pass

    return types.GenerateContentConfig(**kwargs)


def _extract_response_text(response: Any) -> str | None:
    """
    Extract plain text from a Gemini response.

    Handles both response.text and candidate/part fallback.
    """

    text = getattr(response, "text", None)

    if text and str(text).strip():
        return str(text).strip()

    candidates = getattr(response, "candidates", None) or []

    if not candidates:
        return None

    candidate = candidates[0]

    content = getattr(candidate, "content", None)

    if content is None:
        return None

    parts = getattr(content, "parts", None) or []

    text_parts: list[str] = []

    for part in parts:
        part_text = getattr(part, "text", None)

        if part_text:
            text_parts.append(str(part_text))

    joined = "".join(text_parts).strip()

    return joined or None


def generate_content(
    *,
    contents: Any,
    api_key: str,
    system_instruction: str | None = None,
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
    thinking_level: str = DEFAULT_THINKING_LEVEL,
    response_mime_type: str | None = None,
    model: str | None = None,
    tools: list[Any] | None = None,
) -> str | None:
    """
    Call Gemini through google.genai.

    `contents` may be:
    - a string
    - a list of Gemini Content objects
    - a multi-turn conversation

    `tools` may contain Python callables or Gemini tool declarations.

    When Python callables are supplied, the google-genai SDK can
    automatically handle the function-calling cycle.
    """

    try:
        from google import genai
    except ImportError:
        return None

    model_id = model or GEMINI_MODEL

    try:
        client = genai.Client(
            api_key=api_key
        )

        config = _build_config(
            system_instruction=system_instruction,
            max_output_tokens=max_output_tokens,
            thinking_level=thinking_level,
            response_mime_type=response_mime_type,
            tools=tools,
        )

        response = client.models.generate_content(
            model=model_id,
            contents=contents,
            config=config,
        )

        return _extract_response_text(response)

    except Exception:
        return None


def build_chat_contents(
    history: list[dict[str, str]],
    user_message: str,
) -> list[Any]:
    """
    Build proper Gemini multi-turn conversation state.

    Gemini roles:
        user
        model

    The frontend can continue sending:
        role = user
        role = assistant

    and this function converts assistant -> model.
    """

    from google.genai import types

    contents: list[Any] = []

    for item in history[-12:]:
        role_raw = (
            item.get("role") or "user"
        ).lower()

        if role_raw in (
            "assistant",
            "model",
        ):
            role = "model"
        else:
            role = "user"

        text = (
            item.get("content") or ""
        ).strip()

        if not text:
            continue

        contents.append(
            types.Content(
                role=role,
                parts=[
                    types.Part.from_text(
                        text=text
                    )
                ],
            )
        )

    contents.append(
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(
                    text=user_message
                )
            ],
        )
    )

    return contents
