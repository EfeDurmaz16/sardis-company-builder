"""Sardis Company Builder — Autonomous AI agent that starts companies.

The agent discovers MPP services, uses Claude to plan which services to use,
executes the plan, adapts based on results, and generates specs for coding agents.

No fixed pipeline — the AI decides what to do based on available services
and the specific company idea.

Usage:
    python company_builder.py "AI-powered micropayments platform"
"""

from __future__ import annotations

import json
import logging
import sys
import time

from discovery import ServiceDiscovery
from services import MPPCaller
from agent import Agent, AgentPlan, AgentStep
from report import CompanyReport, StepResult

logger = logging.getLogger("company_builder")


class CompanyBuilder:
    """Autonomous company builder powered by AI agent + MPP services."""

    def __init__(self, company_description: str, budget: float = 5.0):
        self.company_description = company_description
        self.budget = budget
        self.spent = 0.0

        # Core components
        self.discovery = ServiceDiscovery()
        self.caller = MPPCaller()
        self.agent = Agent(self.caller, self.discovery)

        # State
        self.report = CompanyReport(company_description=company_description)
        self.step_counter = 0
        self.completed_results: list[dict] = []

    @property
    def budget_remaining(self) -> float:
        return max(0, self.budget - self.spent)

    def build(self) -> CompanyReport:
        """Execute the autonomous company-building pipeline."""
        logger.info("=" * 60)
        logger.info("  SARDIS COMPANY BUILDER (Autonomous Agent)")
        logger.info("  Goal: %s", self.company_description)
        logger.info("  Budget: $%.2f USDC", self.budget)
        logger.info("=" * 60)

        try:
            # Phase 0: Discover services
            services = self._discover_services()

            # Phase 1: AI creates the plan
            plan = self._create_plan(services)

            # Phase 2: Execute the plan with adaptive loop
            self._execute_plan(plan)

            # Phase 3: Generate specs for coding agents
            self._generate_specs(plan)

        except Exception as e:
            logger.error("Pipeline error: %s", e, exc_info=True)

        self.report.finalize()
        return self.report

    def _discover_services(self) -> list:
        """Discover available MPP services."""
        step_num = self._next_step()
        logger.info("Step %d: Discovering MPP services...", step_num)

        services = self.discovery.discover_all()
        self.report.discovered_services = len(services)

        ids = [s.id for s in services]
        self.report.add_step(StepResult(
            step_number=step_num, step_name="Service Discovery",
            service_id="tempo-directory", agent_id="orchestrator",
            success=len(services) > 0,
            data_summary=f"Discovered {len(services)} services: {', '.join(ids[:12])}...",
            cost=0.0, latency_ms=0, raw_data=ids,
        ))

        return services

    def _create_plan(self, services: list) -> AgentPlan:
        """Ask the AI agent to create an execution plan."""
        step_num = self._next_step()
        logger.info("Step %d: AI agent creating plan...", step_num)

        t0 = time.monotonic()
        plan = self.agent.create_plan(self.company_description, services)
        latency = (time.monotonic() - t0) * 1000

        self.report.company_name = plan.company_name
        cost = 0.01  # Claude call cost
        self.spent += cost

        plan_summary = (
            f"Company: {plan.company_name} | "
            f"Steps: {len(plan.steps)} | "
            f"Phases: {', '.join(plan.phases)} | "
            f"Est. cost: ${plan.total_estimated_cost:.2f}"
        )

        logger.info("Plan: %s", plan_summary)
        for i, step in enumerate(plan.steps):
            logger.info("  [%d] %s (%s) — %s", i + 1, step.name, step.service_id, step.reason[:60])

        self.report.add_step(StepResult(
            step_number=step_num, step_name="AI Planning",
            service_id="anthropic", agent_id="planner",
            success=len(plan.steps) > 0,
            data_summary=plan_summary,
            cost=cost, latency_ms=latency,
            raw_data={"company_name": plan.company_name, "summary": plan.summary,
                      "step_count": len(plan.steps), "phases": plan.phases},
        ))

        return plan

    def _execute_plan(self, plan: AgentPlan):
        """Execute the agent's plan, adapting after each phase."""
        remaining_steps = list(plan.steps)
        current_phase = ""

        while remaining_steps and self.budget_remaining > 0.02:
            step = remaining_steps.pop(0)

            # Log phase transitions
            if step.phase != current_phase:
                current_phase = step.phase
                logger.info("--- Phase: %s ---", current_phase.upper())

            # Execute the step
            self._execute_step(step)

            # After completing a phase, ask agent if we should adapt
            next_phase = remaining_steps[0].phase if remaining_steps else None
            if next_phase and next_phase != current_phase:
                adapted = self._maybe_adapt(remaining_steps)
                if adapted is not None:
                    remaining_steps = adapted

    def _execute_step(self, step: AgentStep):
        """Execute a single step from the plan."""
        step_num = self._next_step()
        logger.info("Step %d: %s via %s...", step_num, step.name, step.service_id)

        # Discover the service URL
        svc = self.discovery.get_service(step.service_id)
        if not svc:
            self._record_skip(step_num, step.name, step.service_id, "Service not found in directory")
            return

        # Validate endpoint path — must start with /
        endpoint = step.endpoint_path
        if not endpoint or not endpoint.startswith("/"):
            endpoint = self._resolve_endpoint(svc, step)
            if not endpoint:
                self._record_skip(step_num, step.name, step.service_id, f"No valid endpoint found")
                return
            logger.info("  Resolved endpoint: %s → %s", step.endpoint_path, endpoint)

        # Special handling for StableUpload (2-step upload)
        if step.service_id == "stableupload" and "/upload" in endpoint:
            self._execute_upload_step(step_num, step, svc)
            return

        # Execute the call
        result = self.caller.call(
            service_url=svc.service_url,
            endpoint_path=endpoint,
            method=step.method,
            data=step.data,
            service_id=step.service_id,
            cost_estimate=step.cost_estimate,
        )

        self.spent += result.cost
        self._record_result(step_num, step.name, step.service_id, step.phase, result)

        # Store for adaptation
        self.completed_results.append({
            "step": step.name,
            "service": step.service_id,
            "phase": step.phase,
            "success": result.success,
            "summary": self._summarize_data(result.data) if result.success else result.error,
        })

    def _execute_upload_step(self, step_num: int, step: AgentStep, svc):
        """Handle StableUpload's 2-step upload process."""
        # Step 1: Get upload slot
        slot_data = step.data or {"filename": "index.html", "contentType": "text/html", "tier": "10mb"}
        result = self.caller.call(
            service_url=svc.service_url, endpoint_path="/api/upload",
            method="POST", data=slot_data,
            service_id="stableupload", cost_estimate=step.cost_estimate,
        )

        if result.success and isinstance(result.data, dict):
            upload_url = result.data.get("uploadUrl", "")
            if upload_url:
                # Step 2: PUT content
                content = step.data.get("content", "<html><body>Coming soon</body></html>") if isinstance(step.data, dict) else ""
                import subprocess
                try:
                    subprocess.run(
                        ["curl", "-s", "-X", "PUT", upload_url,
                         "-H", "Content-Type: text/html", "--data-binary", str(content)],
                        capture_output=True, text=True, timeout=30,
                    )
                except Exception as e:
                    logger.warning("Upload PUT failed: %s", e)

        self.spent += result.cost
        self._record_result(step_num, step.name, "stableupload", step.phase, result)

    def _maybe_adapt(self, remaining_steps: list[AgentStep]) -> list[AgentStep] | None:
        """Ask the agent if the plan should be adapted."""
        if self.budget_remaining < 0.05:
            return None  # Don't spend on adaptation if low budget

        logger.info("Agent: evaluating progress and adapting...")
        adapted = self.agent.evaluate_and_adapt(
            company_description=self.company_description,
            completed_steps=self.completed_results,
            remaining_steps=remaining_steps,
            budget_remaining=self.budget_remaining,
        )

        if adapted:
            logger.info("Agent: plan adapted! New steps: %d", len(adapted))
            self.spent += 0.01  # Claude call cost
            return adapted

        return None

    def _generate_specs(self, plan: AgentPlan):
        """Generate technical specs for coding agents."""
        if self.budget_remaining < 0.02:
            logger.info("Skipping spec generation (low budget)")
            return

        step_num = self._next_step()
        logger.info("Step %d: Generating specs for coding agents...", step_num)

        t0 = time.monotonic()
        specs = self.agent.generate_specs(
            company_description=self.company_description,
            company_name=plan.company_name or self.company_description[:30],
            results=self.completed_results,
        )
        latency = (time.monotonic() - t0) * 1000

        cost = 0.01
        self.spent += cost

        self.report.add_step(StepResult(
            step_number=step_num, step_name="Technical Specs (for coding agents)",
            service_id="anthropic", agent_id="architect",
            success=bool(specs),
            data_summary=specs[:300] if specs else "No specs generated",
            cost=cost, latency_ms=latency,
            raw_data=specs,
        ))

        # Save specs to file
        if specs:
            with open("SPECS.md", "w") as f:
                f.write(f"# {plan.company_name or 'Company'} — Technical Specs\n\n")
                f.write(f"*Generated by Sardis Company Builder*\n\n")
                f.write(f"## Company Description\n{self.company_description}\n\n")
                f.write(specs)
            logger.info("Specs saved to SPECS.md — feed this to your coding agent!")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _next_step(self) -> int:
        self.step_counter += 1
        return self.step_counter

    def _record_result(self, step_num: int, step_name: str, service_id: str, agent_id: str, result):
        data_summary = self._summarize_data(result.data) if result.success else ""
        self.report.add_step(StepResult(
            step_number=step_num, step_name=step_name,
            service_id=service_id, agent_id=agent_id,
            success=result.success, data_summary=data_summary,
            cost=result.cost, latency_ms=result.latency_ms,
            error=result.error, raw_data=result.data,
        ))

    def _record_skip(self, step_num: int, step_name: str, service_id: str, reason: str):
        self.report.add_step(StepResult(
            step_number=step_num, step_name=step_name,
            service_id=service_id, agent_id="orchestrator",
            success=False, data_summary="", cost=0.0, latency_ms=0, error=reason,
        ))

    @staticmethod
    def _resolve_endpoint(svc, step) -> str:
        """Resolve the correct endpoint path from service metadata."""
        # Known service → endpoint mappings (most reliable)
        KNOWN = {
            "perplexity": "/perplexity/search",
            "stableenrich": "/api/exa/search",
            "browserbase": "/search",
            "fal": "/fal-ai/flux/schnell",
            "stableemail": "/api/send",
            "stableupload": "/api/upload",
            "stripe-climate": "/api/contribute",
            "hunter": "/hunter/domain-search",
            "agentmail": "/v0/inboxes",
            "anthropic": "/v1/messages",
            "openai": "/v1/chat/completions",
        }

        # Check known mappings first
        if step.service_id in KNOWN:
            # But if the step has a partial path hint, try to match
            if step.endpoint_path and svc.endpoints:
                for ep in svc.endpoints:
                    ep_path = ep.get("path", "")
                    if step.endpoint_path.strip("/") in ep_path:
                        return ep_path
            return KNOWN[step.service_id]

        # Fallback: match from service metadata
        if not svc.endpoints:
            return ""

        # Prefer POST endpoints
        for ep in svc.endpoints:
            if ep.get("method", "").upper() == step.method.upper():
                path = ep.get("path", "")
                if path.startswith("/"):
                    return path

        # Any endpoint
        path = svc.endpoints[0].get("path", "")
        return path if path.startswith("/") else ""

    @staticmethod
    def _summarize_data(data) -> str:
        if isinstance(data, dict):
            return json.dumps(data, default=str)[:300]
        elif isinstance(data, list):
            return f"{len(data)} results"
        elif data:
            return str(data)[:300]
        return ""


def generate_idea() -> str:
    """Use Claude to generate a startup idea, then build it."""
    from discovery import ServiceDiscovery
    from services import MPPCaller

    disco = ServiceDiscovery()
    caller = MPPCaller()

    svc = disco.get_service("anthropic")
    if not svc:
        print("Error: Anthropic service not found")
        return ""

    print("\nGenerating startup idea via Claude...")
    result = caller.call(
        service_url=svc.service_url,
        endpoint_path="/v1/messages",
        method="POST",
        data={
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 512,
            "messages": [{"role": "user", "content":
                "Generate ONE unique, specific startup idea that:\n"
                "- Solves a real problem\n"
                "- Can be built as a software product\n"
                "- Has a clear revenue model\n"
                "- Is relevant to the AI/crypto/fintech space in 2026\n\n"
                "Respond with ONLY the idea description in 1-2 sentences. "
                "No preamble, no explanation, just the idea."
            }],
        },
        service_id="anthropic",
        cost_estimate=0.01,
    )

    if result.success and isinstance(result.data, dict):
        content = result.data.get("content", [])
        if content and isinstance(content, list):
            first = content[0]
            idea = first.get("text", "") if isinstance(first, dict) else str(first)
            print(f"\nGenerated idea: {idea}\n")
            return idea.strip()

    print("Failed to generate idea")
    return "AI-powered micropayments platform for autonomous agents"


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s | %(message)s",
        datefmt="%H:%M:%S",
    )

    # Check for --generate-idea flag
    args = sys.argv[1:]
    if "--generate-idea" in args or "-g" in args:
        args = [a for a in args if a not in ("--generate-idea", "-g")]
        description = generate_idea()
    elif args:
        description = " ".join(args)
    else:
        description = "AI-powered micropayments platform for autonomous agents"

    builder = CompanyBuilder(description, budget=5.0)
    report = builder.build()

    print("\n" + report.to_text())

    with open("report.json", "w") as f:
        json.dump(report.to_json(), f, indent=2, default=str)

    with open("report.html", "w") as f:
        f.write(report.to_html())

    print(f"\nReports saved: report.json, report.html")
    if report.steps and any(s.step_name == "Technical Specs (for coding agents)" for s in report.steps):
        print("Technical specs saved: SPECS.md — feed this to your coding agent!")

    return report


if __name__ == "__main__":
    main()
