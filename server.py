from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from rare_agents.intake_parser import parse_ehr_intake
from rare_agents.service import (
    DEPARTMENTS,
    OUTPUT_STYLES,
    get_bootstrap_payload,
    get_session,
    load_settings,
    profile_from_payload,
    save_profile,
    save_settings,
    serialize_session,
    settings_from_payload,
    submit_case,
    test_provider_connection,
)


ROOT = Path(__file__).resolve().parent
FRONTEND_DIR = ROOT / "frontend"

app = FastAPI(title="RareMDT", version="2.0.0")

app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")
app.mount("/vendor", StaticFiles(directory=FRONTEND_DIR / "vendor"), name="vendor")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/bootstrap")
def bootstrap() -> dict:
    return get_bootstrap_payload()


@app.get("/api/sessions/{session_id}")
def session_detail(session_id: str) -> dict:
    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    return {"session": serialize_session(session)}


@app.post("/api/intake/prefill")
async def intake_prefill(request: Request) -> dict:
    payload = await request.json()
    case_summary = str(payload.get("case_summary", "")).strip()
    if not case_summary:
        raise HTTPException(status_code=400, detail="请先输入病例摘要。")
    settings = load_settings()
    prefill = parse_ehr_intake(case_summary, settings.default_department)
    return {"prefill": prefill.__dict__}


@app.put("/api/profile")
async def update_profile(request: Request) -> dict:
    payload = await request.json()
    profile = profile_from_payload(payload)
    save_profile(profile)
    return {"profile": profile.__dict__}


@app.put("/api/settings")
async def update_settings(request: Request) -> dict:
    payload = await request.json()
    settings = settings_from_payload(payload)
    save_settings(settings)
    return {"settings": settings.__dict__}


@app.post("/api/providers/test")
async def test_provider(request: Request) -> dict:
    payload = await request.json()
    try:
        return test_provider_connection(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/diagnose")
async def diagnose(request: Request) -> dict:
    payload = await request.json()
    try:
        return submit_case(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/{full_path:path}", response_class=HTMLResponse)
def spa(full_path: str) -> FileResponse:
    index_path = FRONTEND_DIR / "index.html"
    return FileResponse(index_path)
