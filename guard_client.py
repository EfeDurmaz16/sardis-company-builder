"""Sardis Guard V2 Client — Mandate management + payment evaluation.

Composes with the Guard Intelligence Plane deployed at Cloud Run.
Free endpoints (mandates, screening, dashboard) use httpx directly.
Paid endpoints (/evaluate/v2) use tempo CLI for MPP payment.

Usage:
    guard = GuardClient()
    root = guard.create_root_mandate("principal", "agent", max_total="5.00")
    child = guard.delegate_mandate(root["mandate_id"], "researcher", max_total="2.00")
    verdict = guard.evaluate(amount="0.05", merchant="perplexity.mpp.paywithlocus.com",
                             agent_id="researcher", mandate_id=child["mandate_id"])
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger("company_builder.guard")

GUARD_URL = "https://sardis-guard-482463483786.us-central1.run.app"


@dataclass
class GuardVerdict:
    """Result of a Sardis Guard policy evaluation."""

    allowed: bool
    action: str
    summary: str
    risk_score: float
    checks: list[dict]
    latency_ms: float
    agent_id: str
    mandate_id: str
    event_id: str = ""
    raw: dict | None = None

    @classmethod
    def from_response(cls, data: dict) -> GuardVerdict:
        return cls(
            allowed=data.get("action", "") == "ALLOW",
            action=data.get("action", "UNKNOWN"),
            summary=data.get("summary", ""),
            risk_score=data.get("risk_score", 0.0),
            checks=data.get("gate_results", data.get("checks", [])),
            latency_ms=data.get("total_latency_ms", 0),
            agent_id=data.get("agent_id", ""),
            mandate_id=data.get("mandate_id", ""),
            event_id=data.get("event_id", ""),
            raw=data,
        )


class GuardClient:
    """Sardis Guard V2 client with mandate tree + evaluation support."""

    def __init__(
        self,
        guard_url: str = GUARD_URL,
        tempo_path: str | None = None,
        timeout: int = 30,
    ):
        self.guard_url = guard_url.rstrip("/")
        self.timeout = timeout
        self.mandates: dict[str, dict] = {}  # Track created mandates

        # Find tempo CLI for paid endpoints
        if tempo_path:
            self.tempo_path = tempo_path
        else:
            found = shutil.which("tempo")
            if not found:
                raise RuntimeError("tempo CLI not found in PATH")
            self.tempo_path = found

    # --- Free endpoints (httpx) ---

    def _http_request(self, method: str, path: str, data: dict | None = None) -> dict:
        """Make a direct HTTP request to Guard (no MPP payment)."""
        url = f"{self.guard_url}{path}"
        logger.debug("%s %s", method, url)

        try:
            with httpx.Client(timeout=self.timeout) as client:
                if method.upper() == "GET":
                    resp = client.get(url)
                else:
                    resp = client.post(url, json=data or {})
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as e:
            logger.error("Guard HTTP %d: %s", e.response.status_code, e.response.text[:200])
            return {"error": str(e), "status": e.response.status_code}
        except Exception as e:
            logger.error("Guard request failed: %s", e)
            return {"error": str(e)}

    def health(self) -> dict:
        """Check Guard service health (free)."""
        return self._http_request("GET", "/health")

    def create_root_mandate(
        self,
        principal_id: str,
        agent_id: str,
        max_total: str = "5.00",
        max_per_tx: str = "1.00",
        allowed_services: list[str] | None = None,
        allowed_merchants: list[str] | None = None,
        blocked_merchants: list[str] | None = None,
        allowed_chains: list[str] | None = None,
        allowed_currencies: list[str] | None = None,
    ) -> dict:
        """Create a root spending mandate.

        Args:
            principal_id: Who is authorizing the spending.
            agent_id: The agent this mandate is for.
            max_total: Total budget in USD.
            max_per_tx: Max per transaction in USD.
            allowed_services: List of allowed service IDs.
            allowed_merchants: List of allowed merchant URLs.
            blocked_merchants: List of blocked merchant URLs.
            allowed_chains: Allowed blockchain networks.
            allowed_currencies: Allowed currencies.

        Returns:
            Dict with mandate_id and mandate details.
        """
        payload = {
            "principal_id": principal_id,
            "agent_id": agent_id,
            "max_total": max_total,
            "max_per_tx": max_per_tx,
            "allowed_services": allowed_services or [],
            "allowed_merchants": allowed_merchants or [],
            "blocked_merchants": blocked_merchants or [],
            "allowed_chains": allowed_chains or ["tempo"],
            "allowed_currencies": allowed_currencies or ["USDC", "pathUSD"],
        }

        result = self._http_request("POST", "/mandates/root", payload)
        if "mandate_id" in result:
            self.mandates[result["mandate_id"]] = result
            logger.info("Created root mandate: %s ($%s budget)", result["mandate_id"], max_total)
        return result

    def delegate_mandate(
        self,
        parent_id: str,
        agent_id: str,
        max_total: str = "1.00",
        max_per_tx: str = "0.50",
        allowed_services: list[str] | None = None,
        allowed_merchants: list[str] | None = None,
    ) -> dict:
        """Delegate a child mandate from an existing parent.

        Args:
            parent_id: Parent mandate ID.
            agent_id: Agent this child mandate is for.
            max_total: Budget for this child.
            max_per_tx: Max per transaction for this child.
            allowed_services: Narrow services (must be subset of parent).
            allowed_merchants: Narrow merchants (must be subset of parent).

        Returns:
            Dict with mandate_id and child mandate details.
        """
        payload = {
            "parent_id": parent_id,
            "agent_id": agent_id,
            "max_total": max_total,
            "max_per_tx": max_per_tx,
        }
        if allowed_services:
            payload["allowed_services"] = allowed_services
        if allowed_merchants:
            payload["allowed_merchants"] = allowed_merchants

        result = self._http_request("POST", "/mandates/delegate", payload)
        if "mandate_id" in result:
            self.mandates[result["mandate_id"]] = result
            logger.info(
                "Delegated mandate %s → %s ($%s for %s)",
                parent_id[:8], result["mandate_id"][:8], max_total, agent_id,
            )
        return result

    def get_mandate(self, mandate_id: str) -> dict:
        """Get mandate details."""
        return self._http_request("GET", f"/mandates/{mandate_id}")

    def list_mandates(self) -> dict:
        """List all mandates."""
        return self._http_request("GET", "/mandates")

    def freeze_mandate(self, mandate_id: str, reason: str = "", cascade: bool = True) -> dict:
        """Freeze a mandate (and optionally all children)."""
        return self._http_request("POST", "/mandates/freeze", {
            "mandate_id": mandate_id,
            "reason": reason,
            "cascade": cascade,
        })

    def screen_address(self, address: str) -> dict:
        """Screen a wallet address against OFAC sanctions (free)."""
        result = self._http_request("POST", "/screen/address", {"address": address})
        logger.info("Screen %s: hit=%s", address[:10], result.get("hit", "unknown"))
        return result

    def screen_entity(self, name: str) -> dict:
        """Screen an entity name against OFAC sanctions (free)."""
        return self._http_request("POST", "/screen/entity", {"name": name})

    def get_dashboard(self) -> dict:
        """Get aggregate dashboard stats (free)."""
        return self._http_request("GET", "/dashboard/summary")

    # --- Paid endpoint (tempo CLI) ---

    def _tempo_request(self, method: str, url: str, data: dict | None = None) -> dict | str:
        """Execute a tempo request for MPP-paid endpoints."""
        cmd = [self.tempo_path, "request", "-j", "-X", method.upper()]

        if data is not None:
            cmd.extend(["--json", json.dumps(data)])

        cmd.extend(["-m", str(self.timeout), "--retries", "2", url])

        logger.debug("Running: %s", " ".join(cmd))

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout + 10,
            )
        except subprocess.TimeoutExpired:
            return {"error": f"tempo timeout after {self.timeout}s"}
        except FileNotFoundError:
            return {"error": f"tempo CLI not found at {self.tempo_path}"}

        output = result.stdout.strip()

        if result.returncode != 0:
            stderr = result.stderr.strip()
            return {"error": stderr or output or f"exit code {result.returncode}"}

        return self._parse_output(output)

    @staticmethod
    def _parse_output(output: str) -> dict | str:
        """Parse tempo CLI output, extracting JSON from mixed output."""
        if not output:
            return {}

        try:
            return json.loads(output)
        except json.JSONDecodeError:
            pass

        lines = output.split("\n")
        for i in range(len(lines) - 1, -1, -1):
            candidate = "\n".join(lines[i:]).strip()
            if candidate.startswith("{") or candidate.startswith("["):
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    continue

        for line in reversed(lines):
            line = line.strip()
            if line.startswith("{") or line.startswith("["):
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    continue

        return output

    def evaluate(
        self,
        amount: str,
        merchant: str,
        currency: str = "USDC",
        network: str = "tempo",
        category: str = "general",
        agent_id: str = "",
        principal_id: str = "",
        mandate_id: str = "",
        service_id: str = "",
        service_path: str = "",
        destination_address: str = "",
    ) -> GuardVerdict:
        """Evaluate a payment via the V2 intelligence pipeline (paid, $0.001).

        Runs the full 8-gate pipeline: dedup, governance, sanctions,
        risk ML, policy, action resolution, spend recording, audit.
        """
        payload = {
            "amount": amount,
            "merchant": merchant,
            "currency": currency,
            "network": network,
            "category": category,
            "agent_id": agent_id,
            "principal_id": principal_id,
            "mandate_id": mandate_id,
            "service_id": service_id,
            "service_path": service_path,
            "destination_address": destination_address,
        }

        logger.info("Evaluating: $%s to %s (agent=%s, mandate=%s)",
                     amount, merchant, agent_id, mandate_id[:8] if mandate_id else "none")

        response = self._tempo_request(
            method="POST",
            url=f"{self.guard_url}/evaluate/v2",
            data=payload,
        )

        if isinstance(response, str):
            return GuardVerdict(
                allowed=False, action="ERROR", summary=f"Unexpected response: {response}",
                risk_score=1.0, checks=[], latency_ms=0, agent_id=agent_id, mandate_id=mandate_id,
            )

        if "error" in response:
            return GuardVerdict(
                allowed=False, action="ERROR", summary=response["error"],
                risk_score=1.0, checks=[], latency_ms=0, agent_id=agent_id, mandate_id=mandate_id,
            )

        verdict = GuardVerdict.from_response(response)
        logger.info("Verdict: %s — %s", verdict.action, verdict.summary)
        return verdict


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")

    guard = GuardClient()

    print("\n=== Sardis Guard V2 Client ===\n")

    print("[1] Health check...")
    health = guard.health()
    print(f"    {health}\n")

    print("[2] Screen Tornado Cash address...")
    screen = guard.screen_address("0x722122dF12D4e14e13Ac3b6895a86e84145b6967")
    print(f"    Hit: {screen.get('hit')}")
    print(f"    Result: {json.dumps(screen, indent=2)}\n")

    print("Done.")
