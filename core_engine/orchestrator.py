from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

from .agents import DeveloperAgent, ProductManagerAgent, QAAgent


class State(StrEnum):
    RECEIVED = "received"
    SCHEMA_MAPPED = "schema_mapped"
    API_GENERATED = "api_generated"
    QA_SCANNED = "qa_scanned"
    REMEDIATING = "remediating"
    DEPLOYABLE = "deployable"
    FAILED = "failed"


@dataclass(slots=True)
class RunContext:
    brief: str
    state: State = State.RECEIVED
    artifacts: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    transitions: list[State] = field(default_factory=lambda: [State.RECEIVED])

    def transition(self, state: State) -> None:
        self.state = state
        self.transitions.append(state)


@dataclass(slots=True)
class Orchestrator:
    pm: ProductManagerAgent = field(default_factory=ProductManagerAgent)
    developer: DeveloperAgent = field(default_factory=DeveloperAgent)
    qa: QAAgent = field(default_factory=QAAgent)
    max_remediation_cycles: int = 2

    async def run(self, brief: str, source_root: str | Path = ".") -> RunContext:
        ctx = RunContext(brief=brief)
        try:
            schema = await self.pm.run(brief)
            ctx.artifacts["schema"] = schema.model_dump()
            ctx.artifacts["mapping"] = self.pm.schema_mapping(schema)
            ctx.transition(State.SCHEMA_MAPPED)

            endpoints = await self.developer.run(schema)
            ctx.artifacts["endpoints"] = [e.__dict__ for e in endpoints]
            ctx.transition(State.API_GENERATED)

            for cycle in range(self.max_remediation_cycles + 1):
                report = await self.qa.run(source_root)
                ctx.artifacts["qa_report"] = {
                    "passed": report.passed,
                    "findings": [f.__dict__ for f in report.findings],
                    "cycle": cycle,
                }
                ctx.transition(State.QA_SCANNED)
                if report.passed:
                    ctx.transition(State.DEPLOYABLE)
                    return ctx
                if cycle == self.max_remediation_cycles:
                    break
                ctx.transition(State.REMEDIATING)
                await asyncio.sleep(0)
                # Remediation is deliberately fail-closed: findings are returned to the
                # caller rather than silently rewriting source code without a reviewable plan.
            ctx.transition(State.FAILED)
            return ctx
        except Exception as exc:
            ctx.errors.append(str(exc))
            ctx.transition(State.FAILED)
            return ctx
