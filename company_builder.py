"""Sardis Company Builder — AI agent that autonomously starts a company.

Orchestrates real MPP services via tempo CLI to:
- Research the market (Perplexity, Exa, Browserbase)
- Generate branding (fal.ai FLUX)
- Set up communications (AgentMail)
- Make a carbon offset (Stripe Climate)
- Check blockchain data (Allium)

Usage (CLI):
    python company_builder.py "AI-powered micropayments platform"

Usage (Python):
    builder = CompanyBuilder("AI-powered micropayments platform")
    report = builder.build()
    print(report.to_text())
"""

from __future__ import annotations

import json
import logging
import sys
import time

from discovery import ServiceDiscovery
from services import MPPCaller
from report import CompanyReport, StepResult

logger = logging.getLogger("company_builder")


class CompanyBuilder:
    """Orchestrates autonomous company creation via MPP services."""

    def __init__(
        self,
        company_description: str,
        budget: float = 5.0,
    ):
        self.company_description = company_description
        self.budget = budget

        self.discovery = ServiceDiscovery()
        self.caller = MPPCaller()

        self.report = CompanyReport(company_description=company_description)
        self.step_counter = 0

    def build(self) -> CompanyReport:
        """Execute the full company-building pipeline."""
        logger.info("Starting company builder: %s", self.company_description)
        logger.info("Budget: $%.2f", self.budget)

        try:
            self._step_discover_services()
            self._step_market_research()
            self._step_competitor_search()
            self._step_web_scraping()
            self._step_logo_generation()
            self._step_email_setup()
            self._step_carbon_offset()
            self._step_blockchain_check()
        except Exception as e:
            logger.error("Pipeline error: %s", e, exc_info=True)

        self.report.finalize()
        return self.report

    def _next_step(self) -> int:
        self.step_counter += 1
        return self.step_counter

    # ------------------------------------------------------------------
    # Step 1: Discover services
    # ------------------------------------------------------------------

    def _step_discover_services(self):
        step_num = self._next_step()
        logger.info("Step %d: Discovering MPP services...", step_num)

        services = self.discovery.discover_all()
        self.report.discovered_services = len(services)

        service_ids = [s.id for s in services]
        summary = f"Discovered {len(services)} services: {', '.join(service_ids[:10])}..."

        self.report.add_step(StepResult(
            step_number=step_num,
            step_name="Service Discovery",
            service_id="tempo-directory",
            agent_id="orchestrator",
            success=len(services) > 0,
            data_summary=summary,
            cost=0.0,
            latency_ms=0,
            raw_data=service_ids,
        ))

    # ------------------------------------------------------------------
    # Step 2: Market research (Perplexity)
    # ------------------------------------------------------------------

    def _step_market_research(self):
        step_num = self._next_step()
        logger.info("Step %d: Market research via Perplexity...", step_num)

        svc = self.discovery.get_service("perplexity")
        if not svc:
            self._record_skip(step_num, "Market Research", "perplexity", "Service not found")
            return

        query = (
            f"Market size, TAM, key trends, and growth projections for: "
            f"{self.company_description}. "
            f"Include competitor landscape and market opportunities."
        )

        result = self.caller.call(
            service_url=svc.service_url,
            endpoint_path="/perplexity/search",
            method="POST",
            data={"query": query},
            service_id="perplexity",
            cost_estimate=0.05,
        )

        self._record_result(step_num, "Market Research", "perplexity", "researcher", result)

    # ------------------------------------------------------------------
    # Step 3: Competitor search (Exa via StableEnrich)
    # ------------------------------------------------------------------

    def _step_competitor_search(self):
        step_num = self._next_step()
        logger.info("Step %d: Competitor search via Exa...", step_num)

        svc = self.discovery.get_service("stableenrich")
        if not svc:
            self._record_skip(step_num, "Competitor Search", "stableenrich", "Service not found")
            return

        query = f"Companies and startups building {self.company_description}"

        result = self.caller.call(
            service_url=svc.service_url,
            endpoint_path="/api/exa/search",
            method="POST",
            data={"query": query, "num_results": 5},
            service_id="stableenrich",
            cost_estimate=0.01,
        )

        self._record_result(step_num, "Competitor Search", "stableenrich", "researcher", result)

    # ------------------------------------------------------------------
    # Step 4: Web scraping (Browserbase)
    # ------------------------------------------------------------------

    def _step_web_scraping(self):
        step_num = self._next_step()
        logger.info("Step %d: Web scraping via Browserbase...", step_num)

        svc = self.discovery.get_service("browserbase")
        if not svc:
            self._record_skip(step_num, "Web Scraping", "browserbase", "Service not found")
            return

        query = f"{self.company_description} market analysis 2026"

        result = self.caller.call(
            service_url=svc.service_url,
            endpoint_path="/search",
            method="POST",
            data={"query": query},
            service_id="browserbase",
            cost_estimate=0.01,
        )

        self._record_result(step_num, "Web Scraping", "browserbase", "researcher", result)

    # ------------------------------------------------------------------
    # Step 5: Logo generation (fal.ai FLUX)
    # ------------------------------------------------------------------

    def _step_logo_generation(self):
        step_num = self._next_step()
        logger.info("Step %d: Logo generation via fal.ai...", step_num)

        svc = self.discovery.get_service("fal")
        if not svc:
            self._record_skip(step_num, "Logo Generation", "fal", "Service not found")
            return

        company_short = self.company_description.split(".")[0][:50]
        prompt = (
            f"Minimalist modern tech company logo for '{company_short}', "
            f"clean vector style, gradient colors, white background, "
            f"professional, simple geometric shapes"
        )

        result = self.caller.call(
            service_url=svc.service_url,
            endpoint_path="/fal-ai/flux/schnell",
            method="POST",
            data={"prompt": prompt, "image_size": "square_hd", "num_images": 1},
            service_id="fal",
            cost_estimate=0.05,
        )

        self._record_result(step_num, "Logo Generation", "fal", "designer", result)

    # ------------------------------------------------------------------
    # Step 6: Email setup (AgentMail)
    # ------------------------------------------------------------------

    def _step_email_setup(self):
        step_num = self._next_step()
        logger.info("Step %d: Email setup via AgentMail...", step_num)

        svc = self.discovery.get_service("agentmail")
        if not svc:
            self._record_skip(step_num, "Email Setup", "agentmail", "Service not found")
            return

        result = self.caller.call(
            service_url=svc.service_url,
            endpoint_path="/v0/inboxes",
            method="POST",
            data={"name": "Sardis Company Builder"},
            service_id="agentmail",
            cost_estimate=0.01,
        )

        self._record_result(step_num, "Email Setup", "agentmail", "comms", result)

    # ------------------------------------------------------------------
    # Step 7: Carbon offset (Stripe Climate)
    # ------------------------------------------------------------------

    def _step_carbon_offset(self):
        step_num = self._next_step()
        logger.info("Step %d: Carbon offset via Stripe Climate...", step_num)

        svc = self.discovery.get_service("stripe-climate")
        if not svc:
            self._record_skip(step_num, "Carbon Offset", "stripe-climate", "Service not found")
            return

        result = self.caller.call(
            service_url=svc.service_url,
            endpoint_path="/api/contribute",
            method="POST",
            data={"amount": 1},  # 1 cent minimum
            service_id="stripe-climate",
            cost_estimate=0.01,
        )

        self._record_result(step_num, "Carbon Offset", "stripe-climate", "finance", result)

    # ------------------------------------------------------------------
    # Step 8: Blockchain check (Allium)
    # ------------------------------------------------------------------

    def _step_blockchain_check(self):
        step_num = self._next_step()
        logger.info("Step %d: Blockchain data via Allium...", step_num)

        svc = self.discovery.get_service("allium")
        if not svc:
            self._record_skip(step_num, "Blockchain Check", "allium", "Service not found")
            return

        result = self.caller.call(
            service_url=svc.service_url,
            endpoint_path="/api/v1/developer/prices",
            method="POST",
            data={"tokens": [{"symbol": "USDC", "chain": "tempo"}]},
            service_id="allium",
            cost_estimate=0.01,
        )

        self._record_result(step_num, "Blockchain Check", "allium", "finance", result)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _record_result(self, step_num: int, step_name: str, service_id: str, agent_id: str, result):
        """Record a service call result."""
        data_summary = ""
        if result.success and result.data:
            if isinstance(result.data, dict):
                data_summary = json.dumps(result.data, default=str)[:300]
            elif isinstance(result.data, list):
                data_summary = f"{len(result.data)} results"
            else:
                data_summary = str(result.data)[:300]

        self.report.add_step(StepResult(
            step_number=step_num,
            step_name=step_name,
            service_id=service_id,
            agent_id=agent_id,
            success=result.success,
            data_summary=data_summary,
            cost=result.cost,
            latency_ms=result.latency_ms,
            error=result.error,
            raw_data=result.data,
        ))

    def _record_skip(self, step_num: int, step_name: str, service_id: str, reason: str):
        """Record a skipped step."""
        self.report.add_step(StepResult(
            step_number=step_num,
            step_name=step_name,
            service_id=service_id,
            agent_id="orchestrator",
            success=False,
            data_summary="",
            cost=0.0,
            latency_ms=0,
            error=reason,
        ))


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s | %(message)s",
        datefmt="%H:%M:%S",
    )

    description = (
        " ".join(sys.argv[1:])
        if len(sys.argv) > 1
        else "AI-powered micropayments platform for autonomous agents"
    )

    print(f"\n{'='*70}")
    print(f"  SARDIS COMPANY BUILDER")
    print(f"  Building: {description}")
    print(f"{'='*70}\n")

    builder = CompanyBuilder(description, budget=5.0)
    report = builder.build()

    print("\n" + report.to_text())

    report_path = "report.json"
    with open(report_path, "w") as f:
        json.dump(report.to_json(), f, indent=2, default=str)
    print(f"\nJSON report saved to: {report_path}")

    html_path = "report.html"
    with open(html_path, "w") as f:
        f.write(report.to_html())
    print(f"HTML report saved to: {html_path}")

    return report


if __name__ == "__main__":
    main()
