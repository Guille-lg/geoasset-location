import logging
import re
from pathlib import Path

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
    file: UploadFile = File(...),
    company_name: str | None = Form(default=None),
    force_refresh: bool = Form(default=False),
):
    filename = file.filename or "uploaded_document"
    suffix = Path(filename).suffix.lower()

    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported file type. Use PDF, DOCX, or PPTX.")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    max_size_bytes = settings.UPLOAD_MAX_SIZE_MB * 1024 * 1024
    if len(file_bytes) > max_size_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max allowed size is {settings.UPLOAD_MAX_SIZE_MB} MB.",
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
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
