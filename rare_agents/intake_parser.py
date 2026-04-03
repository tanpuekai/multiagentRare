from __future__ import annotations

import re
from dataclasses import dataclass

from rare_agents.models import DepartmentOption


@dataclass
class IntakePrefill:
    department: str
    output_style: str
    urgency: str
    chief_complaint: str
    case_summary: str
    patient_age: str
    patient_sex: str
    insurance_type: str


DEPARTMENT_KEYWORDS = {
    DepartmentOption.ORTHOPEDICS.value: [
        "骨科",
        "骨",
        "脊柱",
        "关节",
        "肌骨",
        "skeletal",
        "orthopedic",
        "orthopaedic",
        "bone",
        "fracture",
    ],
    DepartmentOption.NEUROLOGY.value: [
        "神经",
        "脑",
        "脊髓",
        "癫痫",
        "neurology",
        "neuromuscular",
        "neuro",
        "seizure",
    ],
    DepartmentOption.PEDIATRICS.value: [
        "儿科",
        "儿童",
        "小儿",
        "婴儿",
        "新生儿",
        "pediatric",
        "paediatric",
        "child",
        "infant",
        "neonate",
    ],
    DepartmentOption.ICU.value: [
        "icu",
        "重症",
        "危重",
        "监护",
        "intensive care",
        "ventilator",
        "shock",
    ],
    DepartmentOption.EMERGENCY.value: [
        "急诊",
        "a&e",
        "er",
        "emergency",
        "创伤",
        "抢救",
        "急性",
    ],
    DepartmentOption.PULMONARY.value: [
        "呼吸",
        "肺",
        "pulmonary",
        "lung",
        "interstitial",
        "dyspnea",
        "咳嗽",
        "气促",
    ],
    DepartmentOption.GENETICS.value: [
        "遗传",
        "基因",
        "变异",
        "genetic",
        "genomics",
        "mutation",
        "exome",
    ],
    DepartmentOption.MULTIDISCIPLINARY.value: [
        "罕见病",
        "mdt",
        "多学科",
        "multidisciplinary",
        "cross-specialty",
    ],
}


CHIEF_COMPLAINT_LABELS = ["主诉", "Chief Complaint", "chief complaint", "CC", "C/C"]
AGE_LABELS = ["年龄", "Age"]
SEX_LABELS = ["性别", "Sex", "Gender"]
INSURANCE_LABELS = ["医保", "支付方式", "保险", "Insurance", "Payment"]
DEPARTMENT_LABELS = ["科室", "就诊科室", "Department", "Service"]
URGENCY_LABELS = ["紧急程度", "急诊分级", "Urgency", "Priority"]


def _normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _extract_labeled_value(text: str, labels: list[str]) -> str:
    for label in labels:
        pattern = re.compile(rf"(?:^|\n)\s*{re.escape(label)}\s*[:：]\s*(.+)", re.IGNORECASE)
        match = pattern.search(text)
        if match:
            return match.group(1).strip()
    return ""


def _extract_age(text: str) -> str:
    labeled = _extract_labeled_value(text, AGE_LABELS)
    if labeled:
        return labeled[:32]

    patterns = [
        re.compile(r"(\d{1,3})\s*(岁|个月|月|天)"),
        re.compile(r"(\d{1,3})\s*(years?\s*old|year-old|yrs?\s*old|yrs?|y/o|yo)\b", re.IGNORECASE),
    ]
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            return " ".join(part for part in match.groups() if part).strip()
    return ""


def _extract_sex(text: str) -> str:
    labeled = _extract_labeled_value(text, SEX_LABELS).lower()
    if labeled:
        if "男" in labeled or "male" in labeled or "boy" in labeled:
            return "Male"
        if "女" in labeled or "female" in labeled or "girl" in labeled:
            return "Female"

    lowered = text.lower()
    if re.search(r"(性别\s*[:：]?\s*男)|(\bmale\b)|(\bman\b)|(\bboy\b)|男婴|男性", text, re.IGNORECASE):
        return "Male"
    if re.search(r"(性别\s*[:：]?\s*女)|(\bfemale\b)|(\bwoman\b)|(\bgirl\b)|女婴|女性", text, re.IGNORECASE):
        return "Female"
    return "Unknown"


def _extract_insurance(text: str) -> str:
    labeled = _extract_labeled_value(text, INSURANCE_LABELS)
    lowered = f"{labeled}\n{text}".lower()
    if any(token in lowered for token in ["自费", "self-pay", "uninsured", "无医保", "cash pay"]):
        return "Self-pay / uninsured"
    if any(token in lowered for token in ["职工医保", "employee insurance", "职工"]):
        return "Employee insurance"
    if any(token in lowered for token in ["居民医保", "resident insurance", "城乡居民", "居民"]):
        return "Resident insurance"
    if any(token in lowered for token in ["商业保险", "commercial insurance", "commercial"]):
        return "Commercial"
    return "Resident insurance"


def _extract_urgency(text: str) -> str:
    labeled = _extract_labeled_value(text, URGENCY_LABELS).lower()
    lowered = f"{labeled}\n{text}".lower()
    emergency_tokens = ["急诊", "抢救", "危急", "emergency", "shock", "respiratory failure", "icu", "危重"]
    priority_tokens = ["加急", "priority", "urgent", "尽快", "expedite"]
    if any(token in lowered for token in emergency_tokens):
        return "Emergency"
    if any(token in lowered for token in priority_tokens):
        return "Priority"
    return "Routine"


def _extract_department(text: str, default_department: str) -> str:
    labeled = _extract_labeled_value(text, DEPARTMENT_LABELS).lower()
    scored: dict[str, int] = {department: 0 for department in DEPARTMENT_KEYWORDS}

    haystack = f"{labeled}\n{text}".lower()
    for department, keywords in DEPARTMENT_KEYWORDS.items():
        for keyword in keywords:
            if keyword.lower() in haystack:
                scored[department] += 1

    best_department = max(scored, key=scored.get)
    if scored[best_department] == 0:
        return default_department

    top_score = scored[best_department]
    top_departments = [department for department, score in scored.items() if score == top_score and score > 0]
    if len(top_departments) > 1:
        mdt_tokens = DEPARTMENT_KEYWORDS[DepartmentOption.MULTIDISCIPLINARY.value]
        if any(token.lower() in haystack for token in mdt_tokens):
            return DepartmentOption.MULTIDISCIPLINARY.value
        if default_department in top_departments:
            return default_department
        return top_departments[0]

    if DepartmentOption.MULTIDISCIPLINARY.value == best_department and default_department != best_department:
        return DepartmentOption.MULTIDISCIPLINARY.value
    return best_department


def _extract_output_style(text: str) -> str:
    lowered = text.lower()
    treatment_tokens = [
        "手术",
        "术前",
        "术后",
        "切除",
        "固定",
        "介入",
        "麻醉",
        "operative",
        "operation",
        "surgery",
        "resection",
        "fusion",
        "management plan",
        "treatment plan",
        "治疗方案",
    ]
    matches = sum(1 for token in treatment_tokens if token in lowered)
    return "Surgical / Treatment Plan" if matches >= 1 else "Diagnostic"


def _extract_chief_complaint(text: str) -> str:
    labeled = _extract_labeled_value(text, CHIEF_COMPLAINT_LABELS)
    if labeled:
        return labeled[:120].strip("。.;； ")

    for line in text.splitlines():
        cleaned = line.strip()
        if not cleaned:
            continue
        if len(cleaned) <= 120:
            return cleaned.strip("。.;； ")

    sentence = re.split(r"[。\n.;；]", text, maxsplit=1)[0]
    return sentence[:120].strip()


def parse_ehr_intake(text: str, default_department: str) -> IntakePrefill:
    normalized = _normalize_text(text)
    return IntakePrefill(
        department=_extract_department(normalized, default_department),
        output_style=_extract_output_style(normalized),
        urgency=_extract_urgency(normalized),
        chief_complaint=_extract_chief_complaint(normalized),
        case_summary=normalized[:5000],
        patient_age=_extract_age(normalized),
        patient_sex=_extract_sex(normalized),
        insurance_type=_extract_insurance(normalized),
    )
