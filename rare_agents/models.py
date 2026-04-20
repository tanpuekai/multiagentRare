from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class DepartmentOption(str, Enum):
    ORTHOPEDICS = "Orthopedics / Bone"
    NEUROLOGY = "Neural / Neurology"
    PEDIATRICS = "Pediatrics"
    ICU = "ICU"
    EMERGENCY = "A&E / Emergency"
    PULMONARY = "Pulmonary / Lung"
    GENETICS = "Medical Genetics"
    MULTIDISCIPLINARY = "MDT / Cross-specialty"


class OrchestrationMode(str, Enum):
    SYMMETRIC = "Symmetric"
    ASYMMETRIC = "Asymmetric"


@dataclass
class APIProviderConfig:
    provider_id: str = ""
    provider_name: str = "DeepSeek"
    model_name: str = "deepseek-chat"
    endpoint: str = ""
    api_key: str = ""
    agents_for_api: int = 2
    enabled: bool = True


@dataclass
class AgentRoleConfig:
    role_name: str = "Orchestrator"
    role_spec: str = (
        "负责协调各专科智能体、推动结论收敛、消除冲突，并生成适合临床阅读的最终结论。"
    )
    provider_id: str = ""
    provider_name: str = "DeepSeek"
    agent_count: int = 1


@dataclass
class AppProfile:
    user_name: str = "演示医生"
    title: str = "主任医师"
    hospital_name: str = "港大医院（HKU-SZH）"
    department: str = DepartmentOption.PEDIATRICS.value
    specialty_focus: str = "罕见病 MDT"
    locale: str = "深圳，中国"
    patient_population: str = "儿科与成人罕见病转诊人群"
    first_run_complete: bool = False


@dataclass
class SystemSettings:
    orchestration_mode: str
    default_department: str
    consensus_threshold: float
    max_rounds: int
    show_diagnostics: bool
    api_providers: list[APIProviderConfig] = field(default_factory=list)
    agent_roles: list[AgentRoleConfig] = field(default_factory=list)


@dataclass
class CaseSubmission:
    department: str
    output_style: str
    urgency: str
    chief_complaint: str
    case_summary: str
    patient_age: str
    patient_sex: str
    insurance_type: str
    uploaded_images: list[str]
    uploaded_docs: list[str]
    show_process: bool
    image_assets: list[dict[str, str]] = field(default_factory=list)
    single_model_test: bool = False
    is_ready: bool = True

    @classmethod
    def empty(cls) -> "CaseSubmission":
        return cls(
            department="",
            output_style="",
            urgency="",
            chief_complaint="",
            case_summary="",
            patient_age="",
            patient_sex="",
            insurance_type="",
            uploaded_images=[],
            uploaded_docs=[],
            image_assets=[],
            show_process=False,
            single_model_test=False,
            is_ready=False,
        )


@dataclass
class EngineResult:
    title: str
    executive_summary: str
    department: str
    output_style: str
    professional_answer: str
    coding_table: list[dict[str, str]]
    cost_table: list[dict[str, str]]
    references: list[dict[str, str]]
    next_steps: list[str]
    safety_note: str
    rounds: list[dict[str, object]]
    agent_trace: list[dict[str, str]]
    consensus_score: float
    topology_used: str
    show_process: bool
    execution_mode: str = "multi_agent"
    serving_provider: str = ""
    serving_model: str = ""
    activated_agent: str = ""
    plan_steps: list[dict[str, object]] = field(default_factory=list)
    plan_display_steps: list[dict[str, object]] = field(default_factory=list)
    execution_records: list[dict[str, object]] = field(default_factory=list)
    answer_source: str = ""
    raw_model_text: str = ""
    raw_provider_request: str = ""
    raw_provider_payload: str = ""
    display_payload: str = ""
    workflow_revision: str = ""
    display_quality_warnings: list[str] = field(default_factory=list)


@dataclass
class QueryHistoryItem:
    timestamp: str
    title: str
    department: str
    output_style: str
    summary: str
    consensus_score: float

    @classmethod
    def from_result(cls, submission: CaseSubmission, result: EngineResult) -> "QueryHistoryItem":
        return cls(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            title=result.title,
            department=submission.department,
            output_style=submission.output_style,
            summary=result.executive_summary,
            consensus_score=result.consensus_score,
        )


@dataclass
class SessionTurn:
    turn_id: str
    timestamp: str
    user_input: str
    submission: CaseSubmission
    result: EngineResult


@dataclass
class DoctorApproval:
    approval_id: str
    turn_id: str
    execution_mode: str
    action: str
    note: str = ""
    created_at: str = ""


@dataclass
class EvidenceFeedback:
    evidence_id: str
    rating: int


@dataclass
class CaseFeedback:
    submitted_at: str
    diagnosis_rating: int
    report_rating: int
    evidence_ratings: list[EvidenceFeedback] = field(default_factory=list)
    comment: str = ""
    workflow_revision: str = ""


@dataclass
class CaseSessionRecord:
    session_id: str
    timestamp: str
    title: str
    department: str
    output_style: str
    summary: str
    consensus_score: float
    show_in_sidebar: bool = True
    submission: CaseSubmission | None = None
    result: EngineResult | None = None
    context_submission: CaseSubmission | None = None
    turns: list[SessionTurn] = field(default_factory=list)
    doctor_approvals: list[DoctorApproval] = field(default_factory=list)
    case_feedback: CaseFeedback | None = None

    @classmethod
    def from_result(
        cls,
        session_id: str,
        submission: CaseSubmission,
        result: EngineResult,
        *,
        user_input: str | None = None,
        turn_id: str = "",
    ) -> "CaseSessionRecord":
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        turn = SessionTurn(
            turn_id=turn_id,
            timestamp=timestamp,
            user_input=(user_input or submission.case_summary).strip(),
            submission=submission,
            result=result,
        )
        return cls(
            session_id=session_id,
            timestamp=timestamp,
            title=result.title,
            department=submission.department,
            output_style=submission.output_style,
            summary=result.executive_summary,
            consensus_score=result.consensus_score,
            show_in_sidebar=True,
            submission=submission,
            result=result,
            context_submission=submission,
            turns=[turn],
        )

    @classmethod
    def from_history_item(cls, session_id: str, item: QueryHistoryItem) -> "CaseSessionRecord":
        return cls(
            session_id=session_id,
            timestamp=item.timestamp,
            title=item.title,
            department=item.department,
            output_style=item.output_style,
            summary=item.summary,
            consensus_score=item.consensus_score,
            show_in_sidebar=True,
        )


def default_profile() -> AppProfile:
    return AppProfile()


def default_settings() -> SystemSettings:
    return SystemSettings(
        orchestration_mode=OrchestrationMode.ASYMMETRIC.value,
        default_department=DepartmentOption.PEDIATRICS.value,
        consensus_threshold=0.82,
        max_rounds=3,
        show_diagnostics=True,
        api_providers=[
            APIProviderConfig(
                provider_id="provider-deepseek-default",
                provider_name="DeepSeek",
                model_name="deepseek-chat",
                endpoint="https://api.deepseek.com",
                agents_for_api=2,
            ),
            APIProviderConfig(
                provider_id="provider-glm-default",
                provider_name="GLM / BigModel",
                model_name="glm-4.5",
                endpoint="https://open.bigmodel.cn/api/paas/v4",
                agents_for_api=1,
            ),
            APIProviderConfig(
                provider_id="provider-kimi-default",
                provider_name="Kimi",
                model_name="moonshot-v1-128k",
                endpoint="https://api.moonshot.cn/v1",
                agents_for_api=1,
            ),
        ],
        agent_roles=[
            AgentRoleConfig(
                role_name="Orchestrator",
                provider_id="provider-deepseek-default",
                provider_name="DeepSeek",
                agent_count=1,
                role_spec="负责结构化拆解病例、统筹轮次级综合分析，并在智能体之间解决冲突。",
            ),
            AgentRoleConfig(
                role_name="Planner",
                provider_id="provider-glm-default",
                provider_name="GLM / BigModel",
                agent_count=1,
                role_spec="规划鉴别诊断或治疗路径，明确下一步证据需求，并优先排序罕见病分支。",
            ),
            AgentRoleConfig(
                role_name="Executor",
                provider_id="provider-glm-default",
                provider_name="GLM / BigModel",
                agent_count=1,
                role_spec="负责执行多模态诊断步骤，产出具备定位与量化依据的结构化证据。",
            ),
            AgentRoleConfig(
                role_name="Generator",
                provider_id="provider-kimi-default",
                provider_name="Kimi",
                agent_count=2,
                role_spec="起草面向临床医生的结构化回答，要求表达专业、分区清晰，并体现专科细节。",
            ),
            AgentRoleConfig(
                role_name="Fact Checker",
                provider_id="provider-deepseek-default",
                provider_name="DeepSeek",
                agent_count=1,
                role_spec="核查前后不一致、证据不足、不安全建议，以及编码或费用披露缺失等问题。",
            ),
            AgentRoleConfig(
                role_name="Guideline Retriever",
                provider_id="provider-glm-default",
                provider_name="GLM / BigModel",
                agent_count=1,
                role_spec="为结论补充中国与国际罕见病、专科及围手术期指南或共识依据。",
            ),
            AgentRoleConfig(
                role_name="Web Search",
                provider_id="provider-kimi-default",
                provider_name="Kimi",
                agent_count=1,
                role_spec="用于正式部署时检索最新共识、院内路径与医保支付规则。",
            ),
        ],
    )
