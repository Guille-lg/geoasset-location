# Document Upload & Asset Extraction Pipeline

Add the ability to upload company reports (PDF, DOCX, PPTX), parse them with Docling (CPU-optimized), extract geolocation data for productive assets via a multi-stage LLM pipeline, and display results on the existing map.

---

## Architecture Overview

The new feature adds a **parallel data source** alongside the existing Google Maps pipeline. Users can upload documents from the landing page, and the system processes them through a dedicated document pipeline that reuses the existing scoring, map visualization, and persistence layers.

```
┌────────────────────────────────────────────────────────────────────┐
│                       LANDING PAGE (SearchBar.vue)                 │
│         ┌─────────────────┐        ┌──────────────────────┐        │
│         │ Company Search  │        │ Document Upload      │        │
│         │ (existing)      │        │ PDF / DOCX / PPTX    │        │
│         └────────┬────────┘        └──────────┬───────────┘        │
└──────────────────┼─────────────────────────────┼───────────────────┘
                   │                             │
                   ▼                             ▼
┌──────────────────────────┐   ┌─────────────────────────────────────┐
│ Existing Pipeline        │   │ Document Pipeline (NEW)             │
│ Step 0: Identify company │   │ Step D0: Docling parse (CPU)        │
│ Step 1: Google Maps      │   │ Step D1: Chunk (HybridChunker)      │
│ Step 2: LLM filter       │   │ Step D2: LLM extract per chunk      │
│ Step 3: LLM enrich       │   │ Step D3: Deduplicate & merge        │
│ Step 4: Scoring          │   │ Step D4: LLM geocode & enrich       │
│ Step D5: Scoring (reuse step4)      │
└──────────┬───────────────┘   └──────────┬──────────────────────────┘
           │                              │
           ▼                              ▼
┌────────────────────────────────────────────────────────────────────┐
│              Same results view: map + sidebar + export             │
└────────────────────────────────────────────────────────────────────┘
```

### Document Pipeline Detail (Steps D0–D5)

```
 Upload (PDF/DOCX/PPTX)
        │
        ▼
 ┌──────────────┐
 │ D0: Docling   │  CPU-only: AcceleratorDevice.CPU, no OCR for DOCX/PPTX
 │    Parse      │  Output: DoclingDocument (structured markdown)
 └──────┬───────┘
        │
        ▼
 ┌──────────────┐
 │ D1: Hybrid    │  HybridChunker with ~2000 token chunks
 │    Chunking   │  Preserves headings/tables context via contextualize()
 └──────┬───────┘
        │
        ▼
 ┌──────────────────┐
 │ D2: LLM Extract   │  Parallel: each chunk → LLM with structured prompt
 │    per Chunk      │  Output: list of {asset_name, category, location_hints,
 │    (batched)      │          address, coordinates_if_found, evidence_quote}
 └──────┬────────────┘
        │
        ▼
 ┌──────────────────┐
 │ D3: Deduplicate   │  Merge identical assets from different chunks
 │    & Merge        │  Combine evidence, keep richest metadata
 └──────┬────────────┘
        │
        ▼
 ┌──────────────────┐
 │ D4: LLM Geocode   │  For assets without coordinates:
 │    & Enrich       │  LLM infers lat/lon from address/context
 │                   │  + Google Geocoding API as fallback
 └──────┬────────────┘
        │
        ▼
 ┌──────────────────┐
 │ D5: Scoring       │  Reuses existing step4_scoring.py
 │    (reuse)       │  Adapted signal weights for document source
 └──────┬────────────┘
        │
        ▼
  Assets displayed on map (same as Google Maps pipeline)
```

**Why this is sophisticated (not just "paste document into LLM"):**
1. **Structural parsing** — Docling preserves document structure (headings, tables, sections) instead of raw text
2. **Semantic chunking** — HybridChunker creates context-aware chunks with heading breadcrumbs, not arbitrary splits
3. **Per-chunk parallel extraction** — Each chunk is independently analyzed by an LLM, keeping token usage efficient and enabling parallelism
4. **Deduplication & evidence merging** — Same asset mentioned across multiple sections gets consolidated with combined evidence
5. **Two-phase geocoding** — LLM attempts coordinate inference first, then falls back to Google Geocoding API
6. **Reusable scoring** — Confidence scoring adapted for document-sourced assets with different signal weights

---

## Implementation Steps

### 1. Backend — Dependencies & Config

- **Add to `pyproject.toml`**: `docling` (includes PDF/DOCX/PPTX support), `python-multipart` (for FastAPI file uploads)
- **Add to `config.py`**: `UPLOAD_MAX_SIZE_MB`, `OMP_NUM_THREADS` setting for docling CPU control
- **Add to Dockerfiles**: system dep `libgl1-mesa-glx` (or use `opencv-python-headless` — needed by docling)

### 2. Backend — Document Processing Service (`app/services/document_parser.py`)

- Initialize `DocumentConverter` with CPU-only settings:
  - `AcceleratorOptions(device=AcceleratorDevice.CPU, num_threads=4)`
  - `PdfPipelineOptions` with `do_ocr=False` (for speed on text-based PDFs; can be toggled)
- Accept `UploadFile` → convert to `DocumentStream` → parse → return markdown text
- Use `HybridChunker` to split document into ~2000-token chunks with context

### 3. Backend — Document Pipeline Steps

- **`app/pipeline/steps/doc_step0_parse.py`** — Receive uploaded file bytes, run Docling, return structured text
- **`app/pipeline/steps/doc_step1_chunk.py`** — Run HybridChunker, return list of contextualized chunks
- **`app/pipeline/steps/doc_step2_extract.py`** — For each chunk, call LLM with extraction prompt (parallel batches). New prompt in `prompts/v1/extract_doc_assets.yaml`
- **`app/pipeline/steps/doc_step3_dedup.py`** — Deduplicate assets by name similarity + location proximity
- **`app/pipeline/steps/doc_step4_geocode.py`** — For assets without coordinates: LLM geocoding + Google Geocoding API fallback. New prompt in `prompts/v1/geocode_assets.yaml`
- **`app/pipeline/steps/doc_step5_scoring.py`** — Adapted scoring with document-specific signal weights (e.g. `evidence_strength`, `address_specificity`, `coordinate_source`)

### 4. Backend — Document Pipeline Orchestrator (`app/pipeline/doc_orchestrator.py`)

- New `run_doc_pipeline_sse()` async generator, mirrors existing `run_pipeline_sse()` pattern
- Emits SSE events for each step: parse → chunk → extract → dedup → geocode → score → complete
- Converts final assets to same `Asset` model, persists to DB and cache

### 5. Backend — New API Endpoint (`app/api/documents.py`)

- `POST /api/v1/documents/analyze` — Accepts multipart file upload (PDF/DOCX/PPTX), optional `company_name` parameter
- Validates file type and size
- Returns `StreamingResponse` with SSE events (same pattern as `/assets/analyze`)
- Register router in `main.py`

### 6. Backend — New LLM Prompts

- **`prompts/v1/extract_doc_assets.yaml`** — System prompt for extracting asset locations from a document chunk. Requests structured JSON with: asset name, category, location clues, address, coordinates (if mentioned), evidence quote
- **`prompts/v1/geocode_assets.yaml`** — System prompt for inferring lat/lon from address descriptions and location context

### 7. Frontend — Landing Page Update (`SearchBar.vue`)

- Add a document upload zone below the search bar (drag-and-drop + file picker)
- Accept `.pdf`, `.docx`, `.pptx` files
- On upload: set store state, switch to processing view with document mode
- Optional text field for company name (helps LLM context)

### 8. Frontend — Backend Service (`services/backend.ts`)

- New `startDocumentAnalysisSSE()` function that POSTs multipart form data to `/api/v1/documents/analyze`
- Reads SSE stream with same event handler pattern as `startAnalysisSSE()`

### 9. Frontend — Store Update (`stores/store.ts`)

- Add `analysisMode: 'search' | 'document'` to state
- Add `uploadedFileName` to state for display in processing view
- Update `AppView` type if needed

### 10. Frontend — Processing View Update (`ProcessingView.vue`)

- Detect `analysisMode` and show document pipeline steps (D0–D5) instead of Google Maps steps
- Reuse all existing animation/progress infrastructure

### 11. Frontend — Types Update (`types/types.ts`)

- `Asset` type already accommodates document-sourced assets (the `data_sources` field will contain `"document_upload"` + `"llm_inference"`)
- `google_place_id` will be set to a generated ID for document-sourced assets

### 12. Docker Updates

- **`Dockerfile` & `dev.Dockerfile`**: add `libgl1-mesa-glx` or ensure `opencv-python-headless` is used
- **`docker-compose.yml`**: add `OMP_NUM_THREADS=4` env var to backend service

### 13. README.md Update

- Add new section documenting the Document Upload feature
- Include the pipeline diagram (ASCII art above)
- Document the new API endpoint
- Update architecture diagram to show document pipeline
- Add docling to the tech stack table

---

## Files to Create

| File | Purpose |
|------|---------|
| `backend/app/api/documents.py` | New API router for document upload |
| `backend/app/services/document_parser.py` | Docling wrapper (CPU-optimized) |
| `backend/app/pipeline/doc_orchestrator.py` | Document pipeline SSE orchestrator |
| `backend/app/pipeline/steps/doc_step0_parse.py` | Docling parsing step |
| `backend/app/pipeline/steps/doc_step1_chunk.py` | HybridChunker step |
| `backend/app/pipeline/steps/doc_step2_extract.py` | LLM extraction per chunk |
| `backend/app/pipeline/steps/doc_step3_dedup.py` | Deduplication & merge |
| `backend/app/pipeline/steps/doc_step4_geocode.py` | Geocoding (LLM + API fallback) |
| `backend/app/pipeline/steps/doc_step5_scoring.py` | Document-adapted scoring |
| `backend/app/prompts/v1/extract_doc_assets.yaml` | Extraction prompt |
| `backend/app/prompts/v1/geocode_assets.yaml` | Geocoding prompt |

## Files to Modify

| File | Changes |
|------|---------|
| `backend/pyproject.toml` | Add `docling`, `python-multipart` deps |
| `backend/app/main.py` | Register `documents` router |
| `backend/app/core/config.py` | Add upload/docling config vars |
| `backend/app/pipeline/models.py` | Add `DocumentAnalyzeRequest` model + document-source asset variants |
| `backend/Dockerfile` | Add system deps for docling |
| `backend/dev.Dockerfile` | Add system deps for docling |
| `docker-compose.yml` | Add `OMP_NUM_THREADS` env |
| `dev.docker-compose.yml` | Add `OMP_NUM_THREADS` env |
| `frontend/src/components/SearchBar.vue` | Add upload zone |
| `frontend/src/services/backend.ts` | Add `startDocumentAnalysisSSE()` |
| `frontend/src/stores/store.ts` | Add `analysisMode`, `uploadedFileName` |
| `frontend/src/types/types.ts` | Add `AppView` variant if needed |
| `frontend/src/components/ProcessingView.vue` | Document pipeline steps |
| `frontend/src/App.vue` | Minor: handle document mode |
| `README.md` | Document new feature + pipeline diagram |
