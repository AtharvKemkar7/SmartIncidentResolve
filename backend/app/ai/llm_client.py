import json

import httpx
from loguru import logger

from app.core.config import settings

DEFAULT_MODEL = "openai/gpt-4o-mini"


class LLMClientError(Exception):
    pass


def _chat_url() -> str:
    base = settings.openrouter_base_url.rstrip("/")
    return f"{base}/chat/completions"


def complete_json(messages: list[dict[str, str]]) -> dict:
    if not settings.openrouter_api_key:
        raise LLMClientError("OPENROUTER_API_KEY is not configured")

    model = settings.openrouter_model or DEFAULT_MODEL
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
    }
    headers = {
        "Authorization": "Bearer [redacted]",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://localhost",
        "X-Title": "AI Kubernetes Agent",
    }

    last_error = "OpenRouter request failed"
    timeout = httpx.Timeout(settings.openrouter_timeout_seconds)
    retries = max(1, settings.openrouter_max_retries)

    for attempt in range(1, retries + 1):
        try:
            request_headers = {
                **headers,
                "Authorization": f"Bearer {settings.openrouter_api_key}",
            }
            with httpx.Client(timeout=timeout) as client:
                response = client.post(_chat_url(), headers=request_headers, json=payload)

            if response.status_code in {408, 429, 500, 502, 503, 504}:
                last_error = f"OpenRouter returned HTTP {response.status_code}"
                logger.warning("LLM attempt {}/{} failed: {}", attempt, retries, last_error)
                continue

            if response.status_code >= 400:
                last_error = f"OpenRouter returned HTTP {response.status_code}"
                logger.error("LLM request rejected: {}", last_error)
                raise LLMClientError(last_error)

            content = _extract_content(response.json())
            return _parse_json_object(content)
        except LLMClientError:
            raise
        except httpx.TimeoutException:
            last_error = "OpenRouter request timed out"
            logger.warning("LLM attempt {}/{} timed out", attempt, retries)
        except httpx.HTTPError:
            last_error = "OpenRouter network error"
            logger.warning("LLM attempt {}/{} network error", attempt, retries)
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            last_error = "OpenRouter returned an unreadable response"
            logger.warning("LLM attempt {}/{} parse error: {}", attempt, retries, type(exc).__name__)

    raise LLMClientError(last_error)


def _extract_content(body: dict) -> str:
    choices = body.get("choices") or []
    if not choices:
        raise ValueError("missing choices")
    message = choices[0].get("message") or {}
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise ValueError("missing content")
    return content


def _parse_json_object(content: str) -> dict:
    text = content.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()

    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("response is not a JSON object")
    return parsed
