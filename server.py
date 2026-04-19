from __future__ import annotations

import asyncio
import json
import logging
import queue
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from rare_agents.auth import authenticate_token, login_user, revoke_session_token
from rare_agents.intake_parser import parse_ehr_intake
from rare_agents.service import (
    DEPARTMENTS,
    OUTPUT_STYLES,
    create_auto_job,
    create_executor_job,
    create_managed_account,
    delete_managed_account,
    get_bootstrap_payload,
    get_auto_job,
    get_executor_job,
    get_session,
    list_account_summaries,
    load_settings,
    profile_from_payload,
    save_profile,
    save_settings,
    serialize_session,
    settings_from_payload,
    submit_case,
    submit_case_feedback,
    submit_turn_approval,
    subscribe_auto_job,
    test_provider_connection,
    unsubscribe_auto_job,
    update_managed_account,
    update_session_sidebar_visibility,
)


ROOT = Path(__file__).resolve().parent
FRONTEND_DIR = ROOT / "frontend"

app = FastAPI(title="RareMDT", version="2.0.0")
logger = logging.getLogger("raremdt.api")

app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")
app.mount("/vendor", StaticFiles(directory=FRONTEND_DIR / "vendor"), name="vendor")


def _bearer_token(request: Request) -> str:
    header = request.headers.get("Authorization", "")
    if header.startswith("Bearer "):
        return header[7:].strip()
    return ""


def require_user(request: Request) -> dict:
    account = authenticate_token(_bearer_token(request))
    if not account:
        raise HTTPException(status_code=401, detail="请先登录。")
    return account


def require_admin(request: Request) -> dict:
    account = require_user(request)
    if not account.get("is_admin"):
        raise HTTPException(status_code=403, detail="需要管理员权限。")
    return account


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/auth/login")
async def login(request: Request) -> dict:
    payload = await request.json()
    try:
        token, user = login_user(str(payload.get("username", "")), str(payload.get("password", "")))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"token": token, "user": user}


@app.post("/api/auth/logout")
def logout(request: Request) -> dict[str, bool]:
    token = _bearer_token(request)
    if token:
        revoke_session_token(token)
    return {"ok": True}


@app.get("/api/bootstrap")
def bootstrap(request: Request) -> dict:
    return get_bootstrap_payload(require_user(request))


@app.get("/api/sessions/{session_id}")
def session_detail(session_id: str, request: Request) -> dict:
    user = require_user(request)
    session = get_session(user["username"], session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    return {"session": serialize_session(session)}


@app.post("/api/intake/prefill")
async def intake_prefill(request: Request) -> dict:
    user = require_user(request)
    payload = await request.json()
    case_summary = str(payload.get("case_summary", "")).strip()
    if not case_summary:
        raise HTTPException(status_code=400, detail="请先输入病例摘要。")
    settings = load_settings(user["username"])
    prefill = parse_ehr_intake(case_summary, settings.default_department)
    return {"prefill": prefill.__dict__}


@app.put("/api/profile")
async def update_profile(request: Request) -> dict:
    user = require_user(request)
    payload = await request.json()
    profile = profile_from_payload(user["username"], payload)
    save_profile(user["username"], profile)
    return {"profile": profile.__dict__}


@app.put("/api/settings")
async def update_settings(request: Request) -> dict:
    user = require_user(request)
    payload = await request.json()
    settings = settings_from_payload(user["username"], payload)
    save_settings(user["username"], settings)
    return {"settings": settings.__dict__}


@app.post("/api/providers/test")
async def test_provider(request: Request) -> dict:
    require_user(request)
    payload = await request.json()
    try:
        return test_provider_connection(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.put("/api/sessions/sidebar-visibility")
async def update_session_visibility(request: Request) -> dict:
    user = require_user(request)
    payload = await request.json()
    try:
        sessions = update_session_sidebar_visibility(
            user["username"],
            show_in_sidebar=bool(payload.get("show_in_sidebar", True)),
            session_id=str(payload.get("session_id", "")).strip() or None,
            apply_to_all=bool(payload.get("apply_to_all", False)),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"sessions": [serialize_session(session, include_details=False) for session in sessions]}


@app.get("/api/admin/accounts")
def admin_accounts(request: Request) -> dict:
    require_admin(request)
    return {"accounts": list_account_summaries()}


@app.post("/api/admin/accounts")
async def admin_create_account(request: Request) -> dict:
    require_admin(request)
    payload = await request.json()
    try:
        account = create_managed_account(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"account": account, "accounts": list_account_summaries()}


@app.put("/api/admin/accounts/{username}")
async def admin_update_account(username: str, request: Request) -> dict:
    admin = require_admin(request)
    if username.strip().lower() == str(admin.get("username", "")).lower():
        raise HTTPException(status_code=400, detail="不能停用当前登录账户。")
    payload = await request.json()
    try:
        account = update_managed_account(username, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"account": account, "accounts": list_account_summaries()}


@app.delete("/api/admin/accounts/{username}")
def admin_delete_account(username: str, request: Request) -> dict:
    admin = require_admin(request)
    if username.strip().lower() == str(admin.get("username", "")).lower():
        raise HTTPException(status_code=400, detail="不能删除当前登录账户。")
    try:
        delete_managed_account(username)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"accounts": list_account_summaries()}


@app.post("/api/diagnose")
async def diagnose(request: Request) -> dict:
    user = require_user(request)
    payload = await request.json()
    try:
        return submit_case(user["username"], payload)
    except ValueError as exc:
        logger.exception("diagnose failed for user=%s detail=%s", user.get("username"), exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/executor-jobs")
async def create_executor_job_api(request: Request) -> dict:
    user = require_user(request)
    payload = await request.json()
    try:
        return {"job": create_executor_job(user["username"], payload)}
    except ValueError as exc:
        logger.exception("executor job create failed for user=%s detail=%s", user.get("username"), exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/executor-jobs/{job_id}")
def executor_job_detail(job_id: str, request: Request) -> dict:
    user = require_user(request)
    job = get_executor_job(user["username"], job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Executor job not found.")
    return {"job": job}


@app.post("/api/auto-jobs")
async def create_auto_job_api(request: Request) -> dict:
    user = require_user(request)
    payload = await request.json()
    try:
        return {"job": create_auto_job(user["username"], payload)}
    except ValueError as exc:
        logger.exception("auto job create failed for user=%s detail=%s", user.get("username"), exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/auto-jobs/{job_id}")
def auto_job_detail(job_id: str, request: Request) -> dict:
    user = require_user(request)
    job = get_auto_job(user["username"], job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Auto job not found.")
    return {"job": job}


@app.get("/api/auto-jobs/{job_id}/stream")
async def auto_job_stream(job_id: str, request: Request) -> StreamingResponse:
    user = require_user(request)
    snapshot, listener = subscribe_auto_job(user["username"], job_id)
    if snapshot is None or listener is None:
        raise HTTPException(status_code=404, detail="Auto job not found.")

    async def events():
        try:
            yield f"data: {json.dumps({'job': snapshot}, ensure_ascii=False)}\n\n"
            if snapshot.get("status") in {"completed", "failed"}:
                return
            while True:
                if await request.is_disconnected():
                    return
                try:
                    update = await asyncio.to_thread(listener.get, True, 15)
                except queue.Empty:
                    latest = get_auto_job(user["username"], job_id, include_details=False)
                    if latest is None:
                        missing = {
                            "job_id": job_id,
                            "status": "failed",
                            "stage": "failed",
                            "error_message": "Auto job not found.",
                        }
                        yield f"data: {json.dumps({'job': missing}, ensure_ascii=False)}\n\n"
                        return
                    if latest.get("status") in {"completed", "failed"}:
                        yield f"data: {json.dumps({'job': latest}, ensure_ascii=False)}\n\n"
                        return
                    yield ": keepalive\n\n"
                    continue
                yield f"data: {json.dumps({'job': update}, ensure_ascii=False)}\n\n"
                if update.get("status") in {"completed", "failed"}:
                    return
        finally:
            unsubscribe_auto_job(job_id, listener)

    return StreamingResponse(events(), media_type="text/event-stream")


@app.post("/api/sessions/{session_id}/approvals")
async def approve_session_turn(session_id: str, request: Request) -> dict:
    user = require_user(request)
    payload = await request.json()
    try:
        return submit_turn_approval(user["username"], session_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/sessions/{session_id}/feedback")
async def submit_session_feedback(session_id: str, request: Request) -> dict:
    user = require_user(request)
    payload = await request.json()
    try:
        return submit_case_feedback(user["username"], session_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/{full_path:path}", response_class=HTMLResponse)
def spa(full_path: str) -> FileResponse:
    index_path = FRONTEND_DIR / "index.html"
    return FileResponse(index_path)
