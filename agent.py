"""Sardis AI Agent — The brain that plans and decides autonomously.

Uses Claude (via Anthropic MPP) to:
1. Analyze available MPP services
2. Create a dynamic execution plan based on the company idea
3. Decide which services to use and in what order
4. Evaluate results after each step and adapt
5. Generate actionable specs for coding agents

The agent doesn't follow a fixed pipeline — it creates its own.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field

from discovery import ServiceDiscovery, DiscoveredService
from services import MPPCaller, ServiceResult

logger = logging.getLogger("company_builder.agent")

SYSTEM_PROMPT = """You are an autonomous AI agent that starts companies. You have access to real MPP (Machine Payments Protocol) services on the Tempo blockchain. Every service costs real money (USDC micropayments).

Your job: given a company idea, create and execute a plan to start it. You decide which services to use based on what's available.

RULES:
- Be cost-efficient. Each call costs real money.
- Use the most relevant services for the task.
- Skip services that aren't useful for this specific company idea.
- After research, validate the idea before spending on branding/infrastructure.
- Output actionable results — not vague suggestions.

You will be called multiple times:
1. First to CREATE A PLAN given available services
2. Then to EVALUATE RESULTS after each step and decide next actions"""


@dataclass
class AgentStep:
    """A single step the agent wants to execute."""
    name: str
    service_id: str
    endpoint_path: str
    method: str = "POST"
    data: dict | list | None = None
    reason: str = ""
    cost_estimate: float = 0.0
    phase: str = "research"  # research, validation, creation, infrastructure


@dataclass
class AgentPlan:
    """The agent's execution plan."""
    company_name: str = ""
    summary: str = ""
    steps: list[AgentStep] = field(default_factory=list)
    phases: list[str] = field(default_factory=list)
    total_estimated_cost: float = 0.0
    raw_response: str = ""


class Agent:
    """AI brain that plans and decides using Claude via MPP."""

    def __init__(self, caller: MPPCaller, discovery: ServiceDiscovery):
        self.caller = caller
        self.discovery = discovery
        self._anthropic_url = ""

    def _get_anthropic_url(self) -> str:
        if not self._anthropic_url:
            svc = self.discovery.get_service("anthropic")
            if svc:
                self._anthropic_url = svc.service_url
            else:
                raise RuntimeError("Anthropic service not found in MPP directory")
        return self._anthropic_url

    def _call_claude(self, prompt: str, system: str = SYSTEM_PROMPT, max_tokens: int = 2048) -> str:
        """Call Claude via Anthropic MPP and return text response."""
        url = self._get_anthropic_url()

        result = self.caller.call(
            service_url=url,
            endpoint_path="/v1/messages",
            method="POST",
            data={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": max_tokens,
                "system": system,
                "messages": [{"role": "user", "content": prompt}],
            },
            service_id="anthropic",
            cost_estimate=0.01,
        )

        if not result.success:
            logger.error("Claude call failed: %s", result.error)
            return ""

        if isinstance(result.data, dict):
            content = result.data.get("content", [])
            if content and isinstance(content, list):
                first = content[0]
                if isinstance(first, dict):
                    return first.get("text", "")
                return str(first)
        return str(result.data)

    def create_plan(self, company_description: str, services: list[DiscoveredService]) -> AgentPlan:
        """Ask Claude to create an execution plan based on available services."""
        logger.info("Agent: creating plan for '%s'...", company_description[:50])

        # Build service catalog for Claude
        catalog = self._build_service_catalog(services)

        prompt = f"""Create an execution plan to start this company:

COMPANY IDEA: {company_description}

AVAILABLE MPP SERVICES (real, paid via micropayments):
{catalog}

Create a JSON plan with these phases:
1. **research** — understand the market (2-3 steps max)
2. **validation** — validate the idea with real data (1-2 steps)
3. **creation** — branding, communications, infrastructure (2-4 steps)

For each step, specify:
- name: human-readable step name
- service_id: which service to use (from the list above)
- endpoint_path: the API endpoint path
- method: HTTP method (usually POST)
- data: the request body (JSON object or array)
- reason: why this step is needed
- cost_estimate: estimated cost in USD
- phase: research, validation, or creation

CRITICAL RULES:
- Use ONLY services from the list above. Do not invent services.
- ALWAYS include the full endpoint_path starting with /
- Keep total plan cost under $1.00
- Do NOT use anthropic for content generation steps — only use it for AI validation. Use other services for research and creation.
- Maximum 8 steps total.

EXACT REQUEST FORMATS (you MUST use these exact formats):

perplexity /perplexity/search: {{"query": "your search query"}}
stableenrich /api/exa/search: {{"query": "search query", "num_results": 5}}
stableenrich /api/reddit/search: {{"query": "search query"}}
stableenrich /api/serper/news: {{"query": "news search query"}}
stableenrich /api/firecrawl/scrape: {{"url": "https://example.com"}}
browserbase /search: {{"query": "search query"}}
browserbase /fetch: {{"url": "https://example.com"}}
fal /fal-ai/flux/schnell: {{"prompt": "image description", "image_size": "square_hd", "num_images": 1}}
stableemail /api/send: {{"to": ["email@example.com"], "subject": "Subject", "text": "Body"}}
hunter /hunter/domain-search: {{"domain": "example.com", "limit": 5}}
stableupload /api/upload: {{"filename": "index.html", "contentType": "text/html", "tier": "10mb"}}
stripe-climate /api/contribute: {{"amount": 1}}
allium /api/v1/developer/prices: [{{"token_address": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", "chain": "ethereum"}}]
spyfu — GET endpoints, use for SEO/keyword research
modal /sandbox/create: create code execution sandboxes
browser-use /api/browser-use-mpp/run-task: {{"task": "description of browser task"}}

Also suggest:
- company_name: a short, memorable name for this company
- summary: one-paragraph executive summary

Respond with ONLY valid JSON, no markdown fences. Schema:
{{"company_name": "...", "summary": "...", "steps": [...], "total_estimated_cost": 0.0}}"""

        response = self._call_claude(prompt)
        return self._parse_plan(response)

    def evaluate_and_adapt(
        self,
        company_description: str,
        completed_steps: list[dict],
        remaining_steps: list[AgentStep],
        budget_remaining: float,
    ) -> list[AgentStep] | None:
        """Ask Claude to evaluate results and optionally adapt the plan.

        Returns None to keep the current plan, or a new list of steps.
        """
        if not remaining_steps:
            return None

        completed_summary = json.dumps(completed_steps[-3:], indent=2, default=str)[:2000]

        prompt = f"""You are partway through starting a company. Evaluate progress and decide if the plan needs changes.

COMPANY: {company_description}

COMPLETED STEPS (last 3):
{completed_summary}

REMAINING STEPS:
{json.dumps([{"name": s.name, "service_id": s.service_id, "phase": s.phase} for s in remaining_steps], indent=2)}

BUDGET REMAINING: ${budget_remaining:.2f}

Should the remaining steps change? Consider:
- Did research reveal the idea needs pivoting?
- Are there better services to use based on what we learned?
- Should we skip any steps to save budget?

Respond with ONLY valid JSON:
- If no changes needed: {{"adapt": false}}
- If changes needed: {{"adapt": true, "reason": "...", "new_steps": [same schema as before]}}"""

        response = self._call_claude(prompt)
        if not response:
            return None

        try:
            parsed = self._extract_json(response)
            if isinstance(parsed, dict) and parsed.get("adapt"):
                new_steps = parsed.get("new_steps", [])
                return [self._dict_to_step(s) for s in new_steps if isinstance(s, dict)]
        except Exception:
            pass

        return None

    def generate_specs(
        self,
        company_description: str,
        company_name: str,
        results: list[dict],
    ) -> str:
        """Generate actionable specs that a coding agent can execute.

        This is the output that Claude Code, Codex, or any coding agent
        can pick up and start building from.
        """
        results_summary = json.dumps(results[:8], indent=2, default=str)[:3000]

        prompt = f"""Based on the research and setup done for this company, generate actionable technical specs.

COMPANY: {company_name} — {company_description}

COMPLETED WORK:
{results_summary}

Generate a technical specification document that a coding agent (like Claude Code or Codex) can use to start building the product. Include:

1. **Product spec** — what to build (features, MVP scope)
2. **Tech stack recommendation** — based on the market/competitor research
3. **Repository structure** — suggested files and folders
4. **API design** — key endpoints if it's a service
5. **Data model** — key entities
6. **Deployment plan** — how to deploy (should use MPP services where possible)
7. **Next steps** — prioritized list of what the coding agent should do first

Be specific and actionable. This should be copy-pasteable into a coding agent prompt.
Complete the entire document — do not cut off or abbreviate any section."""

        return self._call_claude(prompt, max_tokens=4096)

    def _build_service_catalog(self, services: list[DiscoveredService]) -> str:
        """Build a concise service catalog string for Claude."""
        lines = []
        for svc in services:
            endpoints = []
            for ep in svc.endpoints[:5]:  # Limit to 5 endpoints per service
                path = ep.get("path", "")
                desc = ep.get("description", "")
                method = ep.get("method", "POST")
                cost = ""
                if "payment" in ep:
                    amt = ep["payment"].get("amount")
                    dec = ep["payment"].get("decimals", 6)
                    if amt:
                        cost = f" (${int(amt) / 10**dec:.4f})"
                    else:
                        cost = " (dynamic pricing)"
                endpoints.append(f"    {method} {path} — {desc}{cost}")

            lines.append(f"- {svc.id} ({svc.name}): {svc.description}")
            lines.append(f"  URL: {svc.service_url}")
            if endpoints:
                lines.append("  Endpoints:")
                lines.extend(endpoints[:5])
            lines.append("")

        return "\n".join(lines)

    def _parse_plan(self, response: str) -> AgentPlan:
        """Parse Claude's plan response into an AgentPlan."""
        if not response:
            return AgentPlan()

        try:
            data = self._extract_json(response)
        except Exception:
            logger.warning("Could not parse plan JSON, using fallback")
            return AgentPlan(raw_response=response)

        if not isinstance(data, dict):
            return AgentPlan(raw_response=response)

        steps = []
        for s in data.get("steps", []):
            if isinstance(s, dict):
                steps.append(self._dict_to_step(s))

        return AgentPlan(
            company_name=data.get("company_name", ""),
            summary=data.get("summary", ""),
            steps=steps,
            phases=list(dict.fromkeys(s.phase for s in steps)),
            total_estimated_cost=data.get("total_estimated_cost", 0.0),
            raw_response=response,
        )

    @staticmethod
    def _dict_to_step(s: dict) -> AgentStep:
        return AgentStep(
            name=s.get("name", "Unknown"),
            service_id=s.get("service_id", ""),
            endpoint_path=s.get("endpoint_path", ""),
            method=s.get("method", "POST"),
            data=s.get("data"),
            reason=s.get("reason", ""),
            cost_estimate=s.get("cost_estimate", 0.01),
            phase=s.get("phase", "research"),
        )

    @staticmethod
    def _extract_json(text: str) -> dict | list:
        """Extract JSON from text that might contain markdown fences or extra text."""
        # Try direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Remove markdown fences
        cleaned = text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            # Remove first and last fence lines
            json_lines = []
            in_fence = False
            for line in lines:
                if line.strip().startswith("```") and not in_fence:
                    in_fence = True
                    continue
                if line.strip() == "```" and in_fence:
                    break
                if in_fence:
                    json_lines.append(line)
            cleaned = "\n".join(json_lines)
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                pass

        # Find JSON object/array in text
        for start_char, end_char in [("{", "}"), ("[", "]")]:
            start = text.find(start_char)
            if start < 0:
                continue
            # Find matching end
            depth = 0
            for i in range(start, len(text)):
                if text[i] == start_char:
                    depth += 1
                elif text[i] == end_char:
                    depth -= 1
                    if depth == 0:
                        try:
                            return json.loads(text[start:i + 1])
                        except json.JSONDecodeError:
                            break

        raise ValueError(f"No JSON found in response: {text[:200]}")
