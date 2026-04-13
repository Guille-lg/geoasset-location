import asyncio
import json
import logging
from typing import List, Optional

import litellm

from app.core.config import settings

logger = logging.getLogger(__name__)

litellm.drop_params = True

_semaphore: Optional[asyncio.Semaphore] = None


def get_semaphore() -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(settings.LITELLM_MAX_WORKERS)
    return _semaphore


async def llm_completion(messages: list, temperature: float = 0.1, max_tokens: int = 4096) -> Optional[str]:
    sem = get_semaphore()
    async with sem:
        try:
            response = await litellm.acompletion(
                model=settings.LITELLM_MODEL,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=settings.LITELLM_TIMEOUT,
                aws_region_name=settings.AWS_REGION_NAME,
                response_format={"type": "json_object"},
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM error: {e}")
            if settings.LITELLM_FALLBACK_MODEL:
                try:
                    response = await litellm.acompletion(
                        model=settings.LITELLM_FALLBACK_MODEL,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        timeout=settings.LITELLM_TIMEOUT,
                        aws_region_name=settings.AWS_REGION_NAME,
                    )
                    return response.choices[0].message.content
                except Exception as e2:
                    logger.error(f"Fallback LLM error: {e2}")
            return None


async def llm_json(messages: list, temperature: float = 0.1) -> Optional[dict]:
    content = await llm_completion(messages, temperature=temperature)
    if not content:
        return None
    try:
        content = content.strip()
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:-1]) if len(lines) > 2 else content
        return json.loads(content)
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse LLM JSON: {e}\nContent: {content[:500]}")
        return None
