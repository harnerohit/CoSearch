"""The only module that talks to the LLM: complete_json(system, user) -> dict (Sections 7-8)."""

import json
import logging
import os
import time

from dotenv import load_dotenv
from openai import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    BadRequestError,
    OpenAI,
    RateLimitError,
)

from src import config

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Any LLM failure; the pipeline converts it into a friendly message, never a traceback."""


load_dotenv()

# JSON mode requires the word "json" somewhere in the messages (live-verified 2026-10-01).
_JSON_INSTRUCTION = " Respond with one JSON object and nothing else."


def _parse_object(choice: object) -> dict | None:
    """The choice's content as a JSON object, or None when empty, truncated, or invalid."""
    if choice is None or choice.finish_reason == "length":
        return None
    content = choice.message.content
    if not content:
        return None
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def complete_json(system: str, user: str) -> dict:
    """One JSON completion with Section 7 retries; raises LLMError on any failure."""
    required = ("LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL")
    values = {name: os.environ.get(name) for name in required}
    missing = [name for name in required if not values[name]]
    if missing:
        raise LLMError(
            f"Missing environment variable(s): {', '.join(missing)}. "
            "Set them in .env (local) or Streamlit secrets (cloud)."
        )
    client = OpenAI(
        api_key=values["LLM_API_KEY"],
        base_url=values["LLM_BASE_URL"],
        timeout=config.LLM_TIMEOUT_SECONDS,
        max_retries=0,  # retries are ours, bounded by Section 7
    )
    transient_retries = 0
    json_retries = 0
    while True:
        try:
            response = client.chat.completions.create(
                model=values["LLM_MODEL"],
                messages=[
                    {"role": "system", "content": system + _JSON_INSTRUCTION},
                    {"role": "user", "content": user},
                ],
                temperature=config.LLM_TEMPERATURE,
                response_format={"type": "json_object"},
                reasoning_effort=config.LLM_REASONING_EFFORT,
                max_tokens=config.LLM_MAX_TOKENS,
            )
        except (APITimeoutError, APIConnectionError, RateLimitError) as exc:
            transient_retries += 1
            if transient_retries > config.LLM_MAX_RETRIES:
                raise LLMError(
                    f"LLM unreachable after {config.LLM_MAX_RETRIES} retries "
                    f"({type(exc).__name__})."
                ) from exc
            logger.warning("transient LLM error: %s", type(exc).__name__)
            time.sleep(config.LLM_BACKOFF_SECONDS)
            continue
        except BadRequestError as exc:
            # Exhausted reasoning tokens surface as json_validate_failed with empty content.
            if "json_validate_failed" not in str(exc):
                raise LLMError("The LLM rejected the request.") from exc
            if json_retries >= config.LLM_JSON_RETRIES:
                raise LLMError("The LLM returned an empty answer.") from exc
            json_retries += 1
            time.sleep(config.LLM_BACKOFF_SECONDS)
            continue
        except APIError as exc:
            raise LLMError(f"LLM request failed ({type(exc).__name__}).") from exc

        choice = response.choices[0] if response.choices else None
        parsed = _parse_object(choice)
        if parsed is not None:
            return parsed
        if json_retries >= config.LLM_JSON_RETRIES:
            raise LLMError("The LLM returned an empty, truncated, or non-JSON answer.")
        json_retries += 1
        time.sleep(config.LLM_BACKOFF_SECONDS)
