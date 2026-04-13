import asyncio
import os
import tempfile
from typing import List

from app.core.config import settings

_docling_converter = None
_hybrid_chunker = None


def _get_docling_converter():
    global _docling_converter
    if _docling_converter is None:
        from docling.document_converter import DocumentConverter  # type: ignore

        _docling_converter = DocumentConverter()
    return _docling_converter


def _get_hybrid_chunker():
    global _hybrid_chunker
    if _hybrid_chunker is None:
        from docling.chunking import HybridChunker  # type: ignore

        _hybrid_chunker = HybridChunker(max_tokens=2000)
    return _hybrid_chunker


def _chunk_fallback(markdown_text: str, max_chars: int = 8000) -> List[str]:
    paragraphs = [p.strip() for p in markdown_text.split("\n\n") if p.strip()]
    if not paragraphs:
        return []

    chunks: List[str] = []
    current: List[str] = []
    current_len = 0

    for paragraph in paragraphs:
        p_len = len(paragraph)
        if current and current_len + p_len > max_chars:
            chunks.append("\n\n".join(current))
            current = []
            current_len = 0

        current.append(paragraph)
        current_len += p_len

    if current:
        chunks.append("\n\n".join(current))

    return chunks


def _parse_with_docling_sync(file_name: str, file_bytes: bytes) -> str:
    os.environ["OMP_NUM_THREADS"] = str(settings.OMP_NUM_THREADS)

    suffix = os.path.splitext(file_name)[1].lower() or ".bin"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=True) as tmp:
        tmp.write(file_bytes)
        tmp.flush()

        converter = _get_docling_converter()
        result = converter.convert(tmp.name)
        document = getattr(result, "document", result)

        if hasattr(document, "export_to_markdown"):
            markdown = document.export_to_markdown()
            if isinstance(markdown, str) and markdown.strip():
                return markdown

        if hasattr(document, "to_markdown"):
            markdown = document.to_markdown()
            if isinstance(markdown, str) and markdown.strip():
                return markdown

        if hasattr(result, "text") and isinstance(result.text, str) and result.text.strip():
            return result.text

    raise ValueError("Docling could not extract markdown content")


async def parse_document_to_markdown(file_name: str, file_bytes: bytes) -> str:
    try:
        return await asyncio.to_thread(_parse_with_docling_sync, file_name, file_bytes)
    except Exception as exc:
        raise RuntimeError(f"Document parsing failed: {exc}") from exc


async def chunk_document_markdown(markdown_text: str) -> List[str]:
    try:
        chunker = _get_hybrid_chunker()
        chunks = []
        for chunk in chunker.chunk(markdown_text):
            if hasattr(chunk, "contextualize"):
                value = chunk.contextualize()
            elif hasattr(chunk, "text"):
                value = chunk.text
            else:
                value = str(chunk)
            if value and str(value).strip():
                chunks.append(str(value).strip())

        if chunks:
            return chunks
    except Exception:
        pass

    return _chunk_fallback(markdown_text)
