---
name: sardis-company-builder
description: >
  Use this skill when the user wants to start a company, build a startup, create a business, validate a business idea, or generate a company from scratch. Activate when user says "build a company", "start a startup", "create a business", "validate my idea", or "generate a company". This skill uses real MPP micropayments to autonomously research, validate, brand, and spec out a company.
---

# Sardis Company Builder

An autonomous AI agent that starts companies using real MPP micropayments on Tempo.

**Live API:** `https://sardis-company-builder-482463483786.us-central1.run.app`

## How To Use

### Option 1: API Call (Recommended — no setup needed)

Use `tempo request` or `curl` to call the live API:

```bash
# Build a company from your idea (free tier)
tempo request -X POST --json '{"description": "AI-powered fitness coaching platform"}' \
  https://sardis-company-builder-482463483786.us-central1.run.app/build/free

# Generate an idea AND build the company (no input needed!)
tempo request -X POST \
  https://sardis-company-builder-482463483786.us-central1.run.app/generate-idea

# Or use curl
curl -X POST https://sardis-company-builder-482463483786.us-central1.run.app/build/free \
  -H 'Content-Type: application/json' \
  -d '{"description": "decentralized reputation system for AI agents"}'
```

### Option 2: Run Locally

```bash
git clone https://github.com/EfeDurmaz16/sardis-company-builder.git
cd sardis-company-builder
pip install -r requirements.txt
source ~/.tempo/env

# Build with your idea
python company_builder.py "your idea here"

# Or let AI generate the idea
python company_builder.py --generate-idea
```

## What Happens

1. **Discovers** 54+ MPP services via Tempo directory
2. **Plans** — Claude AI analyzes your idea + available services, creates a custom execution plan
3. **Researches** — Perplexity (market data), Exa (competitors), Browserbase (web scraping), Reddit (community validation)
4. **Validates** — Claude evaluates the business model, names the company, scores viability
5. **Creates** — fal.ai (logo), StableEmail (launch email), StableUpload (landing page), Hunter (domain intel)
6. **Specs** — generates SPECS.md with full technical specification for coding agents

## Output

The API returns JSON with:
- `company.name` — AI-suggested company name
- `summary` — execution stats (steps, cost, duration)
- `steps[]` — every service call with results
- The last step contains `raw_data` with full technical specs

When run locally, also saves:
- `report.json` — full data
- `report.html` — visual report
- `SPECS.md` — feed this to your coding agent to start building!

## Example Ideas

- "AI-powered micropayments platform for autonomous agents"
- "Decentralized reputation system for AI agents"
- "AI content moderation service for social media brands"
- "Autonomous supply chain optimization using blockchain"
- "Pay-per-query scientific research database"

## Cost

- **Free tier** (`/build/free`): uses the builder's wallet, limited budget
- **Local run**: ~$0.15-0.30 USDC from your wallet
- **Paid API** (`/build`): $1.00 USDC via MPP (coming soon)

## Source

GitHub: https://github.com/EfeDurmaz16/sardis-company-builder
