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

from rare_agents.models import AppProfile, CaseSubmission, EngineResult, SystemSettings
from rare_agents.provider_client import StreamCallback, request_chat_completion_stream


DECIDER_AGENT_NAME = "Decider"
DECIDER_TRIGGER_PATTERN = re.compile(r"@decider\b", re.IGNORECASE)
DECISION_STATUS_ZH = {
    "supported": "支持当前判断",
    "uncertain": "不确定",
    "insufficient_evidence": "证据不足",
}
WEIGHT_ZH_BY_EN = {"high": "高", "medium": "中", "low": "低"}
DISPLAY_STATUS_ZH_VALUES = set(DECISION_STATUS_ZH.values())
DISPLAY_WEIGHT_ZH_VALUES = set(WEIGHT_ZH_BY_EN.values())


def is_decider_invocation(text: str) -> bool:
    return bool(DECIDER_TRIGGER_PATTERN.search(str(text or "")))


def strip_decider_mention(text: str) -> str:
    cleaned = re.sub(r"@decider\b", "", str(text or ""), flags=re.IGNORECASE)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _normalize_provider_endpoint(raw: str) -> str:
    raw = str(raw or "").strip()
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
        first = choices[0]
        if isinstance(first, dict):
            message = first.get("message")
            if isinstance(message, dict):
                content = message.get("content")
                if isinstance(content, str):
                    return content
                if isinstance(content, list):
                    texts = [str(item.get("text", "")) for item in content if isinstance(item, dict) and item.get("type") == "text"]
                    if texts:
                        return "\n".join(texts)
            text = first.get("text")
            if isinstance(text, str):
                return text
    raise ValueError("Decider API response did not include usable text content.")


def _parse_json_text(raw: str) -> Any:
    text = str(raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE).strip()
        text = re.sub(r"```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
        raise


def _resolve_decider_provider(settings: SystemSettings) -> Any:
    role = next((item for item in settings.agent_roles if item.role_name.lower() == "decider"), None)
    if role is None:
        raise ValueError("Decider provider is not configured.")
    for provider in settings.api_providers:
        role_provider_id = str(getattr(role, "provider_id", "") or "").strip()
        provider_id = str(getattr(provider, "provider_id", "") or "").strip()
        if (
            ((role_provider_id and provider_id and provider_id == role_provider_id) or (not role_provider_id and provider.provider_name == role.provider_name))
            and provider.enabled
            and provider.endpoint
            and provider.api_key
            and provider.model_name
        ):
            return provider
    raise ValueError("Decider provider is not configured.")


def _decider_request(
    provider: Any,
    messages: list[dict[str, Any]],
    *,
    max_tokens: int,
    stream_callback: StreamCallback | None = None,
) -> str:
    url = f"{_normalize_provider_endpoint(provider.endpoint).rstrip('/')}/chat/completions"
    body = {
        "model": provider.model_name,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0,
    }
    if stream_callback is not None:
        return request_chat_completion_stream(
            url=url,
            api_key=provider.api_key,
            body=body,
            user_agent="RareMDT-Decider/0.1",
            on_delta=stream_callback,
        )
    payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {provider.api_key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Connection": "close",
        "User-Agent": "RareMDT-Decider/0.1",
    }
    last_error: Exception | None = None
    for attempt in range(3):
        request = urllib_request.Request(url, data=payload, headers=headers, method="POST")
        try:
            with urllib_request.urlopen(request, timeout=120) as response:
                response_payload = json.loads(response.read().decode("utf-8", errors="replace"))
            return _extract_chat_content(response_payload)
        except urllib_error.HTTPError as exc:
            detail = ""
            try:
                detail = exc.read().decode("utf-8", errors="replace").strip()
            except Exception:
                detail = ""
            last_error = RuntimeError(f"HTTP Error {exc.code}: {exc.reason}. {detail[:1000]}".strip())
            if attempt == 2:
                break
            time.sleep(1.0 + attempt)
        except (urllib_error.URLError, RemoteDisconnected, TimeoutError, ConnectionError, OSError) as exc:
            last_error = exc
            if attempt == 2:
                break
            time.sleep(1.0 + attempt)
    if last_error is not None:
        raise last_error
    raise ValueError("Decider request failed.")


def _compact_evidence_value(value: Any, *, depth: int = 0) -> Any:
    if depth > 4:
        return str(value)[:240]
    if isinstance(value, dict):
        skipped = {"boundary_points", "local_boundary_points", "mask_spans", "vision_probe"}
        return {str(key): _compact_evidence_value(val, depth=depth + 1) for key, val in value.items() if key not in skipped}
    if isinstance(value, list):
        return [_compact_evidence_value(item, depth=depth + 1) for item in value[:12]]
    if isinstance(value, str):
        return value[:1200]
    return value


def _evidence_packet(execution_bundle: dict[str, Any]) -> dict[str, Any]:
    records = execution_bundle.get("records")
    if not isinstance(records, list) or not records:
        raise ValueError("Decider requires completed Executor evidence records.")
    compact_records: list[dict[str, Any]] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        evidence = record.get("evidence") if isinstance(record.get("evidence"), dict) else {}
        display = record.get("display") if isinstance(record.get("display"), dict) else {}
        compact_records.append(
            {
                "evidence_id": f"E{int(record.get('step_id') or len(compact_records) + 1)}",
                "step_id": int(record.get("step_id") or len(compact_records) + 1),
                "action": str(record.get("action") or ""),
                "finding": str(record.get("finding") or ""),
                "tool_type": str(record.get("tool_type") or ""),
                "output_type": str(record.get("output_type") or ""),
                "display": _compact_evidence_value(display),
                "evidence": _compact_evidence_value(evidence),
            }
        )
    if not compact_records:
        raise ValueError("Decider requires usable Executor evidence records.")
    return {
        "plan_steps": _compact_evidence_value(execution_bundle.get("plan_steps") or []),
        "records": compact_records,
        "executor_provider": execution_bundle.get("provider", ""),
        "executor_model": execution_bundle.get("model", ""),
    }


def _known_evidence_ids(execution_bundle: dict[str, Any]) -> set[str]:
    records = execution_bundle.get("records")
    if not isinstance(records, list):
        return set()
    evidence_ids: set[str] = set()
    for record in records:
        if not isinstance(record, dict):
            continue
        step_id = int(record.get("step_id") or 0)
        if step_id > 0:
            evidence_ids.add(f"E{step_id}")
    return evidence_ids


def _decider_prompt(submission: CaseSubmission, profile: AppProfile, execution_bundle: dict[str, Any]) -> str:
    packet = _evidence_packet(execution_bundle)
    available_evidence_ids = sorted(_known_evidence_ids(execution_bundle))
    return dedent(
        f"""
        You are @Decider in a clinical evidence-based multi-agent workflow.
        Your only job is to synthesize Executor evidence into a diagnostic decision.
        You are not a report writer and you must not generate patient-facing prose.
        Treat Executor records as the only evidence source.

        Clinician/profile context:
        - department: {submission.department}
        - urgency: {submission.urgency}
        - chief_complaint: {submission.chief_complaint}
        - case_summary: {submission.case_summary}
        - patient_age: {submission.patient_age}
        - patient_sex: {submission.patient_sex}
        - hospital_context: {profile.hospital_name}

        Executor evidence packet:
        {json.dumps(packet, ensure_ascii=False, indent=2)}

        Available evidence IDs:
        {json.dumps(available_evidence_ids, ensure_ascii=False)}

        Return ONLY JSON with this exact top-level object shape:
        {{
          "diagnostic_impression": "",
          "diagnosis_confidence": 0.0,
          "decision_status": "supported|uncertain|insufficient_evidence",
          "key_evidence": [
            {{"evidence_id": "E1", "supports": "", "quote": "", "weight": "high|medium|low"}}
          ],
          "differential_diagnoses": [
            {{"name": "", "likelihood": "high|medium|low", "supporting_evidence_ids": ["E1"], "refuting_evidence_ids": ["E2"], "comment": ""}}
          ],
          "evidence_gaps": [""],
          "recommended_next_steps": [""],
          "safety_flags": [""],
          "human_review_points": [""],
          "display_zh": {{
            "decision_status_zh": "支持当前判断|不确定|证据不足",
            "diagnostic_impression_zh": "",
            "key_evidence": [
              {{"evidence_id": "E1", "supports_zh": "", "quote_zh": "", "weight_zh": "高|中|低"}}
            ],
            "differential_diagnoses": [
              {{"name_zh": "", "likelihood_zh": "高|中|低", "supporting_evidence_ids": ["E1"], "refuting_evidence_ids": ["E2"], "comment_zh": ""}}
            ],
            "evidence_gaps_zh": [""],
            "recommended_next_steps_zh": [""],
            "safety_flags_zh": [""],
            "human_review_points_zh": [""]
          }}
        }}

        Rules:
        - All top-level machine fields except display_zh must be in English for downstream agent execution.
        - display_zh must be concise Simplified Chinese for clinician-facing UI, while preserving the same evidence IDs and clinical meaning.
        - Every diagnostic claim must cite one or more Executor evidence_id values from the available evidence ID list.
        - If evidence is not sufficient, set decision_status to "insufficient_evidence" and lower diagnosis_confidence.
        - Do not cite plan steps as evidence unless an Executor record completed that step.
        - diagnostic_impression must be one concise clinical sentence.
        - key_evidence should contain the 3 to 5 most decision-relevant evidence items.
        - differential_diagnoses should contain at most 4 items.
        - recommended_next_steps should contain at most 5 action-oriented items.
        - safety_flags should be empty unless there is a concrete safety concern.
        - human_review_points should name what a doctor should approve, reject, or steer next.
        """
    ).strip()


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _normalize_evidence_id_list(value: Any, *, valid_ids: set[str], field: str, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list):
        if allow_empty:
            return []
        raise ValueError(f"Decider output field {field} must be a list.")
    cleaned = [str(item).strip() for item in value if str(item).strip()]
    if not cleaned and not allow_empty:
        raise ValueError(f"Decider output field {field} must cite at least one evidence id.")
    invalid = [item for item in cleaned if item not in valid_ids]
    if invalid:
        raise ValueError(f"Decider output field {field} contains unknown evidence ids: {', '.join(invalid)}")
    return cleaned


def _validate_decision(payload: Any, *, valid_evidence_ids: set[str]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Decider output is not a JSON object.")
    required = [
        "diagnostic_impression",
        "diagnosis_confidence",
        "decision_status",
        "key_evidence",
        "differential_diagnoses",
        "evidence_gaps",
        "recommended_next_steps",
        "safety_flags",
        "human_review_points",
    ]
    for key in required:
        if key not in payload:
            raise ValueError(f"Decider output is missing {key}.")
    status = str(payload["decision_status"]).strip()
    if status not in {"supported", "uncertain", "insufficient_evidence"}:
        raise ValueError("Decider output has invalid decision_status.")
    confidence = max(0.0, min(1.0, float(payload.get("diagnosis_confidence") or 0.0)))
    key_evidence = payload.get("key_evidence")
    differentials = payload.get("differential_diagnoses")
    if not isinstance(key_evidence, list) or not key_evidence:
        raise ValueError("Decider output must include key_evidence.")
    if not isinstance(differentials, list):
        raise ValueError("Decider output must include differential_diagnoses.")
    cleaned_key_evidence: list[dict[str, Any]] = []
    for index, item in enumerate(key_evidence, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Decider key_evidence item #{index} must be an object.")
        evidence_id = str(item.get("evidence_id") or "").strip()
        if evidence_id not in valid_evidence_ids:
            raise ValueError(f"Decider key_evidence item #{index} cites unknown evidence id: {evidence_id or 'empty'}")
        supports = str(item.get("supports") or "").strip()
        quote = str(item.get("quote") or "").strip()
        if not supports and not quote:
            raise ValueError(f"Decider key_evidence item #{index} must include supports or quote.")
        weight = str(item.get("weight") or "medium").strip().lower()
        if weight not in {"high", "medium", "low"}:
            raise ValueError(f"Decider key_evidence item #{index} has invalid weight.")
        cleaned_key_evidence.append(
            {
                "evidence_id": evidence_id,
                "supports": supports,
                "quote": quote,
                "weight": weight,
            }
        )
    cleaned_differentials: list[dict[str, Any]] = []
    for index, item in enumerate(differentials, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Decider differential item #{index} must be an object.")
        name = str(item.get("name") or "").strip()
        if not name:
            raise ValueError(f"Decider differential item #{index} is missing name.")
        likelihood = str(item.get("likelihood") or "").strip().lower()
        if likelihood not in {"high", "medium", "low"}:
            raise ValueError(f"Decider differential item #{index} has invalid likelihood.")
        supporting_ids = _normalize_evidence_id_list(
            item.get("supporting_evidence_ids"),
            valid_ids=valid_evidence_ids,
            field=f"differential_diagnoses[{index}].supporting_evidence_ids",
            allow_empty=True,
        )
        refuting_ids = _normalize_evidence_id_list(
            item.get("refuting_evidence_ids"),
            valid_ids=valid_evidence_ids,
            field=f"differential_diagnoses[{index}].refuting_evidence_ids",
            allow_empty=True,
        )
        if not supporting_ids and not refuting_ids:
            raise ValueError(f"Decider differential item #{index} must cite supporting or refuting evidence.")
        cleaned_differentials.append(
            {
                "name": name,
                "likelihood": likelihood,
                "supporting_evidence_ids": supporting_ids,
                "refuting_evidence_ids": refuting_ids,
                "comment": str(item.get("comment") or "").strip(),
            }
        )
    return {
        "diagnostic_impression": str(payload["diagnostic_impression"]).strip(),
        "diagnosis_confidence": round(confidence, 4),
        "decision_status": status,
        "key_evidence": cleaned_key_evidence,
        "differential_diagnoses": cleaned_differentials,
        "evidence_gaps": _string_list(payload.get("evidence_gaps")),
        "recommended_next_steps": _string_list(payload.get("recommended_next_steps")),
        "safety_flags": _string_list(payload.get("safety_flags")),
        "human_review_points": _string_list(payload.get("human_review_points")),
    }


def _validate_decision_display(payload: Any, *, valid_evidence_ids: set[str], decision: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Decider output is missing display_zh.")
    status_zh = str(payload.get("decision_status_zh") or "").strip()
    if status_zh not in DISPLAY_STATUS_ZH_VALUES:
        raise ValueError("Decider output field display_zh.decision_status_zh is invalid.")
    expected_status_zh = DECISION_STATUS_ZH.get(str(decision.get("decision_status") or "").strip())
    if expected_status_zh and status_zh != expected_status_zh:
        raise ValueError("Decider output field display_zh.decision_status_zh must match machine decision_status.")
    diagnostic_impression_zh = str(payload.get("diagnostic_impression_zh") or "").strip()
    if not diagnostic_impression_zh:
        raise ValueError("Decider output field display_zh.diagnostic_impression_zh is required.")
    key_evidence = payload.get("key_evidence")
    if not isinstance(key_evidence, list) or not key_evidence:
        raise ValueError("Decider output field display_zh.key_evidence must be a non-empty list.")
    cleaned_key_evidence: list[dict[str, Any]] = []
    for index, item in enumerate(key_evidence, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Decider display_zh.key_evidence item #{index} must be an object.")
        evidence_id = str(item.get("evidence_id") or "").strip()
        if evidence_id not in valid_evidence_ids:
            raise ValueError(f"Decider display_zh.key_evidence item #{index} cites unknown evidence id: {evidence_id or 'empty'}")
        supports_zh = str(item.get("supports_zh") or "").strip()
        quote_zh = str(item.get("quote_zh") or "").strip()
        if not supports_zh and not quote_zh:
            raise ValueError(f"Decider display_zh.key_evidence item #{index} must include supports_zh or quote_zh.")
        weight_zh = str(item.get("weight_zh") or "").strip()
        if weight_zh not in DISPLAY_WEIGHT_ZH_VALUES:
            raise ValueError(f"Decider display_zh.key_evidence item #{index} has invalid weight_zh.")
        cleaned_key_evidence.append(
            {
                "evidence_id": evidence_id,
                "supports_zh": supports_zh,
                "quote_zh": quote_zh,
                "weight_zh": weight_zh,
            }
        )
    expected_key_ids = {str(item.get("evidence_id") or "").strip() for item in decision.get("key_evidence", []) if str(item.get("evidence_id") or "").strip()}
    actual_key_ids = {item["evidence_id"] for item in cleaned_key_evidence}
    if expected_key_ids != actual_key_ids:
        raise ValueError("Decider output field display_zh.key_evidence must cover every machine-decision evidence_id exactly once.")
    machine_key_by_id = {
        str(item.get("evidence_id") or "").strip(): item
        for item in decision.get("key_evidence", [])
        if isinstance(item, dict) and str(item.get("evidence_id") or "").strip()
    }
    for item in cleaned_key_evidence:
        machine_item = machine_key_by_id.get(item["evidence_id"], {})
        expected_weight_zh = WEIGHT_ZH_BY_EN.get(str(machine_item.get("weight") or "").strip().lower())
        if expected_weight_zh and item["weight_zh"] != expected_weight_zh:
            raise ValueError(f"Decider output field display_zh.key_evidence for {item['evidence_id']} must match machine weight.")
    differentials = payload.get("differential_diagnoses")
    if not isinstance(differentials, list):
        raise ValueError("Decider output field display_zh.differential_diagnoses must be a list.")
    cleaned_differentials: list[dict[str, Any]] = []
    for index, item in enumerate(differentials, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Decider display_zh.differential_diagnoses item #{index} must be an object.")
        name_zh = str(item.get("name_zh") or "").strip()
        if not name_zh:
            raise ValueError(f"Decider display_zh.differential_diagnoses item #{index} is missing name_zh.")
        likelihood_zh = str(item.get("likelihood_zh") or "").strip()
        if likelihood_zh not in DISPLAY_WEIGHT_ZH_VALUES:
            raise ValueError(f"Decider display_zh.differential_diagnoses item #{index} has invalid likelihood_zh.")
        supporting_ids = _normalize_evidence_id_list(
            item.get("supporting_evidence_ids"),
            valid_ids=valid_evidence_ids,
            field=f"display_zh.differential_diagnoses[{index}].supporting_evidence_ids",
            allow_empty=True,
        )
        refuting_ids = _normalize_evidence_id_list(
            item.get("refuting_evidence_ids"),
            valid_ids=valid_evidence_ids,
            field=f"display_zh.differential_diagnoses[{index}].refuting_evidence_ids",
            allow_empty=True,
        )
        if not supporting_ids and not refuting_ids:
            raise ValueError(f"Decider display_zh.differential_diagnoses item #{index} must cite supporting or refuting evidence.")
        cleaned_differentials.append(
            {
                "name_zh": name_zh,
                "likelihood_zh": likelihood_zh,
                "supporting_evidence_ids": supporting_ids,
                "refuting_evidence_ids": refuting_ids,
                "comment_zh": str(item.get("comment_zh") or "").strip(),
            }
        )
    if len(cleaned_differentials) != len(decision.get("differential_diagnoses", [])):
        raise ValueError("Decider output field display_zh.differential_diagnoses must align one-to-one with machine differential_diagnoses.")
    for index, item in enumerate(cleaned_differentials):
        machine_item = decision.get("differential_diagnoses", [])[index] if index < len(decision.get("differential_diagnoses", [])) else {}
        expected_likelihood_zh = WEIGHT_ZH_BY_EN.get(str(machine_item.get("likelihood") or "").strip().lower())
        if expected_likelihood_zh and item["likelihood_zh"] != expected_likelihood_zh:
            raise ValueError(f"Decider output field display_zh.differential_diagnoses[{index + 1}].likelihood_zh must match machine likelihood.")
        if item["supporting_evidence_ids"] != list(machine_item.get("supporting_evidence_ids") or []):
            raise ValueError(f"Decider output field display_zh.differential_diagnoses[{index + 1}].supporting_evidence_ids must match machine supporting_evidence_ids.")
        if item["refuting_evidence_ids"] != list(machine_item.get("refuting_evidence_ids") or []):
            raise ValueError(f"Decider output field display_zh.differential_diagnoses[{index + 1}].refuting_evidence_ids must match machine refuting_evidence_ids.")
    evidence_gaps_zh = _string_list(payload.get("evidence_gaps_zh"))
    recommended_next_steps_zh = _string_list(payload.get("recommended_next_steps_zh"))
    safety_flags_zh = _string_list(payload.get("safety_flags_zh"))
    human_review_points_zh = _string_list(payload.get("human_review_points_zh"))
    if len(evidence_gaps_zh) != len(decision.get("evidence_gaps", [])):
        raise ValueError("Decider output field display_zh.evidence_gaps_zh must align with machine evidence_gaps.")
    if len(recommended_next_steps_zh) != len(decision.get("recommended_next_steps", [])):
        raise ValueError("Decider output field display_zh.recommended_next_steps_zh must align with machine recommended_next_steps.")
    if len(safety_flags_zh) != len(decision.get("safety_flags", [])):
        raise ValueError("Decider output field display_zh.safety_flags_zh must align with machine safety_flags.")
    if len(human_review_points_zh) != len(decision.get("human_review_points", [])):
        raise ValueError("Decider output field display_zh.human_review_points_zh must align with machine human_review_points.")
    return {
        "decision_status_zh": status_zh,
        "diagnostic_impression_zh": diagnostic_impression_zh,
        "key_evidence": cleaned_key_evidence,
        "differential_diagnoses": cleaned_differentials,
        "evidence_gaps_zh": evidence_gaps_zh,
        "recommended_next_steps_zh": recommended_next_steps_zh,
        "safety_flags_zh": safety_flags_zh,
        "human_review_points_zh": human_review_points_zh,
    }


def _decision_markdown(decision: dict[str, Any], display: dict[str, Any] | None = None) -> str:
    display = display or {}
    display_key_evidence = display.get("key_evidence") if isinstance(display.get("key_evidence"), list) else []
    display_key_by_id = {
        str(item.get("evidence_id") or "").strip(): item
        for item in display_key_evidence
        if isinstance(item, dict) and str(item.get("evidence_id") or "").strip()
    }
    display_differentials = display.get("differential_diagnoses") if isinstance(display.get("differential_diagnoses"), list) else []
    evidence_lines = "\n".join(
        (
            lambda display_item, item=item: (
                f"- [{item.get('evidence_id')}] "
                f"{display_item.get('supports_zh') or display_item.get('quote_zh') or item.get('supports') or item.get('quote') or ''}"
                f"（权重：{display_item.get('weight_zh') or item.get('weight', 'medium')}）"
            )
        )(display_key_by_id.get(str(item.get("evidence_id") or "").strip(), {}))
        for item in decision.get("key_evidence", [])
    )
    differential_lines = "\n".join(
        (
            lambda display_item, item=item: (
                f"- {display_item.get('name_zh') or item.get('name', '')}"
                f"：{display_item.get('likelihood_zh') or item.get('likelihood', '')}"
                f"；支持 {', '.join(item.get('supporting_evidence_ids') or []) or '无'}"
                f"；反证 {', '.join(item.get('refuting_evidence_ids') or []) or '无'}。"
                f"{display_item.get('comment_zh') or item.get('comment', '')}"
            )
        )(display_differentials[index] if index < len(display_differentials) and isinstance(display_differentials[index], dict) else {})
        for index, item in enumerate(decision.get("differential_diagnoses", []))
    )
    gaps = "\n".join(f"- {item}" for item in display.get("evidence_gaps_zh", [])) or "- 未列出"
    next_steps = "\n".join(f"- {item}" for item in display.get("recommended_next_steps_zh", [])) or "- 未列出"
    review = "\n".join(f"- {item}" for item in display.get("human_review_points_zh", [])) or "- 请医生复核关键证据与诊断结论"
    return dedent(
        f"""
        **诊断判断**
        {display.get('diagnostic_impression_zh') or decision['diagnostic_impression']}

        **证据依据**
        {evidence_lines}

        **鉴别诊断**
        {differential_lines or "- 未列出"}

        **证据缺口**
        {gaps}

        **建议下一步**
        {next_steps}

        **医生复核 / Steer 点**
        {review}
        """
    ).strip()


def run_decider_case(
    submission: CaseSubmission,
    profile: AppProfile,
    settings: SystemSettings,
    *,
    execution_bundle: dict[str, Any] | None = None,
    stream_callback: StreamCallback | None = None,
) -> EngineResult:
    if execution_bundle is None:
        raise ValueError("Decider requires completed Executor evidence in the current context. Invoke @Executor first.")
    provider = _resolve_decider_provider(settings)
    valid_evidence_ids = _known_evidence_ids(execution_bundle)
    if not valid_evidence_ids:
        raise ValueError("Decider requires valid Executor evidence ids in the current context.")
    raw = _decider_request(
        provider,
        [
            {"role": "system", "content": "You are @Decider. Return only strict JSON grounded in provided evidence IDs."},
            {"role": "user", "content": _decider_prompt(submission, profile, execution_bundle)},
        ],
        max_tokens=3200,
        stream_callback=stream_callback,
    )
    payload = _parse_json_text(raw)
    decision = _validate_decision(payload, valid_evidence_ids=valid_evidence_ids)
    decision_display = _validate_decision_display(payload.get("display_zh"), valid_evidence_ids=valid_evidence_ids, decision=decision)
    confidence = float(decision["diagnosis_confidence"])
    display_key_by_id = {
        str(item.get("evidence_id") or "").strip(): item
        for item in decision_display["key_evidence"]
        if isinstance(item, dict)
    }
    return EngineResult(
        title=f"Decider 诊断判断：{submission.chief_complaint or '当前病例'}",
        executive_summary=(
            f"@Decider 已基于 {len((execution_bundle or {}).get('records') or [])} 条执行证据形成诊断判断，"
            f"状态：{decision_display['decision_status_zh']}。"
        ),
        department=submission.department,
        output_style=submission.output_style,
        professional_answer=_decision_markdown(decision, decision_display),
        coding_table=[],
        cost_table=[],
        references=[
            {
                "type": "executor_evidence",
                "title": item.get("evidence_id", ""),
                "region": (
                    (display_key_by_id.get(str(item.get("evidence_id") or "").strip(), {}) or {}).get("supports_zh")
                    or item.get("supports", "")
                ),
            }
            for item in decision["key_evidence"]
        ],
        next_steps=decision_display["recommended_next_steps_zh"] or decision["recommended_next_steps"],
        safety_note="该输出是证据融合判断，必须由医生复核后进入正式诊疗记录。",
        rounds=[
            {
                "round": 1,
                "alignment": confidence,
                "summary": "Decider collected Executor evidence, weighed support/refutation, and produced an evidence-cited diagnostic impression.",
            }
        ],
        agent_trace=[
            {
                "role": DECIDER_AGENT_NAME,
                "provider": provider.provider_name,
                "note": "Synthesized Executor evidence into an evidence-cited diagnostic decision.",
            }
        ],
        consensus_score=confidence,
        topology_used="Decider",
        show_process=submission.show_process,
        execution_mode="decider",
        serving_provider=provider.provider_name,
        serving_model=provider.model_name,
        activated_agent=DECIDER_AGENT_NAME,
        plan_steps=list((execution_bundle or {}).get("plan_steps") or []),
        plan_display_steps=list((execution_bundle or {}).get("plan_display_steps") or []),
        execution_records=list((execution_bundle or {}).get("records") or []),
        raw_model_text=raw,
        raw_provider_payload=json.dumps(decision, ensure_ascii=False),
        display_payload=json.dumps(decision_display, ensure_ascii=False),
        workflow_revision=str((execution_bundle or {}).get("workflow_revision") or "").strip(),
    )
