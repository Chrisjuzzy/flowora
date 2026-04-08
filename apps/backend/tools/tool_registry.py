from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional
import logging
import inspect

from tools.handlers import (
    http_tool,
    database_tool,
    web_search_tool,
    web_automation_tool,
    code_execution_tool,
    document_analysis_tool,
)

logger = logging.getLogger(__name__)


@dataclass
class ToolDefinition:
    name: str
    description: str
    input_schema: Dict[str, Any]
    handler: Callable[..., Any]


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        self._tools[tool.name] = tool
        logger.debug("Registered tool: %s", tool.name)

    def get(self, name: str) -> Optional[ToolDefinition]:
        return self._tools.get(name)

    def list_tools(self) -> Dict[str, ToolDefinition]:
        return dict(self._tools)

    def execute(self, name: str, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Any:
        tool = self.get(name)
        if not tool:
            raise ValueError(f"Tool '{name}' not found")
        if context is None:
            return tool.handler(arguments)
        try:
            sig = inspect.signature(tool.handler)
            if len(sig.parameters) >= 2:
                return tool.handler(arguments, context)
        except Exception:
            pass
        return tool.handler(arguments)


def _noop_tool(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {"status": "not_implemented", "message": "Tool execution stub", "input": payload}


tool_registry = ToolRegistry()

# Real tool integrations
tool_registry.register(
    ToolDefinition(
        name="web_search",
        description="Search the web for information using DuckDuckGo",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer"}
            },
            "required": ["query"]
        },
        handler=web_search_tool
    )
)
tool_registry.register(
    ToolDefinition(
        name="http_request",
        description="Call external HTTP APIs",
        input_schema={
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "method": {"type": "string"},
                "headers": {"type": "object"},
                "params": {"type": "object"},
                "json": {"type": "object"},
                "data": {"type": ["object", "string"]},
                "timeout": {"type": "integer"}
            },
            "required": ["url"]
        },
        handler=http_tool
    )
)
tool_registry.register(
    ToolDefinition(
        name="http_tool",
        description="Alias for HTTP API calls",
        input_schema={
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "method": {"type": "string"},
                "headers": {"type": "object"},
                "params": {"type": "object"},
                "json": {"type": "object"},
                "data": {"type": ["object", "string"]},
                "timeout": {"type": "integer"}
            },
            "required": ["url"]
        },
        handler=http_tool
    )
)
tool_registry.register(
    ToolDefinition(
        name="database_query",
        description="Run a read-only database query",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "params": {"type": "object"},
                "limit": {"type": "integer"}
            },
            "required": ["query"]
        },
        handler=database_tool
    )
)
tool_registry.register(
    ToolDefinition(
        name="database_tool",
        description="Alias for read-only database queries",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "params": {"type": "object"},
                "limit": {"type": "integer"}
            },
            "required": ["query"]
        },
        handler=database_tool
    )
)
tool_registry.register(
    ToolDefinition(
        name="code_execution",
        description="Execute Python code snippets in a sandbox",
        input_schema={
            "type": "object",
            "properties": {
                "code": {"type": "string"},
                "language": {"type": "string"}
            },
            "required": ["code"]
        },
        handler=code_execution_tool
    )
)
tool_registry.register(
    ToolDefinition(
        name="document_analysis",
        description="Extract text from documents",
        input_schema={
            "type": "object",
            "properties": {
                "content_base64": {"type": "string"},
                "object_name": {"type": "string"},
                "filename": {"type": "string"}
            }
        },
        handler=document_analysis_tool
    )
)
tool_registry.register(
    ToolDefinition(
        name="web_automation",
        description="Automate browser-based actions or scraping tasks",
        input_schema={
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "actions": {"type": "array"},
                "timeout": {"type": "integer"}
            },
            "required": ["url"]
        },
        handler=web_automation_tool
    )
)

# Optional stub for compatibility with existing flows
tool_registry.register(
    ToolDefinition(
        name="automation_task",
        description="Trigger an automation workflow or webhook",
        input_schema={
            "type": "object",
            "properties": {"task": {"type": "string"}, "payload": {"type": "object"}}
        },
        handler=_noop_tool
    )
)
