from __future__ import annotations

import subprocess
from dataclasses import asdict
from datetime import datetime
from html import escape
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


# ── Paths ────────────────────────────────────────────────────────────────────

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
PROFILE_PATH = DATA_DIR / "profile.json"
SETTINGS_PATH = DATA_DIR / "settings.json"
HISTORY_PATH = DATA_DIR / "history.json"

# ── Constants ─────────────────────────────────────────────────────────────────

WORKSPACE_VIEWS = ["Control Room", "Settings", "Profile", "History"]
SETTINGS_SECTIONS = ["医生档案", "系统设置", "历史记录"]
SETTINGS_MENU = [
    ("账户", "医生档案", ":material/manage_accounts:", "管理当前医生档案与账户资料。"),
    ("API / 智能体", "系统设置", ":material/hub:", "配置接口、模型和多智能体工位。"),
    ("历史记录", "历史记录", ":material/history:", "回看既往病例与会诊记录。"),
]
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

# ── Label maps ────────────────────────────────────────────────────────────────

VIEW_LABELS = {
    "Control Room": "会诊工作台",
    "Settings": "系统设置",
    "Profile": "医生档案",
    "History": "历史记录",
}
VIEW_DESCRIPTIONS = {
    "Control Room": "左侧查看既往记录，中间处理病例，右上角打开多智能体诊断与快速设置。",
    "Settings": "管理模型接口、编排拓扑和多智能体角色配置。",
    "Profile": "维护当前医生档案，便于系统贴合真实部署场景。",
    "History": "查看既往会诊摘要与一致性结果，快速回看记录。",
}
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
SETTINGS_SECTION_META = {
    "医生档案": {
        "nav_label": "账户",
        "title": "账户设置",
        "copy": "维护医生档案、所属医院与专业方向，让会诊结果更贴近真实部署场景。",
    },
    "系统设置": {
        "nav_label": "API / 智能体",
        "title": "API 与智能体配置",
        "copy": "集中管理模型接口、编排拓扑、角色工位与默认会诊参数。",
    },
    "历史记录": {
        "nav_label": "历史记录",
        "title": "会诊历史",
        "copy": "查看既往诊疗记录与一致性摘要，支持快速回到工作区继续处理。",
    },
}

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

# ── Helpers ───────────────────────────────────────────────────────────────────

def lbl(value: str, mapping: dict) -> str:
    return mapping.get(value, value)


def migrate_profile(data: dict) -> dict:
    d = dict(data)
    for key in ["user_name", "title", "hospital_name", "specialty_focus", "locale", "patient_population"]:
        if d.get(key) in PROFILE_MIGRATIONS:
            d[key] = PROFILE_MIGRATIONS[d.get(key)]
    return d


def migrate_roles(roles: list[AgentRoleConfig]) -> list[AgentRoleConfig]:
    return [
        AgentRoleConfig(
            role_name=r.role_name,
            role_spec=ROLE_SPEC_MIGRATIONS.get(r.role_spec, r.role_spec),
            provider_name=r.provider_name,
            agent_count=r.agent_count,
        )
        for r in roles
    ]


# ── Storage ───────────────────────────────────────────────────────────────────

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
    return AppProfile(**migrate_profile(data))


def load_settings() -> SystemSettings:
    data = load_json(SETTINGS_PATH, asdict(default_settings()))
    providers = [APIProviderConfig(**p) for p in data.get("api_providers", [])]
    roles = [AgentRoleConfig(**r) for r in data.get("agent_roles", [])]
    roles = migrate_roles(roles)
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
    return [QueryHistoryItem(**item) for item in load_json(HISTORY_PATH, [])]


def save_profile(p: AppProfile) -> None:
    save_json(PROFILE_PATH, asdict(p))


def save_settings(s: SystemSettings) -> None:
    save_json(SETTINGS_PATH, asdict(s))


def save_history(h: list[QueryHistoryItem]) -> None:
    save_json(HISTORY_PATH, [asdict(i) for i in h])


def read_clipboard() -> str:
    try:
        r = subprocess.run(["pbpaste"], check=True, capture_output=True, text=True)
        return r.stdout.strip()
    except Exception:
        return ""


def paste_clipboard_into_input() -> None:
    text = read_clipboard()
    if text:
        existing = st.session_state.get("input_main", "").strip()
        st.session_state["input_main"] = f"{existing}\n\n{text}".strip() if existing else text
        st.rerun()
    else:
        st.warning("未读取到剪贴板内容")


# ── Session state ─────────────────────────────────────────────────────────────

def init_state() -> None:
    ensure_storage()
    defaults = {
        "profile": load_profile(),
        "settings": load_settings(),
        "history": load_history(),
        "active_view": "Control Room",
        "history_focus": None,
        "settings_workspace_section": SETTINGS_SECTIONS[0],
        # Conversation messages: list of dicts
        "messages": [],          # {"role": "user"|"assistant"|"system", "content": str, "meta": dict}
        "input_expanded": False,  # Whether input card is in expanded mode
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)


def latest_result():
    for message in reversed(st.session_state.messages):
        if message.get("role") == "assistant":
            return message.get("content")
    return None


def open_view(view: str) -> None:
    st.session_state.active_view = view
    if view != "History":
        st.session_state.history_focus = None


def open_settings_workspace(section: str = SETTINGS_SECTIONS[0]) -> None:
    st.session_state.active_view = "Settings"
    if section in SETTINGS_SECTIONS:
        st.session_state.settings_workspace_section = section


def close_settings_workspace() -> None:
    open_view("Control Room")


def focus_history_item(index: int) -> None:
    st.session_state.history_focus = index


def reset_workspace() -> None:
    settings: SystemSettings = st.session_state.settings
    st.session_state.messages = []
    st.session_state.active_view = "Control Room"
    st.session_state.history_focus = None
    defaults = {
        "input_main": "",
        "input_dept": settings.default_department,
        "input_style": OUTPUT_STYLES[0],
        "input_urgency": URGENCY_OPTIONS[0],
        "input_sex": SEX_OPTIONS[0],
        "input_insurance": INSURANCE_OPTIONS[0],
        "input_age": "",
        "input_chief": "",
        "input_expanded": False,
    }
    for key, value in defaults.items():
        st.session_state[key] = value
    for key in ["input_images", "input_docs"]:
        st.session_state.pop(key, None)

def render_sidebar_rail() -> None:
    st.html(
        """
        <div style="height:0;overflow:visible">
            <button
                id="sidebar-toggle-rail"
                type="button"
                class="sidebar-toggle-rail"
                aria-label="Toggle sidebar"
                title="Toggle sidebar"
            >
                <span class="sidebar-toggle-rail-core"></span>
            </button>
        </div>
        <script>
            (() => {{
                const body = window.document.body;
                const rail = window.document.getElementById("sidebar-toggle-rail");
                if (!rail) return;
                const apply = (collapsed) => {{
                    body.classList.toggle("sidebar-collapsed", collapsed);
                    window.__raremdtSidebarCollapsed = collapsed;
                }};
                const read = () => window.__raremdtSidebarCollapsed === true;

                apply(read());

                if (rail.dataset.bound !== "1") {{
                    rail.dataset.bound = "1";
                    rail.addEventListener("click", (event) => {{
                        event.preventDefault();
                        const next = !body.classList.contains("sidebar-collapsed");
                        apply(next);
                    }});
                }}
            }})();
        </script>
        """,
        unsafe_allow_javascript=True,
    )


def sync_sidebar_settings_defaults(settings: SystemSettings) -> None:
    signature = (
        settings.orchestration_mode,
        settings.default_department,
        float(settings.consensus_threshold),
        int(settings.max_rounds),
        bool(settings.show_diagnostics),
    )
    if st.session_state.get("sidebar_settings_signature") != signature:
        st.session_state["sidebar_settings_signature"] = signature
        st.session_state["sidebar_topology"] = settings.orchestration_mode
        st.session_state["sidebar_dept"] = settings.default_department
        st.session_state["sidebar_threshold"] = float(settings.consensus_threshold)
        st.session_state["sidebar_rounds"] = int(settings.max_rounds)
        st.session_state["sidebar_show_diag"] = bool(settings.show_diagnostics)


def sync_sidebar_profile_defaults(profile: AppProfile) -> None:
    signature = (
        profile.user_name,
        profile.title,
        profile.hospital_name,
        profile.department,
        profile.specialty_focus,
        profile.locale,
        profile.patient_population,
    )
    if st.session_state.get("sidebar_profile_signature") != signature:
        st.session_state["sidebar_profile_signature"] = signature
        st.session_state["sidebar_pf_name"] = profile.user_name
        st.session_state["sidebar_pf_title"] = profile.title
        st.session_state["sidebar_pf_hospital"] = profile.hospital_name
        st.session_state["sidebar_pf_dept"] = profile.department
        st.session_state["sidebar_pf_specialty"] = profile.specialty_focus
        st.session_state["sidebar_pf_locale"] = profile.locale
        st.session_state["sidebar_pf_pop"] = profile.patient_population


def render_sidebar_settings_panel() -> None:
    settings: SystemSettings = st.session_state.settings
    sync_sidebar_settings_defaults(settings)

    st.selectbox(
        "编排模式",
        TOPOLOGIES,
        key="sidebar_topology",
        format_func=lambda x: lbl(x, TOPOLOGY_LABELS),
    )
    st.selectbox(
        "默认科室",
        DEPARTMENTS,
        key="sidebar_dept",
        format_func=lambda x: lbl(x, DEPT_LABELS),
    )
    st.slider("一致性阈值", 0.50, 0.99, key="sidebar_threshold")
    st.slider("最大轮次", 1, 6, key="sidebar_rounds")
    st.toggle("默认显示多智能体诊断", key="sidebar_show_diag")
    st.caption(
        f"{sum(1 for p in settings.api_providers if p.enabled)} 个接口已启用，"
        f"{sum(r.agent_count for r in settings.agent_roles)} 个智能体工位已配置。"
    )

    if st.button("保存设置", key="sidebar_settings_save", use_container_width=True):
        st.session_state.settings = SystemSettings(
            orchestration_mode=st.session_state.get("sidebar_topology", settings.orchestration_mode),
            default_department=st.session_state.get("sidebar_dept", settings.default_department),
            consensus_threshold=float(st.session_state.get("sidebar_threshold", settings.consensus_threshold)),
            max_rounds=int(st.session_state.get("sidebar_rounds", settings.max_rounds)),
            show_diagnostics=bool(st.session_state.get("sidebar_show_diag", settings.show_diagnostics)),
            api_providers=settings.api_providers,
            agent_roles=settings.agent_roles,
        )
        save_settings(st.session_state.settings)
        st.success("设置已保存。")


def render_sidebar_profile_panel() -> None:
    profile: AppProfile = st.session_state.profile
    sync_sidebar_profile_defaults(profile)

    st.text_input("医生姓名", key="sidebar_pf_name")
    st.text_input("职称", key="sidebar_pf_title")
    st.text_input("医院名称", key="sidebar_pf_hospital")
    st.selectbox(
        "所属科室",
        DEPARTMENTS,
        key="sidebar_pf_dept",
        format_func=lambda x: lbl(x, DEPT_LABELS),
    )
    st.text_input("专业方向", key="sidebar_pf_specialty")
    st.text_input("地区", key="sidebar_pf_locale")
    st.text_area("服务人群 / 备注", key="sidebar_pf_pop", height=90)

    if st.button("保存档案", key="sidebar_profile_save", use_container_width=True):
        st.session_state.profile = AppProfile(
            user_name=st.session_state.get("sidebar_pf_name", profile.user_name),
            title=st.session_state.get("sidebar_pf_title", profile.title),
            hospital_name=st.session_state.get("sidebar_pf_hospital", profile.hospital_name),
            department=st.session_state.get("sidebar_pf_dept", profile.department),
            specialty_focus=st.session_state.get("sidebar_pf_specialty", profile.specialty_focus),
            locale=st.session_state.get("sidebar_pf_locale", profile.locale),
            patient_population=st.session_state.get("sidebar_pf_pop", profile.patient_population),
            first_run_complete=True,
        )
        save_profile(st.session_state.profile)
        st.success("档案已保存。")


# ── Sidebar ───────────────────────────────────────────────────────────────────

def render_sidebar() -> None:
    profile: AppProfile = st.session_state.profile
    settings: SystemSettings = st.session_state.settings
    history = st.session_state.history
    enabled_providers = sum(1 for p in settings.api_providers if p.enabled)
    total_agents = sum(r.agent_count for r in settings.agent_roles)

    with st.sidebar:
        st.markdown(
            """
            <div class="sidebar-brand">
                <div class="sidebar-brand-logo">
                    <div class="sidebar-logo-mark">R</div>
                    <div class="sidebar-brand-copy">
                        <div class="sidebar-logo-text">RareMDT</div>
                        <div class="sidebar-brand-sub">罕见病多智能体诊疗系统</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button("＋ 新建病例", key="sidebar_new_case", use_container_width=True):
            reset_workspace()
            st.rerun()

        st.markdown(
            f"""
            <div class="sidebar-status-strip">
                <div class="sidebar-status-card">
                    <div class="sidebar-status-label">接口</div>
                    <div class="sidebar-status-value">{enabled_providers}</div>
                </div>
                <div class="sidebar-status-card">
                    <div class="sidebar-status-label">智能体</div>
                    <div class="sidebar-status-value">{total_agents}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)

        st.markdown('<div class="sidebar-section-label">最近记录</div>', unsafe_allow_html=True)
        if history:
            for index, item in enumerate(history[:6]):
                button_label = item.title if len(item.title) <= 26 else item.title[:25] + "…"
                if st.button(button_label, key=f"sidebar_history_{index}", use_container_width=True):
                    focus_history_item(index)
                    st.rerun()
                st.caption(
                    f"{item.timestamp} · {lbl(item.department, DEPT_LABELS)} · {item.consensus_score:.0%} 一致性"
                )
        else:
            st.markdown(
                """
                <div class="sidebar-empty">
                    暂无历史会诊记录。提交首个病例后，这里会显示最近结果。
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)

        st.markdown('<div class="sidebar-section-label">当前医生</div>', unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class="sidebar-profile-card">
                <div class="sidebar-profile-name">{escape(profile.user_name)}</div>
                <div class="sidebar-profile-meta">{escape(profile.title)}</div>
                <div class="sidebar-profile-meta">{escape(profile.hospital_name)}</div>
                <div class="sidebar-profile-meta">{lbl(profile.department, DEPT_LABELS)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.popover("⚙ 系统设置", use_container_width=True):
            st.markdown(
                """
                <div class="settings-menu-card">
                    <div class="settings-menu-title">设置中心</div>
                    <div class="settings-menu-copy">从这里进入账户、API / 智能体与历史记录页面。</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            for label, section, icon, copy in SETTINGS_MENU:
                if st.button(label, key=f"sidebar_settings_menu_{section}", icon=icon, use_container_width=True):
                    open_settings_workspace(section)
                    st.rerun()
                st.caption(copy)

        st.markdown(
            f"""
            <div class="sidebar-footer">
                RareMDT · 演示版本<br/>
                PK Chen · Marco Xu
            </div>
            """,
            unsafe_allow_html=True,
        )


# ── Topbar ─────────────────────────────────────────────────────────────────────

def render_topbar() -> None:
    result = latest_result()
    active_view = st.session_state.active_view
    if active_view != "Control Room":
        return
    spacer_col, diagnostics_col = st.columns(
        [7.3, 1.05],
        gap="small",
    )

    with spacer_col:
        st.empty()

    with diagnostics_col:
        with st.popover("诊断面板", use_container_width=True):
            render_diagnostics_popover(result)


def render_diagnostics_popover(result) -> None:
    if result is None:
        st.info("提交病例后即可查看多智能体诊断。")
        return

    st.markdown("#### 多智能体诊断")
    stat1, stat2, stat3 = st.columns(3)
    stat1.metric("一致性", f"{result.consensus_score:.0%}")
    stat2.metric("轮次", len(result.rounds))
    stat3.metric("角色", len(result.agent_trace))
    st.caption(
        f"{lbl(result.department, DEPT_LABELS)} · {lbl(result.output_style, OUTPUT_LABELS)} · "
        f"{lbl(result.topology_used, TOPOLOGY_LABELS)}"
    )

    st.markdown("##### 收敛过程")
    for round_info in result.rounds:
        st.markdown(
            f"""
            <div class="diagnostic-round-card">
                <div class="diagnostic-round-head">
                    <span>第 {int(round_info['round'])} 轮</span>
                    <span>{float(round_info['alignment']):.0%}</span>
                </div>
                <div class="diagnostic-round-copy">{escape(str(round_info['summary']))}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.progress(float(round_info["alignment"]))

    st.markdown("##### 智能体工位")
    for trace in result.agent_trace:
        with st.expander(
            f"{lbl(trace['role'], ROLE_LABELS)} · {lbl(trace['provider'], PROVIDER_LABELS)}",
            expanded=False,
        ):
            st.write(trace["note"])


# ── Conversation helpers ───────────────────────────────────────────────────────

def add_user_message(
    content: str,
    department: str,
    chief_complaint: str,
    patient_age: str,
    patient_sex: str,
    insurance: str,
    output_style: str,
    urgency: str,
) -> None:
    meta = {
        "department": department,
        "chief_complaint": chief_complaint,
        "patient_age": patient_age,
        "patient_sex": patient_sex,
        "insurance": insurance,
        "output_style": output_style,
        "urgency": urgency,
        "timestamp": datetime.now().strftime("%H:%M"),
    }
    st.session_state.messages.append({"role": "user", "content": content, "meta": meta})


def add_assistant_message(result) -> None:
    meta = {
        "title": result.title,
        "department": result.department,
        "output_style": result.output_style,
        "consensus_score": result.consensus_score,
        "topology": result.topology_used,
        "timestamp": datetime.now().strftime("%H:%M"),
    }
    st.session_state.messages.append({"role": "assistant", "content": result, "meta": meta})


# ── Message rendering ──────────────────────────────────────────────────────────

def _render_user_message(content: str, meta: dict, ts: str) -> None:
    dept = lbl(meta.get("department", ""), DEPT_LABELS)
    sex = lbl(meta.get("patient_sex", ""), SEX_LABELS)
    age = meta.get("patient_age", "")
    insurance = lbl(meta.get("insurance", ""), INSURANCE_LABELS)
    urgency = lbl(meta.get("urgency", ""), URGENCY_LABELS)
    output_style = lbl(meta.get("output_style", ""), OUTPUT_LABELS)

    chips = []
    if dept: chips.append(f'<span class="msg-dept-chip">{escape(dept)}</span>')
    if urgency: chips.append(f'<span style="font-size:0.68rem;color:var(--accent);background:var(--accent-soft);padding:0.12rem 0.5rem;border-radius:999px;font-weight:600">{escape(urgency)}</span>')
    chips_html = " ".join(chips)

    summary_lines = []
    if meta.get("chief_complaint"):
        summary_lines.append(f"**主诉**：{escape(meta.get('chief_complaint', ''))}")
    if age or sex:
        summary_lines.append(f"**患者**：{escape(age)} {escape(sex)}")
    if insurance:
        summary_lines.append(f"**医保**：{escape(insurance)}")
    if meta.get("output_style"):
        summary_lines.append(f"**输出模式**：{escape(output_style)}")

    summary_html = ""
    if summary_lines:
        summary_html = (
            '<div style="margin-bottom:0.7rem;padding:0.6rem 0.8rem;background:var(--bg-elevated);border:1px solid var(--border-subtle);border-radius:var(--radius-md);font-size:0.82rem;color:var(--text-secondary);line-height:1.6">'
            + "<br>".join(summary_lines)
            + "</div>"
        )

    st.markdown(
        f"""
        <div class="msg-card">
            <div class="msg-avatar msg-avatar-user">U</div>
            <div class="msg-body">
                <div class="msg-meta">
                    <span class="msg-role">你</span>
                    {chips_html}
                    <span class="msg-time">{ts}</span>
                </div>
                <div class="msg-content">{summary_html}<div>{escape(content)}</div></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_assistant_message(result, meta: dict, ts: str) -> None:
    dept = lbl(meta.get("department", ""), DEPT_LABELS)
    output_style = lbl(meta.get("output_style", ""), OUTPUT_LABELS)
    consensus = meta.get("consensus_score", 0)
    topology = lbl(meta.get("topology", ""), TOPOLOGY_LABELS)
    title = meta.get("title", "")

    consensus_color = (
        "var(--green)" if consensus >= 0.85
        else "var(--accent)" if consensus >= 0.70
        else "var(--red)"
    )
    consensus_bg = (
        "var(--green-soft)" if consensus >= 0.85
        else "var(--accent-soft)" if consensus >= 0.70
        else "var(--red-soft)"
    )

    chips_html = ""
    if dept:
        chips_html += f'<span class="msg-dept-chip">{escape(dept)}</span>'
    if output_style:
        chips_html += f'<span style="font-size:0.68rem;color:var(--blue);background:var(--blue-soft);padding:0.12rem 0.5rem;border-radius:999px;font-weight:600">{escape(output_style)}</span>'
    chips_html += f'<span style="font-size:0.68rem;color:{consensus_color};background:{consensus_bg};padding:0.12rem 0.5rem;border-radius:999px;font-weight:600">{consensus:.0%} 一致性</span>'

    st.markdown(
        f"""
        <div class="msg-card">
            <div class="msg-avatar msg-avatar-claude">R</div>
            <div class="msg-body">
                <div class="msg-meta">
                    <span class="msg-role">RareMDT 智能体团队</span>
                    {chips_html}
                    <span class="msg-time">{ts}</span>
                </div>
                <div class="msg-content">
                    <h2 style="font-size:1.05rem;margin:0 0 0.6rem">{escape(title)}</h2>
                    <p style="color:var(--text-secondary);margin:0 0 1rem;font-size:0.88rem">{escape(result.executive_summary)}</p>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Input area ─────────────────────────────────────────────────────────────────

def render_input_area() -> None:
    """Primary composer surface for new case submission."""
    settings: SystemSettings = st.session_state.settings
    with st.container(border=True):
        head_col, toggle_col, reset_col = st.columns([0.64, 0.2, 0.16], vertical_alignment="center")
        with head_col:
            st.markdown(
                """
                <div class="composer-head">
                    <div class="composer-head-copy">
                        <div class="composer-eyebrow">RareMDT Intake</div>
                        <div class="composer-title">病例输入区</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with reset_col:
            if st.button(
                " ",
                key="reset_workspace_icon",
                icon=":material/restart_alt:",
                help="清空重置",
                width="stretch",
                type="tertiary",
            ):
                reset_workspace()
                st.rerun()
        with toggle_col:
            st.toggle(
                "高级模式",
                key="input_expanded",
                value=st.session_state.get("input_expanded", False),
                label_visibility="visible",
            )

        if st.session_state.get("input_expanded", False):
            _render_expanded_input(settings)
        else:
            _render_compact_input(settings)


def _render_compact_input(settings: SystemSettings) -> None:
    """Single-line input: textarea + send button."""
    # Ensure defaults
    st.session_state.setdefault("input_main", "")
    st.session_state.setdefault("input_dept", settings.default_department)
    st.session_state.setdefault("input_style", OUTPUT_STYLES[0])
    st.session_state.setdefault("input_urgency", URGENCY_OPTIONS[0])
    st.session_state.setdefault("input_sex", SEX_OPTIONS[0])
    st.session_state.setdefault("input_insurance", INSURANCE_OPTIONS[0])
    st.session_state.setdefault("input_age", "")
    st.session_state.setdefault("input_chief", "")

    st.markdown('<div class="composer-section-label">病例摘要</div>', unsafe_allow_html=True)
    st.text_area(
        "病例摘要",
        key="input_main",
        height=96,
        placeholder="粘贴或输入完整病例摘要（病史、查体、检验/影像摘要等）…",
        label_visibility="collapsed",
    )

    st.markdown('<div class="composer-section-label">附件与操作</div>', unsafe_allow_html=True)
    img_col, doc_col, paste_col, send_col = st.columns([1.1, 1.1, 0.24, 0.92])
    with img_col:
        st.file_uploader(
            "影像",
            type=["png", "jpg", "jpeg", "webp"],
            key="input_images",
            accept_multiple_files=True,
            label_visibility="collapsed",
        )
    with doc_col:
        st.file_uploader(
            "文档",
            type=["pdf", "txt", "docx"],
            key="input_docs",
            accept_multiple_files=True,
            label_visibility="collapsed",
        )
    with paste_col:
        if st.button(
            " ",
            key="paste_clipboard_compact",
            icon=":material/content_paste:",
            help="从剪贴板粘贴病历",
            width="stretch",
            type="tertiary",
        ):
            paste_clipboard_into_input()
    with send_col:
        if st.button("启动会诊", key="send_btn", help="启动多智能体会诊", use_container_width=True, type="primary"):
            _handle_submit(settings)


def _render_expanded_input(settings: SystemSettings) -> None:
    """Full-featured input form — all fields visible, no toggle needed."""
    # Ensure defaults
    for key, val in {
        "input_main": "",
        "input_dept": settings.default_department,
        "input_style": OUTPUT_STYLES[0],
        "input_urgency": URGENCY_OPTIONS[0],
        "input_sex": SEX_OPTIONS[0],
        "input_insurance": INSURANCE_OPTIONS[0],
        "input_age": "",
        "input_chief": "",
    }.items():
        st.session_state.setdefault(key, val)

    with st.container():
        st.markdown('<div class="composer-section-label">病例摘要</div>', unsafe_allow_html=True)
        st.text_area(
            "病例摘要",
            key="input_main",
            height=120,
            placeholder="粘贴或输入完整病例摘要（病史、查体、检验/影像摘要等）…",
            label_visibility="collapsed",
        )

        st.markdown('<div class="composer-section-label">患者与病例信息</div>', unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns([1.2, 0.8, 0.8, 1.0])
        with c1:
            st.text_input("主诉", key="input_chief", placeholder="主要症状")
        with c2:
            st.text_input("年龄", key="input_age", placeholder="e.g. 3岁")
        with c3:
            st.radio(
                "性别",
                SEX_OPTIONS,
                key="input_sex",
                format_func=lambda x: lbl(x, SEX_LABELS),
                horizontal=True,
                label_visibility="collapsed",
            )
        with c4:
            st.selectbox(
                "医保",
                INSURANCE_OPTIONS,
                key="input_insurance",
                format_func=lambda x: lbl(x, INSURANCE_LABELS),
            )

        # Second row
        c5, c6, c7 = st.columns([1.2, 1.0, 0.9])
        with c5:
            st.selectbox(
                "科室",
                DEPARTMENTS,
                key="input_dept",
                format_func=lambda x: lbl(x, DEPT_LABELS),
            )
        with c6:
            st.radio(
                "输出模式",
                OUTPUT_STYLES,
                key="input_style",
                format_func=lambda x: lbl(x, OUTPUT_LABELS),
                horizontal=True,
            )
        with c7:
            st.radio(
                "紧急程度",
                URGENCY_OPTIONS,
                key="input_urgency",
                format_func=lambda x: lbl(x, URGENCY_LABELS),
                horizontal=True,
            )

        st.markdown('<div class="composer-section-label">附件与操作</div>', unsafe_allow_html=True)
        fu1, fu2 = st.columns(2)
        with fu1:
            st.file_uploader(
                "上传影像 / 照片",
                type=["png", "jpg", "jpeg", "webp"],
                key="input_images",
                accept_multiple_files=True,
            )
        with fu2:
            st.file_uploader(
                "上传报告 / PDF",
                type=["pdf", "txt", "docx"],
                key="input_docs",
                accept_multiple_files=True,
            )

        # Action row
        action_col, paste_col, clear_col = st.columns([1.7, 0.26, 0.84])
        with action_col:
            if st.button("启动多智能体会诊", key="submit_expanded", use_container_width=True, type="primary"):
                _handle_submit(settings)
        with paste_col:
            if st.button(
                " ",
                key="paste_clipboard",
                icon=":material/content_paste:",
                help="从剪贴板粘贴病历",
                width="stretch",
                type="tertiary",
            ):
                paste_clipboard_into_input()
        with clear_col:
            if st.button("清空输入", key="clear_input"):
                for k in [
                    "input_main", "input_chief", "input_age",
                    "input_sex", "input_insurance",
                ]:
                    st.session_state[k] = "" if k != "input_sex" else SEX_OPTIONS[0]
                st.session_state["input_dept"] = settings.default_department
                st.session_state["input_style"] = OUTPUT_STYLES[0]
                st.session_state["input_urgency"] = URGENCY_OPTIONS[0]
                st.rerun()


def _handle_submit(settings: SystemSettings) -> None:
    """Process the case submission."""
    main_text = st.session_state.get("input_main", "").strip()
    if not main_text:
        st.warning("请先输入病例摘要。")
        return

    # Try to parse the EHR text for prefill
    prefill = parse_ehr_intake(main_text, settings.default_department)

    chief = st.session_state.get("input_chief", "") or prefill.chief_complaint or ""
    age = st.session_state.get("input_age", "") or prefill.patient_age or ""
    sex = st.session_state.get("input_sex", SEX_OPTIONS[0])
    if prefill.patient_sex:
        sex = prefill.patient_sex
    insurance = st.session_state.get("input_insurance", INSURANCE_OPTIONS[0])
    if prefill.insurance_type:
        insurance = prefill.insurance_type
    dept = st.session_state.get("input_dept", settings.default_department)
    if prefill.department:
        dept = prefill.department
    output_style = st.session_state.get("input_style", OUTPUT_STYLES[0])
    if prefill.output_style:
        output_style = prefill.output_style
    urgency = st.session_state.get("input_urgency", URGENCY_OPTIONS[0])
    if prefill.urgency:
        urgency = prefill.urgency

    # Build submission
    images = st.session_state.get("input_images", []) or []
    docs = st.session_state.get("input_docs", []) or []
    image_names = [f.name for f in images]
    doc_names = [f.name for f in docs]

    submission = CaseSubmission(
        department=dept,
        output_style=output_style,
        urgency=urgency,
        chief_complaint=chief,
        case_summary=main_text,
        patient_age=age,
        patient_sex=sex,
        insurance_type=insurance,
        uploaded_images=image_names,
        uploaded_docs=doc_names,
        show_process=settings.show_diagnostics,
    )

    # Add user message to conversation
    add_user_message(
        content=main_text,
        department=dept,
        chief_complaint=chief,
        patient_age=age,
        patient_sex=sex,
        insurance=insurance,
        output_style=output_style,
        urgency=urgency,
    )

    # Run the multi-agent engine
    result = run_multiagent_case(
        submission=submission,
        profile=st.session_state.profile,
        settings=settings,
    )

    # Add assistant message
    add_assistant_message(result)

    # Save to history
    history_item = QueryHistoryItem.from_result(submission, result)
    st.session_state.history = [history_item] + st.session_state.history
    save_history(st.session_state.history)

    # Clear input
    st.session_state["input_main"] = ""
    st.session_state.active_view = "Control Room"
    st.session_state.history_focus = None
    st.rerun()


# ── Empty state ────────────────────────────────────────────────────────────────

def render_workspace_summary() -> None:
    settings: SystemSettings = st.session_state.settings
    result = latest_result()
    history = st.session_state.history
    focus_index = st.session_state.get("history_focus")
    enabled_providers = sum(1 for p in settings.api_providers if p.enabled)
    total_agents = sum(r.agent_count for r in settings.agent_roles)
    latest_status = f"{result.consensus_score:.0%} 一致性" if result else "等待首个病例"
    latest_copy = result.title if result else "提交病例后即可在这里查看本次会诊输出与过程诊断。"

    cards = [
        ("默认科室", lbl(settings.default_department, DEPT_LABELS), "新病例将默认进入该工作流。"),
        (
            "编排方式",
            f"{lbl(settings.orchestration_mode, TOPOLOGY_LABELS)} · {total_agents} agents",
            f"{enabled_providers} 个接口当前可用。",
        ),
        ("当前状态", latest_status, latest_copy),
    ]

    cols = st.columns(3)
    for col, (label, value, copy) in zip(cols, cards):
        with col:
            st.markdown(
                f"""
                <div class="workspace-summary-card">
                    <div class="workspace-summary-label">{escape(label)}</div>
                    <div class="workspace-summary-value">{escape(value)}</div>
                    <div class="workspace-summary-copy">{escape(copy)}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    if focus_index is not None and 0 <= focus_index < len(history):
        item = history[focus_index]
        st.markdown(
            f"""
            <div class="history-highlight-card">
                <div class="history-highlight-kicker">选中的既往记录</div>
                <div class="history-highlight-title">{escape(item.title)}</div>
                <div class="history-highlight-meta">
                    {escape(item.timestamp)} · {lbl(item.department, DEPT_LABELS)} ·
                    {lbl(item.output_style, OUTPUT_LABELS)} · {item.consensus_score:.0%} 一致性
                </div>
                <div class="history-highlight-copy">{escape(item.summary)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_empty_state() -> None:
    settings: SystemSettings = st.session_state.settings
    dept_label = lbl(settings.default_department, DEPT_LABELS)
    st.markdown(
        f"""
        <div class="empty-state">
            <div class="empty-state-icon">AI</div>
            <h2>从这里开始新的罕见病会诊</h2>
            <p>
                将病例摘要粘贴到下方工作区。RareMDT 会在中间面板生成临床结论，并在右上角提供多智能体收敛诊断。
            </p>
            <div style="display:flex;gap:0.5rem;flex-wrap:wrap;justify-content:center;margin-top:1.5rem">
                <span class="quick-chip quick-chip-active">默认科室：{dept_label}</span>
                <span class="quick-chip">多智能体协同</span>
                <span class="quick-chip">结果会带编码与费用评估</span>
                <span class="quick-chip">右上角可展开诊断面板</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Result detail (shown below the assistant message card) ───────────────────

def render_result_detail(result) -> None:
    """Render the full result panel below the assistant card."""
    tabs = st.tabs(["📋 结论", "🏷 编码与费用", "📖 依据与安全", "🧠 协作诊断"])

    with tabs[0]:
        st.markdown(result.professional_answer)

    with tabs[1]:
        col_code, col_cost = st.columns(2)
        with col_code:
            st.markdown("### 编码摘要")
            st.table(result.coding_table)
        with col_cost:
            st.markdown("### 费用评估")
            st.table(result.cost_table)

    with tabs[2]:
        st.markdown("#### 下一步建议")
        for step in result.next_steps:
            st.markdown(f"- {step}")

        st.markdown("#### 指南与共识依据")
        for ref in result.references:
            st.markdown(
                f"- **{escape(ref['type'])}**：{escape(ref['title'])}（{escape(ref['region'])}）"
            )

        st.markdown("#### 安全提示")
        st.warning(result.safety_note)

    with tabs[3]:
        metric_cols = st.columns(4)
        metric_cols[0].metric("一致性", f"{result.consensus_score:.0%}")
        metric_cols[1].metric("轮次", len(result.rounds))
        metric_cols[2].metric("角色", len(result.agent_trace))
        metric_cols[3].metric("拓扑", lbl(result.topology_used, TOPOLOGY_LABELS))

        if not result.show_process:
            st.caption("当前设置未默认展示流程诊断，下列内容为本次运行的内部摘要。")

        st.markdown("#### 收敛轮次")
        for round_info in result.rounds:
            st.markdown(
                f"""
                <div class="diagnostic-round-card">
                    <div class="diagnostic-round-head">
                        <span>第 {int(round_info['round'])} 轮</span>
                        <span>{float(round_info['alignment']):.0%}</span>
                    </div>
                    <div class="diagnostic-round-copy">{escape(str(round_info['summary']))}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.progress(float(round_info["alignment"]))

        st.markdown("#### 智能体工位")
        trace_cols = st.columns(2)
        for index, trace in enumerate(result.agent_trace):
            with trace_cols[index % 2]:
                st.markdown(
                    f"""
                    <div class="agent-trace-card">
                        <div class="agent-trace-title">{escape(lbl(trace['role'], ROLE_LABELS))}</div>
                        <div class="agent-trace-meta">{escape(lbl(trace['provider'], PROVIDER_LABELS))}</div>
                        <div class="agent-trace-copy">{escape(trace['note'])}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


# ── Control Room ──────────────────────────────────────────────────────────────

def render_control_room() -> None:
    messages = st.session_state.messages
    pad_left, main_col, pad_right = st.columns([0.8, 7.0, 0.8])
    with main_col:
        for msg in messages:
            role = msg["role"]
            meta = msg.get("meta", {})
            ts = meta.get("timestamp", "")

            if role == "user":
                _render_user_message(msg["content"], meta, ts)
            elif role == "assistant":
                _render_assistant_message(msg["content"], meta, ts)
                with st.container():
                    render_result_detail(msg["content"])

        st.markdown('<div class="dialog-composer-buffer"></div>', unsafe_allow_html=True)
        render_input_area()


# ── Settings view ─────────────────────────────────────────────────────────────

def sync_settings_defaults(s: SystemSettings) -> None:
    st.session_state.setdefault("st_topology", s.orchestration_mode)
    st.session_state.setdefault("st_dept", s.default_department)
    st.session_state.setdefault("st_threshold", float(s.consensus_threshold))
    st.session_state.setdefault("st_rounds", int(s.max_rounds))
    st.session_state.setdefault("st_show_diag", bool(s.show_diagnostics))
    for i, p in enumerate(s.api_providers):
        st.session_state.setdefault(f"pv_name_{i}", p.provider_name)
        st.session_state.setdefault(f"pv_model_{i}", p.model_name)
        st.session_state.setdefault(f"pv_ep_{i}", p.endpoint)
        st.session_state.setdefault(f"pv_key_{i}", p.api_key)
        st.session_state.setdefault(f"pv_count_{i}", int(p.agents_for_api))
        st.session_state.setdefault(f"pv_en_{i}", bool(p.enabled))
    for i, r in enumerate(s.agent_roles):
        st.session_state.setdefault(f"rl_name_{i}", r.role_name)
        st.session_state.setdefault(f"rl_prov_{i}", r.provider_name)
        st.session_state.setdefault(f"rl_count_{i}", int(r.agent_count))
        st.session_state.setdefault(f"rl_spec_{i}", r.role_spec)


def ensure_choice(key: str, opts: list, fallback: str) -> None:
    if not opts:
        return
    if st.session_state.get(key) not in opts:
        st.session_state[key] = fallback if fallback in opts else opts[0]


def render_page_intro(title: str, copy: str) -> None:
    st.markdown(
        f"""
        <div class="page-intro-card">
            <div class="page-intro-kicker">RareMDT</div>
            <div class="page-intro-title">{escape(title)}</div>
            <div class="page-intro-copy">{escape(copy)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_settings_view(embedded: bool = False) -> None:
    settings: SystemSettings = st.session_state.settings
    sync_settings_defaults(settings)
    ensure_choice("st_topology", TOPOLOGIES, settings.orchestration_mode)
    ensure_choice("st_dept", DEPARTMENTS, settings.default_department)

    if not embedded:
        render_page_intro("系统设置", "在这里调整多智能体编排、接口配置和角色工位。")

    # Top section
    with st.container():
        c1, c2, c3, c4 = st.columns([1.2, 1, 1, 1])
        with c1:
            st.selectbox(
                "编排模式",
                TOPOLOGIES,
                key="st_topology",
                format_func=lambda x: lbl(x, TOPOLOGY_LABELS),
            )
        with c2:
            st.selectbox(
                "默认科室",
                DEPARTMENTS,
                key="st_dept",
                format_func=lambda x: lbl(x, DEPT_LABELS),
            )
        with c3:
            st.slider("一致性阈值", 0.5, 0.99, 0.01, key="st_threshold")
        with c4:
            st.slider("最大收敛轮次", 1, 6, 1, key="st_rounds")
        st.toggle("默认显示收敛诊断", key="st_show_diag")

    st.markdown("---")

    # API Providers
    st.markdown("### API 接口配置")
    providers = []
    for i in range(len(settings.api_providers)):
        ensure_choice(f"pv_name_{i}", list(PROVIDER_PRESETS.keys()),
                      settings.api_providers[i].provider_name)
        with st.container():
            r1, r2, r3, r4 = st.columns([1.2, 1.2, 1.2, 0.8])
            with r1:
                pv = st.selectbox(
                    "供应商",
                    list(PROVIDER_PRESETS.keys()),
                    key=f"pv_name_{i}",
                    format_func=lambda x: lbl(x, PROVIDER_LABELS),
                )
            with r2:
                st.text_input("模型", key=f"pv_model_{i}", placeholder="e.g. deepseek-chat")
            with r3:
                ep = st.text_input("接口地址", key=f"pv_ep_{i}")
                if not ep and st.button("填充", key=f"pv_fill_{i}", use_container_width=True):
                    st.session_state[f"pv_ep_{i}"] = PROVIDER_PRESETS.get(pv, "")
            with r4:
                st.text_input("密钥", type="password", key=f"pv_key_{i}")
            r5, r6 = st.columns([1, 0.4])
            with r5:
                st.number_input("分配智能体数", 0, 12, key=f"pv_count_{i}")
            with r6:
                st.toggle("启用", key=f"pv_en_{i}")

        providers.append(
            APIProviderConfig(
                provider_name=pv,
                model_name=st.session_state.get(f"pv_model_{i}", ""),
                endpoint=st.session_state.get(f"pv_ep_{i}", ""),
                api_key=st.session_state.get(f"pv_key_{i}", ""),
                agents_for_api=int(st.session_state.get(f"pv_count_{i}", 0)),
                enabled=bool(st.session_state.get(f"pv_en_{i}", True)),
            )
        )

    pv_c1, pv_c2 = st.columns(2)
    if pv_c1.button("+ 新增接口", use_container_width=True):
        settings.api_providers.append(APIProviderConfig())
        i = len(settings.api_providers) - 1
        st.session_state[f"pv_name_{i}"] = "DeepSeek"
        st.session_state[f"pv_model_{i}"] = "deepseek-chat"
        st.rerun()
    if pv_c2.button("- 删除最后一个", use_container_width=True):
        if settings.api_providers:
            i = len(settings.api_providers) - 1
            for k in [f"pv_name_{i}", f"pv_model_{i}", f"pv_ep_{i}", f"pv_key_{i}", f"pv_count_{i}", f"pv_en_{i}"]:
                st.session_state.pop(k, None)
            settings.api_providers.pop()
            st.rerun()

    st.markdown("---")

    # Agent roles
    st.markdown("### 智能体角色工位")
    pv_names = [p.provider_name for p in providers] or ["DeepSeek"]
    roles = []
    for i in range(len(settings.agent_roles)):
        ensure_choice(f"rl_name_{i}", ROLE_TEMPLATES, settings.agent_roles[i].role_name)
        ensure_choice(f"rl_prov_{i}", pv_names, settings.agent_roles[i].provider_name)
        with st.container():
            rr1, rr2, rr3 = st.columns([1.2, 1.0, 0.8])
            with rr1:
                rn = st.selectbox(
                    "角色",
                    ROLE_TEMPLATES,
                    key=f"rl_name_{i}",
                    format_func=lambda x: lbl(x, ROLE_LABELS),
                )
            with rr2:
                rp = st.selectbox(
                    "绑定接口",
                    pv_names,
                    key=f"rl_prov_{i}",
                    format_func=lambda x: lbl(x, PROVIDER_LABELS),
                )
            with rr3:
                st.number_input("数量", 1, 12, key=f"rl_count_{i}")
            st.text_area("角色说明", key=f"rl_spec_{i}", height=90)

        roles.append(
            AgentRoleConfig(
                role_name=rn,
                role_spec=st.session_state.get(f"rl_spec_{i}", ""),
                provider_name=rp,
                agent_count=int(st.session_state.get(f"rl_count_{i}", 1)),
            )
        )

    rl_c1, rl_c2 = st.columns(2)
    if rl_c1.button("+ 新增角色", use_container_width=True):
        prov = providers[0].provider_name if providers else "DeepSeek"
        settings.agent_roles.append(AgentRoleConfig(provider_name=prov))
        i = len(settings.agent_roles) - 1
        st.session_state[f"rl_name_{i}"] = "Orchestrator"
        st.session_state[f"rl_prov_{i}"] = prov
        st.session_state[f"rl_count_{i}"] = 1
        st.rerun()
    if rl_c2.button("- 删除最后一个", use_container_width=True):
        if settings.agent_roles:
            i = len(settings.agent_roles) - 1
            for k in [f"rl_name_{i}", f"rl_prov_{i}", f"rl_count_{i}", f"rl_spec_{i}"]:
                st.session_state.pop(k, None)
            settings.agent_roles.pop()
            st.rerun()

    st.markdown("---")

    # Save
    sc1, sc2 = st.columns([1, 1])
    with sc1:
        if st.button("保存设置", use_container_width=True):
            st.session_state.settings = SystemSettings(
                orchestration_mode=st.session_state.get("st_topology", settings.orchestration_mode),
                default_department=st.session_state.get("st_dept", settings.default_department),
                consensus_threshold=float(st.session_state.get("st_threshold", settings.consensus_threshold)),
                max_rounds=int(st.session_state.get("st_rounds", settings.max_rounds)),
                show_diagnostics=bool(st.session_state.get("st_show_diag", settings.show_diagnostics)),
                api_providers=providers,
                agent_roles=roles,
            )
            save_settings(st.session_state.settings)
            st.success("系统设置已保存。")
    with sc2:
        if st.button("重新载入", use_container_width=True):
            st.session_state.settings = load_settings()
            st.rerun()

# ── Profile view ──────────────────────────────────────────────────────────────

def render_profile_view(embedded: bool = False) -> None:
    profile: AppProfile = st.session_state.profile
    if not embedded:
        render_page_intro("医生档案", "维护当前账号的基础资料，帮助系统更贴近真实医院场景。")

    with st.container():
        r1, r2 = st.columns([1, 1])
        st.text_input("医生姓名", profile.user_name, key="pf_name")
        st.text_input("职称", profile.title, key="pf_title")
        r3, r4 = st.columns([1, 1])
        st.text_input("医院名称", profile.hospital_name, key="pf_hospital")
        st.selectbox(
            "所属科室",
            DEPARTMENTS,
            index=DEPARTMENTS.index(profile.department),
            key="pf_dept",
            format_func=lambda x: lbl(x, DEPT_LABELS),
        )
        r5, r6 = st.columns([1, 1])
        st.text_input("专业方向", profile.specialty_focus, key="pf_specialty")
        st.text_input("地区", profile.locale, key="pf_locale")
        st.text_area("服务人群 / 备注", profile.patient_population, key="pf_pop", height=100)

    if st.button("保存档案", use_container_width=True):
        st.session_state.profile = AppProfile(
            user_name=st.session_state.get("pf_name", profile.user_name),
            title=st.session_state.get("pf_title", profile.title),
            hospital_name=st.session_state.get("pf_hospital", profile.hospital_name),
            department=st.session_state.get("pf_dept", profile.department),
            specialty_focus=st.session_state.get("pf_specialty", profile.specialty_focus),
            locale=st.session_state.get("pf_locale", profile.locale),
            patient_population=st.session_state.get("pf_pop", profile.patient_population),
            first_run_complete=True,
        )
        save_profile(st.session_state.profile)
        st.success("档案已保存。")

# ── History view ──────────────────────────────────────────────────────────────

def render_history_view(embedded: bool = False) -> None:
    history = st.session_state.history
    focus_index = st.session_state.get("history_focus")
    if not embedded:
        render_page_intro("历史记录", "左侧侧栏显示最近会诊，这里提供完整列表与重点回看。")

    if not history:
        st.info("暂无历史查询记录。")
        return

    if focus_index is not None and 0 <= focus_index < len(history):
        item = history[focus_index]
        st.markdown(
            f"""
            <div class="history-highlight-card">
                <div class="history-highlight-kicker">最近选中的记录</div>
                <div class="history-highlight-title">{escape(item.title)}</div>
                <div class="history-highlight-meta">
                    {escape(item.timestamp)} · {lbl(item.department, DEPT_LABELS)} ·
                    {lbl(item.output_style, OUTPUT_LABELS)} · {item.consensus_score:.0%} 一致性
                </div>
                <div class="history-highlight-copy">{escape(item.summary)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    for idx, item in enumerate(history):
        with st.container():
            cols = st.columns([1, 0.2, 0.3])
            with cols[0]:
                st.markdown(
                    f"**{escape(item.title)}**"
                    f"<br><span style='font-size:0.75rem;color:var(--text-tertiary)'>"
                    f"{item.timestamp} · {lbl(item.department, DEPT_LABELS)} · "
                    f"{lbl(item.output_style, OUTPUT_LABELS)}</span>",
                    unsafe_allow_html=True,
                )
                st.markdown(f"<span style='font-size:0.8rem;color:var(--text-secondary)'>{escape(item.summary)}</span>", unsafe_allow_html=True)
            with cols[1]:
                consensus_color = (
                    "var(--green)" if item.consensus_score >= 0.85
                    else "var(--accent)" if item.consensus_score >= 0.70
                    else "var(--red)"
                )
                st.markdown(
                    f"<div style='text-align:center'><div style='font-size:1.2rem;font-weight:700;color:{consensus_color}'>{item.consensus_score:.0%}</div><div style='font-size:0.65rem;color:var(--text-tertiary)'>一致性</div></div>",
                    unsafe_allow_html=True,
                )
            with cols[2]:
                if st.button("工作台", key=f"hist_rerun_{idx}", help="返回工作台", use_container_width=True):
                    open_view("Control Room")
                    st.rerun()

        st.markdown("---")

def render_settings_workspace() -> None:
    current_section = st.session_state.get("settings_workspace_section", SETTINGS_SECTIONS[0])
    meta = SETTINGS_SECTION_META[current_section]

    pad_left, main_col, pad_right = st.columns([0.7, 7.6, 0.7])
    with main_col:
        head_col, close_col = st.columns([4.8, 1.1], vertical_alignment="center")
        with head_col:
            st.markdown(
                f"""
                <div class="settings-shell-card">
                    <div class="settings-shell-kicker">Settings</div>
                    <div class="settings-shell-title">{escape(meta['title'])}</div>
                    <div class="settings-shell-copy">{escape(meta['copy'])}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with close_col:
            if st.button("关闭设置", key="settings_close_button", use_container_width=True):
                close_settings_workspace()
                st.rerun()

        nav_cols = st.columns(3)
        for nav_col, (label, section, icon, _) in zip(nav_cols, SETTINGS_MENU):
            with nav_col:
                if st.button(
                    label,
                    key=f"settings_nav_{section}",
                    icon=icon,
                    type="primary" if current_section == section else "secondary",
                    use_container_width=True,
                ):
                    open_settings_workspace(section)
                    st.rerun()

        if current_section == "医生档案":
            render_profile_view(embedded=True)
        elif current_section == "系统设置":
            render_settings_view(embedded=True)
        else:
            render_history_view(embedded=True)


# ── First-run guard ───────────────────────────────────────────────────────────

def first_run_guard() -> None:
    profile: AppProfile = st.session_state.profile
    if profile.first_run_complete:
        return

    open_settings_workspace("医生档案")
    st.markdown(
        """
        <div class="empty-state">
            <div class="empty-state-icon">✦</div>
            <h2>欢迎使用 RareMDT</h2>
            <p>请先完成医生档案设置，以便系统匹配医院部署场景。</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    render_settings_workspace()
    st.stop()


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    st.set_page_config(
        page_title="RareMDT · 罕见病多智能体诊疗",
        page_icon="✦",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_css()
    init_state()
    render_sidebar()
    first_run_guard()
    render_topbar()
    if st.session_state.active_view == "Settings":
        render_settings_workspace()
    else:
        render_control_room()
    render_sidebar_rail()


if __name__ == "__main__":
    main()
