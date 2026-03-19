# Sardis Company Builder

AI agent that autonomously starts a company using real MPP (Machine Payments Protocol) micropayments on the Tempo blockchain.

**Give it a company description. It discovers services, researches the market, validates with AI, generates a logo, sets up email, deploys a website — all paid via micropayments, all autonomous.**

Built for the [Tempo MPP Hackathon](https://tempo.xyz) (March 2026).

## What It Does

The agent receives a goal like *"Start a company in the AI payments space"* and autonomously executes an end-to-end pipeline:

| Step | Service | What | Cost |
|------|---------|------|------|
| 1 | Tempo Directory | Discovers 54+ available MPP services | Free |
| 2 | Perplexity | Market research — TAM, trends, projections | ~$0.05 |
| 3 | Exa (StableEnrich) | Competitor search — finds similar startups | ~$0.01 |
| 4 | Browserbase | Web scraping — deep industry analysis | ~$0.01 |
| 5 | **Claude (Anthropic)** | **AI validation — evaluates idea, names company, scores viability** | ~$0.01 |
| 6 | fal.ai FLUX | Logo generation — creates company branding | ~$0.05 |
| 7 | Hunter | Domain intelligence — email/company data for the domain | ~$0.01 |
| 8 | StableEmail | Launch email — sends announcement email | ~$0.02 |
| 9 | StableUpload | Website deployment — deploys a generated landing page | ~$0.02 |
| 10 | Stripe Climate | Carbon offset — funds removal projects | ~$0.01 |
| 11 | Allium | Blockchain data — checks live token prices | ~$0.01 |

**Total cost per run: ~$0.20 USDC**

Every service is **discovered dynamically** via `tempo wallet services` — no hardcoded URLs. The agent uses the Tempo service directory to find services, their endpoints, and pricing at runtime.

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

## Sample Output

```
SARDIS COMPANY BUILDER — RUN REPORT

  Company: AgentFlow
  Duration: 56.6s
  Total Cost: $0.2000 USDC
  Services Discovered: 54
  Steps: 10/11 successful

  [+] Step 2: Market Research (Perplexity)         $0.0500  3.7s
  [+] Step 3: Competitor Search (Exa)              $0.0100  3.3s
  [+] Step 4: Web Research (Browserbase)           $0.0100  3.9s
  [+] Step 5: AI Validation (Claude)               $0.0100  12.0s
  [+] Step 6: Logo Generation (fal.ai FLUX)        $0.0500  14.9s
  [+] Step 7: Domain Intelligence (Hunter)         $0.0100  3.1s
  [+] Step 8: Launch Email (StableEmail)           $0.0200  2.6s
  [+] Step 9: Website Deploy (StableUpload)        $0.0200  3.3s
  [+] Step 11: Token Prices (Allium)               $0.0100  5.9s
```

## Architecture

```
company_builder.py     # Main orchestrator — 11-step pipeline
├── discovery.py       # Native service discovery via `tempo wallet services`
├── services.py        # Generic MPP caller — works with any discovered service
├── report.py          # Report generator (JSON, text, HTML)
├── guard_client.py    # Optional: Sardis Guard governance layer
└── server.py          # FastAPI API endpoint
```

### Native Service Discovery

The builder doesn't hardcode any service URLs. It uses `tempo wallet -j services` to discover all available MPP services at runtime:

```python
from discovery import ServiceDiscovery

disco = ServiceDiscovery()
services = disco.discover_all()                # 54+ services
perplexity = disco.get_service("perplexity")   # Full metadata
ai_services = disco.search("image generation") # Search by intent
```

### MPP Proxy for Non-MPP Services

Services not natively on MPP can be wrapped using [Cloudflare mpp-proxy](https://github.com/cloudflare/mpp-proxy) — a Cloudflare Worker that adds MPP payment gating to any origin API. This enables the builder to potentially use any API through the MPP payment flow.

## API Server

```bash
# Start the server
uvicorn server:app --host 0.0.0.0 --port 8080

# Build a company (JSON response)
curl -X POST http://localhost:8080/build \
  -H 'Content-Type: application/json' \
  -d '{"description": "AI-powered micropayments platform"}'

# Build a company (HTML response)
curl -X POST http://localhost:8080/build/html \
  -H 'Content-Type: application/json' \
  -d '{"description": "AI-powered micropayments platform"}'
```

## Deployment

```bash
# Cloud Run
gcloud run deploy sardis-company-builder \
  --source . --region us-central1 --allow-unauthenticated
```

## Tech Stack

- **Python 3.12+** with FastAPI
- **Tempo CLI** for MPP payments
- **54+ real MPP services** via native discovery
- **USDC on Tempo** (chain 4217)

## Services Used

| Service | Category | What It Does |
|---------|----------|-------------|
| Perplexity | AI Search | Web-grounded research with citations |
| Exa (StableEnrich) | Neural Search | Find similar companies and content |
| Browserbase | Web Scraping | Headless browser for deep research |
| Anthropic (Claude) | AI | Business idea validation and naming |
| fal.ai | Image Gen | FLUX-based logo generation |
| Hunter | Data | Email finding and domain intelligence |
| StableEmail | Email | Pay-per-send email delivery |
| StableUpload | Hosting | Static site hosting with CDN |
| Stripe Climate | Sustainability | Carbon offset contributions |
| Allium | Blockchain | Real-time token price data |

## Part of Sardis

This is Session 2 of the Sardis project for the Tempo MPP Hackathon:
- **Session 1**: [Sardis Guard Intelligence Plane](https://github.com/EfeDurmaz16/sardis-guard-mpp) — 8-gate financial intelligence for AI agent payments
- **Session 2**: This repo — AI agent that autonomously starts a company using MPP

## License

MIT
