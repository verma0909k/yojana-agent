"""Trace logging for YojanaAgent live inspection panel."""

from datetime import datetime
from typing import Any
from shared.schemas import TraceStep


class TraceLogger:
    """Collects chronological trace events from all sub-agents."""

    def __init__(self):
        self.steps: list[TraceStep] = []

    def log(self, agent_name: str, action: str, details: dict[str, Any] = None) -> TraceStep:
        step = TraceStep(
            agent_name=agent_name,
            action=action,
            details=details or {},
            timestamp=datetime.now().strftime("%H:%M:%S.%f")[:-3]
        )
        self.steps.append(step)
        return step

    def clear(self):
        self.steps.clear()

    def get_steps(self) -> list[TraceStep]:
        return list(self.steps)
