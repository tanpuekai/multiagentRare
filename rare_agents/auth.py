from __future__ import annotations

import hashlib
import secrets
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from rare_agents.storage import load_json, save_json


ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
USERS_DIR = DATA_DIR / "users"
ACCOUNTS_PATH = DATA_DIR / "accounts.json"
AUTH_SESSIONS_PATH = DATA_DIR / "auth_sessions.json"

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "Hkuszh888@"


def now_timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def normalize_username(value: str) -> str:
    cleaned = "".join(char for char in value.strip() if char.isalnum() or char in {"_", "-", "."})
    return cleaned.lower()


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    actual_salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), actual_salt.encode("utf-8"), 200_000).hex()
    return digest, actual_salt


def verify_password(password: str, password_hash: str, salt: str) -> bool:
    candidate, _ = hash_password(password, salt)
    return secrets.compare_digest(candidate, password_hash)


def default_admin_account() -> dict[str, Any]:
    password_hash, salt = hash_password(ADMIN_PASSWORD)
    return {
        "username": ADMIN_USERNAME,
        "password_hash": password_hash,
        "salt": salt,
        "is_admin": True,
        "disabled": False,
        "created_at": now_timestamp(),
    }


def ensure_auth_storage() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    USERS_DIR.mkdir(parents=True, exist_ok=True)

    accounts = load_json(ACCOUNTS_PATH, [])
    if not accounts:
        accounts = [default_admin_account()]
        save_json(ACCOUNTS_PATH, accounts)
    elif not any(item.get("username") == ADMIN_USERNAME for item in accounts):
        accounts.append(default_admin_account())
        save_json(ACCOUNTS_PATH, accounts)

    if not AUTH_SESSIONS_PATH.exists():
        save_json(AUTH_SESSIONS_PATH, [])


def user_data_dir(username: str) -> Path:
    return USERS_DIR / normalize_username(username)


def load_accounts() -> list[dict[str, Any]]:
    ensure_auth_storage()
    return load_json(ACCOUNTS_PATH, [])


def save_accounts(accounts: list[dict[str, Any]]) -> None:
    save_json(ACCOUNTS_PATH, accounts)


def load_auth_sessions() -> list[dict[str, Any]]:
    ensure_auth_storage()
    return load_json(AUTH_SESSIONS_PATH, [])


def save_auth_sessions(sessions: list[dict[str, Any]]) -> None:
    save_json(AUTH_SESSIONS_PATH, sessions)


def find_account(username: str) -> dict[str, Any] | None:
    normalized = normalize_username(username)
    for account in load_accounts():
        if account.get("username") == normalized:
            return account
    return None


def serialize_auth_user(account: dict[str, Any]) -> dict[str, Any]:
    return {
        "username": account["username"],
        "is_admin": bool(account.get("is_admin", False)),
        "disabled": bool(account.get("disabled", False)),
        "created_at": account.get("created_at", ""),
    }


def revoke_sessions_for_username(username: str) -> None:
    normalized = normalize_username(username)
    sessions = [item for item in load_auth_sessions() if item.get("username") != normalized]
    save_auth_sessions(sessions)


def revoke_session_token(token: str) -> None:
    sessions = [item for item in load_auth_sessions() if item.get("token") != token]
    save_auth_sessions(sessions)


def create_login_session(username: str) -> str:
    normalized = normalize_username(username)
    token = secrets.token_urlsafe(32)
    sessions = load_auth_sessions()
    sessions.append({"token": token, "username": normalized, "created_at": now_timestamp()})
    save_auth_sessions(sessions)
    return token


def authenticate_token(token: str) -> dict[str, Any] | None:
    if not token:
        return None
    normalized = token.strip()
    for session in load_auth_sessions():
        if session.get("token") == normalized:
            account = find_account(session.get("username", ""))
            if not account or account.get("disabled"):
                return None
            return account
    return None


def login_user(username: str, password: str) -> tuple[str, dict[str, Any]]:
    normalized = normalize_username(username)
    if not normalized or not password:
        raise ValueError("请输入用户名和密码。")
    account = find_account(normalized)
    if not account or not verify_password(password, account["password_hash"], account["salt"]):
        raise ValueError("用户名或密码错误。")
    if account.get("disabled"):
        raise ValueError("该账户已被停用。")
    token = create_login_session(normalized)
    return token, serialize_auth_user(account)


def count_admin_accounts(accounts: list[dict[str, Any]] | None = None) -> int:
    source = accounts if accounts is not None else load_accounts()
    return sum(1 for account in source if account.get("is_admin"))


def create_account(username: str, password: str, *, is_admin: bool = False) -> dict[str, Any]:
    normalized = normalize_username(username)
    if len(normalized) < 3:
        raise ValueError("用户名至少需要 3 个字符。")
    if len(password) < 8:
        raise ValueError("密码至少需要 8 个字符。")
    accounts = load_accounts()
    if any(item.get("username") == normalized for item in accounts):
        raise ValueError("该用户名已存在。")
    password_hash, salt = hash_password(password)
    account = {
        "username": normalized,
        "password_hash": password_hash,
        "salt": salt,
        "is_admin": bool(is_admin),
        "disabled": False,
        "created_at": now_timestamp(),
    }
    accounts.append(account)
    save_accounts(accounts)
    return account


def set_account_disabled(username: str, disabled: bool) -> dict[str, Any]:
    normalized = normalize_username(username)
    accounts = load_accounts()
    for account in accounts:
        if account.get("username") == normalized:
            if account.get("is_admin") and disabled and count_admin_accounts(accounts) <= 1:
                raise ValueError("至少需要保留一个管理员账户。")
            account["disabled"] = bool(disabled)
            save_accounts(accounts)
            if disabled:
                revoke_sessions_for_username(normalized)
            return account
    raise ValueError("未找到对应账户。")


def delete_account(username: str) -> None:
    normalized = normalize_username(username)
    accounts = load_accounts()
    account = next((item for item in accounts if item.get("username") == normalized), None)
    if not account:
        raise ValueError("未找到对应账户。")
    if account.get("is_admin") and count_admin_accounts(accounts) <= 1:
        raise ValueError("至少需要保留一个管理员账户。")
    remaining = [item for item in accounts if item.get("username") != normalized]
    save_accounts(remaining)
    revoke_sessions_for_username(normalized)
    shutil.rmtree(user_data_dir(normalized), ignore_errors=True)
