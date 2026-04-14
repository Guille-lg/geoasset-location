import logging
from pathlib import Path
from urllib.parse import unquote

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from app.core.config import settings
from app.pipeline.agent_orchestrator import run_agent_pipeline_sse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/agent", tags=["Agent"])


class AgentSearchRequest(BaseModel):
    company_name: str
    company_id: str


def _resolve_session_file(session_id: str, filename: str) -> Path:
    decoded = unquote(filename)
    safe_name = Path(decoded).name
    if safe_name != decoded:
        raise HTTPException(status_code=400, detail="Invalid filename")

    session_dir = Path(settings.AGENT_SESSION_DIR) / session_id
    file_path = session_dir / safe_name
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Document not found in agent session")
    return file_path


@router.post("/search")
async def agent_search(request: AgentSearchRequest):
    """
    Start the agentic document search pipeline.
    Streams SSE events:
      agent_started, agent_thinking, agent_searching, agent_found_urls,
      agent_downloading, agent_accepted, agent_rejected, agent_error,
      agent_complete | agent_timeout
    """
    return StreamingResponse(
        run_agent_pipeline_sse(
            company_name=request.company_name,
            company_id=request.company_id,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/sessions/{session_id}/documents/{filename:path}")
async def get_agent_session_document(session_id: str, filename: str):
    file_path = _resolve_session_file(session_id, filename)
    suffix = file_path.suffix.lower()
    media_type = {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    }.get(suffix, "application/octet-stream")

    safe_filename = file_path.name.replace('"', "")
    return FileResponse(
        path=file_path,
        media_type=media_type,
        headers={"Content-Disposition": f'inline; filename="{safe_filename}"'},
    )


@router.get("/sessions/{session_id}/documents/{filename:path}/metadata")
async def get_agent_session_document_metadata(session_id: str, filename: str):
    file_path = _resolve_session_file(session_id, filename)
    stat = file_path.stat()

    page_count = None
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        try:
            import pdfplumber

            with pdfplumber.open(str(file_path)) as pdf:
                page_count = len(pdf.pages)
        except Exception as exc:
            logger.warning("Could not read PDF page count for %s: %s", file_path.name, exc)

    return {
        "filename": file_path.name,
        "size": stat.st_size,
        "page_count": page_count,
        "extension": suffix,
    }
