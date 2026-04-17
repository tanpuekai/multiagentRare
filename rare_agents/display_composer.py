from __future__ import annotations

import json
import re
import time
from http.client import RemoteDisconnected
from textwrap import dedent
from typing import Any
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request

from rare_agents.models import CaseSubmission


PLAN_DISPLAY_FIELDS = ("id", "title_zh", "goal_zh", "evidence_zh", "human_check_zh", "tag_zh")
EXECUTION_DISPLAY_FIELDS = (
    "step_id",
    "title_zh",
    "conclusion_zh",
    "evidence_summary_zh",
    "human_check_zh",
    "tag_zh",
)

PLACEHOLDER_PATTERNS = [
    r"\bcurrent\s+finding\b",
    r"\btarget\s+finding\b",
    r"\bdiagnostic\s+finding\b",
    r"\bstep\s+\d+\b",
    r"当前征象",
    r"目标征象",
    r"当前诊断步骤",
    r"步骤\s*\d+",
]

PLAN_TAGS = {"定位", "量化", "证据", "解读"}
EXECUTION_TAGS = {"完成", "处理中"}
ALLOWED_LATIN_TERMS = [
    "BI-RADS",
    "PI-RADS",
    "LI-RADS",
    "PET-CT",
    "CT",
    "MRI",
    "PET",
    "SPECT",
    "OCT",
    "TNM",
    "DNA",
    "RNA",
    "HER2",
    "ER",
    "PR",
    "Ki-67",
    "p53",
    "HbA1c",
    "eGFR",
    "CK",
    "LDH",
    "VLM",
    "cm",
    "mm",
    "ml",
    "mL",
    "kg",
    "mg",
    "mmHg",
]


def _normalize_endpoint(endpoint: str) -> str:
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


def _extract_chat_content(payload: dict[str, Any]) -> str:
    choices = payload.get("choices")
    if isinstance(choices, list) and choices:
        message = choices[0].get("message", {}) if isinstance(choices[0], dict) else {}
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            return content.strip()
        if isinstance(content, list):
            parts = [str(item.get("text", "")) for item in content if isinstance(item, dict) and item.get("type") == "text"]
            text = "\n".join(part for part in parts if part).strip()
            if text:
                return text
    raise ValueError("Display composer API response did not include usable text content.")


def _parse_json_text(text: str) -> Any:
    raw = str(text or "").strip()
    if not raw:
        raise json.JSONDecodeError("Expecting value", raw, 0)
    if raw.startswith("```"):
        chunks = raw.split("```")
        for chunk in chunks:
            candidate = chunk.strip()
            if not candidate:
                continue
            if candidate.lower().startswith("json"):
                candidate = candidate[4:].strip()
            if candidate.startswith("[") or candidate.startswith("{"):
                return json.loads(candidate)
    return json.loads(raw)


def _request_display_json(provider: Any, messages: list[dict[str, Any]], *, max_tokens: int) -> Any:
    url = f"{_normalize_endpoint(provider.endpoint).rstrip('/')}/chat/completions"
    payload = json.dumps(
        {
            "model": provider.model_name,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0,
        }
    ).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {provider.api_key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Connection": "close",
        "User-Agent": "RareMDT-DisplayComposer/0.1",
    }
    last_error: Exception | None = None
    for attempt in range(3):
        request = urllib_request.Request(url, data=payload, headers=headers, method="POST")
        try:
            with urllib_request.urlopen(request, timeout=120) as response:
                response_payload = json.loads(response.read().decode("utf-8", errors="replace"))
            content = _extract_chat_content(response_payload)
            return _parse_json_text(content)
        except (urllib_error.URLError, urllib_error.HTTPError, RemoteDisconnected, TimeoutError, ConnectionError, OSError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt == 2:
                break
            time.sleep(1.0 + attempt)
    raise ValueError(f"Display composer request failed: {last_error}") from last_error


def _compose_validated_display(
    *,
    provider: Any,
    system_prompt: str,
    user_prompt: str,
    validator: Any,
    max_tokens: int,
    label: str,
) -> list[dict[str, Any]]:
    messages = [
        {
            "role": "system",
            "content": system_prompt,
        },
        {
            "role": "user",
            "content": user_prompt,
        },
    ]
    last_error: ValueError | None = None
    for attempt in range(3):
        raw = _request_display_json(provider, messages, max_tokens=max_tokens)
        try:
            return validator(raw)
        except ValueError as exc:
            last_error = exc
            if attempt == 2:
                break
            messages = [
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
                {
                    "role": "assistant",
                    "content": json.dumps(raw, ensure_ascii=False, indent=2),
                },
                {
                    "role": "user",
                    "content": dedent(
                        f"""
                        The previous JSON failed strict validation:
                        {exc}

                        Return the complete corrected JSON array only.
                        Keep the same ids, order, and schema.
                        Rewrite every clinician-facing field in Simplified Chinese.
                        Do not copy descriptive English nouns or adjectives from the backend evidence.
                        Preserve only standard uppercase medical abbreviations when clinically necessary.
                        """
                    ).strip(),
                },
            ]
    raise ValueError(f"{label} failed strict validation after 3 attempts: {last_error}") from last_error


def _has_placeholder(text: str) -> bool:
    lowered = text.lower()
    return any(re.search(pattern, lowered, flags=re.IGNORECASE) for pattern in PLACEHOLDER_PATTERNS)


def _assert_zh_text(value: object, *, field: str) -> str:
    text = " ".join(str(value or "").split()).strip()
    if not text:
        raise ValueError(f"Display field {field} is empty.")
    if _has_placeholder(text):
        raise ValueError(f"Display field {field} contains placeholder wording: {text}")
    if not re.search(r"[\u4e00-\u9fff]", text):
        raise ValueError(f"Display field {field} must be written in Chinese.")
    latin_checked = text
    for term in ALLOWED_LATIN_TERMS:
        latin_checked = re.sub(re.escape(term), "", latin_checked, flags=re.IGNORECASE)
    if re.search(r"[A-Za-z]", latin_checked):
        raise ValueError(f"Display field {field} contains untranslated English: {text}")
    return text


def _assert_tag(value: object, *, field: str, allowed: set[str]) -> str:
    tag = _assert_zh_text(value, field=field)
    if tag not in allowed:
        raise ValueError(f"Display field {field} has unsupported tag: {tag}")
    return tag


def _compact_text(value: object, *, limit: int = 360) -> str:
    text = " ".join(str(value or "").split()).strip()
    if len(text) <= limit:
        return text
    return f"{text[: limit - 1]}..."


def _round_coord(value: object) -> float:
    try:
        return round(float(value), 3)
    except (TypeError, ValueError):
        return 0.0


def _compact_coord_list(value: object, *, expected_len: int) -> list[float]:
    if not isinstance(value, list):
        return []
    return [_round_coord(item) for item in value[:expected_len]]


def _compact_measurements(value: object) -> Any:
    if isinstance(value, dict):
        compact: dict[str, Any] = {}
        for key, item in value.items():
            if isinstance(item, (int, float)):
                compact[str(key)] = round(float(item), 4)
            elif isinstance(item, dict):
                compact[str(key)] = _compact_measurements(item)
            elif isinstance(item, list):
                compact[str(key)] = [_compact_measurements(entry) for entry in item[:8]]
            else:
                compact[str(key)] = _compact_text(item, limit=120)
        return compact
    if isinstance(value, list):
        return [_compact_measurements(item) for item in value[:8]]
    if isinstance(value, (int, float)):
        return round(float(value), 4)
    return _compact_text(value, limit=120)


def _compact_grounding(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    boundary_points = value.get("boundary_points")
    if not isinstance(boundary_points, list):
        boundary_points = value.get("polygon")
    compact = {
        "bbox": _compact_coord_list(value.get("bbox") or value.get("coarse_bbox"), expected_len=4),
        "mask_bbox": _compact_coord_list(value.get("mask_bbox"), expected_len=4),
        "positive_point": _compact_coord_list(value.get("positive_point"), expected_len=2),
        "boundary_point_count": len(boundary_points) if isinstance(boundary_points, list) else 0,
        "mask_size": _compact_coord_list(value.get("mask_size"), expected_len=2),
        "mask_row_count": len(value.get("mask_spans")) if isinstance(value.get("mask_spans"), list) else 0,
        "mask_area_ratio_image": round(float(value.get("mask_area_ratio_image")), 4) if isinstance(value.get("mask_area_ratio_image"), (int, float)) else 0,
    }
    return {key: item for key, item in compact.items() if item not in ([], "", 0)}


def _compact_evidence(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    compact: dict[str, Any] = {}
    for key in ("artifact_type", "target_label", "conclusion", "confidence", "logical_output_path"):
        if key in value:
            item = value.get(key)
            compact[key] = round(float(item), 4) if isinstance(item, (int, float)) else _compact_text(item, limit=180)
    if value.get("rationale"):
        compact["rationale"] = _compact_text(value.get("rationale"), limit=260)
    if value.get("measurements") is not None:
        compact["measurements"] = _compact_measurements(value.get("measurements"))
    grounding = _compact_grounding(value.get("grounding"))
    if grounding:
        compact["grounding"] = grounding
    validation = value.get("validation")
    if isinstance(validation, dict) and validation:
        compact["validation"] = _compact_measurements(validation)
    return compact


def _compact_plan_step(step: dict[str, Any]) -> dict[str, Any]:
    tool_config = step.get("tool_config") if isinstance(step.get("tool_config"), dict) else {}
    return {
        "id": step.get("id"),
        "tool_type": tool_config.get("tool_type"),
        "action_type": step.get("action_type"),
        "finding": _compact_text(step.get("finding"), limit=220),
        "action": _compact_text(step.get("action"), limit=260),
        "input_type": step.get("input_type"),
        "output_type": step.get("output_type"),
        "relative_to_step": step.get("relative_to_step"),
    }


def _combine_plan_desc(item: dict[str, str]) -> str:
    return f"{item['goal_zh']} {item['evidence_zh']} 人工核查：{item['human_check_zh']}"


def _combine_execution_desc(item: dict[str, str]) -> str:
    return f"{item['evidence_summary_zh']} 人工核查：{item['human_check_zh']}"


def _submission_context(submission: CaseSubmission) -> dict[str, Any]:
    return {
        "department": submission.department,
        "urgency": submission.urgency,
        "chief_complaint": submission.chief_complaint,
        "case_summary": submission.case_summary,
        "patient_age": submission.patient_age,
        "patient_sex": submission.patient_sex,
        "uploaded_images": submission.uploaded_images,
        "uploaded_docs": submission.uploaded_docs,
    }


def _plan_display_prompt(
    *,
    submission: CaseSubmission,
    plan_steps: list[dict[str, Any]],
    visual_profile: dict[str, Any] | None,
    rag_text: str,
) -> str:
    return dedent(
        f"""
        You are the display composer for a clinical multi-agent system.
        The executable plan below is the backend contract and must remain English.
        Your task is to produce a human-readable Simplified Chinese display plan for clinicians.

        Source case:
        {json.dumps(_submission_context(submission), ensure_ascii=False, indent=2)}

        Visual profile:
        {json.dumps(visual_profile or {}, ensure_ascii=False, indent=2)}

        Retrieved planning context:
        {rag_text}

        English executable plan:
        {json.dumps(plan_steps, ensure_ascii=False, indent=2)}

        Return ONLY a strict JSON array. One display object per executable step.
        Required schema:
        [
          {{
            "id": 1,
            "title_zh": "简短中文标题",
            "goal_zh": "说明本步骤要完成什么诊断子任务",
            "evidence_zh": "说明下游 agent 必须产出什么证据",
            "human_check_zh": "说明医生核查时应该看什么",
            "tag_zh": "定位|量化|证据|解读"
          }}
        ]

        Rules:
        - Preserve the executable step ids exactly and in the same order.
        - Do not translate word-by-word; explain the clinical purpose of each step.
        - Do not add diagnosis, report generation, decider fusion, or treatment advice.
        - Do not use placeholders such as 当前征象, 目标征象, 步骤4, current finding, target finding.
        - Use concise Simplified Chinese. Translate all descriptive English words into Chinese.
        - Do not copy English nouns or adjectives from the backend plan into Chinese fields.
        - Standard uppercase medical abbreviations are allowed only when clinically necessary.
        """
    ).strip()


def compose_plan_display(
    *,
    provider: Any,
    submission: CaseSubmission,
    plan_steps: list[dict[str, Any]],
    visual_profile: dict[str, Any] | None,
    rag_text: str,
) -> list[dict[str, Any]]:
    prompt = _plan_display_prompt(
        submission=submission,
        plan_steps=plan_steps,
        visual_profile=visual_profile,
        rag_text=rag_text,
    )
    return _compose_validated_display(
        provider=provider,
        system_prompt="You compose clinician-facing UI text from strict backend plans. Return only JSON.",
        user_prompt=prompt,
        validator=lambda raw: validate_plan_display(raw, plan_steps),
        max_tokens=2400,
        label="Plan display composition",
    )


def validate_plan_display(raw: Any, plan_steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        raise ValueError("Plan display composer output must be a JSON array.")
    expected_ids = [int(step.get("id") or index) for index, step in enumerate(plan_steps, start=1)]
    if len(raw) != len(expected_ids):
        raise ValueError("Plan display composer output length does not match executable plan length.")
    cleaned: list[dict[str, Any]] = []
    seen_ids: list[int] = []
    for index, item in enumerate(raw, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Plan display item #{index} must be an object.")
        missing = [field for field in PLAN_DISPLAY_FIELDS if field not in item]
        if missing:
            raise ValueError(f"Plan display item #{index} is missing fields: {', '.join(missing)}")
        step_id = int(item["id"])
        seen_ids.append(step_id)
        display_item = {
            "id": step_id,
            "title_zh": _assert_zh_text(item["title_zh"], field=f"plan[{step_id}].title_zh"),
            "goal_zh": _assert_zh_text(item["goal_zh"], field=f"plan[{step_id}].goal_zh"),
            "evidence_zh": _assert_zh_text(item["evidence_zh"], field=f"plan[{step_id}].evidence_zh"),
            "human_check_zh": _assert_zh_text(item["human_check_zh"], field=f"plan[{step_id}].human_check_zh"),
            "tag_zh": _assert_tag(item["tag_zh"], field=f"plan[{step_id}].tag_zh", allowed=PLAN_TAGS),
        }
        display_item["desc_zh"] = _combine_plan_desc(display_item)
        cleaned.append(display_item)
    if seen_ids != expected_ids:
        raise ValueError(f"Plan display ids {seen_ids} do not match executable plan ids {expected_ids}.")
    return cleaned


def _execution_display_prompt(
    *,
    submission: CaseSubmission,
    plan_steps: list[dict[str, Any]],
    records: list[dict[str, Any]],
) -> str:
    compact_plan_steps = [_compact_plan_step(step) for step in plan_steps]
    compact_records = [
        {
            "step_id": record.get("step_id"),
            "action": _compact_text(record.get("action"), limit=260),
            "finding": _compact_text(record.get("finding"), limit=220),
            "tool_type": record.get("tool_type"),
            "output_type": record.get("output_type"),
            "evidence": _compact_evidence(record.get("evidence")),
        }
        for record in records
    ]
    return dedent(
        f"""
        You are the evidence display composer for a clinical multi-agent system.
        The executor records below are backend evidence objects. Compose clinician-facing Simplified Chinese summaries.

        Source case:
        {json.dumps(_submission_context(submission), ensure_ascii=False, indent=2)}

        Compact English executable plan:
        {json.dumps(compact_plan_steps, ensure_ascii=False, indent=2)}

        Compact executor evidence records:
        {json.dumps(compact_records, ensure_ascii=False, indent=2)}

        Return ONLY a strict JSON array. One display object per executor record.
        Required schema:
        [
          {{
            "step_id": 1,
            "title_zh": "简短中文标题",
            "conclusion_zh": "当前结论：明确说明支持/不支持/无法确定哪个具体征象或已完成哪个量化任务",
            "evidence_summary_zh": "概括该步骤的关键证据，不要泛泛说支持",
            "human_check_zh": "说明医生核查本步骤证据图或量化结果时应该看什么",
            "tag_zh": "完成|处理中"
          }}
        ]

        Rules:
        - Preserve step_id exactly and in the same order.
        - conclusion_zh must name the concrete finding or quantification target.
        - If the evidence has grounding coordinates, mention that the corresponding evidence figure should be checked.
        - Do not invent image quadrants or anatomical locations from bbox values. If location is not explicitly anatomical, say "证据图中标注区域".
        - If an evidence rationale mentions a crop quadrant, do not convert it into a full-image location.
        - Do not create a final diagnosis or treatment recommendation.
        - Do not use placeholders such as 当前征象, 目标征象, 当前诊断步骤, current finding, target finding.
        - Use concise Simplified Chinese. Translate all descriptive English words into Chinese.
        - Do not copy English nouns or adjectives from backend evidence into Chinese fields.
        - Standard uppercase medical abbreviations are allowed only when clinically necessary.
        """
    ).strip()


def compose_execution_display(
    *,
    provider: Any,
    submission: CaseSubmission,
    plan_steps: list[dict[str, Any]],
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    prompt = _execution_display_prompt(submission=submission, plan_steps=plan_steps, records=records)
    return _compose_validated_display(
        provider=provider,
        system_prompt="You compose clinician-facing UI text from strict executor evidence records. Return only JSON.",
        user_prompt=prompt,
        validator=lambda raw: validate_execution_display(raw, records),
        max_tokens=2600,
        label="Executor display composition",
    )


def validate_execution_display(raw: Any, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        raise ValueError("Execution display composer output must be a JSON array.")
    expected_ids = [int(record.get("step_id") or index) for index, record in enumerate(records, start=1)]
    if len(raw) != len(expected_ids):
        raise ValueError("Execution display composer output length does not match executor record length.")
    cleaned: list[dict[str, Any]] = []
    seen_ids: list[int] = []
    for index, item in enumerate(raw, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Execution display item #{index} must be an object.")
        missing = [field for field in EXECUTION_DISPLAY_FIELDS if field not in item]
        if missing:
            raise ValueError(f"Execution display item #{index} is missing fields: {', '.join(missing)}")
        step_id = int(item["step_id"])
        seen_ids.append(step_id)
        display_item = {
            "step_id": step_id,
            "title_zh": _assert_zh_text(item["title_zh"], field=f"execution[{step_id}].title_zh"),
            "conclusion_zh": _assert_zh_text(item["conclusion_zh"], field=f"execution[{step_id}].conclusion_zh"),
            "evidence_summary_zh": _assert_zh_text(item["evidence_summary_zh"], field=f"execution[{step_id}].evidence_summary_zh"),
            "human_check_zh": _assert_zh_text(item["human_check_zh"], field=f"execution[{step_id}].human_check_zh"),
            "tag_zh": _assert_tag(item["tag_zh"], field=f"execution[{step_id}].tag_zh", allowed=EXECUTION_TAGS),
        }
        display_item["desc_zh"] = _combine_execution_desc(display_item)
        cleaned.append(display_item)
    if seen_ids != expected_ids:
        raise ValueError(f"Execution display ids {seen_ids} do not match executor record ids {expected_ids}.")
    return cleaned
