---
name: sardis-company-builder
description: >
  Use this skill when the user wants to start a company, build a startup, create a business, validate a business idea, or generate a company from scratch. The agent will autonomously discover MPP services, research the market, validate the idea with AI, generate branding, set up email, deploy a website, and produce technical specs.
---

# Sardis Company Builder

An autonomous AI agent that starts companies using real MPP micropayments on the Tempo blockchain.

## What It Does

Give it a company idea. It will:
1. **Discover** 54+ MPP services dynamically
2. **Plan** using Claude AI — picks the best services for your idea
3. **Research** the market (Perplexity, Exa, Browserbase)
4. **Validate** the idea (Reddit, news, blockchain data)
5. **Create** branding (fal.ai logo), email (StableEmail), website (StableUpload)
6. **Generate** SPECS.md — actionable technical specs for coding agents

## Quick Start

```bash
# Clone and install
git clone https://github.com/EfeDurmaz16/sardis-company-builder.git
cd sardis-company-builder
pip install -r requirements.txt

# Make sure tempo CLI is set up
source ~/.tempo/env
tempo wallet whoami

# Run the builder
python company_builder.py "your company idea here"
```

## Output Files

- **report.json** — full execution data (every API call, cost, result)
- **report.html** — visual HTML report
- **SPECS.md** — technical specs for coding agents

## Feed Specs to Your Coding Agent

After running the builder, use the generated SPECS.md:

```bash
# With Claude Code
cat SPECS.md  # then ask Claude Code to implement it

# Or pipe directly
python company_builder.py "AI fitness coach" && cat SPECS.md
```

## As an MPP Service

The builder is also available as a paid MPP service:

```bash
# Build a company via MPP ($1.00 per run)
tempo request -X POST --json '{"description": "AI-powered marketplace for freelance developers"}' \
  https://sardis-company-builder-277977675568.us-central1.run.app/build

# Free tier for testing
tempo request -X POST --json '{"description": "your idea"}' \
  https://sardis-company-builder-277977675568.us-central1.run.app/build/free
```

## Example Ideas to Try

- "Decentralized reputation system for AI agents"
- "AI-powered content moderation service for social platforms"
- "Autonomous supply chain optimization using blockchain"
- "Pay-per-query scientific research database"
- "AI agent marketplace for business process automation"

## How It Discovers Services

The agent uses `tempo wallet services` to find all available MPP services at runtime. No hardcoded URLs. It then asks Claude to pick the best services for your specific company idea.

Services it commonly uses: Perplexity (AI search), Exa (neural search), Browserbase (web scraping), Anthropic Claude (AI validation), fal.ai (image generation), Hunter (domain intel), StableEmail (email), StableUpload (website hosting), Stripe Climate (carbon offset), Allium (blockchain data).

## Cost

~$0.20-0.30 USDC per run (paid by the builder to downstream services).
If using the hosted MPP service: $1.00 per run.
