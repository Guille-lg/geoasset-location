import logging

from app.services.document_parser import parse_document_to_markdown

logger = logging.getLogger(__name__)


async def parse_uploaded_document(file_name: str, file_bytes: bytes) -> str:
    markdown = await parse_document_to_markdown(file_name, file_bytes)
    logger.info("Doc Step D0: parsed '%s' into %s markdown chars", file_name, len(markdown))
    return markdown
