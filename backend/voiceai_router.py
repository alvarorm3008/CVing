"""Contrato VoiceAI: context de entrevista + arranque de llamada.

GET  /voiceai/v1/context?resource_id=
POST /voiceai/v1/resources   — guarda CV/oferta y devuelve resource_id
POST /voiceai/v1/start-call  — hidrata VoiceAI (server-side) y devuelve call_url
"""

from __future__ import annotations

import os
import secrets
import time
from typing import Any

import httpx
from ats_checker import structured_cv_to_text
from cv_schema import OfferResearch, StructuredCV
from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/voiceai/v1", tags=["voiceai"])

_TTL_SECONDS = 60 * 60
_RESOURCES: dict[str, dict[str, Any]] = {}


class ResourceBody(BaseModel):
    cv: dict[str, Any] = Field(description="StructuredCV JSON")
    job: str = Field(default="", description="Texto de la oferta")
    offer_research: dict[str, Any] | None = None
    ats_match: dict[str, Any] | None = None
    candidate_name: str | None = None


class StartCallBody(BaseModel):
    resource_id: str
    access_token: str | None = None


def _purge() -> None:
    now = time.time()
    dead = [k for k, v in _RESOURCES.items() if now - v["created_at"] > _TTL_SECONDS]
    for key in dead:
        _RESOURCES.pop(key, None)


def _expected_token() -> str:
    return (
        os.getenv("VOICEAI_ACCESS_TOKEN", "").strip()
        or os.getenv("CVING_VOICEAI_TOKEN", "").strip()
        or "demo"
    )


def _check_bearer(authorization: str | None) -> None:
    expected = _expected_token()
    if expected == "demo":
        return
    token = ""
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    if token != expected:
        raise HTTPException(status_code=401, detail="Bearer token inválido")


def _context_from_resource(row: dict[str, Any]) -> dict[str, str]:
    cv_raw = row.get("cv") or {}
    research_raw = row.get("offer_research") or {}
    ats_raw = row.get("ats_match") or {}
    job = str(row.get("job") or "")

    candidate = str(row.get("candidate_name") or "").strip()
    company = ""
    role = ""
    cv_text = ""

    cv = None
    if isinstance(cv_raw, dict) and cv_raw:
        try:
            cv = StructuredCV.model_validate(cv_raw)
        except Exception:
            cv = None
    if cv is not None:
        candidate = candidate or (cv.contact.full_name if cv.contact else "") or ""
        role = (cv.contact.headline if cv.contact else "") or ""
        try:
            cv_text = structured_cv_to_text(cv)
        except Exception:
            cv_text = str(cv_raw)

    research = None
    if isinstance(research_raw, dict) and research_raw:
        try:
            research = OfferResearch.model_validate(research_raw)
        except Exception:
            research = None
    if research is not None:
        company = (research.company_name or "").strip()
        role = (research.job_title or "").strip() or role

    if isinstance(ats_raw, dict):
        role = str(ats_raw.get("target_role") or role).strip()

    return {
        "candidate_name": candidate or "el candidato",
        "company": company or "la empresa",
        "role": role or "el puesto",
        "job": job or "(sin oferta)",
        "cv": cv_text or str(cv_raw) or "(sin currículum)",
    }


@router.post("/resources")
async def create_resource(body: ResourceBody):
    """Frontend o backend: guarda el paquete de entrevista y obtiene resource_id."""
    _purge()
    resource_id = secrets.token_urlsafe(12)
    _RESOURCES[resource_id] = {
        "cv": body.cv,
        "job": body.job,
        "offer_research": body.offer_research,
        "ats_match": body.ats_match,
        "candidate_name": body.candidate_name,
        "created_at": time.time(),
    }
    return {"resource_id": resource_id, "expires_in": _TTL_SECONDS}


@router.get("/context")
async def get_context(
    resource_id: str | None = Query(default=None),
    authorization: str | None = Header(default=None),
):
    """Contrato VoiceAI: VoiceAI llama aquí con Bearer + resource_id."""
    _check_bearer(authorization)
    _purge()
    if not resource_id or resource_id not in _RESOURCES:
        raise HTTPException(
            status_code=404,
            detail="resource_id desconocido o caducado. Crea uno con POST /voiceai/v1/resources",
        )
    return {
        "agent": "interviewer",
        "context": _context_from_resource(_RESOURCES[resource_id]),
        "actions_base_url": None,
    }


@router.post("/start-call")
async def start_call(
    body: StartCallBody,
    authorization: str | None = Header(default=None),
):
    """Proxy server-side a VoiceAI POST /api/v1/connect. Devuelve call_url."""
    voiceai_url = os.getenv("VOICEAI_API_URL", "").strip().rstrip("/")
    if not voiceai_url:
        raise HTTPException(
            status_code=503,
            detail="Define VOICEAI_API_URL (origen de VoiceAI, sin path)",
        )
    if body.resource_id not in _RESOURCES:
        raise HTTPException(status_code=404, detail="resource_id desconocido o caducado")

    access_token = (body.access_token or _expected_token()).strip()
    headers = {"Content-Type": "application/json"}
    app_key = os.getenv("VOICEAI_API_KEY", "").strip()
    if app_key:
        headers["Authorization"] = f"Bearer {app_key}"

    payload = {
        "connector": "cving",
        "access_token": access_token,
        "resource_id": body.resource_id,
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(
            f"{voiceai_url}/api/v1/connect",
            headers=headers,
            json=payload,
        )
    if response.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail=f"VoiceAI connect falló ({response.status_code}): {response.text[:400]}",
        )
    data = response.json()
    return {
        "session_id": data.get("session_id"),
        "call_url": data.get("call_url"),
        "agent": data.get("agent"),
    }
