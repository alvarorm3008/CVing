import logging
import os
import random
import time
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Literal

import anthropic
from dotenv import load_dotenv
from fastapi import HTTPException
from google import genai
from google.genai import types

load_dotenv()

logger = logging.getLogger(__name__)

AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini").lower()
VALID_PROVIDERS = frozenset({"gemini", "anthropic", "hybrid"})
_provider_override: ContextVar[str | None] = ContextVar("provider_override", default=None)
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
GEMINI_FALLBACK_MODELS = os.getenv(
    "GEMINI_FALLBACK_MODELS", "gemini-2.0-flash,gemini-2.5-flash,gemini-2.5-pro"
)
GEMINI_MAX_RETRIES = int(os.getenv("GEMINI_MAX_RETRIES", "5"))
GEMINI_RATE_LIMIT_RETRIES = int(os.getenv("GEMINI_RATE_LIMIT_RETRIES", "2"))
GEMINI_RETRY_BASE_SECONDS = float(os.getenv("GEMINI_RETRY_BASE_SECONDS", "2"))
GEMINI_MODEL_SWITCH_DELAY = float(os.getenv("GEMINI_MODEL_SWITCH_DELAY", "3"))
GEMINI_FINAL_COOLDOWN_SECONDS = float(os.getenv("GEMINI_FINAL_COOLDOWN_SECONDS", "12"))
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")

AITask = Literal["parse", "adapt", "cover_letter", "research", "default"]

HYBRID_TASK_MAP: dict[str, str] = {
    "parse": "gemini",
    "adapt": "anthropic",
    "cover_letter": "anthropic",
    "research": "gemini",
    "default": "gemini",
}

_gemini_client: genai.Client | None = None


class GeminiQuotaExhausted(Exception):
    """Cuota diaria/RPM de la API key agotada — no sirve reintentar ni cambiar de modelo."""


def _gemini_configured() -> bool:
    return bool(os.getenv("GEMINI_API_KEY", "").strip())


def _anthropic_configured() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY", "").strip())


def _effective_mode() -> str:
    override = _provider_override.get()
    if override in VALID_PROVIDERS:
        return override
    env = AI_PROVIDER if AI_PROVIDER in VALID_PROVIDERS else "gemini"
    return env


def validate_ai_provider(value: str, *, default: str | None = None) -> str:
    fallback = default or (AI_PROVIDER if AI_PROVIDER in VALID_PROVIDERS else "gemini")
    cleaned = (value or fallback).strip().lower()
    if cleaned not in VALID_PROVIDERS:
        return fallback
    if cleaned == "anthropic" and not _anthropic_configured():
        return "gemini"
    if cleaned == "hybrid" and not _anthropic_configured():
        return "gemini"
    return cleaned


@contextmanager
def ai_provider_scope(mode: str):
    validated = validate_ai_provider(mode)
    token = _provider_override.set(validated)
    try:
        yield validated
    finally:
        _provider_override.reset(token)


def _resolve_provider(task: AITask = "default") -> str:
    mode = _effective_mode()
    if mode == "hybrid":
        preferred = HYBRID_TASK_MAP.get(task, "gemini")
        if preferred == "anthropic" and not _anthropic_configured():
            return "gemini"
        return preferred
    if mode in ("gemini", "anthropic"):
        if mode == "anthropic" and not _anthropic_configured():
            return "gemini"
        return mode
    return "gemini"


def get_provider() -> str:
    return _effective_mode()


def get_provider_info() -> dict:
    mode = _effective_mode()
    info = {
        "mode": mode,
        "gemini_available": _gemini_configured(),
        "anthropic_available": _anthropic_configured(),
        "hybrid_available": _anthropic_configured() and _gemini_configured(),
        "tasks": {},
    }
    if mode == "hybrid":
        for task, preferred in HYBRID_TASK_MAP.items():
            if task == "default":
                continue
            resolved = _resolve_provider(task)  # type: ignore[arg-type]
            info["tasks"][task] = resolved
    return info


def list_provider_options() -> list[dict[str, str | bool]]:
    """Uso personal: solo Gemini expuesto como opción activa."""
    return [
        {
            "id": "gemini",
            "name": "Gemini",
            "description": "Google Gemini (gratis con flash-lite)",
            "available": _gemini_configured(),
        },
    ]


def _get_gemini_client() -> genai.Client:
    global _gemini_client
    if _gemini_client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise HTTPException(
                status_code=500,
                detail="GEMINI_API_KEY is not configured. Add it to backend/.env",
            )
        _gemini_client = genai.Client(api_key=api_key)
    return _gemini_client


def _gemini_models_to_try() -> list[str]:
    models = [GEMINI_MODEL]
    for model in GEMINI_FALLBACK_MODELS.split(","):
        model = model.strip()
        if model and model not in models:
            models.append(model)
    return models


def _is_gemini_quota_exhausted(exc: Exception) -> bool:
    message = str(exc).upper()
    return any(
        token in message
        for token in (
            "RESOURCE_EXHAUSTED",
            "EXCEEDED YOUR CURRENT QUOTA",
            "EXCEEDED YOUR QUOTA",
            "QUOTA_EXCEEDED",
            "QUOTA METRIC",
            "BILLING HARD LIMIT",
            "PAYMENT REQUIRED",
            "INSUFFICIENT QUOTA",
        )
    ) or ("429" in message and "QUOTA" in message)


def _is_retryable_gemini_error(exc: Exception) -> bool:
    if _is_gemini_quota_exhausted(exc):
        return False
    message = str(exc).upper()
    if "429" in message:
        return True
    return any(
        token in message
        for token in (
            "503",
            "UNAVAILABLE",
            "HIGH DEMAND",
            "OVERLOADED",
            "RATE LIMIT",
            "RATE_LIMIT",
            "INTERNAL",
            "DEADLINE",
            "TIMEOUT",
            "TEMPORARILY",
        )
    )


def _max_retries_for_error(exc: Exception) -> int:
    if _is_gemini_quota_exhausted(exc):
        return 0
    if "429" in str(exc).upper():
        return GEMINI_RATE_LIMIT_RETRIES
    return GEMINI_MAX_RETRIES


def _gemini_quota_message() -> str:
    return (
        "Has agotado la cuota gratuita de Gemini (límite diario o por minuto). "
        "Revisa uso y límites en https://aistudio.google.com/ — la cuota suele reiniciarse "
        "cada minuto o al día siguiente. Mientras tanto usa «Solo adaptar CV» (1 llamada) "
        "en lugar de «Candidatura completa» (4+ llamadas). No pulses reintentar en bucle."
    )


def _gemini_overload_message(models: list[str], *, web_search: bool = False) -> str:
    scope = "búsqueda web de Gemini" if web_search else "Gemini"
    return (
        f"{scope} está saturado temporalmente. Espera 30–60 segundos y vuelve a intentarlo. "
        "Consejos: activa «Modo rápido», no pulses varias veces seguidas, y reintenta en 1–2 minutos. "
        f"Modelos probados: {', '.join(models)}."
    )


def _gemini_backoff_seconds(attempt: int) -> float:
    base = GEMINI_RETRY_BASE_SECONDS * (2 ** (attempt - 1))
    jitter = random.uniform(0, 0.35 * base)
    return min(base + jitter, 45.0)


def _raise_if_quota_exhausted(exc: Exception) -> None:
    if _is_gemini_quota_exhausted(exc):
        logger.error("Gemini quota exhausted — stopping retries: %s", exc)
        raise GeminiQuotaExhausted(exc) from exc


def _sleep_before_retry(attempt: int, *, reason: str, model: str, max_retries: int) -> None:
    delay = _gemini_backoff_seconds(attempt)
    logger.warning(
        "Gemini retry %s/%s on %s (%s) — waiting %.1fs",
        attempt,
        max_retries,
        model,
        reason,
        delay,
    )
    time.sleep(delay)


def _generate_gemini_once(
    client: genai.Client,
    *,
    model: str,
    system_prompt: str,
    user_message: str,
    max_output_tokens: int,
    json_mode: bool,
    tools: list | None,
) -> tuple[str, object | None]:
    config_kwargs: dict = {
        "system_instruction": system_prompt,
        "max_output_tokens": max_output_tokens,
    }
    if json_mode:
        config_kwargs["response_mime_type"] = "application/json"
    if tools:
        config_kwargs["tools"] = tools

    response = client.models.generate_content(
        model=model,
        contents=user_message,
        config=types.GenerateContentConfig(**config_kwargs),
    )
    text = (response.text or "").strip()
    if not text:
        raise RuntimeError("Empty response from Gemini API")
    return text, response


def _call_gemini_attempts(
    system_prompt: str,
    user_message: str,
    *,
    max_output_tokens: int = 4096,
    json_mode: bool = False,
    tools: list | None = None,
    extract_sources: bool = False,
) -> tuple[str, list[dict[str, str]]]:
    client = _get_gemini_client()
    models = _gemini_models_to_try()
    last_error: Exception | None = None
    had_retryable = False

    for model_index, model in enumerate(models):
        if model_index > 0 and GEMINI_MODEL_SWITCH_DELAY > 0:
            time.sleep(GEMINI_MODEL_SWITCH_DELAY)

        for attempt in range(1, GEMINI_MAX_RETRIES + 1):
            json_options = [json_mode]
            if json_mode and attempt == GEMINI_MAX_RETRIES:
                json_options = [True, False]

            retryable = False
            for use_json in json_options:
                try:
                    text, response = _generate_gemini_once(
                        client,
                        model=model,
                        system_prompt=system_prompt,
                        user_message=user_message,
                        max_output_tokens=max_output_tokens,
                        json_mode=use_json,
                        tools=tools,
                    )
                    sources = _extract_grounding_sources(response) if extract_sources else []
                    return text, sources
                except Exception as exc:
                    last_error = exc
                    _raise_if_quota_exhausted(exc)
                    retryable = _is_retryable_gemini_error(exc)
                    if retryable:
                        had_retryable = True
                    logger.warning(
                        "Gemini error on %s (attempt %s, json=%s): %s",
                        model,
                        attempt,
                        use_json,
                        exc,
                    )

            max_retries = _max_retries_for_error(last_error) if last_error else GEMINI_MAX_RETRIES
            if retryable and attempt < max_retries:
                _sleep_before_retry(
                    attempt,
                    reason=str(last_error)[:120],
                    model=model,
                    max_retries=max_retries,
                )
                continue
            break

    if had_retryable and GEMINI_FINAL_COOLDOWN_SECONDS > 0 and not (
        last_error and _is_gemini_quota_exhausted(last_error)
    ):
        logger.warning(
            "Gemini cooldown %.0fs before final attempt on %s",
            GEMINI_FINAL_COOLDOWN_SECONDS,
            models[0],
        )
        time.sleep(GEMINI_FINAL_COOLDOWN_SECONDS)
        try:
            text, response = _generate_gemini_once(
                client,
                model=models[0],
                system_prompt=system_prompt,
                user_message=user_message,
                max_output_tokens=max_output_tokens,
                json_mode=json_mode,
                tools=tools,
            )
            sources = _extract_grounding_sources(response) if extract_sources else []
            return text, sources
        except Exception as exc:
            _raise_if_quota_exhausted(exc)
            last_error = exc

    if last_error and _is_gemini_quota_exhausted(last_error):
        raise GeminiQuotaExhausted(last_error) from last_error

    raise last_error or RuntimeError("Gemini request failed")


def _call_gemini(
    system_prompt: str,
    user_message: str,
    *,
    max_output_tokens: int = 4096,
    json_mode: bool = False,
) -> str:
    models = _gemini_models_to_try()
    try:
        text, _ = _call_gemini_attempts(
            system_prompt,
            user_message,
            max_output_tokens=max_output_tokens,
            json_mode=json_mode,
        )
        return text
    except GeminiQuotaExhausted:
        raise HTTPException(status_code=429, detail=_gemini_quota_message()) from None
    except Exception:
        raise HTTPException(
            status_code=503,
            detail=_gemini_overload_message(models),
        ) from None


def _call_anthropic(
    system_prompt: str,
    user_message: str,
    *,
    max_output_tokens: int = 4096,
) -> str:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="ANTHROPIC_API_KEY is not configured. Add it to backend/.env",
        )

    client = anthropic.Anthropic(api_key=api_key)

    try:
        message = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=max_output_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
    except anthropic.APIError as exc:
        raise HTTPException(status_code=502, detail=f"Anthropic API error: {exc}") from exc

    parts = []
    for block in message.content:
        if getattr(block, "type", None) == "text":
            parts.append(block.text)

    text = "\n".join(parts).strip()
    if not text:
        raise HTTPException(status_code=502, detail="Empty response from Anthropic API")

    return text


def call_ai(
    system_prompt: str,
    user_message: str,
    *,
    max_output_tokens: int = 4096,
    json_mode: bool = True,
    task: AITask = "default",
) -> str:
    provider = _resolve_provider(task)

    if provider == "gemini":
        return _call_gemini(
            system_prompt,
            user_message,
            max_output_tokens=max_output_tokens,
            json_mode=json_mode,
        )
    if provider == "anthropic":
        json_hint = ""
        if json_mode:
            json_hint = (
                "\n\nCRITICAL: Respond with ONLY valid JSON. No markdown fences, no commentary."
            )
        return _call_anthropic(
            system_prompt + json_hint,
            user_message,
            max_output_tokens=max_output_tokens,
        )

    raise HTTPException(
        status_code=500,
        detail=f"Unknown AI provider configuration '{_effective_mode()}'.",
    )


def _extract_grounding_sources(response) -> list[dict[str, str]]:
    sources: list[dict[str, str]] = []
    seen: set[str] = set()

    candidate = None
    if getattr(response, "candidates", None):
        candidate = response.candidates[0]

    metadata = getattr(candidate, "grounding_metadata", None) if candidate else None
    if not metadata:
        return sources

    for chunk in metadata.grounding_chunks or []:
        web = getattr(chunk, "web", None)
        if not web:
            continue
        url = (web.uri or "").strip()
        title = (web.title or web.domain or url).strip()
        if not url or url in seen:
            continue
        seen.add(url)
        sources.append({"title": title, "url": url})

    return sources


def _web_search_duckduckgo_fallback(
    system_prompt: str,
    user_message: str,
    *,
    max_output_tokens: int,
    json_mode: bool,
) -> tuple[str, list[dict[str, str]]]:
    from web_search_fallback import build_web_context

    context, sources = build_web_context(user_message)
    enriched = user_message
    if context.strip():
        enriched = f"{user_message}\n\nWeb research snippets:\n{context}"

    text, _ = _call_gemini_attempts(
        system_prompt,
        enriched,
        max_output_tokens=max_output_tokens,
        json_mode=json_mode,
        tools=None,
    )
    return text, sources


def call_ai_with_web_search(
    system_prompt: str,
    user_message: str,
    *,
    max_output_tokens: int = 3072,
    json_mode: bool = True,
) -> tuple[str, list[dict[str, str]]]:
    """Research always uses Gemini Google Search (hybrid mode included)."""
    if _resolve_provider("research") != "gemini":
        from web_search_fallback import build_web_context

        context, sources = build_web_context(user_message)
        enriched = f"{user_message}\n\nWeb research snippets:\n{context}"
        return call_ai(system_prompt, enriched, task="research"), sources

    models = _gemini_models_to_try()
    grounding_tool = types.Tool(google_search=types.GoogleSearch())

    try:
        return _call_gemini_attempts(
            system_prompt,
            user_message,
            max_output_tokens=max_output_tokens,
            json_mode=json_mode,
            tools=[grounding_tool],
            extract_sources=True,
        )
    except GeminiQuotaExhausted:
        raise HTTPException(status_code=429, detail=_gemini_quota_message()) from None
    except Exception as exc:
        logger.warning("Gemini web search failed, trying without grounding tool: %s", exc)

    try:
        return _call_gemini_attempts(
            system_prompt,
            user_message,
            max_output_tokens=max_output_tokens,
            json_mode=json_mode,
            tools=None,
            extract_sources=False,
        )
    except GeminiQuotaExhausted:
        raise HTTPException(status_code=429, detail=_gemini_quota_message()) from None
    except Exception as exc:
        logger.warning("Gemini plain failed, trying DuckDuckGo fallback: %s", exc)

    try:
        return _web_search_duckduckgo_fallback(
            system_prompt,
            user_message,
            max_output_tokens=max_output_tokens,
            json_mode=json_mode,
        )
    except GeminiQuotaExhausted:
        raise HTTPException(status_code=429, detail=_gemini_quota_message()) from None
    except Exception:
        raise HTTPException(
            status_code=503,
            detail=_gemini_overload_message(models, web_search=True),
        ) from None
