from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request
from uuid import uuid4

from rare_agents.auth import (
    create_account as create_auth_account,
    delete_account as delete_auth_account,
    ensure_auth_storage,
    load_accounts,
    serialize_auth_user,
    set_account_disabled as set_auth_account_disabled,
    user_data_dir,
)
from rare_agents.engine import run_multiagent_case
from rare_agents.intake_parser import parse_ehr_intake
from rare_agents.models import (
    APIProviderConfig,
    AgentRoleConfig,
    AppProfile,
    CaseSessionRecord,
    CaseSubmission,
    DepartmentOption,
    EngineResult,
    OrchestrationMode,
    QueryHistoryItem,
    SystemSettings,
    default_profile,
    default_settings,
)
from rare_agents.storage import load_json, save_json


ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
LEGACY_PROFILE_PATH = DATA_DIR / "profile.json"
LEGACY_SETTINGS_PATH = DATA_DIR / "settings.json"
LEGACY_HISTORY_PATH = DATA_DIR / "history.json"
LEGACY_SESSIONS_PATH = DATA_DIR / "sessions.json"

SETTINGS_SECTIONS = ["医生档案", "系统设置", "历史记录", "账户管理"]
DEPARTMENTS = [item.value for item in DepartmentOption]
TOPOLOGIES = [mode.value for mode in OrchestrationMode]
OUTPUT_STYLES = ["Diagnostic", "Surgical / Treatment Plan"]
URGENCY_OPTIONS = ["Routine", "Priority", "Emergency"]
SEX_OPTIONS = ["Unknown", "Female", "Male", "Other"]
INSURANCE_OPTIONS = [
    "Resident insurance",
    "Employee insurance",
    "Self-pay / uninsured",
    "Commercial",
]
BASE_SETTINGS_MENU = [
    {"label": "账户", "section": "医生档案", "icon": "account"},
    {"label": "API / 智能体", "section": "系统设置", "icon": "hub"},
    {"label": "历史记录", "section": "历史记录", "icon": "history"},
]
ADMIN_SETTINGS_MENU_ITEM = {"label": "账户管理", "section": "账户管理", "icon": "users"}

DEPT_LABELS = {
    DepartmentOption.ORTHOPEDICS.value: "骨科",
    DepartmentOption.NEUROLOGY.value: "神经内科",
    DepartmentOption.PEDIATRICS.value: "儿科",
    DepartmentOption.ICU.value: "重症 ICU",
    DepartmentOption.EMERGENCY.value: "急诊",
    DepartmentOption.PULMONARY.value: "呼吸科",
    DepartmentOption.GENETICS.value: "医学遗传",
    DepartmentOption.MULTIDISCIPLINARY.value: "多学科 MDT",
}
TOPOLOGY_LABELS = {
    OrchestrationMode.SYMMETRIC.value: "对称",
    OrchestrationMode.ASYMMETRIC.value: "非对称",
}
OUTPUT_LABELS = {
    "Diagnostic": "诊断评估",
    "Surgical / Treatment Plan": "手术 / 治疗方案",
}
URGENCY_LABELS = {
    "Routine": "常规",
    "Priority": "优先",
    "Emergency": "紧急",
}
SEX_LABELS = {
    "Unknown": "未知",
    "Female": "女",
    "Male": "男",
    "Other": "其他",
}
INSURANCE_LABELS = {
    "Resident insurance": "居民医保",
    "Employee insurance": "职工医保",
    "Self-pay / uninsured": "自费",
    "Commercial": "商业保险",
}
PROVIDER_LABELS = {
    "DeepSeek": "DeepSeek",
    "GLM / BigModel": "GLM / BigModel",
    "Kimi": "Kimi",
    "OpenAI Compatible": "OpenAI 兼容",
    "Custom / Hospital Gateway": "自定义 / 医院网关",
}
ROLE_LABELS = {
    "Orchestrator": "编排协调",
    "Planner": "规划分析",
    "Generator": "生成起草",
    "Fact Checker": "事实核查",
    "Guideline Retriever": "指南检索",
    "Web Search": "网络检索",
    "Imaging Reader": "影像解读",
    "Cost Estimator": "费用估算",
}
PROVIDER_PRESETS = {
    "DeepSeek": "https://api.deepseek.com",
    "GLM / BigModel": "https://open.bigmodel.cn/api/paas/v4",
    "Kimi": "https://api.moonshot.cn/v1",
    "OpenAI Compatible": "",
    "Custom / Hospital Gateway": "",
}
ROLE_TEMPLATES = list(ROLE_LABELS.keys())

PROFILE_MIGRATIONS = {
    "Dr. Demo": "演示医生",
    "Consultant": "主任医师",
    "HKU-SZH": "港大医院（HKU-SZH）",
    "Rare disease MDT": "罕见病 MDT",
    "Shenzhen, China": "深圳，中国",
    "Pediatric and adult rare disease referral population": "儿科与成人罕见病转诊人群",
}
ROLE_SPEC_MIGRATIONS = {
    "Coordinate specialist agents, drive convergence, remove contradictions, and produce a final answer fit for clinicians.": "负责协调各专科智能体、推动结论收敛、消除冲突，并生成适合临床阅读的最终结论。",
    "Drive structured case decomposition, round-based synthesis, and conflict resolution across the agent team.": "负责结构化拆解病例、统筹轮次级综合分析，并在智能体之间解决冲突。",
    "Map the differential diagnosis or treatment pathway, decide what evidence is needed next, and prioritize rare disease branches.": "规划鉴别诊断或治疗路径，明确下一步证据需求，并优先排序罕见病分支。",
    "Generate clinician-facing draft answers with clear sections, professional wording, and department-specific detail.": "起草面向临床医生的结构化回答，要求表达专业、分区清晰，并体现专科细节。",
    "Check for inconsistencies, unsupported claims, unsafe recommendations, and missing coding or cost disclosures.": "核查前后不一致、证据不足、不安全建议，以及编码或费用披露缺失等问题。",
    "Anchor statements in Chinese and international rare disease, specialty, and perioperative guideline references.": "为结论补充中国与国际罕见病、专科及围手术期指南或共识依据。",
    "Reserved for real deployment to retrieve recent consensus statements, local hospital pathways, and payer rules.": "用于正式部署时检索最新共识、院内路径与医保支付规则。",
}


def migrate_profile(data: dict[str, Any]) -> dict[str, Any]:
    migrated = dict(data)
    for key in ["user_name", "title", "hospital_name", "specialty_focus", "locale", "patient_population"]:
        value = migrated.get(key)
        if value in PROFILE_MIGRATIONS:
            migrated[key] = PROFILE_MIGRATIONS[value]
    return migrated


def migrate_roles(roles: list[AgentRoleConfig]) -> list[AgentRoleConfig]:
    return [
        AgentRoleConfig(
            role_name=role.role_name,
            role_spec=ROLE_SPEC_MIGRATIONS.get(role.role_spec, role.role_spec),
            provider_name=role.provider_name,
            agent_count=role.agent_count,
        )
        for role in roles
    ]


def _user_paths(username: str) -> dict[str, Path]:
    root = user_data_dir(username)
    return {
        "root": root,
        "profile": root / "profile.json",
        "settings": root / "settings.json",
        "history": root / "history.json",
        "sessions": root / "sessions.json",
    }


def ensure_storage(username: str) -> None:
    ensure_auth_storage()
    paths = _user_paths(username)
    profile_seed = asdict(default_profile())
    profile_seed["user_name"] = username
    defaults = {
        "profile": profile_seed,
        "settings": asdict(default_settings()),
        "history": [],
        "sessions": [],
    }
    legacy_paths = {
        "profile": LEGACY_PROFILE_PATH,
        "settings": LEGACY_SETTINGS_PATH,
        "history": LEGACY_HISTORY_PATH,
        "sessions": LEGACY_SESSIONS_PATH,
    }

    for key in ["profile", "settings", "history", "sessions"]:
        target = paths[key]
        if target.exists():
            continue
        if username == "admin" and legacy_paths[key].exists():
            payload = load_json(legacy_paths[key], defaults[key])
        else:
            payload = defaults[key]
        save_json(target, payload)


def load_profile(username: str) -> AppProfile:
    ensure_storage(username)
    data = load_json(_user_paths(username)["profile"], asdict(default_profile()))
    return AppProfile(**migrate_profile(data))


def load_settings(username: str) -> SystemSettings:
    ensure_storage(username)
    data = load_json(_user_paths(username)["settings"], asdict(default_settings()))
    providers = [APIProviderConfig(**provider) for provider in data.get("api_providers", [])]
    roles = [AgentRoleConfig(**role) for role in data.get("agent_roles", [])]
    return SystemSettings(
        orchestration_mode=data.get("orchestration_mode", OrchestrationMode.ASYMMETRIC.value),
        default_department=data.get("default_department", DepartmentOption.PEDIATRICS.value),
        consensus_threshold=float(data.get("consensus_threshold", 0.82)),
        max_rounds=int(data.get("max_rounds", 3)),
        show_diagnostics=bool(data.get("show_diagnostics", True)),
        api_providers=providers,
        agent_roles=migrate_roles(roles),
    )


def load_history(username: str) -> list[QueryHistoryItem]:
    ensure_storage(username)
    return [QueryHistoryItem(**item) for item in load_json(_user_paths(username)["history"], [])]


def _load_submission(data: dict[str, Any] | None) -> CaseSubmission | None:
    if not data:
        return None
    return CaseSubmission(**data)


def _load_result(data: dict[str, Any] | None) -> EngineResult | None:
    if not data:
        return None
    return EngineResult(**data)


def load_sessions(username: str) -> list[CaseSessionRecord]:
    ensure_storage(username)
    raw = load_json(_user_paths(username)["sessions"], [])
    if raw:
        return [
            CaseSessionRecord(
                session_id=item["session_id"],
                timestamp=item["timestamp"],
                title=item["title"],
                department=item["department"],
                output_style=item["output_style"],
                summary=item["summary"],
                consensus_score=float(item["consensus_score"]),
                show_in_sidebar=bool(item.get("show_in_sidebar", True)),
                submission=_load_submission(item.get("submission")),
                result=_load_result(item.get("result")),
            )
            for item in raw
        ]

    history = load_history(username)
    return [
        CaseSessionRecord.from_history_item(f"history-{index}", item)
        for index, item in enumerate(history, start=1)
    ]


def save_profile(username: str, profile: AppProfile) -> None:
    save_json(_user_paths(username)["profile"], asdict(profile))


def save_settings(username: str, settings: SystemSettings) -> None:
    save_json(_user_paths(username)["settings"], asdict(settings))


def save_history(username: str, history: list[QueryHistoryItem]) -> None:
    save_json(_user_paths(username)["history"], [asdict(item) for item in history])


def save_sessions(username: str, sessions: list[CaseSessionRecord]) -> None:
    save_json(_user_paths(username)["sessions"], [asdict(item) for item in sessions])


def profile_from_payload(username: str, payload: dict[str, Any]) -> AppProfile:
    current = load_profile(username)
    return AppProfile(
        user_name=str(payload.get("user_name", current.user_name)).strip() or current.user_name,
        title=str(payload.get("title", current.title)).strip() or current.title,
        hospital_name=str(payload.get("hospital_name", current.hospital_name)).strip() or current.hospital_name,
        department=str(payload.get("department", current.department)).strip() or current.department,
        specialty_focus=str(payload.get("specialty_focus", current.specialty_focus)).strip() or current.specialty_focus,
        locale=str(payload.get("locale", current.locale)).strip() or current.locale,
        patient_population=str(payload.get("patient_population", current.patient_population)).strip() or current.patient_population,
        first_run_complete=bool(payload.get("first_run_complete", current.first_run_complete)),
    )


def settings_from_payload(username: str, payload: dict[str, Any]) -> SystemSettings:
    current = load_settings(username)
    providers = [
        APIProviderConfig(
            provider_name=str(item.get("provider_name", "DeepSeek")),
            model_name=str(item.get("model_name", "deepseek-chat")),
            endpoint=str(item.get("endpoint", "")),
            api_key=str(item.get("api_key", "")),
            agents_for_api=max(int(item.get("agents_for_api", 1)), 1),
            enabled=bool(item.get("enabled", True)),
        )
        for item in payload.get("api_providers", [asdict(provider) for provider in current.api_providers])
    ]
    roles = [
        AgentRoleConfig(
            role_name=str(item.get("role_name", "Orchestrator")),
            role_spec=str(item.get("role_spec", "")),
            provider_name=str(item.get("provider_name", "DeepSeek")),
            agent_count=max(int(item.get("agent_count", 1)), 1),
        )
        for item in payload.get("agent_roles", [asdict(role) for role in current.agent_roles])
    ]
    return SystemSettings(
        orchestration_mode=str(payload.get("orchestration_mode", current.orchestration_mode)),
        default_department=str(payload.get("default_department", current.default_department)),
        consensus_threshold=float(payload.get("consensus_threshold", current.consensus_threshold)),
        max_rounds=max(int(payload.get("max_rounds", current.max_rounds)), 1),
        show_diagnostics=bool(payload.get("show_diagnostics", current.show_diagnostics)),
        api_providers=providers,
        agent_roles=roles,
    )


def provider_from_payload(payload: dict[str, Any]) -> APIProviderConfig:
    return APIProviderConfig(
        provider_name=str(payload.get("provider_name", "OpenAI Compatible")).strip() or "OpenAI Compatible",
        model_name=str(payload.get("model_name", "")).strip(),
        endpoint=str(payload.get("endpoint", "")).strip(),
        api_key=str(payload.get("api_key", "")).strip(),
        agents_for_api=max(int(payload.get("agents_for_api", 1)), 1),
        enabled=bool(payload.get("enabled", True)),
    )


def _select_value(payload: dict[str, Any], key: str, fallback: str) -> str:
    value = payload.get(key)
    if value is None:
        return fallback
    if isinstance(value, str):
        return value.strip() or fallback
    return str(value)


def _trim_message(value: str, limit: int = 180) -> str:
    clean = " ".join(value.split())
    if len(clean) <= limit:
        return clean
    return f"{clean[: limit - 1].rstrip()}..."


def _normalize_provider_endpoint(endpoint: str) -> str:
    raw = endpoint.strip()
    if not raw:
        return ""
    parsed = urllib_parse.urlsplit(raw if "://" in raw else f"https://{raw}")
    path = parsed.path.rstrip("/")
    for suffix in ("/chat/completions", "/responses", "/completions", "/models"):
        if path.endswith(suffix):
            path = path[: -len(suffix)]
            break
    return urllib_parse.urlunsplit((parsed.scheme or "https", parsed.netloc, path, "", ""))


def _build_probe_targets(provider: APIProviderConfig) -> list[tuple[str, str, bytes | None]]:
    base = _normalize_provider_endpoint(provider.endpoint).rstrip("/")
    targets: list[tuple[str, str, bytes | None]] = [("GET", f"{base}/models", None)]
    if provider.model_name:
        body = json.dumps(
            {
                "model": provider.model_name,
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 1,
                "temperature": 0,
            }
        ).encode("utf-8")
        targets.append(("POST", f"{base}/chat/completions", body))
    return targets


def _request_provider_probe(url: str, method: str, api_key: str, body: bytes | None) -> tuple[int, str]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "User-Agent": "RareMDT/2.0",
    }
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = urllib_request.Request(url, data=body, headers=headers, method=method)
    with urllib_request.urlopen(request, timeout=8) as response:
        payload = response.read().decode("utf-8", errors="replace")
        return int(getattr(response, "status", 200)), payload


def _extract_error_message(raw: str, fallback: str) -> str:
    if not raw:
        return fallback
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return _trim_message(raw)

    if isinstance(parsed, dict):
        detail = parsed.get("error") or parsed.get("detail") or parsed.get("message")
        if isinstance(detail, dict):
            return _trim_message(str(detail.get("message") or detail.get("code") or fallback))
        if detail:
            return _trim_message(str(detail))
    return fallback


def test_provider_connection(payload: dict[str, Any]) -> dict[str, Any]:
    provider_payload = payload.get("provider") if isinstance(payload.get("provider"), dict) else payload
    provider = provider_from_payload(provider_payload)
    provider_name = provider.provider_name or "当前接口"

    if not provider.endpoint:
        raise ValueError("请先填写接口地址。")
    if not provider.api_key:
        raise ValueError("请先填写 API Key。")

    last_message = "无法连接到接口。"
    for method, url, body in _build_probe_targets(provider):
        try:
            _request_provider_probe(url, method, provider.api_key, body)
            suffix = "接口可用。"
            if method == "POST":
                suffix = "接口可用，模型调用测试通过。"
            return {"message": f"{provider_name} {suffix}", "provider_name": provider_name}
        except urllib_error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            detail = _extract_error_message(raw, f"HTTP {exc.code}")
            if exc.code in {404, 405} and method == "GET":
                last_message = f"{provider_name} 未提供 models 探测接口，已尝试继续深度探测。"
                continue
            if exc.code in {401, 403}:
                raise ValueError(f"{provider_name} 鉴权失败，请检查 API Key。") from exc
            if exc.code == 429:
                return {"message": f"{provider_name} 接口可达，但当前触发限流。", "provider_name": provider_name}
            raise ValueError(f"{provider_name} 测试失败：{detail}") from exc
        except urllib_error.URLError as exc:
            reason = getattr(exc, "reason", exc)
            raise ValueError(f"{provider_name} 无法连接：{_trim_message(str(reason))}") from exc

    raise ValueError(last_message)


def submit_case(username: str, payload: dict[str, Any]) -> dict[str, Any]:
    settings = load_settings(username)
    profile = load_profile(username)
    main_text = str(payload.get("case_summary", "")).strip()
    if not main_text:
        raise ValueError("请先输入病例摘要。")

    prefill = parse_ehr_intake(main_text, settings.default_department)

    submission = CaseSubmission(
        department=_select_value(payload, "department", prefill.department or settings.default_department),
        output_style=_select_value(payload, "output_style", prefill.output_style or OUTPUT_STYLES[0]),
        urgency=_select_value(payload, "urgency", prefill.urgency or URGENCY_OPTIONS[0]),
        chief_complaint=_select_value(payload, "chief_complaint", prefill.chief_complaint or ""),
        case_summary=main_text,
        patient_age=_select_value(payload, "patient_age", prefill.patient_age or ""),
        patient_sex=_select_value(payload, "patient_sex", prefill.patient_sex or SEX_OPTIONS[0]),
        insurance_type=_select_value(payload, "insurance_type", prefill.insurance_type or INSURANCE_OPTIONS[0]),
        uploaded_images=[str(item) for item in payload.get("uploaded_images", [])],
        uploaded_docs=[str(item) for item in payload.get("uploaded_docs", [])],
        show_process=bool(payload.get("show_process", settings.show_diagnostics)),
    )

    result = run_multiagent_case(submission=submission, profile=profile, settings=settings)
    session = CaseSessionRecord.from_result(uuid4().hex[:12], submission, result)
    history_item = QueryHistoryItem(
        timestamp=session.timestamp,
        title=session.title,
        department=session.department,
        output_style=session.output_style,
        summary=session.summary,
        consensus_score=session.consensus_score,
    )

    sessions = [session] + load_sessions(username)
    history = [history_item] + load_history(username)
    save_sessions(username, sessions)
    save_history(username, history)

    return {
        "session": serialize_session(session),
        "result": asdict(result),
        "submission": asdict(submission),
        "prefill": asdict(prefill),
        "history": [serialize_history_item(item, f"history-{index}") for index, item in enumerate(history, start=1)],
        "sessions": [serialize_session(item, include_details=False) for item in sessions],
    }


def get_session(username: str, session_id: str) -> CaseSessionRecord | None:
    for session in load_sessions(username):
        if session.session_id == session_id:
            return session
    return None


def serialize_history_item(item: QueryHistoryItem, session_id: str) -> dict[str, Any]:
    return {
        "session_id": session_id,
        "timestamp": item.timestamp,
        "title": item.title,
        "department": item.department,
        "output_style": item.output_style,
        "summary": item.summary,
        "consensus_score": item.consensus_score,
    }


def serialize_session(session: CaseSessionRecord, *, include_details: bool = True) -> dict[str, Any]:
    payload = {
        "session_id": session.session_id,
        "timestamp": session.timestamp,
        "title": session.title,
        "department": session.department,
        "output_style": session.output_style,
        "summary": session.summary,
        "consensus_score": session.consensus_score,
        "show_in_sidebar": session.show_in_sidebar,
    }
    if include_details:
        payload["submission"] = asdict(session.submission) if session.submission else None
        payload["result"] = asdict(session.result) if session.result else None
    return payload


def update_session_sidebar_visibility(username: str, *, show_in_sidebar: bool, session_id: str | None = None, apply_to_all: bool = False) -> list[CaseSessionRecord]:
    sessions = load_sessions(username)
    changed = False

    if apply_to_all:
        for session in sessions:
            if session.show_in_sidebar != show_in_sidebar:
                session.show_in_sidebar = show_in_sidebar
                changed = True
    else:
        if not session_id:
            raise ValueError("缺少会诊记录标识。")
        for session in sessions:
            if session.session_id == session_id:
                if session.show_in_sidebar != show_in_sidebar:
                    session.show_in_sidebar = show_in_sidebar
                    changed = True
                break
        else:
            raise ValueError("未找到对应会诊记录。")

    if changed:
        save_sessions(username, sessions)
    return sessions


def _recent_query_summaries(username: str, limit: int = 3) -> list[dict[str, Any]]:
    return [
        {
            "session_id": session.session_id,
            "title": session.title,
            "timestamp": session.timestamp,
            "summary": session.summary,
        }
        for session in load_sessions(username)[:limit]
    ]


def summarize_account(account: dict[str, Any]) -> dict[str, Any]:
    username = account["username"]
    ensure_storage(username)
    profile = load_profile(username)
    sessions = load_sessions(username)
    return {
        **serialize_auth_user(account),
        "display_name": profile.user_name,
        "title": profile.title,
        "hospital_name": profile.hospital_name,
        "department": profile.department,
        "query_count": len(sessions),
        "last_query_at": sessions[0].timestamp if sessions else "",
        "recent_queries": _recent_query_summaries(username),
    }


def list_account_summaries() -> list[dict[str, Any]]:
    accounts = sorted(load_accounts(), key=lambda item: (not bool(item.get("is_admin")), item.get("username", "")))
    return [summarize_account(account) for account in accounts]


def create_managed_account(payload: dict[str, Any]) -> dict[str, Any]:
    account = create_auth_account(
        str(payload.get("username", "")),
        str(payload.get("password", "")),
        is_admin=bool(payload.get("is_admin", False)),
    )
    ensure_storage(account["username"])
    profile = load_profile(account["username"])
    if profile.user_name == "演示医生":
        profile.user_name = account["username"]
        save_profile(account["username"], profile)
    return summarize_account(account)


def update_managed_account(username: str, payload: dict[str, Any]) -> dict[str, Any]:
    account = set_auth_account_disabled(username, bool(payload.get("disabled", False)))
    return summarize_account(account)


def delete_managed_account(username: str) -> None:
    delete_auth_account(username)


def get_bootstrap_payload(current_user: dict[str, Any]) -> dict[str, Any]:
    username = current_user["username"]
    profile = load_profile(username)
    settings = load_settings(username)
    history = load_history(username)
    sessions = load_sessions(username)
    settings_menu = list(BASE_SETTINGS_MENU)
    if current_user.get("is_admin"):
        settings_menu.append(ADMIN_SETTINGS_MENU_ITEM)
    return {
        "current_user": serialize_auth_user(current_user),
        "profile": asdict(profile),
        "settings": asdict(settings),
        "history": [serialize_history_item(item, f"history-{index}") for index, item in enumerate(history, start=1)],
        "sessions": [serialize_session(session, include_details=False) for session in sessions],
        "admin_accounts": list_account_summaries() if current_user.get("is_admin") else [],
        "meta": {
            "departments": DEPARTMENTS,
            "topologies": TOPOLOGIES,
            "output_styles": OUTPUT_STYLES,
            "urgency_options": URGENCY_OPTIONS,
            "sex_options": SEX_OPTIONS,
            "insurance_options": INSURANCE_OPTIONS,
            "settings_sections": SETTINGS_SECTIONS,
            "settings_menu": settings_menu,
            "provider_presets": PROVIDER_PRESETS,
            "role_templates": ROLE_TEMPLATES,
            "labels": {
                "department": DEPT_LABELS,
                "topology": TOPOLOGY_LABELS,
                "output": OUTPUT_LABELS,
                "urgency": URGENCY_LABELS,
                "sex": SEX_LABELS,
                "insurance": INSURANCE_LABELS,
                "provider": PROVIDER_LABELS,
                "role": ROLE_LABELS,
            },
        },
    }
