import re
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from models import Agent, User
from services.guardrails import EthicalGuardrailsService
import logging

logger = logging.getLogger(__name__)

class SandboxService:
    """
    Provides a safe execution environment for agents.
    1. Input Validation (Size, Injection patterns)
    2. Output Validation (Ethical, PII)
    3. Resource Limits (Timeouts - handled by caller mostly)
    4. Permission Checks (Tools, Data Access)
    """

    MAX_INPUT_LENGTH = 10000
    MAX_OUTPUT_LENGTH = 10000
    FORBIDDEN_PATTERNS = [
        r"os\.system", r"subprocess\.call", r"exec\(", r"eval\(", 
        r"__import__", r"open\(", r"read\("
    ]

    @staticmethod
    def validate_execution_request(db: Session, agent_id: int, user_id: int, input_data: str) -> Dict[str, Any]:
        """
        Validates if the execution is safe to proceed.
        Returns {"valid": bool, "error": str}
        """
        # 1. Input Size
        if input_data and len(input_data) > SandboxService.MAX_INPUT_LENGTH:
            return {"valid": False, "error": f"Input exceeds maximum length of {SandboxService.MAX_INPUT_LENGTH} chars"}

        # 2. Injection / Malicious Code Checks (Basic regex)
        # This is primarily for agents that might interpret code. 
        # Even if they don't run it, preventing them from seeing it is safer.
        if input_data:
            for pattern in SandboxService.FORBIDDEN_PATTERNS:
                if re.search(pattern, input_data):
                    logger.warning(f"Suspicious pattern '{pattern}' found in input for agent {agent_id}")
                    # Block execution for suspicious patterns
                    return {"valid": False, "error": f"Input contains forbidden pattern: {pattern}"}
        
        # 3. Ethical Guardrails (Content Safety)
        if input_data:
            if not EthicalGuardrailsService.check_input(db, None, input_data):
                return {"valid": False, "error": "Input violated ethical guardrails"}

        return {"valid": True, "error": None}

    @staticmethod
    def validate_execution_result(db: Session, agent_id: int, result_text: str) -> Dict[str, Any]:
        """
        Validates the output from the agent.
        """
        # 1. Output Size
        if len(result_text) > SandboxService.MAX_OUTPUT_LENGTH:
            return {"valid": False, "error": "Output exceeds maximum length"}

        # 2. Ethical Guardrails
        if not EthicalGuardrailsService.check_output(db, None, result_text):
             return {"valid": False, "error": "Output violated ethical guardrails"}

        return {"valid": True, "error": None}

sandbox_service = SandboxService()
