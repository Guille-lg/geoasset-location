"""
SSE generator wrapper for the agent search pipeline.
"""

import json
import logging
from typing import AsyncGenerator

from app.services.agent_search import AgentSearchService

logger = logging.getLogger(__name__)


def sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


async def run_agent_pipeline_sse(
    company_name: str,
    company_id: str,
) -> AsyncGenerator[str, None]:
    """
    Wraps AgentSearchService.run() into an SSE byte stream.
    Each yielded string is a complete SSE frame ready for StreamingResponse.
    """
    service = AgentSearchService(company_name=company_name, company_id=company_id)
    async for event_name, event_data in service.run():
        yield sse_event(event_name, event_data)
