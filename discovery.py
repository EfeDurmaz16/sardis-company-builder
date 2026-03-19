"""Native MPP service discovery via tempo CLI.

Wraps `tempo wallet -j services` to dynamically discover all 54+ MPP
services at runtime. No hardcoded URLs — everything is discovered.

Usage:
    disco = ServiceDiscovery()
    services = disco.discover_all()
    perplexity = disco.get_service("perplexity")
    ai_services = disco.search("image generation")
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("company_builder.discovery")


@dataclass
class DiscoveredService:
    """Metadata for a discovered MPP service."""

    id: str
    name: str
    url: str
    service_url: str
    description: str
    categories: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    endpoints: list[dict] = field(default_factory=list)
    docs: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> DiscoveredService:
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            url=data.get("url", ""),
            service_url=data.get("service_url", data.get("url", "")),
            description=data.get("description", ""),
            categories=data.get("categories", []),
            tags=data.get("tags", []),
            endpoints=data.get("endpoints", []),
            docs=data.get("docs", {}),
        )

    def get_endpoint(self, path_contains: str = "", method: str = "POST") -> dict | None:
        """Find an endpoint matching path substring and method."""
        for ep in self.endpoints:
            ep_method = ep.get("method", "").upper()
            ep_path = ep.get("path", "")
            if ep_method == method.upper() and path_contains in ep_path:
                return ep
        # Fallback: just match path
        for ep in self.endpoints:
            if path_contains in ep.get("path", ""):
                return ep
        return None

    def get_cost(self, endpoint_path: str = "") -> float | None:
        """Get the cost for an endpoint in USD (from payment.amount in micro-units)."""
        ep = self.get_endpoint(endpoint_path) if endpoint_path else None
        if ep is None and self.endpoints:
            ep = self.endpoints[0]
        if ep and "payment" in ep:
            payment = ep["payment"]
            amount = payment.get("amount")
            decimals = payment.get("decimals", 6)
            if amount is not None:
                try:
                    return int(amount) / (10 ** decimals)
                except (ValueError, TypeError):
                    pass
        return None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "service_url": self.service_url,
            "description": self.description,
            "categories": self.categories,
            "tags": self.tags,
            "endpoint_count": len(self.endpoints),
        }


class ServiceDiscovery:
    """Native MPP service discovery using `tempo wallet -j services`.

    Discovers services dynamically from the Tempo network directory.
    All service URLs, endpoints, and pricing come from the directory.
    """

    def __init__(self, tempo_path: str | None = None, timeout: int = 30):
        if tempo_path:
            self.tempo_path = tempo_path
        else:
            found = shutil.which("tempo")
            if not found:
                raise RuntimeError("tempo CLI not found in PATH")
            self.tempo_path = found
        self.timeout = timeout
        self._cache: dict[str, DiscoveredService] = {}

    def _run_tempo(self, args: list[str]) -> Any:
        """Run a tempo wallet command and parse JSON output."""
        cmd = [self.tempo_path, "wallet", "-j"] + args
        logger.debug("Running: %s", " ".join(cmd))

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
        except subprocess.TimeoutExpired:
            logger.error("tempo command timed out: %s", " ".join(args))
            return None

        if proc.returncode != 0:
            logger.error("tempo failed (exit %d): %s", proc.returncode, proc.stderr.strip())
            return None

        output = proc.stdout.strip()
        if not output:
            return None

        try:
            return json.loads(output)
        except json.JSONDecodeError:
            # Try to extract JSON from mixed output
            for line in reversed(output.split("\n")):
                line = line.strip()
                if line.startswith("{") or line.startswith("["):
                    try:
                        return json.loads(line)
                    except json.JSONDecodeError:
                        continue
            logger.warning("Could not parse tempo output as JSON")
            return None

    def discover_all(self) -> list[DiscoveredService]:
        """Discover all available MPP services.

        Returns:
            List of all services in the Tempo directory.
        """
        data = self._run_tempo(["services", "list"])
        if not data or not isinstance(data, list):
            logger.warning("No services discovered")
            return []

        services = []
        for item in data:
            svc = DiscoveredService.from_dict(item)
            self._cache[svc.id] = svc
            services.append(svc)

        logger.info("Discovered %d MPP services", len(services))
        return services

    def search(self, query: str) -> list[DiscoveredService]:
        """Search for services matching a query.

        Args:
            query: Search term (matches name, description, tags, category).

        Returns:
            List of matching services.
        """
        data = self._run_tempo(["services", "--search", query])
        if not data or not isinstance(data, list):
            return []

        services = []
        for item in data:
            svc = DiscoveredService.from_dict(item)
            self._cache[svc.id] = svc
            services.append(svc)

        logger.info("Search '%s' found %d services", query, len(services))
        return services

    def get_service(self, service_id: str) -> DiscoveredService | None:
        """Get full metadata for a specific service.

        Args:
            service_id: The service ID (e.g. "perplexity", "fal").

        Returns:
            Service metadata or None if not found.
        """
        # Check cache first
        if service_id in self._cache:
            return self._cache[service_id]

        data = self._run_tempo(["services", service_id])
        if not data or not isinstance(data, dict):
            logger.warning("Service '%s' not found", service_id)
            return None

        svc = DiscoveredService.from_dict(data)
        self._cache[svc.id] = svc
        return svc

    def get_service_url(self, service_id: str) -> str | None:
        """Quick lookup: get just the service URL."""
        svc = self.get_service(service_id)
        return svc.service_url if svc else None

    def list_by_category(self, category: str) -> list[DiscoveredService]:
        """Search services by category."""
        return self.search(category)

    def print_catalog(self):
        """Print a formatted catalog of all discovered services."""
        services = self.discover_all()
        print(f"\n{'='*60}")
        print(f"  MPP Service Directory — {len(services)} services")
        print(f"{'='*60}\n")
        for svc in services:
            cost = svc.get_cost()
            cost_str = f"${cost:.4f}" if cost else "dynamic"
            print(f"  [{svc.id}] {svc.name}")
            print(f"    URL: {svc.service_url}")
            print(f"    {svc.description}")
            print(f"    Endpoints: {len(svc.endpoints)} | Cost: {cost_str}")
            print(f"    Tags: {', '.join(svc.tags)}")
            print()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    disco = ServiceDiscovery()
    disco.print_catalog()
