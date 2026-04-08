from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class ToolCall:
    name: str
    arguments: Dict[str, Any]


@dataclass
class PlanStep:
    step: int
    description: str
    tool: Optional[str] = None
    expected_output: Optional[str] = None


@dataclass
class ExecutionLogEntry:
    step: int
    phase: str
    message: str
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class RuntimeResult:
    status: str
    output: Any
    token_usage: int = 0
    execution_time_ms: int = 0
    cost_estimate: str = "0.0"
    tool_calls: List[ToolCall] = field(default_factory=list)
    plan: List[PlanStep] = field(default_factory=list)
    logs: List[ExecutionLogEntry] = field(default_factory=list)
    error: Optional[str] = None
    started_at: datetime = field(default_factory=datetime.utcnow)
    finished_at: Optional[datetime] = None
