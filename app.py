from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

import streamlit as st

from rare_agents.engine import run_multiagent_case
from rare_agents.intake_parser import IntakePrefill, parse_ehr_intake
from rare_agents.models import (
    APIProviderConfig,
    AgentRoleConfig,
    AppProfile,
    CaseSubmission,
    DepartmentOption,
    OrchestrationMode,
    QueryHistoryItem,
    SystemSettings,
    default_profile,
    default_settings,
)
from rare_agents.storage import load_json, save_json
from rare_agents.style import inject_css


ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
PROFILE_PATH = DATA_DIR / "profile.json"
SETTINGS_PATH = DATA_DIR / "settings.json"
HISTORY_PATH = DATA_DIR / "history.json"
WORKSPACE_VIEWS = ["Control Room", "Settings", "Profile", "History"]
DEPARTMENTS = [item.value for item in DepartmentOption]
TOPOLOGIES = [mode.value for mode in OrchestrationMode]
OUTPUT_STYLES = ["Diagnostic", "Surgical / Treatment Plan"]
URGENCY_OPTIONS = ["Routine", "Priority", "Emergency"]
SEX_OPTIONS = ["Unknown", "Female", "Male", "Other"]
INSURANCE_OPTIONS = ["Resident insurance", "Employee insurance", "Self-pay / uninsured", "Commercial"]
WORKSPACE_VIEW_LABELS = {
    "Control Room": "智能控制台",
    "Settings": "系统设置",
    "Profile": "用户档案",
    "History": "历史记录",
}
DEPARTMENT_LABELS_MAP = {
    DepartmentOption.ORTHOPEDICS.value: "骨科 / 骨病",
    DepartmentOption.NEUROLOGY.value: "神经内科 / 神经系统",
    DepartmentOption.PEDIATRICS.value: "儿科",
    DepartmentOption.ICU.value: "重症医学科 ICU",
    DepartmentOption.EMERGENCY.value: "急诊 / A&E",
    DepartmentOption.PULMONARY.value: "呼吸科 / 肺部",
    DepartmentOption.GENETICS.value: "医学遗传",
    DepartmentOption.MULTIDISCIPLINARY.value: "多学科 MDT",
}
TOPOLOGY_LABELS_MAP = {
    OrchestrationMode.SYMMETRIC.value: "对称模式",
    OrchestrationMode.ASYMMETRIC.value: "非对称模式",
}
OUTPUT_STYLE_LABELS_MAP = {
    "Diagnostic": "诊断评估",
    "Surgical / Treatment Plan": "手术 / 治疗方案",
}
URGENCY_LABELS_MAP = {
    "Routine": "常规",
    "Priority": "优先",
    "Emergency": "紧急",
}
SEX_LABELS_MAP = {
    "Unknown": "未知",
    "Female": "女",
    "Male": "男",
    "Other": "其他",
}
INSURANCE_LABELS_MAP = {
    "Resident insurance": "居民医保",
    "Employee insurance": "职工医保",
    "Self-pay / uninsured": "自费 / 未参保",
    "Commercial": "商业保险",
}
PROVIDER_LABELS_MAP = {
    "DeepSeek": "DeepSeek",
    "GLM / BigModel": "GLM / BigModel",
    "Kimi": "Kimi",
    "OpenAI Compatible": "OpenAI 兼容接口",
    "Custom / Hospital Gateway": "自定义 / 医院网关",
}
ROLE_TEMPLATE_LABELS_MAP = {
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
ROLE_TEMPLATES = [
    "Orchestrator",
    "Planner",
    "Generator",
    "Fact Checker",
    "Guideline Retriever",
    "Web Search",
    "Imaging Reader",
    "Cost Estimator",
]
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


def ui_label(value: str, mapping: dict[str, str]) -> str:
    return mapping.get(value, value)


def migrate_profile_data(data: dict[str, str]) -> dict[str, str]:
    migrated = dict(data)
    for key in ["user_name", "title", "hospital_name", "specialty_focus", "locale", "patient_population"]:
        value = migrated.get(key)
        if value in PROFILE_MIGRATIONS:
            migrated[key] = PROFILE_MIGRATIONS[value]
    return migrated


def migrate_role_specs(roles: list[AgentRoleConfig]) -> list[AgentRoleConfig]:
    migrated_roles: list[AgentRoleConfig] = []
    for role in roles:
        migrated_roles.append(
            AgentRoleConfig(
                role_name=role.role_name,
                role_spec=ROLE_SPEC_MIGRATIONS.get(role.role_spec, role.role_spec),
                provider_name=role.provider_name,
                agent_count=role.agent_count,
            )
        )
    return migrated_roles


def ensure_storage() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not PROFILE_PATH.exists():
        save_json(PROFILE_PATH, asdict(default_profile()))
    if not SETTINGS_PATH.exists():
        save_json(SETTINGS_PATH, asdict(default_settings()))
    if not HISTORY_PATH.exists():
        save_json(HISTORY_PATH, [])


def load_profile() -> AppProfile:
    data = load_json(PROFILE_PATH, asdict(default_profile()))
    data = migrate_profile_data(data)
    return AppProfile(**data)


def load_settings() -> SystemSettings:
    data = load_json(SETTINGS_PATH, asdict(default_settings()))
    providers = [APIProviderConfig(**item) for item in data.get("api_providers", [])]
    roles = [AgentRoleConfig(**item) for item in data.get("agent_roles", [])]
    roles = migrate_role_specs(roles)
    return SystemSettings(
        orchestration_mode=data.get("orchestration_mode", OrchestrationMode.ASYMMETRIC.value),
        default_department=data.get("default_department", DepartmentOption.PEDIATRICS.value),
        consensus_threshold=float(data.get("consensus_threshold", 0.82)),
        max_rounds=int(data.get("max_rounds", 3)),
        show_diagnostics=bool(data.get("show_diagnostics", True)),
        api_providers=providers,
        agent_roles=roles,
    )


def load_history() -> list[QueryHistoryItem]:
    data = load_json(HISTORY_PATH, [])
    return [QueryHistoryItem(**item) for item in data]


def save_profile(profile: AppProfile) -> None:
    save_json(PROFILE_PATH, asdict(profile))


def save_settings(settings: SystemSettings) -> None:
    payload = asdict(settings)
    save_json(SETTINGS_PATH, payload)


def save_history(history: list[QueryHistoryItem]) -> None:
    save_json(HISTORY_PATH, [asdict(item) for item in history])


def init_state() -> None:
    ensure_storage()
    if "profile" not in st.session_state:
        st.session_state.profile = load_profile()
    if "settings" not in st.session_state:
        st.session_state.settings = load_settings()
    if "history" not in st.session_state:
        st.session_state.history = load_history()
    if "last_result" not in st.session_state:
        st.session_state.last_result = None
    if "active_view" not in st.session_state:
        st.session_state.active_view = "Control Room"


def render_sidebar() -> None:
    with st.sidebar:
        st.markdown(
            """
            <div class="sidebar-brand">
                <div class="brand-kicker">HKU-SZH</div>
                <div class="brand-title">multiagent for rare</div>
                <div class="brand-subtitle">SZ Clin Center for Rare Dis</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.session_state.active_view = st.radio(
            "工作区",
            WORKSPACE_VIEWS,
            index=WORKSPACE_VIEWS.index(st.session_state.active_view),
            format_func=lambda x: ui_label(x, WORKSPACE_VIEW_LABELS),
            label_visibility="collapsed",
        )
        st.markdown("---")
        st.caption("部署档案")
        st.markdown(
            f"""
            <div class="glass-card">
                <div><strong>{st.session_state.profile.hospital_name}</strong></div>
                <div>{ui_label(st.session_state.profile.department, DEPARTMENT_LABELS_MAP)}</div>
                <div>{st.session_state.profile.user_name} · {st.session_state.profile.title}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_header() -> None:
    st.markdown(
        """
        <section class="hero-shell hero-compact">
            <div class="hero-left">
                <div class="hero-kicker">罕见病智能协作中枢</div>
                <h1>临床智能控制台</h1>
                <p>
                    多模态接诊录入、智能体快速收敛、诊疗支持与临床级输出，
                    在一个连续工作流中完成。
                </p>
            </div>
            <div class="hero-right">
                <div class="hero-badge">对称 / 非对称编排</div>
                <div class="hero-chip">中国指南 + 国际共识依据</div>
                <div class="hero-chip">透明收敛过程诊断窗</div>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_page_banner(active_view: str) -> None:
    st.markdown(
        f"""
        <section class="page-banner">
            <div class="page-banner-main">
                <div class="page-banner-kicker">HKU-SZH · SZ Clin Center for Rare Dis</div>
                <h1>港大医院 罕见病多智能体 诊疗系统</h1>
                <p>面向临床多学科协作的多模态罕见病智能诊疗演示平台</p>
            </div>
            <div class="page-banner-side">
                <div class="page-banner-view">{ui_label(active_view, WORKSPACE_VIEW_LABELS)}</div>
                <div class="page-banner-chip">multiagent for rare</div>
                <div class="page-banner-chip">顺滑对话式工作流</div>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_button_field_label(label: str) -> None:
    st.markdown(f'<div class="control-label">{label}</div>', unsafe_allow_html=True)


def render_metric_strip(settings: SystemSettings, history: list[QueryHistoryItem]) -> None:
    cols = st.columns(4)
    cols[0].metric("已配置接口", len(settings.api_providers))
    cols[1].metric("智能体数量", sum(role.agent_count for role in settings.agent_roles))
    cols[2].metric("一致性阈值", f"{settings.consensus_threshold:.0%}")
    cols[3].metric("历史查询", len(history))


def render_profile_view() -> None:
    st.subheader("首次使用档案")
    profile = st.session_state.profile
    with st.container(border=True):
        with st.form("profile_form"):
            c1, c2 = st.columns(2)
            user_name = c1.text_input("医生 / 用户姓名", profile.user_name)
            title = c2.text_input("职称", profile.title)
            c3, c4 = st.columns(2)
            hospital_name = c3.text_input("医院名称", profile.hospital_name)
            department = c4.selectbox(
                "所属科室",
                DEPARTMENTS,
                index=DEPARTMENTS.index(profile.department),
                format_func=lambda x: ui_label(x, DEPARTMENT_LABELS_MAP),
            )
            c5, c6 = st.columns(2)
            specialty = c5.text_input("专业方向", profile.specialty_focus)
            locale = c6.text_input("地区", profile.locale)
            patient_population = st.text_area("服务人群 / 备注", profile.patient_population, height=100)
            submitted = st.form_submit_button("保存档案", use_container_width=True)
            if submitted:
                st.session_state.profile = AppProfile(
                    user_name=user_name,
                    title=title,
                    hospital_name=hospital_name,
                    department=department,
                    specialty_focus=specialty,
                    locale=locale,
                    patient_population=patient_population,
                    first_run_complete=True,
                )
                save_profile(st.session_state.profile)
                st.success("档案已保存。")


def sync_settings_widget_defaults(settings: SystemSettings) -> None:
    st.session_state.setdefault("settings_topology", settings.orchestration_mode)
    st.session_state.setdefault("settings_default_department", settings.default_department)
    st.session_state.setdefault("settings_consensus_threshold", float(settings.consensus_threshold))
    st.session_state.setdefault("settings_max_rounds", int(settings.max_rounds))
    st.session_state.setdefault("settings_show_diagnostics", bool(settings.show_diagnostics))

    for idx, provider in enumerate(settings.api_providers):
        st.session_state.setdefault(f"provider_name_{idx}", provider.provider_name)
        st.session_state.setdefault(f"model_name_{idx}", provider.model_name)
        st.session_state.setdefault(f"endpoint_{idx}", provider.endpoint)
        st.session_state.setdefault(f"api_key_{idx}", provider.api_key)
        st.session_state.setdefault(f"agents_for_api_{idx}", int(provider.agents_for_api))
        st.session_state.setdefault(f"enabled_{idx}", bool(provider.enabled))

    for idx, role in enumerate(settings.agent_roles):
        st.session_state.setdefault(f"role_name_{idx}", role.role_name)
        st.session_state.setdefault(f"assigned_provider_{idx}", role.provider_name)
        st.session_state.setdefault(f"role_count_{idx}", int(role.agent_count))
        st.session_state.setdefault(f"role_spec_{idx}", role.role_spec)


def clear_removed_widget_state(prefixes: list[str], start_index: int, end_index: int) -> None:
    for idx in range(start_index, end_index):
        for prefix in prefixes:
            key = f"{prefix}_{idx}"
            if key in st.session_state:
                del st.session_state[key]


def ensure_choice_state(key: str, options: list[str], fallback: str | None = None) -> None:
    if not options:
        return
    preferred = fallback if fallback in options else options[0]
    current = st.session_state.get(key)
    if current not in options:
        st.session_state[key] = preferred


def collect_provider_configs(settings: SystemSettings) -> list[APIProviderConfig]:
    providers: list[APIProviderConfig] = []
    for idx in range(len(settings.api_providers)):
        providers.append(
            APIProviderConfig(
                provider_name=st.session_state.get(f"provider_name_{idx}", "DeepSeek"),
                model_name=st.session_state.get(f"model_name_{idx}", ""),
                endpoint=st.session_state.get(f"endpoint_{idx}", ""),
                api_key=st.session_state.get(f"api_key_{idx}", ""),
                agents_for_api=int(st.session_state.get(f"agents_for_api_{idx}", 0)),
                enabled=bool(st.session_state.get(f"enabled_{idx}", True)),
            )
        )
    return providers


def collect_role_configs(settings: SystemSettings) -> list[AgentRoleConfig]:
    roles: list[AgentRoleConfig] = []
    fallback_provider = "DeepSeek"
    for idx in range(len(settings.agent_roles)):
        roles.append(
            AgentRoleConfig(
                role_name=st.session_state.get(f"role_name_{idx}", "Orchestrator"),
                role_spec=st.session_state.get(f"role_spec_{idx}", ""),
                provider_name=st.session_state.get(f"assigned_provider_{idx}", fallback_provider),
                agent_count=int(st.session_state.get(f"role_count_{idx}", 1)),
            )
        )
    return roles


def render_provider_editor(settings: SystemSettings) -> list[APIProviderConfig]:
    st.markdown("### 接口配置矩阵")
    providers: list[APIProviderConfig] = []
    for idx, provider in enumerate(settings.api_providers):
        ensure_choice_state(
            f"provider_name_{idx}",
            list(PROVIDER_PRESETS.keys()),
            provider.provider_name,
        )
        with st.container(border=True):
            left, middle, right = st.columns([1.2, 1.2, 1.1])
            provider_name = left.selectbox(
                f"接口 {idx + 1}",
                list(PROVIDER_PRESETS.keys()),
                key=f"provider_name_{idx}",
                format_func=lambda x: ui_label(x, PROVIDER_LABELS_MAP),
            )
            model_name = middle.text_input("模型名称", key=f"model_name_{idx}")
            endpoint = right.text_input("接口地址", key=f"endpoint_{idx}")
            a, b, c, d = st.columns([1.2, 1.2, 1.2, 1])
            api_key = a.text_input("接口密钥 / Token", type="password", key=f"api_key_{idx}")
            with b:
                render_button_field_label("快捷操作")
            quick_paste = b.button("快速填入", key=f"quick_paste_{idx}", use_container_width=True)
            agents_for_api = c.number_input(
                "该接口智能体数",
                min_value=0,
                max_value=12,
                key=f"agents_for_api_{idx}",
            )
            enabled = d.toggle("启用", key=f"enabled_{idx}")

            if quick_paste and not endpoint:
                st.session_state[f"endpoint_{idx}"] = PROVIDER_PRESETS[provider_name]
                endpoint = st.session_state[f"endpoint_{idx}"]

            providers.append(
                APIProviderConfig(
                    provider_name=provider_name,
                    model_name=model_name,
                    endpoint=endpoint,
                    api_key=api_key,
                    agents_for_api=agents_for_api,
                    enabled=enabled,
                )
            )

    st.markdown('<div class="action-row-label">接口操作</div>', unsafe_allow_html=True)
    c1, c2 = st.columns([1, 1])
    if c1.button("新增接口", use_container_width=True):
        new_index = len(settings.api_providers)
        settings.api_providers.append(APIProviderConfig())
        st.session_state[f"provider_name_{new_index}"] = "DeepSeek"
        st.session_state[f"model_name_{new_index}"] = "deepseek-chat"
        st.session_state[f"endpoint_{new_index}"] = ""
        st.session_state[f"api_key_{new_index}"] = ""
        st.session_state[f"agents_for_api_{new_index}"] = 2
        st.session_state[f"enabled_{new_index}"] = True
        st.rerun()
    if c2.button("删除最后一个接口", use_container_width=True):
        if settings.api_providers:
            removed_index = len(settings.api_providers) - 1
            settings.api_providers.pop()
            clear_removed_widget_state(
                ["provider_name", "model_name", "endpoint", "api_key", "agents_for_api", "enabled"],
                removed_index,
                removed_index + 1,
            )
            st.rerun()
    return providers


def render_role_editor(settings: SystemSettings) -> list[AgentRoleConfig]:
    st.markdown("### 智能体角色工位")
    roles: list[AgentRoleConfig] = []
    provider_names = [provider.provider_name for provider in settings.api_providers] or ["DeepSeek"]
    for idx, role in enumerate(settings.agent_roles):
        ensure_choice_state(f"role_name_{idx}", ROLE_TEMPLATES, role.role_name)
        ensure_choice_state(f"assigned_provider_{idx}", provider_names, role.provider_name)
        with st.container(border=True):
            top_a, top_b, top_c = st.columns([1.1, 1.2, 0.8])
            role_name = top_a.selectbox(
                f"角色 {idx + 1}",
                ROLE_TEMPLATES,
                key=f"role_name_{idx}",
                format_func=lambda x: ui_label(x, ROLE_TEMPLATE_LABELS_MAP),
            )
            assigned_provider = top_b.selectbox(
                "绑定接口",
                provider_names,
                key=f"assigned_provider_{idx}",
                format_func=lambda x: ui_label(x, PROVIDER_LABELS_MAP),
            )
            agent_count = top_c.number_input(
                "该角色智能体数",
                min_value=1,
                max_value=12,
                key=f"role_count_{idx}",
            )
            role_spec = st.text_area(
                "角色说明",
                height=110,
                key=f"role_spec_{idx}",
            )
            roles.append(
                AgentRoleConfig(
                    role_name=role_name,
                    role_spec=role_spec,
                    provider_name=assigned_provider,
                    agent_count=agent_count,
                )
            )

    st.markdown('<div class="action-row-label">角色操作</div>', unsafe_allow_html=True)
    c1, c2 = st.columns([1, 1])
    if c1.button("新增角色", use_container_width=True):
        provider_name = settings.api_providers[0].provider_name if settings.api_providers else "DeepSeek"
        new_index = len(settings.agent_roles)
        settings.agent_roles.append(AgentRoleConfig(provider_name=provider_name))
        st.session_state[f"role_name_{new_index}"] = "Orchestrator"
        st.session_state[f"assigned_provider_{new_index}"] = provider_name
        st.session_state[f"role_count_{new_index}"] = 1
        st.session_state[f"role_spec_{new_index}"] = AgentRoleConfig(provider_name=provider_name).role_spec
        st.rerun()
    if c2.button("删除最后一个角色", use_container_width=True):
        if settings.agent_roles:
            removed_index = len(settings.agent_roles) - 1
            settings.agent_roles.pop()
            clear_removed_widget_state(
                ["role_name", "assigned_provider", "role_count", "role_spec"],
                removed_index,
                removed_index + 1,
            )
            st.rerun()
    return roles


def sync_case_widget_defaults(settings: SystemSettings) -> None:
    st.session_state.setdefault("ehr_paste_text", "")
    st.session_state.setdefault("case_department", settings.default_department)
    st.session_state.setdefault("case_output_style", OUTPUT_STYLES[0])
    st.session_state.setdefault("case_urgency", URGENCY_OPTIONS[0])
    st.session_state.setdefault("case_chief_complaint", "")
    st.session_state.setdefault("case_summary", "")
    st.session_state.setdefault("case_patient_age", "")
    st.session_state.setdefault("case_patient_sex", SEX_OPTIONS[0])
    st.session_state.setdefault("case_insurance_type", INSURANCE_OPTIONS[0])
    st.session_state.setdefault("case_show_process", bool(settings.show_diagnostics))

    ensure_choice_state("case_department", DEPARTMENTS, settings.default_department)
    ensure_choice_state("case_output_style", OUTPUT_STYLES, OUTPUT_STYLES[0])
    ensure_choice_state("case_urgency", URGENCY_OPTIONS, URGENCY_OPTIONS[0])
    ensure_choice_state("case_patient_sex", SEX_OPTIONS, SEX_OPTIONS[0])
    ensure_choice_state("case_insurance_type", INSURANCE_OPTIONS, INSURANCE_OPTIONS[0])


def apply_case_prefill(prefill: IntakePrefill, settings: SystemSettings) -> None:
    st.session_state["case_department"] = prefill.department or settings.default_department
    st.session_state["case_output_style"] = prefill.output_style or OUTPUT_STYLES[0]
    st.session_state["case_urgency"] = prefill.urgency or URGENCY_OPTIONS[0]
    st.session_state["case_chief_complaint"] = prefill.chief_complaint
    st.session_state["case_summary"] = prefill.case_summary
    st.session_state["case_patient_age"] = prefill.patient_age
    st.session_state["case_patient_sex"] = prefill.patient_sex or SEX_OPTIONS[0]
    st.session_state["case_insurance_type"] = prefill.insurance_type or INSURANCE_OPTIONS[0]


def reset_case_prefill(settings: SystemSettings) -> None:
    st.session_state["ehr_paste_text"] = ""
    st.session_state["case_department"] = settings.default_department
    st.session_state["case_output_style"] = OUTPUT_STYLES[0]
    st.session_state["case_urgency"] = URGENCY_OPTIONS[0]
    st.session_state["case_chief_complaint"] = ""
    st.session_state["case_summary"] = ""
    st.session_state["case_patient_age"] = ""
    st.session_state["case_patient_sex"] = SEX_OPTIONS[0]
    st.session_state["case_insurance_type"] = INSURANCE_OPTIONS[0]
    st.session_state["case_show_process"] = bool(settings.show_diagnostics)


def render_ehr_autofill_panel(settings: SystemSettings) -> None:
    st.markdown("### 病历智能粘贴")
    with st.container(border=True):
        st.caption(
            "请将电子病历段落、入院记录、出院小结或转诊说明直接粘贴到这里。"
            "系统会自动抽取关键信息并填入下方结构化接诊表单。"
        )
        st.text_area(
            "粘贴病历原文",
            key="ehr_paste_text",
            height=180,
            placeholder="在此粘贴长段病历文本，然后点击“自动填充接诊字段”。",
        )
        action_left, action_right = st.columns([1.2, 1])
        autofilled = False
        cleared = False
        if action_left.button("自动填充接诊字段", use_container_width=True):
            pasted_text = st.session_state.get("ehr_paste_text", "").strip()
            if pasted_text:
                prefill = parse_ehr_intake(pasted_text, settings.default_department)
                apply_case_prefill(prefill, settings)
                autofilled = True
            else:
                st.warning("请先粘贴病历文本，再点击“自动填充接诊字段”。")

        if action_right.button("清空已解析字段", use_container_width=True):
            reset_case_prefill(settings)
            cleared = True

        if autofilled:
            st.success(
                "系统已根据粘贴病历自动填入结构化接诊字段。"
                "请在提交前由临床医生复核并修正需要调整的内容。"
            )
        if cleared:
            st.info("已清空病历粘贴区及结构化接诊字段。")


def render_settings_view() -> None:
    st.subheader("系统设置")
    settings = st.session_state.settings
    sync_settings_widget_defaults(settings)
    ensure_choice_state("settings_topology", TOPOLOGIES, settings.orchestration_mode)
    ensure_choice_state("settings_default_department", DEPARTMENTS, settings.default_department)

    with st.container(border=True):
        c1, c2, c3, c4 = st.columns(4)
        c1.selectbox(
            "编排模式",
            TOPOLOGIES,
            key="settings_topology",
            format_func=lambda x: ui_label(x, TOPOLOGY_LABELS_MAP),
        )
        c2.selectbox(
            "默认科室",
            DEPARTMENTS,
            key="settings_default_department",
            format_func=lambda x: ui_label(x, DEPARTMENT_LABELS_MAP),
        )
        c3.slider(
            "一致性阈值",
            0.5,
            0.99,
            0.01,
            key="settings_consensus_threshold",
        )
        c4.slider(
            "最大收敛轮次",
            1,
            6,
            1,
            key="settings_max_rounds",
        )
        st.toggle(
            "默认显示收敛诊断窗",
            key="settings_show_diagnostics",
        )

    if st.session_state.get("settings_topology") == OrchestrationMode.SYMMETRIC.value:
        st.info(
            "对称模式会让不同角色在推理时共享同一启用中的模型接口，"
            "更利于快速收敛并保持输出口径统一。"
        )
    else:
        st.info(
            "非对称模式允许不同角色绑定不同模型接口，"
            "适合把规划、生成、核查、检索等能力分开配置。"
        )

    providers = render_provider_editor(settings)
    roles = render_role_editor(settings)

    st.markdown('<div class="action-row-label">配置操作</div>', unsafe_allow_html=True)
    save_col, reset_col = st.columns([1, 1])
    if save_col.button("保存设置", use_container_width=True):
        st.session_state.settings = SystemSettings(
            orchestration_mode=st.session_state.get("settings_topology", settings.orchestration_mode),
            default_department=st.session_state.get("settings_default_department", settings.default_department),
            consensus_threshold=float(st.session_state.get("settings_consensus_threshold", settings.consensus_threshold)),
            max_rounds=int(st.session_state.get("settings_max_rounds", settings.max_rounds)),
            show_diagnostics=bool(st.session_state.get("settings_show_diagnostics", settings.show_diagnostics)),
            api_providers=providers,
            agent_roles=roles,
        )
        save_settings(st.session_state.settings)
        st.success("系统设置已保存。")

    if reset_col.button("重新载入已保存设置", use_container_width=True):
        st.session_state.settings = load_settings()
        reloaded = st.session_state.settings
        st.session_state["settings_topology"] = reloaded.orchestration_mode
        st.session_state["settings_default_department"] = reloaded.default_department
        st.session_state["settings_consensus_threshold"] = float(reloaded.consensus_threshold)
        st.session_state["settings_max_rounds"] = int(reloaded.max_rounds)
        st.session_state["settings_show_diagnostics"] = bool(reloaded.show_diagnostics)
        clear_removed_widget_state(
            ["provider_name", "model_name", "endpoint", "api_key", "agents_for_api", "enabled"],
            len(reloaded.api_providers),
            20,
        )
        clear_removed_widget_state(
            ["role_name", "assigned_provider", "role_count", "role_spec"],
            len(reloaded.agent_roles),
            20,
        )
        st.rerun()


def collect_submission() -> CaseSubmission:
    settings = st.session_state.settings
    with st.container(border=True):
        with st.form("case_form"):
            c1, c2, c3 = st.columns([1.1, 1, 1])
            department = c1.selectbox(
                "科室",
                DEPARTMENTS,
                key="case_department",
                format_func=lambda x: ui_label(x, DEPARTMENT_LABELS_MAP),
            )
            output_style = c2.selectbox(
                "输出模式",
                OUTPUT_STYLES,
                key="case_output_style",
                format_func=lambda x: ui_label(x, OUTPUT_STYLE_LABELS_MAP),
            )
            urgency = c3.selectbox(
                "紧急程度",
                URGENCY_OPTIONS,
                key="case_urgency",
                format_func=lambda x: ui_label(x, URGENCY_LABELS_MAP),
            )

            chief_complaint = st.text_input("主诉", key="case_chief_complaint")
            case_summary = st.text_area(
                "临床摘要",
                key="case_summary",
                placeholder="病史、查体、影像/检验摘要、疑似罕见病路径、鉴别诊断要点等……",
                height=160,
            )

            p1, p2, p3 = st.columns(3)
            age = p1.text_input("年龄", key="case_patient_age")
            sex = p2.selectbox("性别", SEX_OPTIONS, key="case_patient_sex", format_func=lambda x: ui_label(x, SEX_LABELS_MAP))
            insurance = p3.selectbox(
                "医保类型",
                INSURANCE_OPTIONS,
                key="case_insurance_type",
                format_func=lambda x: ui_label(x, INSURANCE_LABELS_MAP),
            )

            multimodal_images = st.file_uploader(
                "上传影像 / 照片",
                type=["png", "jpg", "jpeg", "webp"],
                accept_multiple_files=True,
            )
            multimodal_docs = st.file_uploader(
                "上传报告 / PDF / DOCX",
                type=["pdf", "txt", "docx"],
                accept_multiple_files=True,
            )

            show_process = st.toggle("显示收敛过程诊断窗", key="case_show_process")
            submitted = st.form_submit_button("启动多智能体会诊", use_container_width=True)

    if not submitted:
        return CaseSubmission.empty()

    image_names = [file.name for file in multimodal_images or []]
    doc_names = [file.name for file in multimodal_docs or []]
    return CaseSubmission(
        department=department,
        output_style=output_style,
        urgency=urgency,
        chief_complaint=chief_complaint,
        case_summary=case_summary,
        patient_age=age,
        patient_sex=sex,
        insurance_type=insurance,
        uploaded_images=image_names,
        uploaded_docs=doc_names,
        show_process=show_process,
    )


def render_case_input() -> None:
    st.subheader("病例接诊")
    settings = st.session_state.settings
    sync_case_widget_defaults(settings)
    render_ehr_autofill_panel(settings)
    submission = collect_submission()
    if not submission.is_ready:
        st.info("请先录入病例信息，再启动多智能体会诊。")
        return

    result = run_multiagent_case(
        submission=submission,
        profile=st.session_state.profile,
        settings=settings,
    )
    st.session_state.last_result = result
    history_item = QueryHistoryItem.from_result(submission, result)
    st.session_state.history = [history_item] + st.session_state.history
    save_history(st.session_state.history)


def render_output_panel() -> None:
    result = st.session_state.last_result
    if not result:
        st.markdown(
            """
            <div class="glass-card result-placeholder">
                <h3>一致性输出结果</h3>
                <p>系统收敛后的诊断建议或治疗方案将在这里展示。</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    st.subheader("临床建议")
    st.markdown(
        f"""
        <div class="result-hero">
            <div>
                <div class="result-eyebrow">{ui_label(result.department, DEPARTMENT_LABELS_MAP)} · {ui_label(result.output_style, OUTPUT_STYLE_LABELS_MAP)}</div>
                <h2>{result.title}</h2>
                <p>{result.executive_summary}</p>
            </div>
            <div class="result-score">
                <div>一致性</div>
                <strong>{result.consensus_score:.0%}</strong>
                <span>{ui_label(result.topology_used, TOPOLOGY_LABELS_MAP)}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns([1.2, 1])
    with c1:
        st.markdown("### 专业结论")
        st.markdown(result.professional_answer)
        st.markdown("### 编码摘要")
        st.table(result.coding_table)
        st.markdown("### 方案与费用")
        st.table(result.cost_table)
    with c2:
        st.markdown("### 下一步建议")
        for step in result.next_steps:
            st.markdown(f"- {step}")
        st.markdown("### 指南与共识依据")
        for ref in result.references:
            st.markdown(f"- **{ref['type']}**：{ref['title']}（{ref['region']}）")
        st.markdown("### 安全提示")
        st.warning(result.safety_note)

    if result.show_process:
        st.markdown("### 收敛过程诊断")
        for round_item in result.rounds:
            st.markdown(
                f"""
                <div class="diag-card">
                    <div class="diag-header">
                        <strong>第 {round_item['round']} 轮</strong>
                        <span>对齐度 {round_item['alignment']:.0%}</span>
                    </div>
                    <div>{round_item['summary']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        st.markdown("### 智能体轨迹")
        for agent_note in result.agent_trace:
            st.markdown(
                f"""
                <div class="trace-card">
                    <div><strong>{ui_label(agent_note['role'], ROLE_TEMPLATE_LABELS_MAP)}</strong> · {ui_label(agent_note['provider'], PROVIDER_LABELS_MAP)}</div>
                    <div>{agent_note['note']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_history_view() -> None:
    st.subheader("历史查询")
    history = st.session_state.history
    if not history:
        st.info("暂时还没有历史查询记录。")
        return

    for item in history:
        with st.container(border=True):
            st.markdown(f"**{item.title}**")
            st.caption(
                f"{item.timestamp} · {ui_label(item.department, DEPARTMENT_LABELS_MAP)} · {ui_label(item.output_style, OUTPUT_STYLE_LABELS_MAP)}"
            )
            st.markdown(item.summary)
            st.markdown(f"一致性：`{item.consensus_score:.0%}`")


def render_control_room() -> None:
    render_header()
    render_metric_strip(st.session_state.settings, st.session_state.history)
    left, right = st.columns([1.1, 1])
    with left:
        render_case_input()
    with right:
        render_output_panel()


def bootstrap_first_run() -> None:
    profile = st.session_state.profile
    if profile.first_run_complete:
        return
    render_page_banner("Profile")
    st.info("请先完成首次使用档案设置，以便系统匹配医院部署场景。")
    render_profile_view()
    st.stop()


def main() -> None:
    st.set_page_config(
        page_title="港大医院罕见病多智能体诊疗系统",
        page_icon="M",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_css()
    init_state()
    render_sidebar()
    bootstrap_first_run()

    active_view = st.session_state.active_view
    render_page_banner(active_view)
    if active_view == "Control Room":
        render_control_room()
    elif active_view == "Settings":
        render_settings_view()
    elif active_view == "Profile":
        render_profile_view()
    else:
        render_history_view()

    st.markdown(
        """
        <div class="footer-note">
            当前为演示版本。若用于医院正式部署，请接入合规数据源、经过验证的模型接口、
            审计日志、权限控制与临床医生签署流程。
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
