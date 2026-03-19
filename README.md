# Sardis Company Builder

AI agent that autonomously starts a company using real MPP (Machine Payments Protocol) micropayments on the Tempo blockchain.

**Give it a company description. It discovers services, researches the market, finds competitors, generates a logo, sets up email, offsets carbon — all paid via micropayments, all autonomous.**

Built for the [Tempo MPP Hackathon](https://tempo.xyz) (March 2026).

## What It Does

The agent receives a goal like *"Start a company in the AI payments space"* and autonomously:

| Step | Service | What | Cost |
|------|---------|------|------|
| 1 | Tempo Directory | Discovers 54+ available MPP services | Free |
| 2 | Perplexity | Market research — TAM, trends, projections | ~$0.05 |
| 3 | Exa (StableEnrich) | Competitor search — finds similar startups | ~$0.01 |
| 4 | Browserbase | Web scraping — deep industry analysis | ~$0.01 |
| 5 | fal.ai FLUX | Logo generation — creates company branding | ~$0.05 |
| 6 | AgentMail | Email setup — creates inbox for the company | ~$0.01 |
| 7 | Stripe Climate | Carbon offset — funds removal projects | ~$0.01 |
| 8 | Allium | Blockchain data — checks token prices | ~$0.01 |

**Total cost per run: ~$0.15 USDC**

Every service is **discovered dynamically** via `tempo wallet services` — no hardcoded URLs.

## Quick Start

```bash
# Install tempo CLI
curl -fsSL https://tempo.xyz/install | bash
source ~/.tempo/env
tempo wallet login

# Install deps
pip install -r requirements.txt

# Run the builder
python company_builder.py "AI-powered micropayments platform for autonomous agents"
```

## API Server

```bash
# Start the server
uvicorn server:app --host 0.0.0.0 --port 8080

# Build a company
curl -X POST http://localhost:8080/build \
  -H 'Content-Type: application/json' \
  -d '{"description": "AI-powered micropayments platform"}'
```

## Architecture

```
company_builder.py     # Main orchestrator — runs the 8-step pipeline
├── discovery.py       # Native service discovery via `tempo wallet services`
├── services.py        # Generic MPP caller — works with any discovered service
├── report.py          # Report generator (JSON, text, HTML)
├── guard_client.py    # Optional: Sardis Guard governance layer
└── server.py          # FastAPI API endpoint
```

### Native Service Discovery

The builder doesn't hardcode any service URLs. Instead, it uses `tempo wallet -j services` to discover all available MPP services at runtime:

```python
from discovery import ServiceDiscovery

disco = ServiceDiscovery()
services = disco.discover_all()         # 54+ services
perplexity = disco.get_service("perplexity")  # Full metadata
ai_services = disco.search("image generation")  # Search by intent
```

### Generic MPP Caller

Any discovered service can be called through a single interface:

```python
from services import MPPCaller

caller = MPPCaller()
result = caller.call(
    service_url="https://stableenrich.dev",
    endpoint_path="/api/exa/search",
    method="POST",
    data={"query": "AI payments startups"},
)
```

## Sample Output

```
======================================================================
  SARDIS COMPANY BUILDER — RUN REPORT
======================================================================

  Company: AI-powered micropayments platform for autonomous agents
  Duration: 35.2s
  Total Cost: $0.1490 USDC
  Services Discovered: 54
  Steps: 6/8 successful

  [+] Step 2: Market Research (Perplexity)    $0.0500  3910ms
  [+] Step 3: Competitor Search (Exa)         $0.0100  4107ms
  [+] Step 4: Web Scraping (Browserbase)      $0.0100  3891ms
  [+] Step 5: Logo Generation (fal.ai FLUX)   $0.0500  15432ms
  [+] Step 7: Carbon Offset (Stripe Climate)  $0.0100  1232ms

  SPENDING BREAKDOWN
  perplexity           $0.0510  #############
  fal                  $0.0510  #############
  stableenrich         $0.0110  ##
  browserbase          $0.0110  ##
  TOTAL                $0.1490
```

## Deployment

### Cloud Run

```bash
gcloud run deploy sardis-company-builder \
  --source . \
  --region us-central1 \
  --allow-unauthenticated
```

## Tech Stack

- **Python 3.12+** with FastAPI
- **Tempo CLI** for MPP payments
- **54+ real MPP services** via native discovery
- **USDC on Tempo** (chain 4217)

## Part of Sardis

This is Session 2 of the Sardis project for the Tempo MPP Hackathon:
- **Session 1**: [Sardis Guard Intelligence Plane](https://github.com/EfeDurmaz16/sardis-guard-mpp) — 8-gate financial intelligence for AI agent payments
- **Session 2**: This repo — AI agent that autonomously starts a company using MPP

## License

MIT
