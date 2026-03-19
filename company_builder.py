"""Sardis Company Builder — AI agent that autonomously starts a company.

End-to-end pipeline: idea → research → validate → brand → comms → deploy.
All via real MPP micropayments on Tempo, all services discovered dynamically.

Steps:
  1. Discover 54+ MPP services via tempo directory
  2. Market research (Perplexity AI search)
  3. Competitor analysis (Exa neural search)
  4. Deep web research (Browserbase headless browser)
  5. AI validation (Claude via Anthropic MPP — validates the business idea)
  6. Logo generation (fal.ai FLUX)
  7. Domain intelligence (Hunter — find emails & company info for the domain)
  8. Email setup (StableEmail — send a launch announcement)
  9. Website deployment (StableUpload — deploy a landing page)
  10. Carbon offset (Stripe Climate)
  11. Token price check (Allium blockchain data)

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
from report import CompanyReport, StepResult

logger = logging.getLogger("company_builder")


class CompanyBuilder:
    """Orchestrates autonomous company creation via MPP services."""

    def __init__(self, company_description: str, budget: float = 5.0):
        self.company_description = company_description
        self.budget = budget

        self.discovery = ServiceDiscovery()
        self.caller = MPPCaller()

        self.report = CompanyReport(company_description=company_description)
        self.step_counter = 0

        # Accumulated data from steps (used by later steps)
        self.market_data: str = ""
        self.competitor_data: str = ""
        self.validation_result: str = ""
        self.logo_url: str = ""
        self.company_name: str = ""

    def build(self) -> CompanyReport:
        """Execute the full company-building pipeline."""
        logger.info("=" * 60)
        logger.info("  SARDIS COMPANY BUILDER")
        logger.info("  Goal: %s", self.company_description)
        logger.info("  Budget: $%.2f USDC", self.budget)
        logger.info("=" * 60)

        try:
            self._step_discover_services()
            self._step_market_research()
            self._step_competitor_search()
            self._step_web_scraping()
            self._step_ai_validation()
            self._step_logo_generation()
            self._step_domain_intelligence()
            self._step_email_launch()
            self._step_deploy_website()
            self._step_carbon_offset()
            self._step_blockchain_check()
        except Exception as e:
            logger.error("Pipeline error: %s", e, exc_info=True)

        self.report.company_name = self.company_name or self.company_description.split(".")[0][:40]
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
        summary = f"Discovered {len(services)} services: {', '.join(service_ids[:12])}..."

        self.report.add_step(StepResult(
            step_number=step_num, step_name="Service Discovery",
            service_id="tempo-directory", agent_id="orchestrator",
            success=len(services) > 0, data_summary=summary,
            cost=0.0, latency_ms=0, raw_data=service_ids,
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
            f"Include competitor landscape, market opportunities, and potential revenue models."
        )

        result = self.caller.call(
            service_url=svc.service_url, endpoint_path="/perplexity/search",
            method="POST", data={"query": query},
            service_id="perplexity", cost_estimate=0.05,
        )

        if result.success and result.data:
            self.market_data = json.dumps(result.data, default=str)[:2000]

        self._record_result(step_num, "Market Research", "perplexity", "researcher", result)

    # ------------------------------------------------------------------
    # Step 3: Competitor search (Exa)
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
            service_url=svc.service_url, endpoint_path="/api/exa/search",
            method="POST", data={"query": query, "num_results": 5},
            service_id="stableenrich", cost_estimate=0.01,
        )

        if result.success and result.data:
            self.competitor_data = json.dumps(result.data, default=str)[:2000]

        self._record_result(step_num, "Competitor Search", "stableenrich", "researcher", result)

    # ------------------------------------------------------------------
    # Step 4: Web scraping (Browserbase)
    # ------------------------------------------------------------------
    def _step_web_scraping(self):
        step_num = self._next_step()
        logger.info("Step %d: Deep web research via Browserbase...", step_num)

        svc = self.discovery.get_service("browserbase")
        if not svc:
            self._record_skip(step_num, "Web Research", "browserbase", "Service not found")
            return

        query = f"{self.company_description} market analysis 2026"

        result = self.caller.call(
            service_url=svc.service_url, endpoint_path="/search",
            method="POST", data={"query": query},
            service_id="browserbase", cost_estimate=0.01,
        )

        self._record_result(step_num, "Web Research", "browserbase", "researcher", result)

    # ------------------------------------------------------------------
    # Step 5: AI Validation (Claude via Anthropic MPP)
    # ------------------------------------------------------------------
    def _step_ai_validation(self):
        step_num = self._next_step()
        logger.info("Step %d: AI validation via Claude (Anthropic MPP)...", step_num)

        svc = self.discovery.get_service("anthropic")
        if not svc:
            self._record_skip(step_num, "AI Validation", "anthropic", "Service not found")
            return

        # Build a validation prompt using research gathered so far
        context = ""
        if self.market_data:
            context += f"\nMarket research data:\n{self.market_data[:800]}\n"
        if self.competitor_data:
            context += f"\nCompetitor data:\n{self.competitor_data[:800]}\n"

        prompt = (
            f"You are a startup advisor. Evaluate this business idea and provide:\n"
            f"1. A suggested company name (short, memorable, tech-sounding)\n"
            f"2. One-paragraph executive summary\n"
            f"3. Key strengths (3 bullet points)\n"
            f"4. Key risks (3 bullet points)\n"
            f"5. Recommended next steps (3 bullet points)\n"
            f"6. Overall viability score (1-10)\n\n"
            f"Business idea: {self.company_description}\n"
            f"{context}\n"
            f"Be concise. Format as JSON with keys: company_name, summary, strengths, risks, next_steps, score."
        )

        result = self.caller.call(
            service_url=svc.service_url, endpoint_path="/v1/messages",
            method="POST",
            data={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 1024,
                "messages": [{"role": "user", "content": prompt}],
            },
            service_id="anthropic", cost_estimate=0.01,
        )

        if result.success and result.data:
            # Extract company name from Claude's response
            data = result.data
            if isinstance(data, dict):
                content = data.get("content", [])
                if content and isinstance(content, list):
                    text = content[0].get("text", "") if isinstance(content[0], dict) else str(content[0])
                    self.validation_result = text[:2000]
                    # Try to extract company name from JSON response
                    try:
                        # Find JSON in the text
                        start = text.find("{")
                        end = text.rfind("}") + 1
                        if start >= 0 and end > start:
                            parsed = json.loads(text[start:end])
                            self.company_name = parsed.get("company_name", "")
                    except (json.JSONDecodeError, KeyError):
                        pass

        self._record_result(step_num, "AI Validation", "anthropic", "advisor", result)

    # ------------------------------------------------------------------
    # Step 6: Logo generation (fal.ai FLUX)
    # ------------------------------------------------------------------
    def _step_logo_generation(self):
        step_num = self._next_step()
        logger.info("Step %d: Logo generation via fal.ai FLUX...", step_num)

        svc = self.discovery.get_service("fal")
        if not svc:
            self._record_skip(step_num, "Logo Generation", "fal", "Service not found")
            return

        name = self.company_name or self.company_description.split(".")[0][:30]
        prompt = (
            f"Minimalist modern tech company logo for '{name}', "
            f"clean vector style, gradient blue and purple colors, "
            f"white background, professional, simple geometric shapes, "
            f"no text, abstract mark only"
        )

        result = self.caller.call(
            service_url=svc.service_url, endpoint_path="/fal-ai/flux/schnell",
            method="POST",
            data={"prompt": prompt, "image_size": "square_hd", "num_images": 1},
            service_id="fal", cost_estimate=0.05,
        )

        # Extract logo URL
        if result.success and isinstance(result.data, dict):
            images = result.data.get("images", [])
            if images:
                self.logo_url = images[0].get("url", "")

        self._record_result(step_num, "Logo Generation", "fal", "designer", result)

    # ------------------------------------------------------------------
    # Step 7: Domain intelligence (Hunter)
    # ------------------------------------------------------------------
    def _step_domain_intelligence(self):
        step_num = self._next_step()
        logger.info("Step %d: Domain intelligence via Hunter...", step_num)

        svc = self.discovery.get_service("hunter")
        if not svc:
            # Fallback: try SpyFu for domain analytics
            svc = self.discovery.get_service("spyfu")
            if not svc:
                self._record_skip(step_num, "Domain Intelligence", "hunter", "Service not found")
                return

        # Use Hunter to check domain info for a potential competitor
        name = self.company_name or "sardis"
        domain = f"{name.lower().replace(' ', '')}.com"

        result = self.caller.call(
            service_url=svc.service_url, endpoint_path="/hunter/domain-search",
            method="POST",
            data={"domain": domain, "limit": 5},
            service_id="hunter", cost_estimate=0.01,
        )

        self._record_result(step_num, "Domain Intelligence", "hunter", "researcher", result)

    # ------------------------------------------------------------------
    # Step 8: Email — send launch announcement (StableEmail)
    # ------------------------------------------------------------------
    def _step_email_launch(self):
        step_num = self._next_step()
        logger.info("Step %d: Send launch email via StableEmail...", step_num)

        svc = self.discovery.get_service("stableemail")
        if not svc:
            self._record_skip(step_num, "Launch Email", "stableemail", "Service not found")
            return

        name = self.company_name or "New Startup"
        subject = f"{name} — We just launched!"
        body = (
            f"Hello!\n\n"
            f"We're excited to announce the launch of {name}.\n\n"
            f"{self.company_description}\n\n"
            f"This company was built entirely by an AI agent using MPP micropayments "
            f"on the Tempo blockchain. Every service — research, branding, email, "
            f"hosting — was discovered and paid for autonomously.\n\n"
            f"Built with Sardis Company Builder.\n"
        )

        result = self.caller.call(
            service_url=svc.service_url, endpoint_path="/api/send",
            method="POST",
            data={
                "to": ["contact@aspendos.net"],
                "subject": subject,
                "text": body,
            },
            service_id="stableemail", cost_estimate=0.02,
        )

        self._record_result(step_num, "Launch Email", "stableemail", "comms", result)

    # ------------------------------------------------------------------
    # Step 9: Deploy landing page (StableUpload)
    # ------------------------------------------------------------------
    def _step_deploy_website(self):
        step_num = self._next_step()
        logger.info("Step %d: Deploy landing page via StableUpload...", step_num)

        svc = self.discovery.get_service("stableupload")
        if not svc:
            self._record_skip(step_num, "Website Deploy", "stableupload", "Service not found")
            return

        # Step 1: Get upload slot
        slot_result = self.caller.call(
            service_url=svc.service_url, endpoint_path="/api/upload",
            method="POST",
            data={"filename": "index.html", "contentType": "text/html", "tier": "10mb"},
            service_id="stableupload", cost_estimate=0.02,
        )

        if not slot_result.success or not isinstance(slot_result.data, dict):
            self._record_result(step_num, "Website Deploy", "stableupload", "engineer", slot_result)
            return

        upload_url = slot_result.data.get("uploadUrl", "")
        public_url = slot_result.data.get("publicUrl", "")

        if not upload_url:
            self._record_result(step_num, "Website Deploy", "stableupload", "engineer", slot_result)
            return

        # Step 2: PUT the HTML content to the upload URL
        name = self.company_name or "New Startup"
        html = self._generate_landing_page(name)

        import subprocess as sp
        try:
            put_result = sp.run(
                ["curl", "-s", "-X", "PUT", upload_url,
                 "-H", "Content-Type: text/html",
                 "--data-binary", html],
                capture_output=True, text=True, timeout=30,
            )
            logger.info("Upload PUT: status=%d, body=%s", put_result.returncode, put_result.stdout[:200])
        except Exception as e:
            logger.error("Upload PUT failed: %s", e)

        # Record with public URL
        slot_result.data["public_url"] = public_url
        self._record_result(step_num, "Website Deploy", "stableupload", "engineer", slot_result)

    # ------------------------------------------------------------------
    # Step 10: Carbon offset (Stripe Climate)
    # ------------------------------------------------------------------
    def _step_carbon_offset(self):
        step_num = self._next_step()
        logger.info("Step %d: Carbon offset via Stripe Climate...", step_num)

        svc = self.discovery.get_service("stripe-climate")
        if not svc:
            self._record_skip(step_num, "Carbon Offset", "stripe-climate", "Service not found")
            return

        result = self.caller.call(
            service_url=svc.service_url, endpoint_path="/api/contribute",
            method="POST", data={"amount": 1},
            service_id="stripe-climate", cost_estimate=0.01,
        )

        self._record_result(step_num, "Carbon Offset", "stripe-climate", "finance", result)

    # ------------------------------------------------------------------
    # Step 11: Blockchain data (Allium)
    # ------------------------------------------------------------------
    def _step_blockchain_check(self):
        step_num = self._next_step()
        logger.info("Step %d: Token prices via Allium...", step_num)

        svc = self.discovery.get_service("allium")
        if not svc:
            self._record_skip(step_num, "Token Prices", "allium", "Service not found")
            return

        result = self.caller.call(
            service_url=svc.service_url, endpoint_path="/api/v1/developer/prices",
            method="POST",
            data=[
                {"token_address": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", "chain": "ethereum"},
            ],
            service_id="allium", cost_estimate=0.01,
        )

        self._record_result(step_num, "Token Prices", "allium", "finance", result)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _generate_landing_page(self, name: str) -> str:
        """Generate a simple HTML landing page for the company."""
        logo_html = f'<img src="{self.logo_url}" alt="{name} logo" style="width:120px;height:120px;border-radius:16px;margin-bottom:1rem;">' if self.logo_url else ""
        validation_html = ""
        if self.validation_result:
            validation_html = f'<div style="background:#161b22;padding:1rem;border-radius:8px;margin:1rem 0;text-align:left;max-width:600px;"><pre style="white-space:pre-wrap;color:#c9d1d9;font-size:0.85rem;">{self.validation_result[:1000]}</pre></div>'

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{name}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0d1117; color: #c9d1d9; margin: 0; padding: 2rem; text-align: center; }}
        h1 {{ color: #58a6ff; font-size: 2.5rem; margin-top: 3rem; }}
        p {{ max-width: 600px; margin: 1rem auto; line-height: 1.6; }}
        .badge {{ display: inline-block; background: linear-gradient(135deg, #238636, #1f6feb); padding: 0.5rem 1.5rem; border-radius: 20px; color: white; font-weight: 600; margin: 1rem 0.5rem; font-size: 0.85rem; }}
        .footer {{ margin-top: 3rem; color: #484f58; font-size: 0.8rem; }}
        a {{ color: #58a6ff; }}
    </style>
</head>
<body>
    {logo_html}
    <h1>{name}</h1>
    <p>{self.company_description}</p>
    <div>
        <span class="badge">Built by AI Agent</span>
        <span class="badge">MPP Micropayments</span>
        <span class="badge">Tempo Blockchain</span>
    </div>
    {validation_html}
    <div class="footer">
        <p>This company was built entirely by an autonomous AI agent using
        <a href="https://tempo.xyz">Tempo MPP</a> micropayments.</p>
        <p>{self.report.discovered_services} services discovered | ~${self.report.total_cost:.4f} USDC spent</p>
        <p>Built with <a href="https://github.com/EfeDurmaz16/sardis-company-builder">Sardis Company Builder</a></p>
    </div>
</body>
</html>"""

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
            step_number=step_num, step_name=step_name,
            service_id=service_id, agent_id=agent_id,
            success=result.success, data_summary=data_summary,
            cost=result.cost, latency_ms=result.latency_ms,
            error=result.error, raw_data=result.data,
        ))

    def _record_skip(self, step_num: int, step_name: str, service_id: str, reason: str):
        """Record a skipped step."""
        self.report.add_step(StepResult(
            step_number=step_num, step_name=step_name,
            service_id=service_id, agent_id="orchestrator",
            success=False, data_summary="", cost=0.0, latency_ms=0,
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

    builder = CompanyBuilder(description, budget=5.0)
    report = builder.build()

    print("\n" + report.to_text())

    with open("report.json", "w") as f:
        json.dump(report.to_json(), f, indent=2, default=str)

    with open("report.html", "w") as f:
        f.write(report.to_html())

    print(f"\nReports saved: report.json, report.html")
    return report


if __name__ == "__main__":
    main()
