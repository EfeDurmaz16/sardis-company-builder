"""Sardis Company Builder — FastAPI server.

POST /build — Build a company (JSON report)
POST /build/html — Build a company (HTML report)
GET /health — Health check
GET / — Service info
"""

from __future__ import annotations

import logging
import time

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from company_builder import CompanyBuilder

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)

app = FastAPI(
    title="Sardis Company Builder",
    description="AI agent that autonomously starts a company using MPP services",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class BuildRequest(BaseModel):
    description: str = Field(
        ...,
        description="Company description / goal",
        examples=["AI-powered micropayments platform for autonomous agents"],
    )
    budget: float = Field(
        default=5.0,
        description="Total budget in USDC",
        ge=0.1,
        le=10.0,
    )


@app.get("/")
async def info():
    return {
        "service": "sardis-company-builder",
        "version": "1.0.0",
        "description": "AI agent that autonomously starts a company using real MPP micropayments",
        "endpoints": {
            "POST /build": "Build a company (JSON report)",
            "POST /build/html": "Build a company (HTML report)",
            "GET /health": "Health check",
        },
    }


@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": time.time()}


@app.post("/build")
async def build_company(request: BuildRequest):
    """Build a company autonomously using MPP services."""
    try:
        builder = CompanyBuilder(
            company_description=request.description,
            budget=request.budget,
        )
        report = builder.build()
        return JSONResponse(content=report.to_json())
    except Exception as e:
        logging.error("Build failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/build/html")
async def build_company_html(request: BuildRequest):
    """Build a company and return an HTML report."""
    try:
        builder = CompanyBuilder(
            company_description=request.description,
            budget=request.budget,
        )
        report = builder.build()
        return HTMLResponse(content=report.to_html())
    except Exception as e:
        logging.error("Build failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
