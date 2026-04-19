from __future__ import annotations

import json
import queue
from base64 import b64encode
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime
from io import BytesIO
from pathlib import Path
import re
import threading
import time
from typing import Any
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request
from uuid import NAMESPACE_URL, uuid4, uuid5

from PIL import Image, ImageDraw

from rare_agents.auth import (
    create_account as create_auth_account,
    delete_account as delete_auth_account,
    ensure_auth_storage,
    load_accounts,
    serialize_auth_user,
    set_account_disabled as set_auth_account_disabled,
    user_data_dir,
)
from rare_agents.engine import run_multiagent_case, run_single_model_case
from rare_agents.intake_parser import parse_ehr_intake
from rare_agents.models import (
    APIProviderConfig,
    AgentRoleConfig,
    AppProfile,
    CaseSessionRecord,
    CaseFeedback,
    CaseSubmission,
    DepartmentOption,
    DoctorApproval,
    EngineResult,
    EvidenceFeedback,
    OrchestrationMode,
    QueryHistoryItem,
    SessionTurn,
    SystemSettings,
    default_profile,
    default_settings,
)
from rare_agents.executor import is_executor_invocation, run_executor_case, strip_executor_mention
from rare_agents.planner import is_planner_invocation, run_planner_case, strip_planner_mention
from rare_agents.decider import is_decider_invocation, run_decider_case, strip_decider_mention
from rare_agents.report_generator import is_report_invocation, run_report_case, strip_report_mention
from rare_agents.storage import load_json, save_json


ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
LEGACY_PROFILE_PATH = DATA_DIR / "profile.json"
LEGACY_SETTINGS_PATH = DATA_DIR / "settings.json"
LEGACY_HISTORY_PATH = DATA_DIR / "history.json"
LEGACY_SESSIONS_PATH = DATA_DIR / "sessions.json"
VISION_TEST_IMAGE_DATA_URL = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAQAAAAEACAIAAADTED8xAAAH+klEQVR4nO3dP2gTbxzH8adtlIIOot0sVLSDLg7BIEhDChVaULGCil2Ni3/q6GBvECsIooUuDjqoOLgpIjUIYgVF0A6KonYQoUPBQV2qiI16DgcltGnSJPfk7p7P+zX1Z5PLE/m+756r/bUtvu8bQFVr1AsAokQAkEYAkEYAkEYAkEYAkEYAkEYAkEYAkEYAkEYAkEYAkEYAkEYAkEYAkEYAkEYAkEYAkEYAkEYAkEYAkEYAkEYAkEYAkEYAkEYAkEYAkEYAkEYAkEYAkEYAkEYAkEYAkEYAkEYAkEYAkEYAkEYAkEYAkEYAkEYAkEYAkEYAkEYAkEYAkJaycdBsNmvjsMCzZ8/C/UvgCgBpBABpBABpVu4BrG7aoCZr85aSKwCkEQCkEQCkEQCkEQCkEQCkEQCkWf93gAjdvn37xo0ba9euXbNmzeXLlzdu3Dg5OXnr1q2bN28aY6anp0+fPl0oFDZt2pROp33f//Hjx4ULF3bt2mWMmZiYuHbtmjHm5cuXO3fuNMYcO3bsxIkT6XQ6OPjAwMDx48ffvn07OjpaLBZTqdT4+PibN2+WPmvfvn1R/01geb4FPSX8iExOTg4ODv769cv3/cePHx84cCD486GhoRcvXvi+f/DgwampKd/3N2/eHHzqw4cP2Wx20XEWPrvo40Aul5udnfV9/8GDB/l8vsIjEc9xcvYKcPXq1ZGRkfb2dmNMX1/fxMREsVhctWrV+fPnh4eHT5482dnZuWPHjtKnbN269cuXLzW9ytevX3///m2M6e/v7+joCPtNwDpnA5ient6+ffvCf46NjQUfdHd3p9Npz/OePHmy6ClPnz7t6emp6VU8z9u7d+/u3bsPHTpU63MRB84G8Pfv3+U+NTc319bW9vPnz/Xr1xtj5ufn9+/fXywWP3369Pz58wrHDB4ZfOx5XiaTOXLkyMDAQKFQGBkZ2bNnz5kzZyy8FVjk7FeBtmzZ8u7du+Bj3/dPnToVfPzq1au5ubkrV66cPXs2+JPVq1ffv3//4cOHw8PDd+7cqXDM4JGBTCbz7du3qampdevWDQ0N3b17N7i3RrI4G8DRo0cvXrw4Pz9vjLl3716wU//z54/neefOnevt7U2lUoVCofQpvb29r1+/XvlLtLS05PP52dlZY8z37987OzstvA/Y5ewWaHBw8PPnz319fRs2bOjo6Lh06ZIx5vr167lcrquryxgzOjp6+PDhXC638JTu7u7379//+/evtbW16hYok8l4njc2NpbP59vb29va2sbHx5v15hCaFt/3jc1v4Ob/B0Ccx8nZLRCwEgQAaQQAaQQAaQQAaQQAaQQAaQQAaQQAaQQAaQQAaQQAaQQAaQQAaQQAaQQAaQQAaQQAaQQAaQQAaQQAaQQAaQQAaQQAaQQAaQQAaQQAaQQAaQQAaQQAaQQAaQQAaQQAaQQAaQQAaQQAaQQAaQQAaQQAaQQAac7+ouzYCn5NdwUzMzPNWgsIIAYTX/nx9GAVV4C4zH3V41CCDQQQ39Eve1gyCBcBNHv0Hz16VPkB/f39VV+CDMJCAM0Y/apDv9yDl4uBDMJCABanv6a5r3yEsiV0dXVxKWgQAViZ/sZHv+wBl2ZAAw0igLiPftUM2A41ggBCm36ro7+SDNgO1YFvhUjY9Fd4RUtffnUbASRy+pd7XRqoFVug2iyasKhGv8J2iL1QTbgCJHj6l1sJ14GVI4A6xWf647mepCCAlUrWaTVZq40QASR781OKjVAdCMCR6Q/QQK0IoDZxnv6krDBWCMDxzXTS128bATh4ck3KOuOAANw/fbrxLiwhADdPq8labYQIQOLE6dJ7CRcBOHtCTeKam48AII0AVPYM7r2jUBCAy3uJ5K68aQgA0ggA0ggA0gigyv1i0rfRpevnPngpAoA0AoA0AoA0AoA0AoA0AoA0AoA0AoA0AoA0AoA0Aiij9DdNVP6djfFXun5+g8ZSBABpBABpBABpBFBdcm8DkrvypiGA8ty7X3TvHYWCACCNAJzdSyRxzc1HABJ7BpfeS7gIwM0TarJWGyECcP/E6ca7sIQAHDytJmWdcUAAjp8+k75+2wjAtZNr/FcYKwRQ80k0zhO2aG2c/qsiAHcaYPrrQAArlayzabJWGyECqFPcLgJxW09SEIALGyE2P3VL1f9USTMzM6U/YzmYvAh/gvTSCNn81IQrQM2WTlhUlwKmv3EEkNQGmP5QsAUKZy/UzO1Q2djY+dSHAOoXzFwzM2D0Q0cA4V8KbGSw3BaLE3+DCMBWA6VTW3cJlW8tmP7GEYDF7VDZOa4aw0rupxn9sBBA8zII5etFjH64CCCaDOo+LMJFALYszGuDJTD3VhGAdYsmuGoPTHwzEUCzMd+xwrdCQBoBQBoBQBoBQBoBQBoBQBoBQBoBQBoBQBoBQBoBQBoBQBoBQBoBQBoBQBoBQBoBQBoBQBoBQBoBQBoBQBoBQFoifyzKtm3bol4Cyvv48aNJFK4AkEYAkEYAkEYAkJbIm+DE3WkhtrgCQBoBQBoBQBoBQBoBQBoBQBoBQBoBQBoBQBoBQBoBQBoBQBoBQBoBQBoBQBoBQBoBQBoBQBoBQBoBQBoBQBoBQBoBQBoBQBoBQBoBQBoBQBoBQBoBQBoBQBoBQBoBQBoBQBoBQBoBQBoBQBoBQBoBQBoBQBoBQBoBQBoBQFrK9gtks1nbLwHUjSsApBEApBEApLX4vh/1GoDIcAWANAKANAKANAKANAKANAKANAKANAKANAKANAKANAKANAKANAKANAKANAKANAKANAKANAKANAKANAKANAKANAKAUfYfMMT2AVXUhg8AAAAASUVORK5CYII="
)


def _build_vision_test_image_data_url() -> str:
    image = Image.new("RGB", (256, 256), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((28, 24, 228, 232), outline=(60, 60, 60), width=4)
    draw.ellipse((92, 84, 164, 156), outline=(30, 30, 30), width=4, fill=(215, 215, 215))
    draw.line((60, 182, 196, 182), fill=(40, 40, 40), width=5)
    draw.text((72, 34), "CXR TEST", fill=(20, 20, 20))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return "data:image/png;base64," + b64encode(buffer.getvalue()).decode("ascii")


VISION_TEST_IMAGE_DATA_URL = _build_vision_test_image_data_url()

EXECUTOR_JOBS: dict[str, dict[str, Any]] = {}
EXECUTOR_JOBS_LOCK = threading.Lock()
AUTO_JOBS: dict[str, dict[str, Any]] = {}
AUTO_JOBS_LOCK = threading.Lock()
AUTO_JOB_SUBSCRIBERS: dict[str, list[queue.Queue[dict[str, Any]]]] = {}
AUTO_JOB_SUBSCRIBERS_LOCK = threading.Lock()

AUTO_TRIGGER_PATTERN = re.compile(r"@auto\b", re.IGNORECASE)

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
    "Executor": "证据执行",
    "Decider": "证据决策",
    "Report Generator": "报告生成",
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
    "Evidence-based executor for multimodal diagnostic steps with grounding-ready outputs.": "负责执行多模态诊断步骤，产出具备定位与量化依据的结构化证据。",
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
    migrated = [
        AgentRoleConfig(
            role_name=role.role_name,
            role_spec=ROLE_SPEC_MIGRATIONS.get(role.role_spec, role.role_spec),
            provider_id=getattr(role, "provider_id", ""),
            provider_name=role.provider_name,
            agent_count=role.agent_count,
        )
        for role in roles
    ]
    if not any(role.role_name == "Executor" for role in migrated):
        planner_role = next((role for role in migrated if role.role_name == "Planner"), None)
        migrated.append(
            AgentRoleConfig(
                role_name="Executor",
                role_spec="负责执行多模态诊断步骤，产出具备定位与量化依据的结构化证据。",
                provider_id=planner_role.provider_id if planner_role else "",
                provider_name=planner_role.provider_name if planner_role else "DeepSeek",
                agent_count=1,
            )
        )
    if not any(role.role_name == "Decider" for role in migrated):
        executor_role = next((role for role in migrated if role.role_name == "Executor"), None)
        planner_role = next((role for role in migrated if role.role_name == "Planner"), None)
        source_role = executor_role or planner_role
        migrated.append(
            AgentRoleConfig(
                role_name="Decider",
                role_spec="收集 Executor 证据，融合支持与反证，形成 evidence-based 诊断判断。",
                provider_id=source_role.provider_id if source_role else "",
                provider_name=source_role.provider_name if source_role else "DeepSeek",
                agent_count=1,
            )
        )
    if not any(role.role_name == "Report Generator" for role in migrated):
        decider_role = next((role for role in migrated if role.role_name == "Decider"), None)
        generator_role = next((role for role in migrated if role.role_name == "Generator"), None)
        source_role = decider_role or generator_role
        migrated.append(
            AgentRoleConfig(
                role_name="Report Generator",
                role_spec="基于 Decider 判断和 Executor 证据生成带证据引用的临床报告。",
                provider_id=source_role.provider_id if source_role else "",
                provider_name=source_role.provider_name if source_role else "DeepSeek",
                agent_count=1,
            )
        )
    return migrated


def _provider_key(provider_name: str, endpoint: str, model_name: str, index: int) -> str:
    seed = "|".join(
        [
            str(provider_name or "").strip(),
            str(endpoint or "").strip(),
            str(model_name or "").strip(),
            str(index),
        ]
    )
    return f"provider-{uuid5(NAMESPACE_URL, seed).hex[:12]}"


def _provider_matches_role(provider: APIProviderConfig, role: AgentRoleConfig) -> bool:
    role_provider_id = str(getattr(role, "provider_id", "") or "").strip()
    provider_id = str(getattr(provider, "provider_id", "") or "").strip()
    if role_provider_id and provider_id:
        return role_provider_id == provider_id
    return provider.provider_name == role.provider_name


def _materialize_provider_bindings(
    providers: list[APIProviderConfig],
    roles: list[AgentRoleConfig],
) -> tuple[list[APIProviderConfig], list[AgentRoleConfig], bool]:
    changed = False
    seen_ids: set[str] = set()
    normalized_providers: list[APIProviderConfig] = []
    for index, provider in enumerate(providers, start=1):
        provider_id = str(getattr(provider, "provider_id", "") or "").strip()
        if not provider_id:
            provider_id = _provider_key(provider.provider_name, provider.endpoint, provider.model_name, index)
        if provider_id in seen_ids:
            provider_id = f"{provider_id}-{index}"
        if provider.provider_id != provider_id:
            provider.provider_id = provider_id
            changed = True
        normalized_providers.append(provider)
        seen_ids.add(provider_id)

    normalized_roles: list[AgentRoleConfig] = []
    for role in roles:
        matched = next((provider for provider in normalized_providers if _provider_matches_role(provider, role)), None)
        if matched is None and role.provider_name:
            matched = next((provider for provider in normalized_providers if provider.provider_name == role.provider_name), None)
        if matched is not None:
            if role.provider_id != matched.provider_id:
                role.provider_id = matched.provider_id
                changed = True
            if role.provider_name != matched.provider_name:
                role.provider_name = matched.provider_name
                changed = True
        normalized_roles.append(role)
    return normalized_providers, normalized_roles, changed


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
    providers, roles, changed = _materialize_provider_bindings(providers, migrate_roles(roles))
    settings = SystemSettings(
        orchestration_mode=data.get("orchestration_mode", OrchestrationMode.ASYMMETRIC.value),
        default_department=data.get("default_department", DepartmentOption.PEDIATRICS.value),
        consensus_threshold=float(data.get("consensus_threshold", 0.82)),
        max_rounds=int(data.get("max_rounds", 3)),
        show_diagnostics=bool(data.get("show_diagnostics", True)),
        api_providers=providers,
        agent_roles=roles,
    )
    if changed:
        save_settings(username, settings)
    return settings


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


def _load_turn(data: dict[str, Any] | None) -> SessionTurn | None:
    if not data:
        return None
    submission = _load_submission(data.get("submission"))
    result = _load_result(data.get("result"))
    if submission is None or result is None:
        return None
    return SessionTurn(
        turn_id=str(data.get("turn_id", "")).strip() or uuid4().hex[:12],
        timestamp=str(data.get("timestamp", "")),
        user_input=str(data.get("user_input", "")),
        submission=submission,
        result=result,
    )


def _load_approval(data: dict[str, Any] | None) -> DoctorApproval | None:
    if not data:
        return None
    return DoctorApproval(
        approval_id=str(data.get("approval_id", "")).strip() or uuid4().hex[:12],
        turn_id=str(data.get("turn_id", "")).strip(),
        execution_mode=str(data.get("execution_mode", "")).strip(),
        action=str(data.get("action", "")).strip(),
        note=str(data.get("note", "")).strip(),
        created_at=str(data.get("created_at", "")).strip(),
    )


def _load_feedback(data: dict[str, Any] | None) -> CaseFeedback | None:
    if not data:
        return None
    evidence_ratings = [
        EvidenceFeedback(
            evidence_id=str(item.get("evidence_id", "")).strip(),
            rating=int(item.get("rating", 0)),
        )
        for item in data.get("evidence_ratings", [])
        if isinstance(item, dict)
    ]
    return CaseFeedback(
        submitted_at=str(data.get("submitted_at", "")).strip(),
        diagnosis_rating=int(data.get("diagnosis_rating", 0)),
        report_rating=int(data.get("report_rating", 0)),
        evidence_ratings=evidence_ratings,
        comment=str(data.get("comment", "")).strip(),
    )


def _safe_image_assets(items: list[dict[str, Any]] | None) -> list[dict[str, str]]:
    cleaned: list[dict[str, str]] = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        analysis_data_url = str(item.get("data_url", "")).strip()
        display_data_url = str(item.get("display_data_url", "")).strip() or analysis_data_url
        media_type = str(item.get("media_type", "")).strip() or "image/jpeg"
        if not analysis_data_url.startswith("data:image/"):
            continue
        if not display_data_url.startswith("data:image/"):
            display_data_url = analysis_data_url
        cleaned.append(
            {
                "name": name,
                "media_type": media_type,
                "data_url": analysis_data_url,
                "display_data_url": display_data_url,
            }
        )
        if len(cleaned) >= 2:
            break
    return cleaned


def _merge_named_lists(base_items: list[str], new_items: list[str]) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for item in [*base_items, *new_items]:
        value = str(item or "").strip()
        key = value.lower()
        if not value or key in seen:
            continue
        merged.append(value)
        seen.add(key)
    return merged


def _merge_image_assets(base_items: list[dict[str, str]], new_items: list[dict[str, str]]) -> list[dict[str, str]]:
    merged: dict[str, dict[str, str]] = {}
    for item in [*base_items, *new_items]:
        key = str(item.get("name", "")).strip().lower() or str(len(merged))
        merged[key] = item
    return list(merged.values())[:2]


def _merge_case_summary(base_summary: str, next_summary: str) -> str:
    base = str(base_summary or "").strip()
    current = str(next_summary or "").strip()
    if not base:
        return current
    if not current or current == base:
        return base
    if current.lower().startswith("please continue") or current.lower().startswith("continue "):
        return base
    return f"{base}\n\nFollow-up instruction:\n{current}"


def _merged_submission_context(base: CaseSubmission | None, current: CaseSubmission) -> CaseSubmission:
    if base is None:
        return current
    has_new_images = bool(current.image_assets or current.uploaded_images)
    if has_new_images:
        merged_assets = list(current.image_assets)
        merged_images = list(current.uploaded_images or [str(item.get("name", "")).strip() for item in current.image_assets if str(item.get("name", "")).strip()])
    else:
        merged_assets = list(base.image_assets)
        merged_images = list(base.uploaded_images)
    merged_docs = _merge_named_lists(base.uploaded_docs, current.uploaded_docs)
    return CaseSubmission(
        department=current.department or base.department,
        output_style=current.output_style or base.output_style,
        urgency=current.urgency or base.urgency,
        chief_complaint=current.chief_complaint or base.chief_complaint,
        case_summary=_merge_case_summary(base.case_summary, current.case_summary),
        patient_age=current.patient_age or base.patient_age,
        patient_sex=current.patient_sex or base.patient_sex,
        insurance_type=current.insurance_type or base.insurance_type,
        uploaded_images=merged_images,
        uploaded_docs=merged_docs,
        show_process=current.show_process if current.show_process is not None else base.show_process,
        image_assets=merged_assets,
        single_model_test=current.single_model_test,
        is_ready=current.is_ready,
    )


def _analysis_payloads_from_submission(submission: CaseSubmission) -> list[dict[str, str]]:
    return [
        {
            "name": item["name"],
            "media_type": item.get("media_type", "image/jpeg"),
            "data_url": item["data_url"],
        }
        for item in submission.image_assets
        if str(item.get("data_url", "")).startswith("data:image/")
    ]


def _context_submission_from_session(session: CaseSessionRecord | None) -> CaseSubmission | None:
    if session is None:
        return None
    if session.context_submission is not None:
        return session.context_submission
    if session.submission is not None:
        return session.submission
    turns = session.turns or []
    for turn in reversed(turns):
        if turn.submission is not None:
            return turn.submission
    return None


def _normalize_context_text(value: object) -> str:
    return " ".join(str(value or "").split()).strip().lower()


def _normalize_name_set(values: list[str] | None) -> set[str]:
    return {_normalize_context_text(value) for value in values or [] if _normalize_context_text(value)}


def _session_has_bundle(session: CaseSessionRecord | None, bundle: str) -> bool:
    if session is None or not bundle:
        return session is not None
    if bundle == "planner":
        return _latest_planner_bundle(session) is not None
    if bundle == "executor":
        return _latest_executor_bundle(session) is not None
    if bundle == "decider":
        return _latest_decider_bundle(session) is not None
    return False


def _session_context_score(session: CaseSessionRecord, reference: CaseSubmission | None) -> int:
    if reference is None:
        return 0
    candidate = _context_submission_from_session(session)
    if candidate is None:
        return -1
    score = 0
    candidate_summary = _normalize_context_text(candidate.case_summary)
    reference_summary = _normalize_context_text(reference.case_summary)
    if candidate_summary and reference_summary:
        if candidate_summary == reference_summary:
            score += 12
        elif candidate_summary in reference_summary or reference_summary in candidate_summary:
            score += 6
    candidate_cc = _normalize_context_text(candidate.chief_complaint)
    reference_cc = _normalize_context_text(reference.chief_complaint)
    if candidate_cc and reference_cc and candidate_cc == reference_cc:
        score += 4
    candidate_images = _normalize_name_set(candidate.uploaded_images)
    reference_images = _normalize_name_set(reference.uploaded_images)
    if candidate_images and reference_images:
        score += 3 * len(candidate_images & reference_images)
    candidate_docs = _normalize_name_set(candidate.uploaded_docs)
    reference_docs = _normalize_name_set(reference.uploaded_docs)
    if candidate_docs and reference_docs:
        score += 2 * len(candidate_docs & reference_docs)
    if _normalize_context_text(candidate.department) and _normalize_context_text(candidate.department) == _normalize_context_text(reference.department):
        score += 1
    if _normalize_context_text(candidate.output_style) and _normalize_context_text(candidate.output_style) == _normalize_context_text(reference.output_style):
        score += 1
    if _normalize_context_text(candidate.urgency) and _normalize_context_text(candidate.urgency) == _normalize_context_text(reference.urgency):
        score += 1
    return score


def _resolve_context_session(
    sessions: list[CaseSessionRecord],
    *,
    context_session_id: str = "",
    required_bundle: str = "",
    reference_submission: CaseSubmission | None = None,
) -> CaseSessionRecord | None:
    exact = next((session for session in sessions if session.session_id == context_session_id), None) if context_session_id else None
    if exact is not None and _session_has_bundle(exact, required_bundle):
        return exact

    target_submission = reference_submission or _context_submission_from_session(exact)
    best_session: CaseSessionRecord | None = None
    best_score = -1
    for session in sessions:
        if exact is not None and session.session_id == exact.session_id:
            continue
        if not _session_has_bundle(session, required_bundle):
            continue
        score = _session_context_score(session, target_submission)
        if score > best_score:
            best_score = score
            best_session = session
    if best_session is not None and best_score > 0:
        return best_session
    if exact is not None:
        return exact
    if required_bundle:
        for session in sessions:
            if _session_has_bundle(session, required_bundle):
                return session
    return sessions[0] if sessions else None


def _latest_planner_bundle(session: CaseSessionRecord | None) -> dict[str, Any] | None:
    if session is None:
        return None
    turns = session.turns or []
    for turn in reversed(turns):
        if turn.result.execution_mode != "planner":
            continue
        if not turn.result.plan_steps:
            continue
        trace = turn.result.agent_trace[0] if turn.result.agent_trace else {}
        return {
            "steps": turn.result.plan_steps,
            "display_steps": turn.result.plan_display_steps,
            "references": turn.result.references,
            "provider": turn.result.serving_provider,
            "model": turn.result.serving_model,
            "note": str(trace.get("note") or "Loaded the existing planner-generated execution plan from context."),
        }
    return None


def _latest_executor_bundle(session: CaseSessionRecord | None) -> dict[str, Any] | None:
    if session is None:
        return None
    turns = session.turns or []
    for turn in reversed(turns):
        if turn.result.execution_mode != "executor":
            continue
        if not turn.result.execution_records:
            continue
        trace = turn.result.agent_trace[-1] if turn.result.agent_trace else {}
        return {
            "records": turn.result.execution_records,
            "plan_steps": turn.result.plan_steps,
            "plan_display_steps": turn.result.plan_display_steps,
            "references": turn.result.references,
            "provider": turn.result.serving_provider,
            "model": turn.result.serving_model,
            "note": str(trace.get("note") or "Loaded the existing executor evidence from context."),
        }
    return None


def _latest_decider_bundle(session: CaseSessionRecord | None) -> dict[str, Any] | None:
    if session is None:
        return None
    turns = session.turns or []
    for turn in reversed(turns):
        if turn.result.execution_mode != "decider":
            continue
        try:
            decision = json.loads(turn.result.raw_provider_payload or "{}")
        except json.JSONDecodeError:
            decision = {}
        if not decision:
            continue
        trace = turn.result.agent_trace[-1] if turn.result.agent_trace else {}
        return {
            "decision": decision,
            "provider": turn.result.serving_provider,
            "model": turn.result.serving_model,
            "note": str(trace.get("note") or "Loaded the existing decider decision from context."),
        }
    return None


def load_sessions(username: str) -> list[CaseSessionRecord]:
    ensure_storage(username)
    raw = load_json(_user_paths(username)["sessions"], [])
    if raw:
        sessions: list[CaseSessionRecord] = []
        for item in raw:
            submission = _load_submission(item.get("submission"))
            result = _load_result(item.get("result"))
            turns = [_load_turn(turn) for turn in item.get("turns", [])]
            materialized_turns = [turn for turn in turns if turn is not None]
            if not materialized_turns and submission is not None and result is not None:
                materialized_turns = [
                    SessionTurn(
                        turn_id=uuid4().hex[:12],
                        timestamp=str(item.get("timestamp", "")),
                        user_input=submission.case_summary,
                        submission=submission,
                        result=result,
                    )
                ]
            approvals = [_load_approval(approval) for approval in item.get("doctor_approvals", [])]
            sessions.append(
                CaseSessionRecord(
                    session_id=item["session_id"],
                    timestamp=item["timestamp"],
                    title=item["title"],
                    department=item["department"],
                    output_style=item["output_style"],
                    summary=item["summary"],
                    consensus_score=float(item["consensus_score"]),
                    show_in_sidebar=bool(item.get("show_in_sidebar", True)),
                    submission=submission,
                    result=result,
                    context_submission=_load_submission(item.get("context_submission")) or submission,
                    turns=materialized_turns,
                    doctor_approvals=[approval for approval in approvals if approval is not None],
                    case_feedback=_load_feedback(item.get("case_feedback")),
                )
            )
        return sessions

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
            provider_id=str(item.get("provider_id", getattr(current.api_providers[index], "provider_id", "") if index < len(current.api_providers) else "")).strip(),
            provider_name=str(item.get("provider_name", "DeepSeek")),
            model_name=str(item.get("model_name", "deepseek-chat")),
            endpoint=str(item.get("endpoint", "")),
            api_key=str(item.get("api_key", "")),
            agents_for_api=max(int(item.get("agents_for_api", 1)), 1),
            enabled=bool(item.get("enabled", True)),
        )
        for index, item in enumerate(payload.get("api_providers", [asdict(provider) for provider in current.api_providers]))
    ]
    roles = [
        AgentRoleConfig(
            role_name=str(item.get("role_name", "Orchestrator")),
            role_spec=str(item.get("role_spec", "")),
            provider_id=str(item.get("provider_id", getattr(current.agent_roles[index], "provider_id", "") if index < len(current.agent_roles) else "")).strip(),
            provider_name=str(item.get("provider_name", "DeepSeek")),
            agent_count=max(int(item.get("agent_count", 1)), 1),
        )
        for index, item in enumerate(payload.get("agent_roles", [asdict(role) for role in current.agent_roles]))
    ]
    providers, roles, _ = _materialize_provider_bindings(providers, roles)
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
        provider_id=str(payload.get("provider_id", "")).strip(),
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


def _build_text_probe_body(provider: APIProviderConfig) -> dict[str, Any]:
    return {
        "model": provider.model_name,
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 1,
        "temperature": 0,
    }


def _build_vision_probe_body(provider: APIProviderConfig) -> dict[str, Any]:
    return {
        "model": provider.model_name,
        "messages": [
            {"role": "system", "content": "Return only JSON."},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": 'Verify that image input is working. Return JSON: {"ok":true,"note":""}.'},
                    {"type": "image_url", "image_url": {"url": VISION_TEST_IMAGE_DATA_URL}},
                ],
            },
        ],
        "max_tokens": 64,
        "temperature": 0,
    }


def _build_vision_probe_target(provider: APIProviderConfig) -> tuple[str, str, bytes]:
    base = _normalize_provider_endpoint(provider.endpoint).rstrip("/")
    body = json.dumps(_build_vision_probe_body(provider)).encode("utf-8")
    return "POST", f"{base}/chat/completions", body


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


def _request_provider_json(url: str, api_key: str, body: dict[str, Any], *, timeout: int = 45) -> dict[str, Any]:
    payload = json.dumps(body).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "RareMDT/2.0",
    }
    request = urllib_request.Request(url, data=payload, headers=headers, method="POST")
    with urllib_request.urlopen(request, timeout=timeout) as response:
        raw = response.read().decode("utf-8", errors="replace")
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("接口返回了无法解析的响应。") from exc
    if not isinstance(parsed, dict):
        raise ValueError("接口返回格式不符合预期。")
    return parsed


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


def _extract_chat_content(payload: dict[str, Any]) -> str:
    choices = payload.get("choices")
    if isinstance(choices, list) and choices:
        message = choices[0].get("message", {}) if isinstance(choices[0], dict) else {}
        content = message.get("content")
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text" and isinstance(item.get("text"), str):
                    parts.append(item["text"])
            if parts:
                return "\n".join(parts).strip()

    output = payload.get("output")
    if isinstance(output, list):
        texts: list[str] = []
        for item in output:
            if not isinstance(item, dict):
                continue
            for content in item.get("content", []):
                if isinstance(content, dict) and content.get("type") == "output_text" and isinstance(content.get("text"), str):
                    texts.append(content["text"])
        if texts:
            return "\n".join(texts).strip()

    raise ValueError("接口返回中未找到可用文本内容。")


def _parse_json_text(raw: str) -> Any:
    text = str(raw or "").strip()
    if text.startswith("```"):
        chunks = sorted(text.split("```"), key=len, reverse=True)
        for chunk in chunks:
            chunk = chunk.strip()
            if not chunk:
                continue
            if chunk.lower().startswith("json"):
                chunk = chunk[4:].strip()
            if chunk.startswith("{") or chunk.startswith("["):
                return json.loads(chunk)
    return json.loads(text)


def _is_json_payload(raw: str) -> bool:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return False
    return isinstance(parsed, (dict, list))


def _resolve_single_model_provider(settings: SystemSettings) -> tuple[AgentRoleConfig, APIProviderConfig]:
    if not settings.agent_roles:
        raise ValueError("未配置 Agent Roles，无法进行单模型测试。")
    first_role = settings.agent_roles[0]
    for provider in settings.api_providers:
        if _provider_matches_role(provider, first_role):
            return first_role, provider
    raise ValueError("首个 Agent Role 绑定的接口不存在，请先检查设置。")


def _build_single_model_messages(submission: CaseSubmission, profile: AppProfile, role: AgentRoleConfig) -> list[dict[str, str]]:
    system_prompt = (
        "你是一名罕见病临床辅助模型，正在为真实医生生成会诊草案。"
        "输出必须专业、谨慎、结构清晰，使用简体中文。"
        "不得假装已确认最终诊断；不确定时应给出鉴别方向、下一步检查与安全提醒。"
        f" 当前角色：{role.role_name}。角色说明：{role.role_spec}"
    )
    user_prompt = (
        f"医院：{profile.hospital_name}\n"
        f"医生：{profile.user_name} {profile.title}\n"
        f"默认专科方向：{profile.specialty_focus}\n\n"
        f"病例摘要：\n{submission.case_summary}\n\n"
        f"主诉：{submission.chief_complaint or '未提供'}\n"
        f"年龄：{submission.patient_age or '未提供'}\n"
        f"性别：{submission.patient_sex or '未提供'}\n"
        f"科室：{submission.department}\n"
        f"输出类型：{submission.output_style}\n"
        f"紧急程度：{submission.urgency}\n"
        f"医保类型：{submission.insurance_type}\n"
        f"影像附件：{', '.join(submission.uploaded_images) if submission.uploaded_images else '无'}\n"
        f"文档附件：{', '.join(submission.uploaded_docs) if submission.uploaded_docs else '无'}\n\n"
        "请直接生成一份适合临床医生阅读的结构化会诊草案，建议包含："
        "诊断判断、主要依据、鉴别诊断、下一步检查/处理建议、安全提醒。"
    )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def _run_single_model_provider_case(
    submission: CaseSubmission,
    profile: AppProfile,
    settings: SystemSettings,
) -> EngineResult:
    role, provider = _resolve_single_model_provider(settings)
    if not provider.endpoint:
        raise ValueError("单模型测试失败：首个 Agent Role 绑定的接口未填写地址。")
    if not provider.api_key:
        raise ValueError("单模型测试失败：首个 Agent Role 绑定的接口未填写 API Key。")
    if not provider.model_name:
        raise ValueError("单模型测试失败：首个 Agent Role 绑定的接口未填写模型名。")

    base = _normalize_provider_endpoint(provider.endpoint).rstrip("/")
    url = f"{base}/chat/completions"
    body = {
        "model": provider.model_name,
        "messages": _build_single_model_messages(submission, profile, role),
        "temperature": 0.2,
    }
    raw_provider_request = json.dumps(body, ensure_ascii=False, indent=2)
    try:
        payload = _request_provider_json(url, provider.api_key, body)
    except urllib_error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        detail = _extract_error_message(raw, f"HTTP {exc.code}")
        if exc.code in {401, 403}:
            raise ValueError("单模型测试失败：鉴权失败，请检查首个 Agent Role 对应接口的 API Key。") from exc
        raise ValueError(f"单模型测试失败：{detail}") from exc
    except urllib_error.URLError as exc:
        reason = getattr(exc, "reason", exc)
        raise ValueError(f"单模型测试失败：无法连接接口，{_trim_message(str(reason))}") from exc

    generated_answer = _extract_chat_content(payload)
    raw_provider_payload = json.dumps(payload, ensure_ascii=False, indent=2)
    return run_single_model_case(
        submission=submission,
        profile=profile,
        settings=settings,
        provider_name=provider.provider_name,
        model_name=provider.model_name,
        role_name=role.role_name,
        role_spec=role.role_spec,
        generated_answer=generated_answer,
        raw_provider_request=raw_provider_request,
        raw_provider_payload=raw_provider_payload,
    )


def test_provider_connection(payload: dict[str, Any]) -> dict[str, Any]:
    provider_payload = payload.get("provider") if isinstance(payload.get("provider"), dict) else payload
    provider = provider_from_payload(provider_payload)
    provider_name = provider.provider_name or "当前接口"
    mode = str(payload.get("mode", "text")).strip().lower()

    if not provider.endpoint:
        raise ValueError("请先填写接口地址。")
    if not provider.api_key:
        raise ValueError("请先填写 API Key。")
    if mode == "vision" and not provider.model_name:
        raise ValueError("请先填写模型名，再测试视觉接口。")

    if mode == "vision":
        base = _normalize_provider_endpoint(provider.endpoint).rstrip("/")
        url = f"{base}/chat/completions"
        body = _build_vision_probe_body(provider)
        try:
            payload = _request_provider_json(url, provider.api_key, body, timeout=25)
            content = _extract_chat_content(payload)
            parsed = _parse_json_text(content)
            if not isinstance(parsed, dict):
                raise ValueError("接口返回的视觉测试结果不是 JSON 对象。")
            return {"message": f"{provider_name} 视觉接口可用，图像输入测试通过。", "provider_name": provider_name}
        except urllib_error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            detail = _extract_error_message(raw, f"HTTP {exc.code}")
            if exc.code in {401, 403}:
                raise ValueError(f"{provider_name} 视觉接口鉴权失败，请检查 API Key 或服务权限。") from exc
            if exc.code == 429:
                return {
                    "message": f"{provider_name} 视觉接口可达，但当前触发限流或余额不足。",
                    "provider_name": provider_name,
                }
            if exc.code == 400:
                raise ValueError(f"{provider_name} 视觉测试失败：当前模型或端点不接受图像输入。{detail}") from exc
            raise ValueError(f"{provider_name} 视觉测试失败：{detail}") from exc
        except urllib_error.URLError as exc:
            reason = getattr(exc, "reason", exc)
            raise ValueError(f"{provider_name} 视觉接口无法连接：{_trim_message(str(reason))}") from exc
        except ValueError as exc:
            raise ValueError(f"{provider_name} 视觉测试失败：{exc}") from exc

    last_message = "无法连接到接口。"
    for method, url, body in _build_probe_targets(provider):
        try:
            _, raw = _request_provider_probe(url, method, provider.api_key, body)
            if method == "GET":
                if not _is_json_payload(raw):
                    last_message = f"{provider_name} /models 返回了非 JSON 内容，已尝试继续深度探测。"
                    continue
                return {"message": f"{provider_name} 接口可用。", "provider_name": provider_name}
            payload = _request_provider_json(
                url,
                provider.api_key,
                _build_text_probe_body(provider),
                timeout=20,
            )
            _extract_chat_content(payload)
            return {"message": f"{provider_name} 接口可用，模型调用测试通过。", "provider_name": provider_name}
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
        except ValueError as exc:
            if method == "GET":
                last_message = f"{provider_name} 接口探测未返回可用 JSON，已尝试继续深度探测。"
                continue
            raise ValueError(f"{provider_name} 测试失败：{exc}") from exc

    raise ValueError(last_message)


def _timestamp_now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def is_auto_invocation(text: str) -> bool:
    return bool(AUTO_TRIGGER_PATTERN.search(str(text or "")))


def strip_auto_mention(text: str) -> str:
    cleaned = AUTO_TRIGGER_PATTERN.sub("", str(text or ""))
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _prepare_case_request(username: str, payload: dict[str, Any]) -> dict[str, Any]:
    settings = load_settings(username)
    profile = load_profile(username)
    sessions = load_sessions(username)
    raw_text = str(payload.get("case_summary", "")).strip()
    context_session_id = str(payload.get("context_session_id", "")).strip()
    report_requested = is_report_invocation(raw_text)
    decider_requested = is_decider_invocation(raw_text)
    executor_requested = is_executor_invocation(raw_text)
    planner_requested = is_planner_invocation(raw_text)
    auto_requested = is_auto_invocation(raw_text)
    context_bundle = "executor" if decider_requested or report_requested else "planner" if executor_requested else ""
    active_session = _resolve_context_session(
        sessions,
        context_session_id=context_session_id,
        required_bundle=context_bundle,
    )
    if auto_requested:
        main_text = strip_auto_mention(raw_text)
    elif report_requested:
        main_text = strip_report_mention(raw_text)
    elif decider_requested:
        main_text = strip_decider_mention(raw_text)
    elif executor_requested:
        main_text = strip_executor_mention(raw_text)
    elif planner_requested:
        main_text = strip_planner_mention(raw_text)
    else:
        main_text = raw_text
    image_assets = _safe_image_assets(
        payload.get("uploaded_image_assets")
        if isinstance(payload.get("uploaded_image_assets"), list)
        else payload.get("uploaded_image_payloads")
    )
    if not main_text:
        context_submission = _context_submission_from_session(active_session)
        if context_submission is not None:
            main_text = context_submission.case_summary
        else:
            raise ValueError("\u8bf7\u5148\u8f93\u5165\u75c5\u4f8b\u6458\u8981\uff0c\u6216\u5728\u5df2\u6709\u4e0a\u4e0b\u6587\u4e2d\u7ee7\u7eed\u6267\u884c\u3002")

    prefill = parse_ehr_intake(main_text, settings.default_department)
    incoming_submission = CaseSubmission(
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
        image_assets=image_assets,
        single_model_test=bool(payload.get("single_model_test", False)),
    )
    active_session = _resolve_context_session(
        sessions,
        context_session_id=context_session_id,
        required_bundle=context_bundle,
        reference_submission=incoming_submission,
    )
    submission = _merged_submission_context(
        _context_submission_from_session(active_session),
        incoming_submission,
    )
    planner_image_payloads = _analysis_payloads_from_submission(submission)
    plan_session = active_session
    execution_session = active_session
    decision_session = active_session
    plan_bundle = None
    execution_bundle = None
    decision_bundle = None

    if executor_requested:
        plan_session = _resolve_context_session(
            sessions,
            context_session_id=context_session_id,
            required_bundle="planner",
            reference_submission=submission,
        )
        if plan_session is not None and plan_session is not active_session:
            submission = _merged_submission_context(_context_submission_from_session(plan_session), incoming_submission)
            planner_image_payloads = _analysis_payloads_from_submission(submission)
        plan_bundle = _latest_planner_bundle(plan_session)

    if decider_requested or report_requested:
        execution_session = _resolve_context_session(
            sessions,
            context_session_id=context_session_id,
            required_bundle="executor",
            reference_submission=submission,
        )
        if execution_session is not None and execution_session is not plan_session and execution_session is not active_session:
            submission = _merged_submission_context(_context_submission_from_session(execution_session), incoming_submission)
            planner_image_payloads = _analysis_payloads_from_submission(submission)
        execution_bundle = _latest_executor_bundle(execution_session)

    if report_requested:
        decision_session = _resolve_context_session(
            sessions,
            context_session_id=context_session_id,
            required_bundle="decider",
            reference_submission=submission,
        )
        if decision_session is not None and decision_session is not execution_session and decision_session is not active_session:
            submission = _merged_submission_context(_context_submission_from_session(decision_session), incoming_submission)
            planner_image_payloads = _analysis_payloads_from_submission(submission)
            if execution_bundle is None:
                execution_bundle = _latest_executor_bundle(decision_session)
        decision_bundle = _latest_decider_bundle(decision_session)

    resolved_session = decision_session or execution_session or plan_session or active_session
    if executor_requested and plan_bundle is None:
        raise ValueError("\u5f53\u524d\u4e0a\u4e0b\u6587\u4e2d\u6ca1\u6709\u53ef\u6267\u884c\u7684\u8bca\u65ad\u8ba1\u5212\u3002\u8bf7\u5148\u8c03\u7528 @Planner \u751f\u6210 plan\u3002")
    if decider_requested and execution_bundle is None:
        raise ValueError("\u5f53\u524d\u4e0a\u4e0b\u6587\u4e2d\u6ca1\u6709\u5df2\u5b8c\u6210\u7684 Executor \u8bc1\u636e\u3002\u8bf7\u5148\u8c03\u7528 @Executor \u6267\u884c\u8ba1\u5212\u3002")
    if report_requested and execution_bundle is None:
        raise ValueError("\u5f53\u524d\u4e0a\u4e0b\u6587\u4e2d\u6ca1\u6709\u5df2\u5b8c\u6210\u7684 Executor \u8bc1\u636e\u3002\u8bf7\u5148\u8c03\u7528 @Executor \u6267\u884c\u8ba1\u5212\u3002")
    if report_requested and decision_bundle is None:
        raise ValueError("\u5f53\u524d\u4e0a\u4e0b\u6587\u4e2d\u6ca1\u6709 Decider \u8bca\u65ad\u5224\u65ad\u3002\u8bf7\u5148\u8c03\u7528 @Decider \u5b8c\u6210\u8bc1\u636e\u878d\u5408\u3002")
    return {
        "settings": settings,
        "profile": profile,
        "prefill": prefill,
        "raw_text": raw_text,
        "active_session_id": resolved_session.session_id if resolved_session else "",
        "submission": submission,
        "planner_image_payloads": planner_image_payloads,
        "report_requested": report_requested,
        "decider_requested": decider_requested,
        "executor_requested": executor_requested,
        "planner_requested": planner_requested,
        "auto_requested": auto_requested,
        "plan_bundle": plan_bundle,
        "execution_bundle": execution_bundle,
        "decision_bundle": decision_bundle,
    }


def _persist_case_result(
    username: str,
    *,
    submission: CaseSubmission,
    result: EngineResult,
    raw_text: str,
    active_session_id: str = "",
) -> dict[str, Any]:
    sessions = load_sessions(username)
    active_session = next((session for session in sessions if session.session_id == active_session_id), None) if active_session_id else None
    if active_session and not active_session.session_id.startswith("history-"):
        turn_timestamp = QueryHistoryItem.from_result(submission, result).timestamp
        active_session.timestamp = turn_timestamp
        active_session.title = result.title
        active_session.department = submission.department
        active_session.output_style = submission.output_style
        active_session.summary = result.executive_summary
        active_session.consensus_score = result.consensus_score
        active_session.submission = submission
        active_session.result = result
        active_session.context_submission = submission
        active_session.turns.append(
            SessionTurn(
                turn_id=uuid4().hex[:12],
                timestamp=turn_timestamp,
                user_input=raw_text or submission.case_summary,
                submission=submission,
                result=result,
            )
        )
        session = active_session
        sessions = [session] + [item for item in sessions if item.session_id != session.session_id]
    else:
        session = CaseSessionRecord.from_result(
            uuid4().hex[:12],
            submission,
            result,
            user_input=raw_text or submission.case_summary,
            turn_id=uuid4().hex[:12],
        )
        sessions = [session] + sessions

    history_item = QueryHistoryItem(
        timestamp=session.timestamp,
        title=session.title,
        department=session.department,
        output_style=session.output_style,
        summary=session.summary,
        consensus_score=session.consensus_score,
    )
    history = [history_item] + load_history(username)
    save_sessions(username, sessions)
    save_history(username, history)
    return {
        "session": serialize_session(session),
        "result": asdict(result),
        "submission": asdict(submission),
        "history": [serialize_history_item(item, f"history-{index}") for index, item in enumerate(history, start=1)],
        "sessions": [serialize_session(item, include_details=False) for item in sessions],
    }


def _serialize_executor_job(job: dict[str, Any]) -> dict[str, Any]:
    return {
        "job_id": str(job.get("job_id", "")),
        "status": str(job.get("status", "")),
        "stage": str(job.get("stage", "")),
        "created_at": str(job.get("created_at", "")),
        "updated_at": str(job.get("updated_at", "")),
        "active_step_id": job.get("active_step_id"),
        "failed_step_id": job.get("failed_step_id"),
        "step_count": int(job.get("step_count", 0)),
        "completed_step_ids": [int(item) for item in job.get("completed_step_ids", [])],
        "plan_display_steps": deepcopy(job.get("plan_display_steps", [])),
        "execution_records": deepcopy(job.get("execution_records", [])),
        "error_message": str(job.get("error_message", "")),
        "session": deepcopy(job.get("session")),
        "sessions": deepcopy(job.get("sessions", [])),
    }


def _update_executor_job(job_id: str, **changes: Any) -> dict[str, Any] | None:
    with EXECUTOR_JOBS_LOCK:
        job = EXECUTOR_JOBS.get(job_id)
        if job is None:
            return None
        for key, value in changes.items():
            job[key] = deepcopy(value)
        job["updated_at"] = _timestamp_now()
        return deepcopy(job)


def _executor_progress_callback(job_id: str):
    def callback(event: dict[str, Any]) -> None:
        records = [dict(item) for item in event.get("records", []) if isinstance(item, dict)]
        _update_executor_job(
            job_id,
            status=str(event.get("status") or "running"),
            stage=str(event.get("stage") or "running"),
            active_step_id=event.get("active_step_id"),
            failed_step_id=event.get("failed_step_id"),
            completed_step_ids=[int(item.get("step_id") or 0) for item in records if int(item.get("step_id") or 0)],
            execution_records=records,
            plan_display_steps=list(event.get("plan_display_steps") or []),
        )

    return callback


def _run_executor_job(job_id: str, username: str, prepared: dict[str, Any]) -> None:
    try:
        result = run_executor_case(
            submission=prepared["submission"],
            profile=prepared["profile"],
            settings=prepared["settings"],
            image_payloads=prepared["planner_image_payloads"],
            plan_bundle=prepared["plan_bundle"],
            progress_callback=_executor_progress_callback(job_id),
        )
        response = _persist_case_result(
            username,
            submission=prepared["submission"],
            result=result,
            raw_text=prepared["raw_text"],
            active_session_id=prepared["active_session_id"],
        )
        _update_executor_job(
            job_id,
            status="completed",
            stage="completed",
            active_step_id=None,
            failed_step_id=None,
            completed_step_ids=[int(item.get("step_id") or 0) for item in result.execution_records if int(item.get("step_id") or 0)],
            execution_records=result.execution_records,
            session=response["session"],
            sessions=response["sessions"],
            error_message="",
        )
    except Exception as exc:
        _update_executor_job(
            job_id,
            status="failed",
            stage="failed",
            active_step_id=None,
            error_message=str(exc),
        )


def create_executor_job(username: str, payload: dict[str, Any]) -> dict[str, Any]:
    prepared = _prepare_case_request(username, payload)
    if not prepared["executor_requested"]:
        raise ValueError("Executor job endpoint requires an @Executor request.")
    created_at = _timestamp_now()
    job_id = uuid4().hex[:12]
    initial_job = {
        "job_id": job_id,
        "username": username,
        "status": "queued",
        "stage": "queued",
        "created_at": created_at,
        "updated_at": created_at,
        "active_step_id": None,
        "failed_step_id": None,
        "step_count": len(list((prepared["plan_bundle"] or {}).get("steps") or [])),
        "completed_step_ids": [],
        "plan_display_steps": list((prepared["plan_bundle"] or {}).get("display_steps") or []),
        "execution_records": [],
        "error_message": "",
        "session": None,
        "sessions": [],
    }
    with EXECUTOR_JOBS_LOCK:
        EXECUTOR_JOBS[job_id] = initial_job
    worker = threading.Thread(
        target=_run_executor_job,
        args=(job_id, username, prepared),
        daemon=True,
        name=f"executor-job-{job_id}",
    )
    worker.start()
    return _serialize_executor_job(initial_job)


def get_executor_job(username: str, job_id: str) -> dict[str, Any] | None:
    with EXECUTOR_JOBS_LOCK:
        job = EXECUTOR_JOBS.get(job_id)
        if job is None or str(job.get("username")) != username:
            return None
        return _serialize_executor_job(job)


def _planner_bundle_from_result(result: EngineResult) -> dict[str, Any]:
    trace = result.agent_trace[0] if result.agent_trace else {}
    return {
        "steps": list(result.plan_steps or []),
        "display_steps": list(result.plan_display_steps or []),
        "references": list(result.references or []),
        "provider": result.serving_provider,
        "model": result.serving_model,
        "note": str(trace.get("note") or "Loaded the existing planner-generated execution plan from context."),
    }


def _executor_bundle_from_result(result: EngineResult) -> dict[str, Any]:
    trace = result.agent_trace[-1] if result.agent_trace else {}
    return {
        "records": list(result.execution_records or []),
        "plan_steps": list(result.plan_steps or []),
        "plan_display_steps": list(result.plan_display_steps or []),
        "references": list(result.references or []),
        "provider": result.serving_provider,
        "model": result.serving_model,
        "note": str(trace.get("note") or "Loaded the existing executor evidence from context."),
    }


def _decider_bundle_from_result(result: EngineResult) -> dict[str, Any]:
    try:
        decision = json.loads(result.raw_provider_payload or "{}")
    except json.JSONDecodeError:
        decision = {}
    trace = result.agent_trace[-1] if result.agent_trace else {}
    return {
        "decision": decision,
        "provider": result.serving_provider,
        "model": result.serving_model,
        "note": str(trace.get("note") or "Loaded the existing decider decision from context."),
    }


def _execution_evidence_ids(execution_bundle: dict[str, Any]) -> list[str]:
    evidence_ids: list[str] = []
    for record in execution_bundle.get("records") or []:
        if not isinstance(record, dict):
            continue
        step_id = int(record.get("step_id") or 0)
        if step_id > 0:
            evidence_ids.append(f"E{step_id}")
    return sorted(set(evidence_ids), key=lambda value: int(value[1:]) if value[1:].isdigit() else 0)


def _serialize_auto_job(job: dict[str, Any], *, include_details: bool = True) -> dict[str, Any]:
    payload = {
        "job_id": str(job.get("job_id", "")),
        "status": str(job.get("status", "")),
        "stage": str(job.get("stage", "")),
        "active_mode": str(job.get("active_mode", "")),
        "created_at": str(job.get("created_at", "")),
        "updated_at": str(job.get("updated_at", "")),
        "active_step_id": job.get("active_step_id"),
        "failed_stage": str(job.get("failed_stage", "")),
        "failed_step_id": job.get("failed_step_id"),
        "step_count": int(job.get("step_count", 0)),
        "completed_step_ids": [int(item) for item in job.get("completed_step_ids", [])],
        "completed_modes": [str(item) for item in job.get("completed_modes", []) if str(item)],
        "stream_stage": str(job.get("stream_stage", "")),
        "stream_label": str(job.get("stream_label", "")),
        "stream_preview": str(job.get("stream_preview", "")),
        "stream_event_count": int(job.get("stream_event_count", 0)),
        "error_message": str(job.get("error_message", "")),
    }
    if include_details:
        payload.update(
            {
                "plan_display_steps": deepcopy(job.get("plan_display_steps", [])),
                "execution_records": deepcopy(job.get("execution_records", [])),
                "session": deepcopy(job.get("session")),
                "sessions": deepcopy(job.get("sessions", [])),
            }
        )
    return payload


def _update_auto_job(job_id: str, **changes: Any) -> dict[str, Any] | None:
    with AUTO_JOBS_LOCK:
        job = AUTO_JOBS.get(job_id)
        if job is None:
            return None
        for key, value in changes.items():
            job[key] = deepcopy(value)
        job["updated_at"] = _timestamp_now()
        updated = deepcopy(job)
    _broadcast_auto_job(_serialize_auto_job(updated, include_details=False))
    return updated


def _broadcast_auto_job(job_snapshot: dict[str, Any]) -> None:
    job_id = str(job_snapshot.get("job_id") or "")
    if not job_id:
        return
    with AUTO_JOB_SUBSCRIBERS_LOCK:
        listeners = list(AUTO_JOB_SUBSCRIBERS.get(job_id, []))
    for listener in listeners:
        listener.put(deepcopy(job_snapshot))


def _auto_executor_progress_callback(job_id: str):
    def callback(event: dict[str, Any]) -> None:
        records = [dict(item) for item in event.get("records", []) if isinstance(item, dict)]
        _update_auto_job(
            job_id,
            status="running",
            stage="executor",
            active_mode="executor",
            active_step_id=event.get("active_step_id"),
            failed_step_id=event.get("failed_step_id"),
            step_count=max(int(len(list(event.get("plan_display_steps") or []))), int(len(list(event.get("records") or [])))),
            completed_step_ids=[int(item.get("step_id") or 0) for item in records if int(item.get("step_id") or 0)],
            plan_display_steps=list(event.get("plan_display_steps") or []),
            execution_records=records,
        )

    return callback


def _append_auto_model_stream(job_id: str, *, stage: str, label: str, delta: str) -> None:
    if not delta:
        return
    with AUTO_JOBS_LOCK:
        job = AUTO_JOBS.get(job_id)
        if job is None:
            return
        preview = f"{job.get('stream_preview') or ''}{delta}"
        job["stream_stage"] = stage
        job["stream_label"] = label
        job["stream_preview"] = preview[-1200:]
        job["stream_event_count"] = int(job.get("stream_event_count") or 0) + 1
        job["updated_at"] = _timestamp_now()
        snapshot = _serialize_auto_job(job, include_details=False)
    _broadcast_auto_job(snapshot)


def _auto_model_stream_callback(job_id: str, *, stage: str, label: str):
    buffer: list[str] = []
    last_emit_at = 0.0
    min_chars = 120
    min_interval_s = 0.5

    def flush() -> None:
        nonlocal last_emit_at
        if not buffer:
            return
        text = "".join(buffer)
        buffer.clear()
        last_emit_at = time.monotonic()
        _append_auto_model_stream(job_id, stage=stage, label=label, delta=text)

    def callback(event: dict[str, Any]) -> None:
        delta = str(event.get("delta") or "")
        if delta:
            buffer.append(delta)
        now = time.monotonic()
        if event.get("done") or len("".join(buffer)) >= min_chars or now - last_emit_at >= min_interval_s:
            flush()

    return callback


def _run_auto_job(job_id: str, username: str, prepared: dict[str, Any]) -> None:
    active_session_id = str(prepared.get("active_session_id") or "")
    completed_modes: list[str] = []
    current_mode = ""
    submission = prepared["submission"]
    profile = prepared["profile"]
    settings = prepared["settings"]
    planner_image_payloads = prepared["planner_image_payloads"]
    raw_text = prepared["raw_text"] or "@Auto"
    try:
        current_mode = "planner"
        _update_auto_job(job_id, status="running", stage="planner", active_mode="planner")
        planner_result = run_planner_case(
            submission=submission,
            profile=profile,
            settings=settings,
            image_payloads=planner_image_payloads,
            stream_callback=_auto_model_stream_callback(job_id, stage="planner", label="@Planner"),
        )
        planner_response = _persist_case_result(
            username,
            submission=submission,
            result=planner_result,
            raw_text=raw_text,
            active_session_id=active_session_id,
        )
        active_session_id = str(planner_response["session"]["session_id"])
        completed_modes.append("planner")
        plan_bundle = _planner_bundle_from_result(planner_result)
        _update_auto_job(
            job_id,
            stage="planner",
            active_mode="planner",
            completed_modes=completed_modes,
            plan_display_steps=list(planner_result.plan_display_steps or []),
            step_count=len(list(planner_result.plan_display_steps or [])),
            session=planner_response["session"],
            sessions=planner_response["sessions"],
        )

        current_mode = "executor"
        _update_auto_job(job_id, status="running", stage="executor", active_mode="executor")
        executor_result = run_executor_case(
            submission=submission,
            profile=profile,
            settings=settings,
            image_payloads=planner_image_payloads,
            plan_bundle=plan_bundle,
            progress_callback=_auto_executor_progress_callback(job_id),
            stream_callback=_auto_model_stream_callback(job_id, stage="executor", label="@Executor"),
        )
        executor_response = _persist_case_result(
            username,
            submission=submission,
            result=executor_result,
            raw_text="@Auto / @Executor",
            active_session_id=active_session_id,
        )
        active_session_id = str(executor_response["session"]["session_id"])
        completed_modes.append("executor")
        execution_bundle = _executor_bundle_from_result(executor_result)
        _update_auto_job(
            job_id,
            stage="executor",
            active_mode="executor",
            completed_modes=completed_modes,
            step_count=len(list(executor_result.plan_display_steps or [])),
            completed_step_ids=[int(item.get("step_id") or 0) for item in executor_result.execution_records if int(item.get("step_id") or 0)],
            execution_records=list(executor_result.execution_records or []),
            plan_display_steps=list(executor_result.plan_display_steps or []),
            session=executor_response["session"],
            sessions=executor_response["sessions"],
        )

        current_mode = "decider"
        _update_auto_job(job_id, status="running", stage="decider", active_mode="decider", active_step_id=None)
        decider_result = run_decider_case(
            submission=submission,
            profile=profile,
            settings=settings,
            execution_bundle=execution_bundle,
            stream_callback=_auto_model_stream_callback(job_id, stage="decider", label="@Decider"),
        )
        decider_response = _persist_case_result(
            username,
            submission=submission,
            result=decider_result,
            raw_text="@Auto / @Decider",
            active_session_id=active_session_id,
        )
        active_session_id = str(decider_response["session"]["session_id"])
        completed_modes.append("decider")
        decision_bundle = _decider_bundle_from_result(decider_result)
        _update_auto_job(
            job_id,
            stage="decider",
            active_mode="decider",
            completed_modes=completed_modes,
            session=decider_response["session"],
            sessions=decider_response["sessions"],
        )

        current_mode = "report"
        _update_auto_job(job_id, status="running", stage="report", active_mode="report", active_step_id=None)
        report_result = run_report_case(
            submission=submission,
            profile=profile,
            settings=settings,
            execution_bundle=execution_bundle,
            decision_bundle=decision_bundle,
            stream_callback=_auto_model_stream_callback(job_id, stage="report", label="@Report"),
        )
        report_response = _persist_case_result(
            username,
            submission=submission,
            result=report_result,
            raw_text="@Auto / @Report",
            active_session_id=active_session_id,
        )
        completed_modes.append("report")
        _update_auto_job(
            job_id,
            status="completed",
            stage="completed",
            active_mode="",
            active_step_id=None,
            failed_stage="",
            failed_step_id=None,
            completed_modes=completed_modes,
            session=report_response["session"],
            sessions=report_response["sessions"],
            error_message="",
        )
    except Exception as exc:
        _update_auto_job(
            job_id,
            status="failed",
            stage="failed",
            active_step_id=None,
            failed_stage=current_mode,
            error_message=str(exc),
        )


def create_auto_job(username: str, payload: dict[str, Any]) -> dict[str, Any]:
    prepared = _prepare_case_request(username, payload)
    if not prepared["auto_requested"]:
        raise ValueError("Auto job endpoint requires an @Auto request.")
    created_at = _timestamp_now()
    job_id = uuid4().hex[:12]
    initial_job = {
        "job_id": job_id,
        "username": username,
        "status": "queued",
        "stage": "queued",
        "active_mode": "",
        "created_at": created_at,
        "updated_at": created_at,
        "active_step_id": None,
        "failed_stage": "",
        "failed_step_id": None,
        "step_count": 0,
        "completed_step_ids": [],
        "completed_modes": [],
        "plan_display_steps": [],
        "execution_records": [],
        "stream_stage": "",
        "stream_label": "",
        "stream_preview": "",
        "stream_event_count": 0,
        "error_message": "",
        "session": None,
        "sessions": [],
    }
    with AUTO_JOBS_LOCK:
        AUTO_JOBS[job_id] = initial_job
    worker = threading.Thread(
        target=_run_auto_job,
        args=(job_id, username, prepared),
        daemon=True,
        name=f"auto-job-{job_id}",
    )
    worker.start()
    return _serialize_auto_job(initial_job)


def get_auto_job(username: str, job_id: str, *, include_details: bool = True) -> dict[str, Any] | None:
    with AUTO_JOBS_LOCK:
        job = AUTO_JOBS.get(job_id)
        if job is None or str(job.get("username")) != username:
            return None
        return _serialize_auto_job(job, include_details=include_details)


def subscribe_auto_job(username: str, job_id: str) -> tuple[dict[str, Any] | None, queue.Queue[dict[str, Any]] | None]:
    listener: queue.Queue[dict[str, Any]] = queue.Queue()
    with AUTO_JOBS_LOCK:
        job = AUTO_JOBS.get(job_id)
        if job is None or str(job.get("username")) != username:
            return None, None
        snapshot = _serialize_auto_job(job, include_details=False)
    with AUTO_JOB_SUBSCRIBERS_LOCK:
        AUTO_JOB_SUBSCRIBERS.setdefault(job_id, []).append(listener)
    with AUTO_JOBS_LOCK:
        latest = AUTO_JOBS.get(job_id)
        if latest is not None and str(latest.get("username")) == username:
            latest_snapshot = _serialize_auto_job(latest, include_details=False)
            if latest_snapshot.get("updated_at") != snapshot.get("updated_at"):
                listener.put(deepcopy(latest_snapshot))
            if latest_snapshot.get("status") in {"completed", "failed"}:
                snapshot = latest_snapshot
    return snapshot, listener


def unsubscribe_auto_job(job_id: str, listener: queue.Queue[dict[str, Any]]) -> None:
    with AUTO_JOB_SUBSCRIBERS_LOCK:
        listeners = AUTO_JOB_SUBSCRIBERS.get(job_id)
        if not listeners:
            return
        AUTO_JOB_SUBSCRIBERS[job_id] = [item for item in listeners if item is not listener]
        if not AUTO_JOB_SUBSCRIBERS[job_id]:
            AUTO_JOB_SUBSCRIBERS.pop(job_id, None)


def _find_session_and_turn(
    username: str,
    *,
    session_id: str,
    turn_id: str = "",
) -> tuple[list[CaseSessionRecord], CaseSessionRecord, SessionTurn | None]:
    sessions = load_sessions(username)
    session = next((item for item in sessions if item.session_id == session_id), None)
    if session is None:
        raise ValueError("Session not found.")
    turn = next((item for item in session.turns if item.turn_id == turn_id), None) if turn_id else None
    return sessions, session, turn


def submit_turn_approval(username: str, session_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    turn_id = str(payload.get("turn_id", "")).strip()
    action = str(payload.get("action", "")).strip().lower()
    note = str(payload.get("note", "")).strip()
    if action not in {"approved", "revision_requested"}:
        raise ValueError("Approval action must be approved or revision_requested.")
    sessions, session, turn = _find_session_and_turn(username, session_id=session_id, turn_id=turn_id)
    if turn is None:
        raise ValueError("Turn not found.")
    session.doctor_approvals.append(
        DoctorApproval(
            approval_id=uuid4().hex[:12],
            turn_id=turn.turn_id,
            execution_mode=turn.result.execution_mode,
            action=action,
            note=note,
            created_at=_timestamp_now(),
        )
    )
    save_sessions(username, sessions)
    return {"session": serialize_session(session)}


def submit_case_feedback(username: str, session_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    sessions, session, _ = _find_session_and_turn(username, session_id=session_id)
    executor_bundle = _latest_executor_bundle(session)
    if executor_bundle is None:
        raise ValueError("Case feedback requires completed Executor evidence.")
    if _latest_decider_bundle(session) is None:
        raise ValueError("Case feedback requires a completed Decider decision.")
    report_turn_exists = any(turn.result.execution_mode == "report" for turn in session.turns)
    if not report_turn_exists:
        raise ValueError("Case feedback requires a completed report.")
    diagnosis_rating = int(payload.get("diagnosis_rating", 0))
    report_rating = int(payload.get("report_rating", 0))
    if diagnosis_rating < 1 or diagnosis_rating > 5:
        raise ValueError("Diagnosis rating must be between 1 and 5.")
    if report_rating < 1 or report_rating > 5:
        raise ValueError("Report rating must be between 1 and 5.")
    evidence_ids = _execution_evidence_ids(executor_bundle)
    evidence_payload = payload.get("evidence_ratings")
    if not isinstance(evidence_payload, list):
        raise ValueError("Evidence ratings must be a list.")
    ratings_by_id: dict[str, int] = {}
    for item in evidence_payload:
        if not isinstance(item, dict):
            raise ValueError("Each evidence rating must be an object.")
        evidence_id = str(item.get("evidence_id", "")).strip()
        rating = int(item.get("rating", 0))
        if evidence_id not in evidence_ids:
            raise ValueError(f"Unknown evidence id in feedback: {evidence_id or 'empty'}.")
        if rating < 1 or rating > 5:
            raise ValueError(f"Evidence rating for {evidence_id} must be between 1 and 5.")
        ratings_by_id[evidence_id] = rating
    missing = [item for item in evidence_ids if item not in ratings_by_id]
    if missing:
        raise ValueError(f"Missing evidence ratings: {', '.join(missing)}")
    session.case_feedback = CaseFeedback(
        submitted_at=_timestamp_now(),
        diagnosis_rating=diagnosis_rating,
        report_rating=report_rating,
        evidence_ratings=[EvidenceFeedback(evidence_id=item, rating=ratings_by_id[item]) for item in evidence_ids],
        comment=str(payload.get("comment", "")).strip(),
    )
    save_sessions(username, sessions)
    return {"session": serialize_session(session)}


def submit_case(username: str, payload: dict[str, Any]) -> dict[str, Any]:
    prepared = _prepare_case_request(username, payload)
    submission = prepared["submission"]
    if prepared["report_requested"]:
        result = run_report_case(
            submission=submission,
            profile=prepared["profile"],
            settings=prepared["settings"],
            execution_bundle=prepared["execution_bundle"],
            decision_bundle=prepared["decision_bundle"],
        )
    elif prepared["decider_requested"]:
        result = run_decider_case(
            submission=submission,
            profile=prepared["profile"],
            settings=prepared["settings"],
            execution_bundle=prepared["execution_bundle"],
        )
    elif prepared["executor_requested"]:
        result = run_executor_case(
            submission=submission,
            profile=prepared["profile"],
            settings=prepared["settings"],
            image_payloads=prepared["planner_image_payloads"],
            plan_bundle=prepared["plan_bundle"],
        )
    elif prepared["planner_requested"]:
        result = run_planner_case(
            submission=submission,
            profile=prepared["profile"],
            settings=prepared["settings"],
            image_payloads=prepared["planner_image_payloads"],
        )
    else:
        result = (
            _run_single_model_provider_case(submission=submission, profile=prepared["profile"], settings=prepared["settings"])
            if submission.single_model_test
            else run_multiagent_case(submission=submission, profile=prepared["profile"], settings=prepared["settings"])
        )
    response = _persist_case_result(
        username,
        submission=submission,
        result=result,
        raw_text=prepared["raw_text"],
        active_session_id=prepared["active_session_id"],
    )
    response["prefill"] = asdict(prepared["prefill"])
    return response


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
        payload["context_submission"] = asdict(session.context_submission) if session.context_submission else None
        payload["turns"] = [asdict(turn) for turn in session.turns]
        payload["doctor_approvals"] = [asdict(item) for item in session.doctor_approvals]
        payload["case_feedback"] = asdict(session.case_feedback) if session.case_feedback else None
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
