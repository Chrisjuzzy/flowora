import json
import logging
from typing import List, Optional

from services.agent_runtime.models import PlanStep

logger = logging.getLogger(__name__)


def _extract_json_array(text: str) -> Optional[list]:
    if not text:
        return None
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(text[start : end + 1])
    except Exception:
        return None


class PlanGenerator:
    def __init__(self, max_steps: int = 6) -> None:
        self.max_steps = max_steps

    async def build_plan(
        self,
        provider,
        goal: str,
        system_prompt: str,
        tool_names: Optional[list] = None
    ) -> List[PlanStep]:
        tool_list = ", ".join(tool_names or [])
        prompt = (
            "Create a concise execution plan for the following goal. "
            "Return a JSON array of steps, each with fields: "
            "`step` (int), `description` (string), optional `tool` (string), "
            "and optional `expected_output` (string). "
            f"Limit to {self.max_steps} steps.\n\n"
            f"Goal: {goal}\n"
            f"Available tools: {tool_list or 'none'}"
        )

        try:
            response = await provider.generate_with_metadata(prompt, system_prompt=system_prompt)
            raw_text = response.get("text", "")
            data = _extract_json_array(raw_text)
            if not data:
                return [PlanStep(step=1, description=goal)]

            steps: List[PlanStep] = []
            for item in data[: self.max_steps]:
                if not isinstance(item, dict):
                    continue
                steps.append(
                    PlanStep(
                        step=int(item.get("step", len(steps) + 1)),
                        description=str(item.get("description", "")).strip() or goal,
                        tool=item.get("tool"),
                        expected_output=item.get("expected_output")
                    )
                )
            return steps or [PlanStep(step=1, description=goal)]
        except Exception as exc:
            logger.warning("Plan generation failed: %s", exc)
            return [PlanStep(step=1, description=goal)]
