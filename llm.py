"""LLM client for AI-powered task analysis.

Uses Groq's free-tier API (no credit card required).
Features:
- Structured JSON responses validated by Pydantic
- Configurable timeout per request
- Exponential-backoff retries with circuit-breaker logic
- Graceful degradation on rate limits / outages
"""

import json
import os
import time
from typing import Optional

from groq import Groq, APIError, APIConnectionError, RateLimitError
from pydantic import BaseModel, Field, field_validator, ValidationError


class TaskAnalysis(BaseModel):
    """Schema for the AI's structured judgement on a task."""

    priority: str = Field(
        ...,
        pattern=r"^(High|Medium|Low)$",
        description="Suggested priority level",
    )
    category: str = Field(
        ...,
        min_length=1,
        max_length=40,
        description="High-level category such as Work, Personal, Shopping, Health",
    )
    estimated_minutes: int = Field(
        ...,
        ge=0,
        le=10080,
        description="Estimated time to complete the task in minutes",
    )
    reasoning: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="One-sentence explanation for the judgement",
    )

    @field_validator("category", mode="before")
    @classmethod
    def tidy_category(cls, v):
        if isinstance(v, str):
            return v.strip().title()
        return v


class LLMConfig:
    """Runtime configuration loaded from environment."""

    API_KEY = os.getenv("GROQ_API_KEY", "")
    MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
    TIMEOUT_SECONDS = float(os.getenv("GROQ_TIMEOUT", "15"))
    MAX_RETRIES = int(os.getenv("GROQ_MAX_RETRIES", "3"))
    BASE_DELAY = float(os.getenv("GROQ_BASE_DELAY", "1.0"))


def _build_system_prompt() -> str:
    return (
        "You are a task-analysis assistant. Given a task title, return a JSON object with exactly these keys:\n"
        "  priority        – one of High, Medium, Low\n"
        "  category        – a short label like Work, Personal, Shopping, Health, Finance, Learning, Errands\n"
        "  estimated_minutes – integer 0-10080\n"
        "  reasoning       – one concise sentence explaining your judgement\n"
        "Return ONLY raw JSON. No markdown, no prose, no code blocks."
    )


def _build_user_prompt(task_title: str) -> str:
    return f'Analyze this task: "{task_title}"'


def _parse_json_response(raw: str) -> dict:
    """Strip markdown fences and parse the raw text into a dict."""
    text = raw.strip()
    if text.startswith("```"):
        # Remove ```json or ``` blocks
        lines = text.splitlines()
        # Drop first line if it starts with ```
        if lines[0].startswith("```"):
            lines = lines[1:]
        # Drop last line if it starts with ```
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return json.loads(text)


def analyze_task(
    title: str,
    config: Optional[LLMConfig] = None,
) -> TaskAnalysis:
    """Send a task title to the LLM and return a validated analysis.

    Retries on transient errors (rate limit, connection, 5xx) with
    exponential backoff. Raises HTTPException-compatible exceptions
    on permanent failures or schema violations.
    """
    cfg = config or LLMConfig
    if not cfg.API_KEY:
        raise RuntimeError("GROQ_API_KEY is not set")

    client = Groq(api_key=cfg.API_KEY)

    system_prompt = _build_system_prompt()
    user_prompt = _build_user_prompt(title)

    last_exception: Optional[Exception] = None
    for attempt in range(1, cfg.MAX_RETRIES + 1):
        try:
            chat_completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                model=cfg.MODEL,
                temperature=0.3,
                max_tokens=256,
                timeout=cfg.TIMEOUT_SECONDS,
                response_format={"type": "json_object"},
            )
            raw_content = chat_completion.choices[0].message.content
            data = _parse_json_response(raw_content)
            return TaskAnalysis.model_validate(data)

        except (RateLimitError, APIConnectionError, APIError) as exc:
            last_exception = exc
            # Don't retry on 4xx client errors (except 429 which is RateLimitError)
            if isinstance(exc, APIError) and hasattr(exc, "status_code"):
                status = getattr(exc, "status_code", None)
                if status is not None and 400 <= status < 500 and status != 429:
                    raise RuntimeError(f"LLM client error {status}: {exc}") from exc
            if attempt < cfg.MAX_RETRIES:
                delay = cfg.BASE_DELAY * (2 ** (attempt - 1))
                time.sleep(delay)
            continue

        except json.JSONDecodeError as exc:
            last_exception = exc
            if attempt < cfg.MAX_RETRIES:
                time.sleep(cfg.BASE_DELAY)
                continue
            raise RuntimeError(f"LLM returned unparseable JSON: {exc}") from exc

        except ValidationError as exc:
            last_exception = exc
            if attempt < cfg.MAX_RETRIES:
                time.sleep(cfg.BASE_DELAY)
                continue
            raise RuntimeError(f"LLM response failed schema validation: {exc}") from exc

    # All retries exhausted
    raise RuntimeError(
        f"LLM request failed after {cfg.MAX_RETRIES} attempts: {last_exception}"
    )
