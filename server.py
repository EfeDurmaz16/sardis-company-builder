"""Sardis Company Builder — MPP-enabled FastAPI server.

This server IS an MPP service. Users pay with their Tempo wallets
to build companies. The server aggregates downstream service costs
with a 1.5x markup.

Endpoints:
  POST /build — Build a company ($1.00 per run via MPP)
  GET /health — Free health check
  GET / — Free service info
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
from pydantic import BaseModel, Field

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)

# --- MPP Payment Setup ---
WALLET_ADDRESS = os.environ.get(
    "WALLET_ADDRESS",
    "0xa4df1d31bc4741e2aa09a5f458311b85ca6c309c",
)
USDC_TOKEN = "0x20c000000000000000000000b9537d11c60e8b50"
MPP_SECRET = os.environ.get("MPP_SECRET_KEY", secrets.token_hex(32))
BUILD_PRICE = "1.00"  # $1.00 per company build

# Try to import pympp for payment verification
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
    logging.info("MPP payment handler initialized (recipient: %s)", WALLET_ADDRESS[:16])
except ImportError:
    logging.warning("pympp not installed — running without payment gating")
except Exception as e:
    logging.warning("MPP init failed: %s — running without payment gating", e)


app = FastAPI(
    title="Sardis Company Builder",
    description="AI agent that autonomously starts a company using MPP micropayments. Pay $1 to build a company.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["WWW-Authenticate", "Payment-Receipt"],
)


class BuildRequest(BaseModel):
    description: str = Field(
        ...,
        description="Company description / goal",
        examples=["AI-powered micropayments platform for autonomous agents"],
    )
    budget: float = Field(
        default=2.0,
        description="Internal budget for downstream MPP services (USDC). Actual charge to user is $1.00.",
        ge=0.5,
        le=5.0,
    )


@app.get("/")
async def info():
    return {
        "service": "sardis-company-builder",
        "version": "2.0.0",
        "description": "AI agent that autonomously starts a company using real MPP micropayments",
        "pricing": {
            "build": f"${BUILD_PRICE} USDC per run",
            "payment_method": "MPP (Machine Payments Protocol)",
            "wallet": WALLET_ADDRESS,
        },
        "how_to_use": {
            "cli": f'tempo request -X POST --json \'{{"description": "your company idea"}}\' https://YOUR_URL/build',
            "skill": "Install the sardis-company-builder tempo skill",
        },
        "endpoints": {
            "POST /build": f"Build a company (${BUILD_PRICE} via MPP)",
            "POST /build/free": "Build a company (no payment, limited)",
            "GET /health": "Health check (free)",
        },
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
    """Build a company autonomously — payment required via MPP.

    Users pay $1.00 USDC via MPP. The server uses the payment to fund
    downstream MPP service calls (research, branding, email, etc.)
    with a margin for the service operator.
    """
    # MPP payment verification
    if mpp_handler is not None:
        from mpp import Challenge
        auth_header = request.headers.get("authorization")
        result = await mpp_handler.charge(
            authorization=auth_header,
            amount=BUILD_PRICE,
            description="Sardis Company Builder — autonomous company creation",
        )
        if isinstance(result, Challenge):
            # Return 402 with payment challenge
            return JSONResponse(
                status_code=402,
                content={
                    "type": "https://paymentauth.org/problems/payment-required",
                    "title": "Payment Required",
                    "status": 402,
                    "detail": f"Pay ${BUILD_PRICE} USDC to build a company",
                    "challengeId": result.id,
                },
                headers={
                    "WWW-Authenticate": result.to_www_authenticate(mpp_handler.realm),
                    "Cache-Control": "no-store",
                },
            )

        credential, receipt = result
        logging.info("Payment received: %s", receipt)

    # Parse request body
    body = await request.json()
    description = body.get("description", "")
    if not description:
        return JSONResponse(status_code=400, content={"error": "description is required"})

    # Run the builder
    from company_builder import CompanyBuilder
    builder = CompanyBuilder(company_description=description, budget=2.0)
    report = builder.build()

    response_data = report.to_json()

    # Add payment receipt if available
    headers = {}
    if mpp_handler is not None and 'receipt' in dir():
        headers["Payment-Receipt"] = str(receipt)

    return JSONResponse(content=response_data, headers=headers)


@app.post("/build/free")
async def build_company_free(request: Request):
    """Build a company — free endpoint (limited, for testing)."""
    body = await request.json()
    description = body.get("description", "")
    if not description:
        return JSONResponse(status_code=400, content={"error": "description is required"})

    from company_builder import CompanyBuilder
    builder = CompanyBuilder(company_description=description, budget=1.0)
    report = builder.build()

    return JSONResponse(content=report.to_json())


@app.post("/build/html")
async def build_company_html(request: Request):
    """Build a company and return HTML report."""
    body = await request.json()
    description = body.get("description", "")
    if not description:
        return JSONResponse(status_code=400, content={"error": "description is required"})

    from company_builder import CompanyBuilder
    builder = CompanyBuilder(company_description=description, budget=2.0)
    report = builder.build()

    return HTMLResponse(content=report.to_html())


@app.post("/generate-idea")
async def generate_and_build(request: Request):
    """Generate a startup idea with AI, then build the company.

    No input needed — Claude generates the idea autonomously.
    """
    from company_builder import generate_idea, CompanyBuilder

    idea = generate_idea()
    builder = CompanyBuilder(company_description=idea, budget=2.0)
    report = builder.build()

    return JSONResponse(content=report.to_json())


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
