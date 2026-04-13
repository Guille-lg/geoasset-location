import logging
from typing import List

from app.services.document_parser import chunk_document_markdown

logger = logging.getLogger(__name__)


async def chunk_document(markdown_text: str) -> List[str]:
    chunks = await chunk_document_markdown(markdown_text)
    logger.info("Doc Step D1: generated %s chunks", len(chunks))
    return chunks
