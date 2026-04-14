"""
CrewAI-powered agentic document search service.

The agent searches the web for PDF/DOCX/PPTX documents describing a company's
productive assets, downloads them, validates relevance, and saves to a session directory.

SSE bridge: CrewAI's kickoff() runs in a thread executor. Tools and the step_callback
emit events to an asyncio.Queue via loop.call_soon_threadsafe(). The async generator
reads from the queue and yields SSE-ready (event, data) tuples.
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
import io
import json
import logging
import re
import threading
import time
import uuid
from html import unescape
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple
from urllib.parse import quote_plus

import httpx
from crewai import Agent, Crew, LLM, Task
from crewai.tools import BaseTool
from pydantic import PrivateAttr

from app.core.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Rate-limit state for the DuckDuckGo MCP client.
# The server enforces 30 req/min and 1 req/sec; we add a client-side guard.
# ---------------------------------------------------------------------------
_DDG_MCP_MIN_INTERVAL: float = 1.1   # seconds between calls (≤ 1 req/sec)
_ddg_mcp_last_call: float = 0.0
_ddg_mcp_call_lock = threading.Lock()


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "").strip()


def _bing_fallback_search(query: str, max_results: int) -> list[dict[str, Any]]:
    """Scrape Bing as a last-resort fallback when the MCP server is unavailable."""
    url = f"https://www.bing.com/search?q={quote_plus(query)}&count={max_results}"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
        )
    }
    try:
        with httpx.Client(timeout=10, follow_redirects=True, headers=headers) as client:
            response = client.get(url)
            response.raise_for_status()
            html = response.text
    except Exception as exc:
        logger.warning("Bing fallback request failed for %r: %s", query, exc)
        return []

    pattern = re.compile(
        r'<li class="b_algo".*?<h2><a href="(?P<url>https?://[^"]+)"[^>]*>(?P<title>.*?)</a>'
        r'.*?(?:<div class="b_caption".*?<p>(?P<snippet>.*?)</p>)?',
        re.S,
    )

    results: list[dict[str, Any]] = []
    for match in pattern.finditer(html):
        url_val = unescape(match.group("url") or "").strip()
        if not url_val:
            continue
        title = unescape(_strip_html(match.group("title") or ""))
        snippet = unescape(_strip_html(match.group("snippet") or ""))[:300]
        results.append({"title": title, "url": url_val, "snippet": snippet})
        if len(results) >= max_results:
            break
    return results


def _parse_mcp_search_result(result: Any) -> list[dict[str, Any]]:
    """Parse the duckduckgo-mcp-server text output into [{title, url, snippet}].

    The server returns a formatted string:
        Found N search results:

        1. Title Here
           URL: https://...
           Summary: brief text...

        2. ...
    """
    text = ""
    if hasattr(result, "content"):
        for item in result.content:
            if hasattr(item, "text"):
                text += item.text

    if not text or "No results" in text:
        return []

    results: list[dict[str, Any]] = []
    # Split on lines that start a new numbered entry (e.g. "1. ", "2. ")
    entries = re.split(r"\n(?=\d+\.\s)", text)
    for entry in entries:
        entry = entry.strip()
        if not entry or not re.match(r"^\d+\.\s", entry):
            continue
        lines = entry.splitlines()
        title = re.sub(r"^\d+\.\s*", "", lines[0]).strip()
        url = ""
        snippet = ""
        for line in lines[1:]:
            line = line.strip()
            if line.startswith("URL:"):
                url = line[4:].strip()
            elif line.startswith("Summary:"):
                snippet = line[8:].strip()[:300]
        if url:
            results.append({"title": title, "url": url, "snippet": snippet})
    return results


class _DdgMcpClient:
    """Manages a persistent DuckDuckGo MCP server subprocess in a background thread.

    The subprocess is started once and kept alive for the lifetime of the process.
    A dedicated daemon thread owns the asyncio event loop; sync callers submit
    coroutines to it via asyncio.run_coroutine_threadsafe().
    """

    def __init__(self) -> None:
        self._loop = asyncio.new_event_loop()
        self._session: Any = None
        self._ready = threading.Event()

        self._thread = threading.Thread(
            target=self._run_loop,
            name="ddg-mcp-bg",
            daemon=True,
        )
        self._thread.start()

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._maintain())

    async def _maintain(self) -> None:
        """Connect to the DDG MCP server and reconnect automatically on failure."""
        import shutil
        from mcp import ClientSession, StdioServerParameters  # type: ignore
        from mcp.client.stdio import stdio_client  # type: ignore

        cmd = shutil.which("duckduckgo-mcp-server") or "duckduckgo-mcp-server"
        server_params = StdioServerParameters(command=cmd, args=[])

        while True:
            try:
                async with stdio_client(server_params) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        self._session = session
                        if not self._ready.is_set():
                            self._ready.set()
                        logger.info("DuckDuckGo MCP server connected (cmd: %s)", cmd)
                        # Block here; the loop remains free to execute call_tool tasks.
                        await asyncio.Event().wait()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                self._session = None
                logger.warning("DDG MCP connection lost (%s); reconnecting in 5 s", exc)
                if not self._ready.is_set():
                    self._ready.set()
                await asyncio.sleep(5)

    @property
    def available(self) -> bool:
        return self._session is not None

    def call_search(self, query: str, max_results: int) -> list[dict[str, Any]]:
        """Synchronous search call; safe to invoke from any thread."""
        if not self._session:
            raise RuntimeError("DDG MCP session not available")
        future = asyncio.run_coroutine_threadsafe(
            self._async_search(query, max_results),
            self._loop,
        )
        return future.result(timeout=15)

    async def _async_search(self, query: str, max_results: int) -> list[dict[str, Any]]:
        result = await self._session.call_tool(
            "search", {"query": query, "max_results": max_results}
        )
        return _parse_mcp_search_result(result)


_ddg_mcp_instance: Optional["_DdgMcpClient"] = None
_ddg_mcp_init_lock = threading.Lock()


def _get_ddg_mcp_client() -> "_DdgMcpClient":
    """Return the module-level singleton, initialising it on first call."""
    global _ddg_mcp_instance
    if _ddg_mcp_instance is None:
        with _ddg_mcp_init_lock:
            if _ddg_mcp_instance is None:
                client = _DdgMcpClient()
                client._ready.wait(timeout=30.0)
                _ddg_mcp_instance = client
    return _ddg_mcp_instance


def _ddgs_text_search(query: str, max_results: int = 10) -> list[dict[str, Any]]:
    """Search via the DuckDuckGo MCP server; falls back to Bing on failure."""
    global _ddg_mcp_last_call

    # --- Primary: DuckDuckGo MCP server ---
    try:
        client = _get_ddg_mcp_client()
        if client.available:
            # Enforce client-side rate limit (1.1 s between calls)
            with _ddg_mcp_call_lock:
                now = time.monotonic()
                wait = _DDG_MCP_MIN_INTERVAL - (now - _ddg_mcp_last_call)
                if wait > 0:
                    time.sleep(wait)
                _ddg_mcp_last_call = time.monotonic()

            results = client.call_search(query, max_results)
            if results:
                return results
    except Exception as exc:
        logger.warning("DDG MCP search failed for %r (%s); using Bing fallback", query, exc)

    # --- Fallback: Bing HTML scraping ---
    return _bing_fallback_search(query, max_results)

# ---------------------------------------------------------------------------
# Monkey-patch: fix CrewAI _parse_native_tool_call for Bedrock tool calls.
# In CrewAI 1.14.x the dict branch does:
#     func_args = func_info.get("arguments", "{}") or tool_call.get("input", {})
# The default "{}" is truthy, so the Bedrock `input` dict is NEVER reached
# and every tool call receives empty arguments → TypeError → infinite retry.
# The fix: use `func_info.get("arguments")` (returns None when missing).
# ---------------------------------------------------------------------------
try:
    from crewai.agents.crew_agent_executor import CrewAgentExecutor
    from crewai.utilities.string_utils import sanitize_tool_name as _sanitize

    def _patched_parse_native_tool_call(
        self, tool_call: Any
    ) -> "tuple[str, str, str | dict[str, Any]] | None":
        if hasattr(tool_call, "function"):
            call_id = getattr(tool_call, "id", f"call_{id(tool_call)}")
            func_name = _sanitize(tool_call.function.name)
            return call_id, func_name, tool_call.function.arguments
        if hasattr(tool_call, "function_call") and tool_call.function_call:
            call_id = f"call_{id(tool_call)}"
            func_name = _sanitize(tool_call.function_call.name)
            func_args = (
                dict(tool_call.function_call.args)
                if tool_call.function_call.args
                else {}
            )
            return call_id, func_name, func_args
        if hasattr(tool_call, "name") and hasattr(tool_call, "input"):
            call_id = getattr(tool_call, "id", f"call_{id(tool_call)}")
            func_name = _sanitize(tool_call.name)
            return call_id, func_name, tool_call.input
        if isinstance(tool_call, dict):
            call_id = (
                tool_call.get("id")
                or tool_call.get("toolUseId")
                or f"call_{id(tool_call)}"
            )
            func_info = tool_call.get("function", {})
            func_name = _sanitize(
                func_info.get("name", "") or tool_call.get("name", "")
            )
            # FIX: use None default so falsy check falls through to Bedrock input
            func_args = func_info.get("arguments") or tool_call.get("input", {})
            return call_id, func_name, func_args
        return None

    CrewAgentExecutor._parse_native_tool_call = _patched_parse_native_tool_call  # type: ignore[assignment]
    logger.info("Applied CrewAI _parse_native_tool_call patch for Bedrock tool args")
except Exception as _patch_err:
    logger.warning("Could not apply CrewAI Bedrock tool-args patch: %s", _patch_err)

# ---------------------------------------------------------------------------
# Monkey-patch 2: merge consecutive same-role messages in Bedrock Converse.
# After tool execution CrewAI appends  user(toolResult) + user(reasoning)
# back-to-back.  The Converse API requires alternating roles, so we merge
# consecutive same-role messages' content blocks into a single message.
# ---------------------------------------------------------------------------
try:
    from crewai.llms.providers.bedrock.completion import BedrockCompletion

    _original_format = BedrockCompletion._format_messages_for_converse

    def _patched_format_messages_for_converse(self, messages):
        converse_messages, system_message = _original_format(self, messages)
        if len(converse_messages) <= 1:
            return converse_messages, system_message
        merged: list = [converse_messages[0]]
        for msg in converse_messages[1:]:
            prev = merged[-1]
            if msg["role"] == prev["role"]:
                prev_content = prev["content"] if isinstance(prev["content"], list) else [{"text": prev["content"]}]
                cur_content = msg["content"] if isinstance(msg["content"], list) else [{"text": msg["content"]}]
                prev["content"] = prev_content + cur_content
            else:
                merged.append(msg)
        return merged, system_message

    BedrockCompletion._format_messages_for_converse = _patched_format_messages_for_converse  # type: ignore[assignment]
    logger.info("Applied Bedrock consecutive-message merge patch")
except Exception as _patch_err2:
    logger.warning("Could not apply Bedrock message-merge patch: %s", _patch_err2)

# ---------------------------------------------------------------------------
# Module-level session registry — allows tools running in a thread executor
# to communicate with the async event queue safely.
# ---------------------------------------------------------------------------
_session_registry: Dict[str, Dict[str, Any]] = {}

ASSET_KEYWORDS = {
    "planta", "fábrica", "almacén", "sede", "oficina", "instalación",
    "factory", "plant", "warehouse", "headquarters", "logistics",
    "logística", "instalaciones", "activos", "assets", "manufacturing",
    "distribution", "distribución", "centro", "facilities", "infraestructura",
    "nave", "terminal", "parque", "complejo", "hangar", "depósito",
}


def _emit_event(session_id: str, event_name: str, data: dict) -> None:
    """Thread-safe SSE event emission via the session registry."""
    state = _session_registry.get(session_id)
    if not state:
        return
    queue: asyncio.Queue = state["queue"]
    loop: asyncio.AbstractEventLoop = state["loop"]
    stop_flag: threading.Event = state["stop_flag"]
    if not stop_flag.is_set():
        loop.call_soon_threadsafe(queue.put_nowait, (event_name, data))


# ---------------------------------------------------------------------------
# CrewAI Tools
# ---------------------------------------------------------------------------

class WebSearchTool(BaseTool):
    name: str = "web_search"
    description: str = (
        "Search the web for documents about a company's productive assets. "
        "Input: a search query string (use varied Spanish and English terms). "
        "Returns: JSON list of results with title, url, and snippet. "
        "Look for annual reports, sustainability reports, investor presentations, "
        "and asset listings that are likely PDF/DOCX/PPTX files."
    )
    session_id: str = ""

    def _run(self, query: str) -> str:
        _emit_event(self.session_id, "agent_searching", {"query": query})

        state = _session_registry.get(self.session_id, {})
        stop_flag: Optional[threading.Event] = state.get("stop_flag")
        if stop_flag and stop_flag.is_set():
            return "[]"

        executor: Optional[ThreadPoolExecutor] = None
        future: Any = None
        try:
            executor = ThreadPoolExecutor(max_workers=1)
            future = executor.submit(_ddgs_text_search, query, 10)
            results = future.result(timeout=15)
            _emit_event(self.session_id, "agent_found_urls", {"count": len(results)})
            return json.dumps(results, ensure_ascii=False)
        except FutureTimeoutError:
            if executor is not None and future is not None:
                future.cancel()
                executor.shutdown(wait=False, cancel_futures=True)
            logger.warning("DuckDuckGo search timed out for %r", query)
            _emit_event(self.session_id, "agent_found_urls", {"count": 0})
            return "[]"
        except Exception as exc:
            logger.warning("DuckDuckGo search failed for %r: %s", query, exc)
            _emit_event(self.session_id, "agent_found_urls", {"count": 0})
            return "[]"
        finally:
            if executor is not None:
                executor.shutdown(wait=False, cancel_futures=True)


class DownloadDocumentTool(BaseTool):
    name: str = "download_document"
    description: str = (
        "Download and validate a document from a URL. "
        "Only accepts PDF, DOCX, or PPTX files under 25 MB that are relevant "
        "to the company's productive assets. "
        "Input: the full URL of the document. "
        "Returns: 'ACCEPTED: <reason>' or 'REJECTED: <reason>'."
    )
    session_id: str = ""
    company_name: str = ""

    def _run(self, url: str) -> str:  # noqa: PLR0911
        state = _session_registry.get(self.session_id, {})
        stop_flag: Optional[threading.Event] = state.get("stop_flag")
        found_files: List[dict] = state.get("found_files", [])
        session_dir: Optional[Path] = state.get("session_dir")

        if stop_flag and stop_flag.is_set():
            return "REJECTED: Time limit reached."

        if len(found_files) >= settings.AGENT_MAX_FILES:
            return f"REJECTED: Already collected {settings.AGENT_MAX_FILES} documents."

        # Derive filename
        raw_name = url.split("?")[0].rstrip("/").split("/")[-1] or "document"
        suffix = Path(raw_name).suffix.lower()

        _emit_event(self.session_id, "agent_downloading", {"url": url, "filename": raw_name})

        try:
            with httpx.Client(timeout=30, follow_redirects=True) as client:
                # HEAD request to probe content type & size
                try:
                    head = client.head(url, timeout=10)
                    ct = head.headers.get("content-type", "").lower()
                    cl = int(head.headers.get("content-length", 0))
                    max_bytes = settings.UPLOAD_MAX_SIZE_MB * 1024 * 1024
                    if cl and cl > max_bytes:
                        return f"REJECTED: File too large ({cl // (1024*1024)} MB)."
                    # Infer suffix from content-type when URL has no extension
                    if suffix not in {".pdf", ".docx", ".pptx"}:
                        if "pdf" in ct:
                            suffix = ".pdf"
                        elif "word" in ct or "docx" in ct or "openxmlformats" in ct:
                            suffix = ".docx"
                        elif "powerpoint" in ct or "pptx" in ct or "presentation" in ct:
                            suffix = ".pptx"
                        else:
                            # Last resort: check URL keywords
                            url_lower = url.lower()
                            if "pdf" in url_lower:
                                suffix = ".pdf"
                            elif "docx" in url_lower or "word" in url_lower:
                                suffix = ".docx"
                            elif "pptx" in url_lower or "powerpoint" in url_lower:
                                suffix = ".pptx"
                            else:
                                return "REJECTED: URL does not appear to be a PDF, DOCX, or PPTX document."
                except httpx.HTTPError:
                    if suffix not in {".pdf", ".docx", ".pptx"}:
                        return "REJECTED: Cannot determine document type from URL."

                response = client.get(url, timeout=30)
                if response.status_code != 200:
                    return f"REJECTED: HTTP {response.status_code}."

                file_bytes = response.content
                if len(file_bytes) < 1024:
                    return "REJECTED: File too small to be a real document."
                if len(file_bytes) > settings.UPLOAD_MAX_SIZE_MB * 1024 * 1024:
                    return f"REJECTED: File too large (>{settings.UPLOAD_MAX_SIZE_MB} MB)."

        except Exception as exc:
            reason = f"Download error: {exc}"
            _emit_event(self.session_id, "agent_rejected", {"filename": raw_name, "reason": reason})
            return f"REJECTED: {reason}"

        # --- Relevance validation via text extraction -----------------------
        relevance_ok, relevance_reason = self._validate_relevance(file_bytes, suffix)
        if not relevance_ok:
            _emit_event(self.session_id, "agent_rejected", {"filename": raw_name, "reason": relevance_reason})
            return f"REJECTED: {relevance_reason}"

        # --- Save file -------------------------------------------------------
        if not session_dir:
            return "REJECTED: No session directory available."

        stem = Path(raw_name).stem or "document"
        filename = f"{stem}{suffix}"
        save_path = session_dir / filename
        counter = 1
        while save_path.exists():
            save_path = session_dir / f"{stem}_{counter}{suffix}"
            counter += 1
        filename = save_path.name

        try:
            save_path.write_bytes(file_bytes)
        except OSError as exc:
            return f"REJECTED: Could not save file: {exc}"

        found_files.append(
            {
                "filename": filename,
                "size": len(file_bytes),
                "url": url,
                "relevance_reason": relevance_reason,
            }
        )

        _emit_event(
            self.session_id,
            "agent_accepted",
            {"filename": filename, "size": len(file_bytes), "reason": relevance_reason},
        )
        return f"ACCEPTED: {relevance_reason}. Saved as {filename}."

    def _validate_relevance(self, file_bytes: bytes, suffix: str) -> Tuple[bool, str]:
        """Extract text and check for company name + asset keywords."""
        text = ""
        try:
            if suffix == ".pdf":
                import pdfplumber
                with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                    text = "\n".join(
                        (page.extract_text() or "") for page in pdf.pages[:5]
                    )
            elif suffix == ".docx":
                try:
                    import docx as python_docx
                    doc = python_docx.Document(io.BytesIO(file_bytes))
                    text = "\n".join(p.text for p in doc.paragraphs[:100])
                except Exception:
                    pass
        except Exception as exc:
            logger.debug("Text extraction failed: %s", exc)
            return True, "Accepted by file type (text extraction unavailable)"

        if not text.strip():
            return True, "Accepted — document appears to be image-based or encrypted"

        text_lower = text.lower()

        # Company name check
        company_words = [w for w in self.company_name.lower().split() if len(w) > 3]
        has_company = any(w in text_lower for w in company_words) if company_words else True

        # Asset keyword density
        keyword_hits = sum(1 for k in ASSET_KEYWORDS if k in text_lower)

        if not has_company:
            return False, f"Document does not mention '{self.company_name}'"
        if keyword_hits < 2:
            return False, f"Document lacks asset/location content ({keyword_hits} keywords found)"

        return True, f"Company mentioned + {keyword_hits} asset-related terms"


# ---------------------------------------------------------------------------
# Agent Search Service
# ---------------------------------------------------------------------------

class AgentSearchService:
    """
    Orchestrates the CrewAI agent run and bridges sync tool events to the
    async SSE generator via an asyncio.Queue.
    """

    def __init__(self, company_name: str, company_id: str) -> None:
        self.company_name = company_name
        self.company_id = company_id
        self.session_id = str(uuid.uuid4())
        self.session_dir = Path(settings.AGENT_SESSION_DIR) / self.session_id
        self.session_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Synchronous crew execution (runs inside thread executor)
    # ------------------------------------------------------------------

    def _run_crew(
        self,
        queue: asyncio.Queue,
        loop: asyncio.AbstractEventLoop,
        stop_flag: threading.Event,
    ) -> None:
        found_files: List[dict] = []
        _session_registry[self.session_id] = {
            "queue": queue,
            "loop": loop,
            "session_dir": self.session_dir,
            "found_files": found_files,
            "stop_flag": stop_flag,
        }

        try:
            web_search = WebSearchTool(session_id=self.session_id)
            download_tool = DownloadDocumentTool(
                session_id=self.session_id,
                company_name=self.company_name,
            )

            llm = LLM(
                model=settings.AGENT_LITELLM_MODEL,
                timeout=max(60.0, float(settings.LITELLM_TIMEOUT)),
            )

            agent = Agent(
                role="Geospatial Asset Intelligence Researcher",
                goal=(
                    f"Find and download PDF/DOCX/PPTX documents describing the physical "
                    f"locations and productive assets of {self.company_name} in Spain"
                ),
                backstory=(
                    "You are an expert corporate intelligence researcher specialising in "
                    "locating company asset documentation. You know how to construct effective "
                    "web searches in both Spanish and English, evaluate search results for "
                    "relevant document URLs, and efficiently download only files that contain "
                    "genuine information about a company's factories, warehouses, offices, "
                    "logistics centres, energy plants, and other productive assets."
                ),
                tools=[web_search, download_tool],
                llm=llm,
                verbose=False,
                max_iter=settings.AGENT_MAX_ITERATIONS,
                max_execution_time=settings.AGENT_MAX_DURATION_SECONDS,
                allow_delegation=False,
            )

            task = Task(
                description=(
                    f"Search the web and download relevant documents about the productive "
                    f"assets of **{self.company_name}** in Spain.\n\n"
                    "Strategy:\n"
                    f"1. Use `web_search` with varied queries such as:\n"
                    f"   - '{self.company_name} informe anual activos productivos instalaciones filetype:pdf'\n"
                    f"   - '{self.company_name} annual report facilities Spain PDF'\n"
                    f"   - '{self.company_name} memoria sostenibilidad plantas almacenes PDF'\n"
                    f"   - '{self.company_name} investor presentation assets locations site:.com'\n"
                    f"   - '{self.company_name} plan estratégico instalaciones PDF site:.es'\n"
                    "2. For each result that looks like a downloadable document (URL contains "
                    "   .pdf/.docx/.pptx or keywords like 'download', 'informe', 'report', "
                    "   'memoria', 'annual'), call `download_document`.\n"
                    f"3. Stop when you have {settings.AGENT_MAX_FILES} accepted documents "
                    "   or when no more promising URLs remain.\n\n"
                    "Be methodical. If one query returns no documents, try a different angle."
                ),
                expected_output=(
                    f"A concise summary of the documents found for {self.company_name}: "
                    "how many were downloaded, what types of assets are described, "
                    "and what key locations were identified."
                ),
                agent=agent,
            )

            def step_callback(step_output: Any, agent_name: str = "") -> None:
                if stop_flag.is_set():
                    return
                try:
                    log_text = ""
                    if hasattr(step_output, "log"):
                        log_text = str(step_output.log)
                    elif hasattr(step_output, "thought"):
                        log_text = str(step_output.thought)
                    elif isinstance(step_output, str):
                        log_text = step_output
                    else:
                        log_text = str(step_output)

                    if not log_text:
                        return

                    # Extract only the Thought portion (strip Action/Observation lines)
                    thought_lines: List[str] = []
                    action_line = ""
                    for line in log_text.splitlines():
                        stripped = line.strip()
                        if stripped.startswith("Action:") and not action_line:
                            action_line = stripped
                        if stripped.startswith("Action Input:") and action_line:
                            action_line = f"{action_line} ({stripped})"
                        if stripped.startswith("Observation:"):
                            break
                        if stripped.startswith("Thought:"):
                            stripped = stripped[8:].strip()
                        if stripped:
                            thought_lines.append(stripped)

                    thought = " ".join(thought_lines)[:400].strip()
                    if not thought and action_line:
                        thought = action_line[:220]
                    if thought and len(thought) > 10:
                        _emit_event(self.session_id, "agent_thinking", {"content": thought})
                except Exception:
                    pass

            crew = Crew(
                agents=[agent],
                tasks=[task],
                verbose=False,
                step_callback=step_callback,
            )

            _emit_event(
                self.session_id,
                "agent_thinking",
                {
                    "content": (
                        f"Starting research run with model '{settings.AGENT_LITELLM_MODEL}'. "
                        "Planning search queries and candidate document sources."
                    )
                },
            )

            logger.info("Crew kickoff starting for session %s", self.session_id)
            crew.kickoff()
            logger.info("Crew kickoff completed for session %s", self.session_id)

        except Exception as exc:
            logger.exception("Agent crew execution failed: %s", exc)
            _emit_event(self.session_id, "agent_error", {"message": str(exc)})

        finally:
            # Signal the async generator that the thread is done
            loop.call_soon_threadsafe(queue.put_nowait, ("__done__", {}))

    # ------------------------------------------------------------------
    # Async SSE generator
    # ------------------------------------------------------------------

    async def run(self) -> AsyncGenerator[Tuple[str, dict], None]:
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue()
        stop_flag = threading.Event()

        yield "agent_started", {
            "company_name": self.company_name,
            "session_id": self.session_id,
            "max_duration_seconds": settings.AGENT_MAX_DURATION_SECONDS,
        }

        # Launch crew in thread executor so it doesn't block the event loop
        future = loop.run_in_executor(None, self._run_crew, queue, loop, stop_flag)

        deadline = loop.time() + settings.AGENT_MAX_DURATION_SECONDS
        timed_out = False
        last_event_at = loop.time()

        try:
            while True:
                remaining = deadline - loop.time()
                if remaining <= 0:
                    stop_flag.set()
                    timed_out = True
                    break

                try:
                    event_name, event_data = await asyncio.wait_for(
                        queue.get(), timeout=min(2.0, remaining)
                    )
                except asyncio.TimeoutError:
                    now = loop.time()
                    if now - last_event_at >= 12:
                        yield "agent_thinking", {
                            "content": "Agent is reasoning and evaluating tool calls..."
                        }
                        last_event_at = now
                    continue

                if event_name == "__done__":
                    break

                last_event_at = loop.time()
                yield event_name, event_data

        except Exception as exc:
            logger.error("Agent SSE generator error: %s", exc)
            stop_flag.set()
            timed_out = True

        # Wait for the thread to exit (brief window)
        try:
            await asyncio.wait_for(asyncio.wrap_future(future), timeout=8.0)
        except (asyncio.TimeoutError, Exception):
            pass

        # Drain any remaining events enqueued just before __done__
        while not queue.empty():
            try:
                event_name, event_data = queue.get_nowait()
                if event_name not in ("__done__",):
                    yield event_name, event_data
            except Exception:
                break

        # Collect found files from registry before cleanup
        state = _session_registry.pop(self.session_id, {})
        found_files: List[dict] = state.get("found_files", [])

        final_event = "agent_timeout" if timed_out else "agent_complete"
        yield final_event, {
            "session_id": self.session_id,
            "found_files": found_files,
            "total_found": len(found_files),
        }
