"""Sardis Company Builder — MPP-enabled FastAPI server.

This server IS an MPP service. Users pay $1.00 USDC with their own
Tempo wallets to build companies. The server aggregates downstream
service costs (~$0.20) and keeps the margin (~$0.80).

Without MPP payment → 402 Payment Required.
No free tier in production. Every call must be paid.
"""

from __future__ import annotations

import json
import logging
import os
import secrets
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)

# --- Payment Config ---
# This is where users' payments go — OUR wallet
WALLET_ADDRESS = "0xa4df1d31bc4741e2aa09a5f458311b85ca6c309c"
USDC_TOKEN = "0x20c000000000000000000000b9537d11c60e8b50"
MPP_SECRET = os.environ.get("MPP_SECRET_KEY", secrets.token_hex(32))
BUILD_PRICE = "1.00"  # Users pay $1.00 per build

# --- MPP Payment Handler ---
mpp_handler = None
try:
    from mpp.server import Mpp
    from mpp.methods.tempo import tempo

    mpp_handler = Mpp.create(
        method=tempo(
            currency=USDC_TOKEN,
            recipient=WALLET_ADDRESS,
        ),
        secret_key=MPP_SECRET,
    )
    logging.info("MPP payment handler initialized — recipient: %s", WALLET_ADDRESS)
except ImportError as e:
    logging.error("pympp not installed: %s — PAYMENT GATING DISABLED", e)
except Exception as e:
    logging.error("MPP init failed: %s — PAYMENT GATING DISABLED", e)


app = FastAPI(
    title="Sardis Company Builder",
    description="AI agent that starts companies. Pay $1 USDC via MPP.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["WWW-Authenticate", "Payment-Receipt"],
)


# --- Helper: verify payment or return 402 ---

async def require_payment(request: Request, amount: str = BUILD_PRICE, description: str = "Company build"):
    """Verify MPP payment or return 402 challenge.

    Returns (credential, receipt) if paid, or a 402 Response if not.
    """
    if mpp_handler is None:
        # If pympp isn't loaded, BLOCK the request — don't give free access
        return JSONResponse(
            status_code=503,
            content={
                "error": "Payment system unavailable",
                "detail": "MPP payment handler not initialized. Service cannot accept payments.",
            },
        )

    from mpp import Challenge

    auth_header = request.headers.get("authorization")
    result = await mpp_handler.charge(
        authorization=auth_header,
        amount=amount,
        description=f"Sardis Company Builder — {description}",
    )

    if isinstance(result, Challenge):
        return JSONResponse(
            status_code=402,
            content={
                "type": "https://paymentauth.org/problems/payment-required",
                "title": "Payment Required",
                "status": 402,
                "detail": f"Pay ${amount} USDC to use Sardis Company Builder. Use `tempo request` to pay automatically.",
                "challengeId": result.id,
            },
            headers={
                "WWW-Authenticate": result.to_www_authenticate(mpp_handler.realm),
                "Cache-Control": "no-store",
            },
        )

    return result  # (credential, receipt) tuple


# --- Endpoints ---

@app.get("/")
async def info():
    return {
        "service": "sardis-company-builder",
        "version": "2.0.0",
        "description": "Autonomous AI agent that starts companies using MPP micropayments",
        "pricing": {
            "build": f"${BUILD_PRICE} USDC",
            "payment": "MPP (Machine Payments Protocol) — pay with your Tempo wallet",
            "recipient": WALLET_ADDRESS,
        },
        "usage": {
            "step_1": "Install tempo CLI: curl -fsSL https://tempo.xyz/install | bash",
            "step_2": "Login: tempo wallet login",
            "step_3": f"Build: tempo request -X POST --json '{{\"description\": \"your idea\"}}' https://sardis-company-builder-482463483786.us-central1.run.app/build",
            "generate_idea": "tempo request -X POST https://sardis-company-builder-482463483786.us-central1.run.app/generate-idea",
        },
        "endpoints": {
            "POST /build": f"Build a company (${BUILD_PRICE} USDC via MPP)",
            "POST /generate-idea": f"AI generates idea + builds (${BUILD_PRICE} USDC via MPP)",
            "GET /health": "Health check (free)",
        },
        "mpp_enabled": mpp_handler is not None,
        "github": "https://github.com/EfeDurmaz16/sardis-company-builder",
    }


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "mpp_enabled": mpp_handler is not None,
        "wallet": WALLET_ADDRESS,
        "timestamp": time.time(),
    }


@app.post("/build")
async def build_company(request: Request):
    """Build a company — requires MPP payment ($1.00 USDC).

    User pays with their Tempo wallet. Payment goes to our wallet.
    We use our wallet to call downstream services (~$0.20).
    """
    # Require payment first
    payment_result = await require_payment(request, BUILD_PRICE, "Build company")
    if isinstance(payment_result, JSONResponse):
        return payment_result  # 402 or 503

    credential, receipt = payment_result
    logging.info("Payment received from user — building company")

    # Parse body
    body = await request.json()
    description = body.get("description", "")
    if not description:
        return JSONResponse(status_code=400, content={"error": "description is required"})

    # Build the company using OUR wallet for downstream calls
    from company_builder import CompanyBuilder
    builder = CompanyBuilder(company_description=description, budget=2.0)
    report = builder.build()

    return JSONResponse(
        content=report.to_json(),
        headers={"Payment-Receipt": str(receipt)},
    )


@app.post("/generate-idea")
async def generate_and_build(request: Request):
    """Generate a startup idea + build — requires MPP payment ($1.00 USDC)."""
    payment_result = await require_payment(request, BUILD_PRICE, "Generate idea + build")
    if isinstance(payment_result, JSONResponse):
        return payment_result

    credential, receipt = payment_result
    logging.info("Payment received — generating idea and building")

    from company_builder import generate_idea, CompanyBuilder
    idea = generate_idea()
    builder = CompanyBuilder(company_description=idea, budget=2.0)
    report = builder.build()

    return JSONResponse(
        content=report.to_json(),
        headers={"Payment-Receipt": str(receipt)},
    )


@app.post("/build/html")
async def build_company_html(request: Request):
    """Build + HTML report — requires MPP payment."""
    payment_result = await require_payment(request, BUILD_PRICE, "Build company (HTML)")
    if isinstance(payment_result, JSONResponse):
        return payment_result

    credential, receipt = payment_result

    body = await request.json()
    description = body.get("description", "")
    if not description:
        return JSONResponse(status_code=400, content={"error": "description is required"})

    from company_builder import CompanyBuilder
    builder = CompanyBuilder(company_description=description, budget=2.0)
    report = builder.build()

    return HTMLResponse(
        content=report.to_html(),
        headers={"Payment-Receipt": str(receipt)},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
