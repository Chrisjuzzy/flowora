import base64
import io
import logging
import os
import re
import tempfile
import subprocess
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import httpx
from sqlalchemy import text

from config_production import settings
from services.tool_permissions import ToolPermissionService
from services.object_storage import ObjectStorageService

logger = logging.getLogger(__name__)


def _require_permission(context: Optional[Dict[str, Any]], tool_name: str) -> None:
    if not context:
        return
    db = context.get("db")
    agent_id = context.get("agent_id")
    if not db or not agent_id:
        return
    allowed = ToolPermissionService.get_allowed_tools(db, agent_id)
    if allowed and tool_name not in allowed:
        raise PermissionError(f"Tool '{tool_name}' not permitted for agent")


def _is_domain_allowed(url: str) -> bool:
    allowlist = settings.HTTP_TOOL_ALLOWLIST
    blocklist = settings.HTTP_TOOL_BLOCKLIST
    domain = urlparse(url).hostname or ""

    if blocklist:
        blocked = {d.strip().lower() for d in blocklist.split(",") if d.strip()}
        if domain.lower() in blocked:
            return False

    if allowlist:
        allowed = {d.strip().lower() for d in allowlist.split(",") if d.strip()}
        return domain.lower() in allowed

    return True


def http_tool(payload: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    _require_permission(context, "http_tool")
    url = payload.get("url")
    if not url:
        return {"status": "error", "error": "Missing url"}
    if not _is_domain_allowed(url):
        return {"status": "error", "error": "Domain not allowed"}

    method = (payload.get("method") or "GET").upper()
    headers = payload.get("headers") or {}
    params = payload.get("params") or {}
    json_body = payload.get("json")
    data = payload.get("data")
    timeout = min(int(payload.get("timeout", settings.HTTP_TOOL_TIMEOUT_SECONDS)), 30)

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.request(
                method,
                url,
                headers=headers,
                params=params,
                json=json_body,
                data=data
            )
        text_body = response.text[: settings.HTTP_TOOL_MAX_CHARS]
        return {
            "status": "ok",
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "body": text_body
        }
    except Exception as exc:
        logger.warning("HTTP tool error: %s", exc)
        return {"status": "error", "error": str(exc)}


def database_tool(payload: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    _require_permission(context, "database_tool")
    if not context or not context.get("db"):
        return {"status": "error", "error": "Database context missing"}

    query = (payload.get("query") or "").strip()
    params = payload.get("params") or {}

    if not query:
        return {"status": "error", "error": "Missing query"}

    lowered = query.lower()
    forbidden = ["insert", "update", "delete", "drop", "alter", "create", "grant", "revoke"]
    if any(keyword in lowered for keyword in forbidden):
        return {"status": "error", "error": "Only SELECT queries are allowed"}
    if not lowered.startswith("select"):
        return {"status": "error", "error": "Only SELECT queries are allowed"}
    if ";" in query:
        return {"status": "error", "error": "Multiple statements are not allowed"}

    max_rows = int(payload.get("limit", settings.DB_TOOL_MAX_ROWS))
    if "limit" not in lowered:
        query = f"{query} LIMIT {max_rows}"

    try:
        result = context["db"].execute(text(query), params)
        rows = [dict(row) for row in result.mappings().all()]
        return {"status": "ok", "rows": rows, "count": len(rows)}
    except Exception as exc:
        logger.warning("Database tool error: %s", exc)
        return {"status": "error", "error": str(exc)}


def web_search_tool(payload: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    _require_permission(context, "web_search")
    query = payload.get("query")
    if not query:
        return {"status": "error", "error": "Missing query"}

    limit = int(payload.get("limit", 5))
    params = {
        "q": query,
        "format": "json",
        "no_html": 1,
        "skip_disambig": 1
    }
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get("https://api.duckduckgo.com/", params=params)
            resp.raise_for_status()
            data = resp.json()

        results = []
        related = data.get("RelatedTopics") or []
        for item in related:
            if "Text" in item and "FirstURL" in item:
                results.append(
                    {"title": item.get("Text"), "url": item.get("FirstURL"), "snippet": item.get("Text")}
                )
            elif "Topics" in item:
                for sub in item.get("Topics") or []:
                    if "Text" in sub and "FirstURL" in sub:
                        results.append(
                            {"title": sub.get("Text"), "url": sub.get("FirstURL"), "snippet": sub.get("Text")}
                        )

        return {
            "status": "ok",
            "abstract": data.get("Abstract"),
            "results": results[:limit]
        }
    except Exception as exc:
        logger.warning("Web search error: %s", exc)
        return {"status": "error", "error": str(exc)}


def web_automation_tool(payload: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    _require_permission(context, "web_automation")
    url = payload.get("url")
    if not url:
        return {"status": "error", "error": "Missing url"}

    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        return {"status": "error", "error": f"Playwright not available: {exc}"}

    actions = payload.get("actions") or []
    timeout = int(payload.get("timeout", 15000))

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=timeout, wait_until="domcontentloaded")
            for action in actions:
                if not isinstance(action, dict):
                    continue
                action_type = action.get("type")
                if action_type == "click":
                    page.click(action.get("selector", ""))
                elif action_type == "fill":
                    page.fill(action.get("selector", ""), action.get("value", ""))
                elif action_type == "wait":
                    page.wait_for_timeout(int(action.get("ms", 500)))
                elif action_type == "scroll":
                    page.mouse.wheel(0, int(action.get("delta", 800)))

            title = page.title()
            content = page.content()[: settings.WEB_AUTOMATION_MAX_CHARS]
            browser.close()
            return {"status": "ok", "title": title, "content": content}
    except Exception as exc:
        logger.warning("Web automation error: %s", exc)
        return {"status": "error", "error": str(exc)}


def code_execution_tool(payload: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    _require_permission(context, "code_execution")
    code = payload.get("code") or ""
    if not code:
        return {"status": "error", "error": "Missing code"}

    if len(code) > settings.CODE_TOOL_MAX_CHARS:
        return {"status": "error", "error": "Code too large"}

    forbidden = [r"\bimport\s+os\b", r"\bimport\s+subprocess\b", r"\bimport\s+socket\b", r"\bopen\(", r"\beval\(", r"\bexec\("]
    if any(re.search(pattern, code) for pattern in forbidden):
        return {"status": "error", "error": "Forbidden code pattern"}

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "snippet.py")
            with open(file_path, "w", encoding="utf-8") as handle:
                handle.write(code)

            result = subprocess.run(
                ["python", "-I", "-S", file_path],
                capture_output=True,
                text=True,
                timeout=settings.CODE_TOOL_TIMEOUT_SECONDS
            )
            stdout = (result.stdout or "")[: settings.CODE_TOOL_MAX_OUTPUT_CHARS]
            stderr = (result.stderr or "")[: settings.CODE_TOOL_MAX_OUTPUT_CHARS]
            return {
                "status": "ok" if result.returncode == 0 else "error",
                "return_code": result.returncode,
                "stdout": stdout,
                "stderr": stderr
            }
    except subprocess.TimeoutExpired:
        return {"status": "error", "error": "Execution timed out"}
    except Exception as exc:
        logger.warning("Code execution error: %s", exc)
        return {"status": "error", "error": str(exc)}


def document_analysis_tool(payload: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    _require_permission(context, "document_analysis")
    content_b64 = payload.get("content_base64")
    object_name = payload.get("object_name")
    filename = payload.get("filename") or payload.get("file_path")

    data: Optional[bytes] = None
    if content_b64:
        try:
            data = base64.b64decode(content_b64)
        except Exception as exc:
            logger.warning("Document analysis base64 decode failed: %s", exc)
            return {"status": "error", "error": "Invalid base64 content"}
    elif object_name:
        try:
            storage = ObjectStorageService()
            response = storage.download(object_name)
            data = response.read()
            response.close()
        except Exception as exc:
            logger.warning("Document analysis download failed: %s", exc)
            return {"status": "error", "error": "Document download failed"}
        if not filename:
            filename = object_name
    else:
        return {"status": "error", "error": "Provide content_base64 or object_name"}

    if not data:
        return {"status": "error", "error": "No data received"}
    if len(data) > settings.DOC_TOOL_MAX_BYTES:
        return {"status": "error", "error": "Document too large"}

    ext = (filename or "").lower()
    try:
        if ext.endswith(".pdf"):
            try:
                from pypdf import PdfReader
            except Exception as exc:
                return {"status": "error", "error": f"pypdf not available: {exc}"}
            reader = PdfReader(io.BytesIO(data))
            text_out = "\n".join(page.extract_text() or "" for page in reader.pages)
        elif ext.endswith(".docx"):
            try:
                import docx
            except Exception as exc:
                return {"status": "error", "error": f"python-docx not available: {exc}"}
            doc = docx.Document(io.BytesIO(data))
            text_out = "\n".join(p.text for p in doc.paragraphs)
        else:
            text_out = data.decode("utf-8", errors="ignore")
    except Exception as exc:
        logger.warning("Document analysis error: %s", exc)
        return {"status": "error", "error": str(exc)}

    text_out = text_out[: settings.DOC_TOOL_MAX_CHARS]
    return {"status": "ok", "text": text_out, "length": len(text_out)}
