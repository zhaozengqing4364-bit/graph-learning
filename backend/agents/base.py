"""AI base client - OpenAI API wrapper with retry and fallback."""

import json
import logging
import time
from typing import Any

from openai import AsyncOpenAI

from backend.core.config import get_settings

logger = logging.getLogger(__name__)

# Cached DB overrides (updated when settings are saved via API)
_db_overrides: dict | None = None

# AI usage tracking
_ai_call_count = 0
_ai_start_time = time.time()


def set_db_overrides(overrides: dict):
    """Update cached DB overrides for AI client configuration.

    Called by settings API after user saves configuration.
    """
    global _db_overrides
    _db_overrides = overrides


def _get_config(field: str) -> str:
    """Get a config value: DB override > .env value."""
    if _db_overrides and _db_overrides.get(field):
        return _db_overrides[field]
    return getattr(get_settings(), field, "")


class AIClient:
    """Wrapper around OpenAI API with structured output support and Ollama fallback."""

    def __init__(self, model: str | None = None):
        api_key = _get_config("openai_api_key")
        base_url = _get_config("openai_base_url")
        default_model = _get_config("openai_model_default") or get_settings().openai_model_default

        client_kwargs: dict[str, Any] = {"api_key": api_key, "timeout": 120.0}
        if base_url:
            client_kwargs["base_url"] = base_url
        self.client = AsyncOpenAI(**client_kwargs)
        self.model = model or default_model
        self.max_retries = 2

    async def _try_ollama_fallback(
        self,
        system_prompt: str,
        user_prompt: str,
        output_schema: dict | None = None,
    ) -> dict | None:
        """Try Ollama as fallback when OpenAI fails."""
        ollama_enabled = _get_config("ollama_enabled")
        ollama_base_url = _get_config("ollama_base_url")
        if not ollama_enabled or not ollama_base_url:
            return None
        try:
            ollama_client = AsyncOpenAI(
                api_key="ollama",
                base_url=ollama_base_url,
                timeout=60.0,
            )
            # Use a sensible default model for Ollama
            ollama_model = self.model
            # Map common model names to Ollama equivalents
            _ollama_map = {
                "gpt-4o": "llama3",
                "gpt-4o-mini": "llama3:8b",
                "gpt-3.5-turbo": "llama3:8b",
                "gpt-4": "llama3",
                "gpt-4-turbo": "llama3",
                "gpt-4.1": "llama3",
                "gpt-4.1-mini": "llama3:8b",
                "gpt-4.1-nano": "llama3:8b",
                "o1": "llama3",
                "o1-mini": "llama3:8b",
                "o3-mini": "llama3:8b",
                "claude": "llama3",
                "deepseek": "deepseek-r1:latest",
            }
            matched = False
            for k, v in _ollama_map.items():
                if k in ollama_model:
                    ollama_model = v
                    matched = True
                    break
            if not matched:
                logger.warning(f"[WARN] No Ollama mapping for '{self.model}', falling back to 'llama3'")
                ollama_model = "llama3"

            kwargs: dict[str, Any] = {
                "model": ollama_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.3,
            }
            if output_schema:
                schema_hint = "\n\n## 输出 JSON Schema（严格遵守）\n```json\n" + json.dumps(output_schema, ensure_ascii=False, indent=2) + "\n```\n"
                kwargs["messages"][0]["content"] += schema_hint
                kwargs["format"] = "json"

            response = await ollama_client.chat.completions.create(**kwargs)
            global _ai_call_count
            _ai_call_count += 1
            elapsed = time.time() - _ai_start_time
            logger.info(f"[AI] Ollama fallback call #{_ai_call_count} | model={ollama_model} | elapsed={elapsed:.1f}s")
            if not response.choices:
                logger.warning("[WARN] Ollama response has empty choices")
                return None
            content = response.choices[0].message.content
            if content:
                return json.loads(content)
        except Exception as e:
            logger.warning(f"[WARN] Ollama fallback also failed: {e}")
        return None

    async def call(
        self,
        system_prompt: str,
        user_prompt: str,
        output_schema: dict | None = None,
        temperature: float = 0.3,
    ) -> dict | None:
        """Call OpenAI with optional structured JSON output, with Ollama fallback.

        Returns parsed dict or None on failure.
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        for attempt in range(self.max_retries + 1):
            try:
                kwargs: dict[str, Any] = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                }

                # Inject JSON schema into system prompt for structured output
                if output_schema:
                    import json as _json
                    schema_hint = "\n\n## 输出 JSON Schema（严格遵守）\n```json\n" + _json.dumps(output_schema, ensure_ascii=False, indent=2) + "\n```\n"
                    messages = [
                        {"role": "system", "content": messages[0]["content"] + schema_hint},
                        {"role": "user", "content": messages[1]["content"]},
                    ]

                kwargs["response_format"] = {"type": "json_object"}

                response = await self.client.chat.completions.create(**kwargs)
                global _ai_call_count
                _ai_call_count += 1
                elapsed = time.time() - _ai_start_time
                logger.info(f"[AI] call #{_ai_call_count} | model={self.model} | elapsed={elapsed:.1f}s | attempt={attempt + 1}")
                if not response.choices:
                    logger.warning("[WARN] AI response has empty choices, retrying")
                    continue
                content = response.choices[0].message.content
                if content:
                    return json.loads(content)
                return None
            except json.JSONDecodeError:
                if attempt == self.max_retries:
                    return None
            except Exception as e:
                if attempt == self.max_retries:
                    logger.warning(f"[WARN] AI call failed after {self.max_retries + 1} attempts: {e}")
                    # Try Ollama fallback
                    return await self._try_ollama_fallback(system_prompt, user_prompt, output_schema)

        return None


def get_ai_client(model: str | None = None) -> AIClient:
    """Get a new AI client instance."""
    return AIClient(model=model)


def validate_ai_output(
    data: dict | None,
    required_fields: list[str],
    field_types: dict[str, type] | None = None,
) -> dict | None:
    """Lightweight validation of AI output. Returns None if validation fails.

    Args:
        data: Raw AI output dict
        required_fields: Fields that must exist and be non-empty
        field_types: Optional type checks for specific fields
    """
    if not isinstance(data, dict):
        return None
    for field in required_fields:
        val = data.get(field)
        if val is None:
            return None
    if field_types:
        for field, expected_type in field_types.items():
            val = data.get(field)
            if val is not None and not isinstance(val, expected_type):
                return None
    return data
