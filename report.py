"""Company Builder report generator.

Compiles all step results into structured output:
- JSON for API responses
- Formatted text for CLI display
- HTML for web display
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class StepResult:
    """Result of a single company-building step."""

    step_number: int
    step_name: str
    service_id: str
    agent_id: str
    success: bool
    data_summary: str
    cost: float
    latency_ms: float
    error: str | None = None
    raw_data: Any = None

    def to_dict(self) -> dict:
        return {
            "step": self.step_number,
            "name": self.step_name,
            "service": self.service_id,
            "agent": self.agent_id,
            "success": self.success,
            "summary": self.data_summary,
            "cost": round(self.cost, 6),
            "latency_ms": round(self.latency_ms, 1),
            "error": self.error,
        }


@dataclass
class CompanyReport:
    """Full report from a company-building run."""

    company_description: str
    company_name: str = ""
    steps: list[StepResult] = field(default_factory=list)
    discovered_services: int = 0
    start_time: float = field(default_factory=time.time)
    end_time: float = 0.0

    @property
    def total_cost(self) -> float:
        return sum(s.cost for s in self.steps)

    @property
    def successful_steps(self) -> int:
        return sum(1 for s in self.steps if s.success)

    @property
    def failed_steps(self) -> int:
        return sum(1 for s in self.steps if not s.success)

    @property
    def duration_seconds(self) -> float:
        end = self.end_time or time.time()
        return end - self.start_time

    def add_step(self, step: StepResult):
        self.steps.append(step)

    def finalize(self):
        self.end_time = time.time()

    def to_json(self) -> dict:
        """Machine-readable JSON report."""
        return {
            "company": {
                "description": self.company_description,
                "name": self.company_name,
            },
            "summary": {
                "total_steps": len(self.steps),
                "successful": self.successful_steps,
                "failed": self.failed_steps,
                "total_cost_usd": round(self.total_cost, 6),
                "duration_seconds": round(self.duration_seconds, 1),
                "services_discovered": self.discovered_services,
            },
            "steps": [s.to_dict() for s in self.steps],
            "meta": {
                "builder": "sardis-company-builder",
                "version": "1.0.0",
                "timestamp": self.start_time,
            },
        }

    def to_text(self) -> str:
        """Human-readable formatted text report."""
        lines = []
        lines.append("=" * 70)
        lines.append("  SARDIS COMPANY BUILDER — RUN REPORT")
        lines.append("=" * 70)
        lines.append("")
        lines.append(f"  Company: {self.company_name or self.company_description}")
        lines.append(f"  Duration: {self.duration_seconds:.1f}s")
        lines.append(f"  Total Cost: ${self.total_cost:.4f} USDC")
        lines.append(f"  Services Discovered: {self.discovered_services}")
        lines.append(f"  Steps: {self.successful_steps}/{len(self.steps)} successful")
        lines.append("")

        lines.append("-" * 70)
        lines.append("  EXECUTION STEPS")
        lines.append("-" * 70)
        for step in self.steps:
            icon = "[+]" if step.success else "[!]"
            lines.append(f"  {icon} Step {step.step_number}: {step.step_name}")
            lines.append(f"      Service: {step.service_id} | Agent: {step.agent_id}")
            lines.append(f"      Cost: ${step.cost:.4f} | Latency: {step.latency_ms:.0f}ms")
            if step.data_summary:
                summary = step.data_summary[:200]
                lines.append(f"      Result: {summary}")
            if step.error:
                lines.append(f"      Error: {step.error}")
            lines.append("")

        lines.append("-" * 70)
        lines.append("  SPENDING BREAKDOWN")
        lines.append("-" * 70)
        by_service: dict[str, float] = {}
        for step in self.steps:
            by_service[step.service_id] = by_service.get(step.service_id, 0) + step.cost
        for svc, cost in sorted(by_service.items(), key=lambda x: -x[1]):
            bar = "#" * max(1, int(cost / self.total_cost * 40)) if self.total_cost > 0 else ""
            lines.append(f"  {svc:20s} ${cost:.4f}  {bar}")
        lines.append(f"  {'TOTAL':20s} ${self.total_cost:.4f}")
        lines.append("")
        lines.append("=" * 70)

        return "\n".join(lines)

    def to_html(self) -> str:
        """HTML report for web display."""
        data = self.to_json()
        steps_html = "\n".join(self._step_html(s) for s in self.steps)
        return f"""<!DOCTYPE html>
<html>
<head>
    <title>Sardis Company Builder Report</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0d1117; color: #c9d1d9; padding: 2rem; max-width: 900px; margin: auto; }}
        h1 {{ color: #58a6ff; }}
        h2 {{ color: #8b949e; border-bottom: 1px solid #21262d; padding-bottom: 0.5rem; }}
        .step {{ background: #161b22; border: 1px solid #21262d; border-radius: 6px; padding: 1rem; margin: 0.5rem 0; }}
        .step.success {{ border-left: 3px solid #3fb950; }}
        .step.error {{ border-left: 3px solid #d29922; }}
        .stat {{ display: inline-block; background: #21262d; padding: 0.5rem 1rem; border-radius: 4px; margin: 0.25rem; }}
        .cost {{ color: #3fb950; font-weight: bold; }}
        pre {{ background: #161b22; padding: 1rem; border-radius: 6px; overflow-x: auto; font-size: 0.85rem; }}
    </style>
</head>
<body>
    <h1>Sardis Company Builder</h1>
    <p>{self.company_name or self.company_description}</p>

    <div>
        <span class="stat">Steps: {self.successful_steps}/{len(self.steps)}</span>
        <span class="stat">Failed: {self.failed_steps}</span>
        <span class="stat cost">Cost: ${self.total_cost:.4f}</span>
        <span class="stat">Duration: {self.duration_seconds:.1f}s</span>
        <span class="stat">Services: {self.discovered_services}</span>
    </div>

    <h2>Execution Steps</h2>
    {steps_html}

    <h2>Raw Data</h2>
    <pre>{json.dumps(data, indent=2)}</pre>
</body>
</html>"""

    def _step_html(self, step: StepResult) -> str:
        cls = "success" if step.success else "error"
        return f"""<div class="step {cls}">
    <b>Step {step.step_number}: {step.step_name}</b><br>
    Service: {step.service_id} | Agent: {step.agent_id} |
    <span class="cost">${step.cost:.4f}</span> | {step.latency_ms:.0f}ms<br>
    {step.data_summary[:200] if step.data_summary else ''}
    {f'<br><i>Error: {step.error}</i>' if step.error else ''}
</div>"""
