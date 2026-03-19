"""Generic MPP service caller — works with any discovered service.

Uses tempo CLI to call any MPP endpoint. Composes with GuardClient
for guarded calls (evaluate first, then call if allowed).

Usage:
    caller = MPPCaller()
    result = caller.call("https://stableenrich.dev", "/api/exa/search",
                         "POST", {"query": "AI payments"})
    # Or with guard:
    result = caller.guarded_call(guard, "https://stableenrich.dev",
                                  "/api/exa/search", "POST", data, ...)
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("company_builder.services")


@dataclass
class ServiceResult:
    """Structured result from an MPP service call."""

    service_id: str
    action: str
    success: bool
    data: dict | list | str | None = None
    error: str | None = None
    cost: float = 0.0
    latency_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "service_id": self.service_id,
            "action": self.action,
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "cost": round(self.cost, 6),
            "latency_ms": round(self.latency_ms, 1),
            "timestamp": self.timestamp,
        }


@dataclass
class GuardedResult:
    """Result of a guarded MPP call: guard verdict + service result."""

    step_name: str
    guard_allowed: bool
    guard_action: str
    guard_summary: str
    service_result: ServiceResult | None = None
    error: str | None = None
    total_cost: float = 0.0  # guard eval cost + service cost

    def to_dict(self) -> dict:
        return {
            "step_name": self.step_name,
            "guard_allowed": self.guard_allowed,
            "guard_action": self.guard_action,
            "guard_summary": self.guard_summary,
            "service_result": self.service_result.to_dict() if self.service_result else None,
            "error": self.error,
            "total_cost": round(self.total_cost, 6),
        }


class MPPCaller:
    """Generic MPP service caller using tempo CLI."""

    GUARD_EVAL_COST = 0.001  # Cost per Guard /evaluate/v2 call

    def __init__(self, tempo_path: str | None = None, timeout: int = 60):
        if tempo_path:
            self.tempo_path = tempo_path
        else:
            found = shutil.which("tempo")
            if not found:
                raise RuntimeError("tempo CLI not found in PATH")
            self.tempo_path = found
        self.timeout = timeout
        self.total_cost: float = 0.0
        self.call_count: int = 0
        self.call_log: list[ServiceResult] = []

    def call(
        self,
        service_url: str,
        endpoint_path: str,
        method: str = "POST",
        data: dict | None = None,
        service_id: str = "",
        cost_estimate: float = 0.0,
    ) -> ServiceResult:
        """Call any MPP service endpoint via tempo CLI.

        Args:
            service_url: Base URL of the service (e.g. "https://stableenrich.dev").
            endpoint_path: API path (e.g. "/api/exa/search").
            method: HTTP method.
            data: Request body (JSON).
            service_id: Service identifier for logging.
            cost_estimate: Estimated cost for tracking.

        Returns:
            ServiceResult with response data.
        """
        url = f"{service_url.rstrip('/')}{endpoint_path}"
        action = endpoint_path.rsplit("/", 1)[-1] if "/" in endpoint_path else endpoint_path
        t0 = time.monotonic()

        cmd = [self.tempo_path, "request", "-j", "-X", method.upper()]

        if data is not None and method.upper() in ("POST", "PUT", "PATCH"):
            cmd.extend(["--json", json.dumps(data)])

        cmd.extend(["-m", str(self.timeout), "--retries", "2", url])

        logger.info("[%s] %s %s", service_id or "mpp", method, url)

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout + 10,
            )
        except subprocess.TimeoutExpired:
            result = ServiceResult(
                service_id=service_id, action=action, success=False,
                error=f"Timeout after {self.timeout}s",
                cost=cost_estimate, latency_ms=(time.monotonic() - t0) * 1000,
            )
            self._record(result)
            return result
        except FileNotFoundError:
            result = ServiceResult(
                service_id=service_id, action=action, success=False,
                error=f"tempo CLI not found at {self.tempo_path}",
                cost=0.0, latency_ms=(time.monotonic() - t0) * 1000,
            )
            self._record(result)
            return result

        latency = (time.monotonic() - t0) * 1000
        output = proc.stdout.strip()
        stderr = proc.stderr.strip()

        if proc.returncode != 0:
            result = ServiceResult(
                service_id=service_id, action=action, success=False,
                error=stderr or output or f"Exit code {proc.returncode}",
                cost=cost_estimate, latency_ms=latency,
            )
            self._record(result)
            return result

        parsed = self._parse_output(output)
        result = ServiceResult(
            service_id=service_id, action=action, success=True,
            data=parsed, cost=cost_estimate, latency_ms=latency,
        )
        self._record(result)
        return result

    def guarded_call(
        self,
        guard,  # GuardClient
        service_url: str,
        endpoint_path: str,
        method: str = "POST",
        data: dict | None = None,
        step_name: str = "",
        amount: str = "0.01",
        merchant: str = "",
        category: str = "general",
        agent_id: str = "",
        mandate_id: str = "",
        service_id: str = "",
        cost_estimate: float = 0.0,
    ) -> GuardedResult:
        """Call a service with Guard evaluation first.

        Flow:
            1. guard.evaluate(amount, merchant, ...) → ALLOW/DENY
            2. If ALLOW → self.call(service_url, endpoint_path, ...)
            3. If DENY → return denial

        Args:
            guard: GuardClient instance.
            service_url: Base URL of the MPP service.
            endpoint_path: API endpoint path.
            method: HTTP method.
            data: Request body.
            step_name: Human-readable step name for reporting.
            amount: Expected cost for Guard evaluation.
            merchant: Merchant URL for Guard.
            category: Spending category.
            agent_id: Agent making the call.
            mandate_id: Mandate authorizing the call.
            service_id: Service identifier.
            cost_estimate: Cost estimate for tracking.

        Returns:
            GuardedResult with guard verdict and optional service result.
        """
        if not merchant:
            from urllib.parse import urlparse
            merchant = urlparse(service_url).netloc

        # Step 1: Guard evaluation
        verdict = guard.evaluate(
            amount=amount,
            merchant=merchant,
            category=category,
            agent_id=agent_id,
            mandate_id=mandate_id,
            service_id=service_id,
            service_path=endpoint_path,
        )

        if not verdict.allowed:
            logger.warning("[%s] DENIED by Guard: %s", step_name, verdict.summary)
            return GuardedResult(
                step_name=step_name,
                guard_allowed=False,
                guard_action=verdict.action,
                guard_summary=verdict.summary,
                error=verdict.summary,
                total_cost=self.GUARD_EVAL_COST,
            )

        # Step 2: Call the service
        logger.info("[%s] ALLOWED — calling %s", step_name, service_id)
        svc_result = self.call(
            service_url=service_url,
            endpoint_path=endpoint_path,
            method=method,
            data=data,
            service_id=service_id,
            cost_estimate=cost_estimate,
        )

        return GuardedResult(
            step_name=step_name,
            guard_allowed=True,
            guard_action=verdict.action,
            guard_summary=verdict.summary,
            service_result=svc_result,
            total_cost=self.GUARD_EVAL_COST + svc_result.cost,
        )

    def _record(self, result: ServiceResult):
        """Track cost and log the call."""
        self.total_cost += result.cost
        self.call_count += 1
        self.call_log.append(result)
        level = logging.INFO if result.success else logging.WARNING
        logger.log(
            level, "[%s] %s — %s (%.0fms, $%.4f)",
            result.service_id, result.action,
            "OK" if result.success else result.error,
            result.latency_ms, result.cost,
        )

    @staticmethod
    def _parse_output(output: str) -> dict | list | str:
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
