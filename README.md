# Sardis Company Builder

**An autonomous AI agent that starts companies using real MPP micropayments.**

> **Live API:** https://sardis-company-builder-482463483786.us-central1.run.app
>
> **Try it now:**
> ```bash
> curl -X POST https://sardis-company-builder-482463483786.us-central1.run.app/build/free \
>   -H 'Content-Type: application/json' \
>   -d '{"description": "AI-powered fitness coaching platform"}'
> ```

Give it an idea. It discovers services, creates a plan, researches the market, validates the idea, generates branding, deploys infrastructure, and produces technical specs — all autonomously, all paid via micropayments on the Tempo blockchain.

Built for the [Tempo MPP Hackathon](https://tempo.xyz) (March 2026).

## How It Works

The agent doesn't follow a fixed pipeline. It **discovers 54+ MPP services**, asks Claude to create a custom plan, executes it, adapts based on results, and generates specs for coding agents.

```
                        ┌─────────────────┐
                        │  Company Idea    │
                        └────────┬────────┘
                                 │
                   ┌─────────────▼─────────────┐
                   │  1. Discover 54+ Services  │  (tempo wallet services)
                   └─────────────┬─────────────┘
                                 │
                   ┌─────────────▼─────────────┐
                   │  2. AI Plans the Pipeline  │  (Claude via Anthropic MPP)
                   └─────────────┬─────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                   │
     ┌────────▼────────┐ ┌──────▼──────┐ ┌─────────▼─────────┐
     │   Research       │ │  Validate   │ │     Create         │
     │ Perplexity      │ │ Reddit      │ │ Logo (fal.ai)     │
     │ Exa Search      │ │ News        │ │ Email (StableEmail)│
     │ Browserbase     │ │ Allium      │ │ Website (Upload)   │
     │ Hunter          │ │ SpyFu       │ │ Domain (Hunter)    │
     └────────┬────────┘ └──────┬──────┘ └─────────┬─────────┘
              │                  │                   │
              └──────────────────┼───────────────────┘
                                 │
                   ┌─────────────▼─────────────┐
                   │  Adapt Plan After Phases   │  (Claude re-evaluates)
                   └─────────────┬─────────────┘
                                 │
                   ┌─────────────▼─────────────┐
                   │  Generate SPECS.md         │  (for coding agents)
                   └───────────────────────────┘
```

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

## Output

The builder produces:
- **report.json** — full execution report with all data
- **report.html** — visual HTML report
- **SPECS.md** — technical specs that coding agents can execute

### Feed SPECS.md to your coding agent

The key output is `SPECS.md` — a complete technical specification that Claude Code, Codex, or any coding agent can use to start building the product:

```bash
# Run the builder
python company_builder.py "decentralized ride-sharing for autonomous vehicles"

# Feed specs to Claude Code
cat SPECS.md | claude "Build this product. Start with the MVP."
```

## Architecture

```
agent.py              # AI brain — Claude decides which services to use
company_builder.py    # Orchestrator — executes the agent's plan
discovery.py          # Native service discovery (tempo wallet services)
services.py           # Generic MPP caller for any service
report.py             # Report generator (JSON, text, HTML)
server.py             # FastAPI API endpoint
guard_client.py       # Optional: Sardis Guard governance
```

### How the Agent Decides

1. **Discovery** — queries `tempo wallet -j services list` to get all 54+ services with their endpoints and pricing
2. **Planning** — sends the service catalog + company idea to Claude, which creates a phased plan
3. **Execution** — runs each step, calling discovered services via tempo CLI
4. **Adaptation** — after each phase, asks Claude if the plan should change based on results
5. **Specs** — generates actionable technical specs from all gathered data

### MPP Proxy for Non-MPP APIs

Services not natively on MPP can be wrapped using [Cloudflare mpp-proxy](https://github.com/cloudflare/mpp-proxy) — a Cloudflare Worker that adds MPP payment gating to any origin API.

## Services Used

The agent dynamically picks from 54+ services. Common ones:

| Service | What | Cost |
|---------|------|------|
| **Anthropic (Claude)** | AI brain — planning, validation, specs | ~$0.01/call |
| **Perplexity** | Market research with citations | ~$0.05 |
| **Exa (StableEnrich)** | Competitor search | ~$0.01 |
| **Browserbase** | Web scraping and search | ~$0.01 |
| **fal.ai FLUX** | Logo and branding generation | ~$0.05 |
| **Hunter** | Domain and email intelligence | ~$0.01 |
| **StableEmail** | Send emails | ~$0.02 |
| **StableUpload** | Static site hosting | ~$0.02 |
| **Reddit (StableEnrich)** | Social validation | ~$0.02 |
| **SpyFu** | SEO/keyword research | varies |
| **Allium** | Blockchain data | varies |
| **Stripe Climate** | Carbon offsets | ~$0.01 |

**Total cost per run: ~$0.20-0.30 USDC**

## API Server

```bash
uvicorn server:app --host 0.0.0.0 --port 8080

curl -X POST http://localhost:8080/build \
  -H 'Content-Type: application/json' \
  -d '{"description": "decentralized ride-sharing platform"}'
```

## Part of Sardis

- **Session 1**: [Sardis Guard Intelligence Plane](https://github.com/EfeDurmaz16/sardis-guard-mpp) — 8-gate financial intelligence for AI agent payments
- **Session 2**: This repo — autonomous AI agent company builder

## License

MIT
