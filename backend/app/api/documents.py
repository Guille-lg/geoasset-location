import logging
import re
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from app.core.config import settings
from app.pipeline.doc_orchestrator import run_doc_pipeline_sse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/documents", tags=["Documents"])

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".pptx"}


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


@router.post("/analyze")
async def analyze_document(
    file: Optional[UploadFile] = File(default=None),
    company_name: Optional[str] = Form(default=None),
    force_refresh: bool = Form(default=False),
    # Agent-session fields — used instead of a file upload when the agent
    # has already downloaded a document to the server's temp directory.
    session_id: Optional[str] = Form(default=None),
    agent_filename: Optional[str] = Form(default=None),
    source_override: Optional[str] = Form(default=None),
):
    """
    Analyse a single document and stream SSE pipeline events.

    Two modes:
    1. Regular upload  — provide `file` as multipart.
    2. Agent session   — provide `session_id` + `agent_filename` (no upload);
                         the backend reads from the agent's temp directory.
    """
    max_size_bytes = settings.UPLOAD_MAX_SIZE_MB * 1024 * 1024

    if session_id and agent_filename:
        # --- Agent-session mode -------------------------------------------
        session_dir = Path(settings.AGENT_SESSION_DIR) / session_id
        file_path = session_dir / agent_filename

        if not file_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Agent session file not found: {agent_filename}",
            )

        suffix = file_path.suffix.lower()
        if suffix not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail="Unsupported file type in agent session.",
            )

        file_bytes = file_path.read_bytes()
        filename = agent_filename

    elif file is not None:
        # --- Regular upload mode ------------------------------------------
        filename = file.filename or "uploaded_document"
        suffix = Path(filename).suffix.lower()

        if suffix not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail="Unsupported file type. Use PDF, DOCX, or PPTX.",
            )

        file_bytes = await file.read()
        if not file_bytes:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        if len(file_bytes) > max_size_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Max allowed size is {settings.UPLOAD_MAX_SIZE_MB} MB.",
            )

    else:
        raise HTTPException(
            status_code=400,
            detail="Provide either a file upload or session_id + agent_filename.",
        )

    derived_company_name = (company_name or Path(filename).stem or "Uploaded Document").strip()
    company_id = f"doc_{_slug(derived_company_name) or 'company'}"

    return StreamingResponse(
        run_doc_pipeline_sse(
            company_id=company_id,
            company_name=derived_company_name,
            file_name=filename,
            file_bytes=file_bytes,
            force_refresh=force_refresh,
            source_override=source_override,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
