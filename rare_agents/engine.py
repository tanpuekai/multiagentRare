from __future__ import annotations

from textwrap import dedent

from rare_agents.models import AppProfile, CaseSubmission, EngineResult, SystemSettings


DEPARTMENT_DISPLAY = {
    "Orthopedics / Bone": "骨科 / 骨病",
    "Neural / Neurology": "神经内科 / 神经系统",
    "Pediatrics": "儿科",
    "ICU": "重症医学科 ICU",
    "A&E / Emergency": "急诊 / A&E",
    "Pulmonary / Lung": "呼吸科 / 肺部",
    "Medical Genetics": "医学遗传",
    "MDT / Cross-specialty": "多学科 MDT",
}
OUTPUT_STYLE_DISPLAY = {
    "Diagnostic": "诊断评估",
    "Surgical / Treatment Plan": "手术 / 治疗方案",
}


REFERENCE_LIBRARY = {
    "Orthopedics / Bone": [
        {"type": "中国", "title": "罕见骨病与骨科 MDT 管理中国专家共识", "region": "中国"},
        {"type": "国际", "title": "Orphanet 与 ERN 关于罕见骨病诊断路径的指导建议", "region": "国际"},
    ],
    "Neural / Neurology": [
        {"type": "中国", "title": "遗传性神经肌肉疾病诊断与管理中国共识", "region": "中国"},
        {"type": "国际", "title": "AAN 与 ERN 关于罕见神经系统疾病评估的共识", "region": "国际"},
    ],
    "Pediatrics": [
        {"type": "中国", "title": "国家罕见病诊疗指南中的儿科相关路径建议", "region": "中国"},
        {"type": "国际", "title": "欧洲参考网络关于儿科罕见病的共识建议", "region": "国际"},
    ],
    "ICU": [
        {"type": "中国", "title": "遗传代谢及罕见系统性危重症中国重症医学共识", "region": "中国"},
        {"type": "国际", "title": "SCCM 与 ERN 关于罕见危重症处理的指导建议", "region": "国际"},
    ],
    "A&E / Emergency": [
        {"type": "中国", "title": "罕见病急性发作与急诊处置中国共识", "region": "中国"},
        {"type": "国际", "title": "未明确诊断罕见病失代偿急诊处理指导", "region": "国际"},
    ],
    "Pulmonary / Lung": [
        {"type": "中国", "title": "间质性及罕见肺部疾病诊疗路径中国共识", "region": "中国"},
        {"type": "国际", "title": "ATS / ERS 关于罕见肺部疾病的推荐意见", "region": "国际"},
    ],
    "Medical Genetics": [
        {"type": "中国", "title": "医学遗传罕见病诊断与转诊中国共识", "region": "中国"},
        {"type": "国际", "title": "ACMG / ESHG 关于罕见病基因组评估的指导意见", "region": "国际"},
    ],
    "MDT / Cross-specialty": [
        {"type": "中国", "title": "罕见病多学科管理中国共识", "region": "中国"},
        {"type": "国际", "title": "EURORDIS 与 ERN 关于多学科罕见病路径的共识", "region": "国际"},
    ],
}


def normalize_refs(department: str) -> list[dict[str, str]]:
    return REFERENCE_LIBRARY.get(department, REFERENCE_LIBRARY["MDT / Cross-specialty"])


def display_department(department: str) -> str:
    return DEPARTMENT_DISPLAY.get(department, department)


def display_output_style(output_style: str) -> str:
    return OUTPUT_STYLE_DISPLAY.get(output_style, output_style)


def build_coding_table(submission: CaseSubmission) -> list[dict[str, str]]:
    primary_hint = submission.chief_complaint or "疑似罕见病综合征"
    return [
        {
            "编码体系": "ICD-10",
            "建议编码": "Q87.8 / G71.2 / J84.1",
            "临床用途": f"需结合“{primary_hint}”按专科进一步细化",
        },
        {
            "编码体系": "ICD-11",
            "建议编码": "LD2Y / 8A7Z",
            "临床用途": "用于更现代的罕见病统一映射",
        },
        {
            "编码体系": "中国 DRG/DIP 备注",
            "建议编码": "需结合本地支付规则进一步映射",
            "临床用途": "建议核对深圳本地医院编码与医保支付口径",
        },
        {
            "编码体系": "ORPHAcode",
            "建议编码": "建议关联候选 ORPHA 编码",
            "临床用途": "用于罕见病登记与跨体系映射",
        },
    ]


def build_cost_table(submission: CaseSubmission) -> list[dict[str, str]]:
    insured = submission.insurance_type != "Self-pay / uninsured"
    patient_share = "人民币 8,000 - 25,000 元" if insured else "人民币 25,000 - 80,000 元"
    total_cost = "人民币 35,000 - 120,000 元" if submission.output_style == "Surgical / Treatment Plan" else "人民币 3,000 - 18,000 元"
    reimbursed = "可结合本地医保路径部分报销，最终以医院目录与罕见病保障政策为准" if insured else "演示估算按无医保报销处理"
    surgical_grade = "Ⅲ - Ⅳ 级" if submission.output_style == "Surgical / Treatment Plan" else "视具体干预而定"
    return [
        {"项目": "预计总费用", "估算": total_cost},
        {"项目": "患者预计自付", "估算": patient_share},
        {"项目": "医保支付说明", "估算": reimbursed},
        {"项目": "手术分级", "估算": surgical_grade},
    ]


def build_professional_answer(submission: CaseSubmission, profile: AppProfile) -> str:
    if submission.output_style == "Diagnostic":
        return dedent(
            f"""
            **诊断判断**

            当前表现更适合按照“罕见病诊断路径”处理，而不是直接下单一疾病结论。基于已提交的多模态资料，系统建议优先开展结构化鉴别诊断，综合表型、影像和对应专科红旗信号进行分层判断。

            **当前优先方向**

            需要重点考虑综合征性或遗传相关疾病的可能性，在正式下最终诊断前，应结合针对性检测、正式影像复核以及 MDT 会诊进行确认。

            **建议的诊断动作**

            1. 补足表型颗粒度、起病时间轴、家族史以及既往治疗反应。
            2. 组织影像与报告的 MDT 联合判读，完成放射科及专科复核。
            3. 按专科路径选择指南支持的遗传、代谢、免疫或组织学检测。
            4. 同步核对 ICD-10、ICD-11、本地医保支付逻辑与罕见病登记术语。

            **临床沟通建议**

            对于 {profile.hospital_name}，建议将本病例表述为“中高疑似罕见病待明确病例”，需等待进一步证据与专科复核后再形成正式结论。
            """
        ).strip()

    return dedent(
        f"""
        **治疗 / 手术方案判断**

        当前病例更适合采用分阶段多学科统筹方案，而不是单专科孤立决策。以下路径的目标是减少相互矛盾的建议，为临床与家属提供一份统一、可执行的方案。

        **建议方案**

        1. 先控制当前风险，明确手术或高级治疗是择期、加急还是抢救级别。
        2. 完成麻醉、影像、病理及罕见病相关围手术期评估。
        3. 形成一份经 MDT 审核的统一方案，覆盖适应证、预期获益、禁忌证、手术分级、康复与随访。
        4. 在安排治疗前，向患者提供中国本地化的费用与医保预估说明。

        **临床沟通建议**

        系统建议围绕 {display_department(submission.department)} 形成 MDT 审核通过的统一治疗包；在事实核查与指南依据尚未充分对齐前，不建议直接进入最终手术或高级治疗决策。
        """
    ).strip()


def build_agent_trace(settings: SystemSettings, submission: CaseSubmission) -> list[dict[str, str]]:
    enabled_providers = [provider for provider in settings.api_providers if provider.enabled]
    shared_provider = enabled_providers[0].provider_name if enabled_providers else "共享接口"
    trace: list[dict[str, str]] = []
    for role in settings.agent_roles:
        provider_name = shared_provider if settings.orchestration_mode == "Symmetric" else role.provider_name
        note = (
            f"聚焦当前病例的{display_output_style(submission.output_style)}任务，并围绕 {display_department(submission.department)} 相关问题执行角色职责；"
            f"角色说明：{role.role_spec}"
        )
        trace.append({"role": role.role_name, "provider": provider_name, "note": note})
    return trace


def build_rounds(settings: SystemSettings, submission: CaseSubmission) -> tuple[list[dict[str, object]], float]:
    rounds: list[dict[str, object]] = []
    base = 0.58 if settings.orchestration_mode == "Asymmetric" else 0.64
    increment = max((settings.consensus_threshold - base) / max(settings.max_rounds, 1), 0.06)
    alignment = base
    for index in range(1, settings.max_rounds + 1):
        alignment = min(alignment + increment + 0.03, 0.97)
        summary = (
            f"本轮由编排智能体整合规划、生成、核查与指南证据，使{display_output_style(submission.output_style)}建议进一步统一，"
            f"并减少了与 {display_department(submission.department)} 相关的关键冲突点。"
        )
        rounds.append({"round": index, "alignment": alignment, "summary": summary})
        if alignment >= settings.consensus_threshold:
            break
    return rounds, alignment


def build_title(submission: CaseSubmission) -> str:
    prefix = "罕见病诊断会诊" if submission.output_style == "Diagnostic" else "罕见病治疗会诊"
    complaint = submission.chief_complaint or "复杂病例"
    return f"{prefix}: {complaint}"


def build_summary(submission: CaseSubmission, consensus_score: float) -> str:
    return (
        f"基于多模态资料，系统已形成面向 {display_department(submission.department)} 的统一{display_output_style(submission.output_style)}路径建议，"
        f"当前智能体一致性达到 {consensus_score:.0%}，输出已整理为临床可读格式。"
    )


def run_multiagent_case(submission: CaseSubmission, profile: AppProfile, settings: SystemSettings) -> EngineResult:
    rounds, consensus_score = build_rounds(settings, submission)
    references = normalize_refs(submission.department)
    title = build_title(submission)
    executive_summary = build_summary(submission, consensus_score)
    answer = build_professional_answer(submission, profile)
    next_steps = [
        "确认最终医疗决策仍由临床医生作出，系统结论仅作辅助参考。",
        "将上传的多模态资料与本院流程、专科意见和影像复核结果进行交叉核对。",
        "在向患者沟通前，先完成编码、支付映射及深圳本地报销逻辑核验。",
        "如仍存在手术、遗传、ICU 或儿科红旗信号，请升级至 MDT 会诊。",
    ]
    safety_note = (
        "当前为演示输出，不可作为诊断、手术或处方的唯一依据。"
        "正式医院部署应补充合规数据接入、审计留痕与医生签署闭环。"
    )
    return EngineResult(
        title=title,
        executive_summary=executive_summary,
        department=submission.department,
        output_style=submission.output_style,
        professional_answer=answer,
        coding_table=build_coding_table(submission),
        cost_table=build_cost_table(submission),
        references=references,
        next_steps=next_steps,
        safety_note=safety_note,
        rounds=rounds,
        agent_trace=build_agent_trace(settings, submission),
        consensus_score=consensus_score,
        topology_used=settings.orchestration_mode,
        show_process=submission.show_process,
    )


def run_single_model_case(
    submission: CaseSubmission,
    profile: AppProfile,
    settings: SystemSettings,
    *,
    provider_name: str,
    model_name: str,
    role_name: str,
    role_spec: str,
    generated_answer: str,
) -> EngineResult:
    references = normalize_refs(submission.department)
    title = f"{build_title(submission)} · 单模型测试"
    executive_summary = (
        f"当前已切换为单模型测试模式，由 {provider_name} / {model_name} 基于首个 Agent Role"
        f"（{role_name}）直接生成临床草案，未执行多智能体收敛流程。"
    )
    answer = generated_answer.strip() or build_professional_answer(submission, profile)
    next_steps = [
        "当前结果来自单模型直出，建议仅用于接口连通性与草案风格测试。",
        "如需正式会诊结论，请关闭单模型测试并重新运行多智能体路径。",
        "提交临床前，仍需由医生复核事实、适应证、编码与费用说明。",
        "如涉及高风险治疗或手术，请升级至 MDT 讨论与院内流程复核。",
    ]
    safety_note = (
        "当前为单模型测试输出，未经过多智能体交叉核查与收敛，"
        "不可作为诊断、手术或处方的唯一依据。"
    )
    return EngineResult(
        title=title,
        executive_summary=executive_summary,
        department=submission.department,
        output_style=submission.output_style,
        professional_answer=answer,
        coding_table=build_coding_table(submission),
        cost_table=build_cost_table(submission),
        references=references,
        next_steps=next_steps,
        safety_note=safety_note,
        rounds=[
            {
                "round": 1,
                "alignment": 1.0,
                "summary": f"单模型测试模式下，由 {provider_name} / {model_name} 直接完成首轮输出，未进入多模型协同。",
            }
        ],
        agent_trace=[
            {
                "role": role_name,
                "provider": provider_name,
                "note": f"单模型测试入口角色；角色说明：{role_spec}",
            }
        ],
        consensus_score=1.0,
        topology_used="Single Model",
        show_process=submission.show_process,
    )
