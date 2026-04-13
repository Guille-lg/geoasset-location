import logging
import os

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.companies import router as companies_router
from app.api.assets import router as assets_router
from app.api.documents import router as documents_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

app = FastAPI(
    title="GeoAssets Intelligence",
    summary="Geospatial intelligence platform for enterprise productive assets",
    version="1.0.0",
    root_path=os.environ.get("BACKEND_ROOT_URL", ""),
    docs_url="/docs",
    openapi_url="/docs/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content={"error": str(exc)})


@app.exception_handler(Exception)
async def exception_handler(request: Request, exc: Exception):
    logging.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"error": str(exc)})


@app.on_event("startup")
async def startup():
    from app.db.session import init_db
    await init_db()


@app.get("/health")
async def health():
    return {"status": "ok"}


app.include_router(companies_router)
app.include_router(assets_router)
app.include_router(documents_router)
