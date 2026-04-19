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


REPORT_AGENT_NAME = "Report Generator"
REPORT_TRIGGER_PATTERN = re.compile(r"@(?:report\s*generator|reportgenerator|report)\b", re.IGNORECASE)


def is_report_invocation(text: str) -> bool:
    return bool(REPORT_TRIGGER_PATTERN.search(str(text or "")))


def strip_report_mention(text: str) -> str:
    cleaned = re.sub(r"@(?:report\s*generator|reportgenerator|report)\b", "", str(text or ""), flags=re.IGNORECASE)
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
    raise ValueError("Report Generator API response did not include usable text content.")


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


def _resolve_report_provider(settings: SystemSettings) -> Any:
    role = next((item for item in settings.agent_roles if item.role_name.lower() == "report generator"), None)
    if role is None:
        raise ValueError("Report Generator provider is not configured.")
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
    raise ValueError("Report Generator provider is not configured.")


def _report_request(
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
            user_agent="RareMDT-Report/0.1",
            on_delta=stream_callback,
        )
    payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {provider.api_key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Connection": "close",
        "User-Agent": "RareMDT-Report/0.1",
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
    raise ValueError("Report Generator request failed.")


def _compact(value: Any, *, depth: int = 0) -> Any:
    if depth > 4:
        return str(value)[:240]
    if isinstance(value, dict):
        skipped = {"boundary_points", "local_boundary_points", "mask_spans", "vision_probe"}
        return {str(key): _compact(val, depth=depth + 1) for key, val in value.items() if key not in skipped}
    if isinstance(value, list):
        return [_compact(item, depth=depth + 1) for item in value[:16]]
    if isinstance(value, str):
        return value[:1400]
    return value


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


def _report_prompt(
    submission: CaseSubmission,
    profile: AppProfile,
    *,
    execution_bundle: dict[str, Any],
    decision_bundle: dict[str, Any],
) -> str:
    available_evidence_ids = sorted(_known_evidence_ids(execution_bundle))
    return dedent(
        f"""
        You are @Report Generator in a clinical evidence-based agent workflow.
        Write a concise clinician-facing delivery report from Decider output and Executor evidence.
        Do not re-decide the case; Decider is the source of diagnostic judgment.
        Every factual diagnostic statement must cite evidence IDs such as [E1], [E2].

        Case context:
        - department: {submission.department}
        - urgency: {submission.urgency}
        - chief_complaint: {submission.chief_complaint}
        - case_summary: {submission.case_summary}
        - patient_age: {submission.patient_age}
        - patient_sex: {submission.patient_sex}
        - hospital_context: {profile.hospital_name}

        Decider decision:
        {json.dumps(_compact(decision_bundle.get("decision") or {}), ensure_ascii=False, indent=2)}

        Executor evidence:
        {json.dumps(_compact(execution_bundle.get("records") or []), ensure_ascii=False, indent=2)}

        Available evidence IDs:
        {json.dumps(available_evidence_ids, ensure_ascii=False)}

        Return ONLY JSON with this exact object shape:
        {{
          "report_title": "",
          "clinical_summary": "",
          "evidence_based_findings": [
            {{"statement": "", "evidence_ids": ["E1"]}}
          ],
          "diagnostic_assessment": "",
          "recommendations": [
            {{"recommendation": "", "rationale": "", "evidence_ids": ["E1"]}}
          ],
          "limitations": [""],
          "doctor_review_checklist": [""],
          "patient_facing_note": ""
        }}

        Rules:
        - Do not create new evidence IDs. Only cite evidence IDs from the available evidence ID list.
        - Do not invent measurements, diagnoses, or findings that are absent from Decider/Executor.
        - Do not generate differential_diagnosis. Differential diagnoses are owned by Decider and will be rendered from Decider's validated structure.
        - If a section cannot be supported, state the limitation rather than filling it.
        - Include a recommendation only when it is justified by one or more available evidence IDs.
        - Do not output placeholder, generic, or unsupported recommendation rows.
        - clinical_summary must be at most 2 sentences.
        - diagnostic_assessment must be at most 3 sentences.
        - evidence_based_findings should contain 3 to 5 high-value findings.
        - recommendations should contain at most 5 concrete next actions.
        - limitations should contain at most 4 items.
        - doctor_review_checklist should contain at most 5 items.
        - patient_facing_note must be short and plain-language; do not mix it into clinician sections.
        - The report should reduce clinician cognitive load: short sections, clear evidence references, and explicit review checklist.
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
        raise ValueError(f"Report Generator output field {field} must be a list.")
    cleaned = [str(item).strip() for item in value if str(item).strip()]
    if not cleaned and not allow_empty:
        raise ValueError(f"Report Generator output field {field} must cite at least one evidence id.")
    invalid = [item for item in cleaned if item not in valid_ids]
    if invalid:
        raise ValueError(f"Report Generator output field {field} contains unknown evidence ids: {', '.join(invalid)}")
    return cleaned


def _validate_report(payload: Any, *, valid_evidence_ids: set[str]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Report Generator output is not a JSON object.")
    required = [
        "report_title",
        "clinical_summary",
        "evidence_based_findings",
        "diagnostic_assessment",
        "recommendations",
        "limitations",
        "doctor_review_checklist",
        "patient_facing_note",
    ]
    for key in required:
        if key not in payload:
            raise ValueError(f"Report Generator output is missing {key}.")
    findings = payload.get("evidence_based_findings")
    if not isinstance(findings, list):
        raise ValueError("Report Generator output must include evidence_based_findings.")
    cleaned_findings: list[dict[str, Any]] = []
    for index, item in enumerate(findings, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Report Generator evidence_based_findings item #{index} must be an object.")
        statement = str(item.get("statement") or "").strip()
        if not statement:
            raise ValueError(f"Report Generator evidence_based_findings item #{index} is missing statement.")
        evidence_ids = _normalize_evidence_id_list(
            item.get("evidence_ids"),
            valid_ids=valid_evidence_ids,
            field=f"evidence_based_findings[{index}].evidence_ids",
        )
        cleaned_findings.append({"statement": statement, "evidence_ids": evidence_ids})
    cleaned_recommendations: list[dict[str, Any]] = []
    for index, item in enumerate(payload.get("recommendations", []), start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Report Generator recommendations item #{index} must be an object.")
        recommendation = str(item.get("recommendation") or "").strip()
        rationale = str(item.get("rationale") or "").strip()
        if not recommendation or not rationale:
            raise ValueError(f"Report Generator recommendations item #{index} must include recommendation and rationale.")
        evidence_ids = _normalize_evidence_id_list(
            item.get("evidence_ids"),
            valid_ids=valid_evidence_ids,
            field=f"recommendations[{index}].evidence_ids",
        )
        cleaned_recommendations.append(
            {
                "recommendation": recommendation,
                "rationale": rationale,
                "evidence_ids": evidence_ids,
            }
        )
    return {
        "report_title": str(payload["report_title"]).strip(),
        "clinical_summary": str(payload["clinical_summary"]).strip(),
        "evidence_based_findings": cleaned_findings,
        "diagnostic_assessment": str(payload["diagnostic_assessment"]).strip(),
        "differential_diagnosis": [],
        "recommendations": cleaned_recommendations,
        "limitations": _string_list(payload.get("limitations")),
        "doctor_review_checklist": _string_list(payload.get("doctor_review_checklist")),
        "patient_facing_note": str(payload["patient_facing_note"]).strip(),
    }


def _request_validated_report(
    provider: Any,
    submission: CaseSubmission,
    profile: AppProfile,
    *,
    execution_bundle: dict[str, Any],
    decision_bundle: dict[str, Any],
    valid_evidence_ids: set[str],
    stream_callback: StreamCallback | None = None,
) -> tuple[str, dict[str, Any]]:
    raw = _report_request(
        provider,
        [
            {"role": "system", "content": "You are @Report Generator. Return only strict JSON and cite evidence IDs."},
            {"role": "user", "content": _report_prompt(submission, profile, execution_bundle=execution_bundle, decision_bundle=decision_bundle)},
        ],
        max_tokens=4200,
        stream_callback=stream_callback,
    )
    return raw, _validate_report(_parse_json_text(raw), valid_evidence_ids=valid_evidence_ids)


def _sort_evidence_ids(values: list[str]) -> list[str]:
    return sorted(set(values), key=lambda value: int(value[1:]) if value.startswith("E") and value[1:].isdigit() else value)


def _differentials_from_decider(decision_bundle: dict[str, Any], *, valid_evidence_ids: set[str]) -> list[dict[str, Any]]:
    decision = decision_bundle.get("decision") if isinstance(decision_bundle, dict) else {}
    if not isinstance(decision, dict):
        return []
    differentials = decision.get("differential_diagnoses")
    if not isinstance(differentials, list):
        return []
    cleaned: list[dict[str, Any]] = []
    for index, item in enumerate(differentials[:3], start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Decider differential_diagnoses[{index}] must be an object before Report can render it.")
        name = str(item.get("name") or "").strip()
        if not name:
            raise ValueError(f"Decider differential_diagnoses[{index}] is missing name before Report can render it.")
        likelihood = str(item.get("likelihood") or "").strip()
        comment = str(item.get("comment") or "").strip()
        supporting_ids = [str(value).strip() for value in item.get("supporting_evidence_ids") or [] if str(value).strip()]
        refuting_ids = [str(value).strip() for value in item.get("refuting_evidence_ids") or [] if str(value).strip()]
        invalid = [value for value in supporting_ids + refuting_ids if value not in valid_evidence_ids]
        if invalid:
            raise ValueError(f"Decider differential_diagnoses[{index}] contains unknown evidence ids: {', '.join(invalid)}")
        evidence_ids = _sort_evidence_ids(supporting_ids + refuting_ids)
        if not evidence_ids:
            raise ValueError(f"Decider differential_diagnoses[{index}] must cite supporting or refuting evidence before Report can render it.")
        assessment_parts: list[str] = []
        if likelihood:
            assessment_parts.append(f"可能性：{likelihood}")
        if comment:
            assessment_parts.append(comment)
        if supporting_ids:
            assessment_parts.append(f"支持证据：{', '.join(_sort_evidence_ids(supporting_ids))}")
        if refuting_ids:
            assessment_parts.append(f"反证/限制：{', '.join(_sort_evidence_ids(refuting_ids))}")
        cleaned.append(
            {
                "name": name,
                "assessment": "；".join(assessment_parts),
                "evidence_ids": evidence_ids,
            }
        )
    return cleaned


def _report_markdown(report: dict[str, Any]) -> str:
    findings = "\n".join(
        f"- {item.get('statement', '')} {' '.join(f'[{eid}]' for eid in (item.get('evidence_ids') or []))}"
        for item in report.get("evidence_based_findings", [])
    )
    differentials = "\n".join(
        f"- {item.get('name', '')}：{item.get('assessment', '')} {' '.join(f'[{eid}]' for eid in (item.get('evidence_ids') or []))}"
        for item in report.get("differential_diagnosis", [])
    )
    recommendations = "\n".join(
        f"- {item.get('recommendation', '')}：{item.get('rationale', '')} {' '.join(f'[{eid}]' for eid in (item.get('evidence_ids') or []))}"
        for item in report.get("recommendations", [])
    )
    limitations = "\n".join(f"- {item}" for item in report.get("limitations", [])) or "- 未列出"
    checklist = "\n".join(f"- {item}" for item in report.get("doctor_review_checklist", [])) or "- 复核证据引用与诊断判断"
    return dedent(
        f"""
        **{report['report_title'] or '医疗报告'}**

        **临床摘要**
        {report['clinical_summary']}

        **证据化发现**
        {findings or "- 未列出"}

        **诊断评估**
        {report['diagnostic_assessment']}

        **鉴别诊断**
        {differentials or "- 未列出"}

        **建议**
        {recommendations or "- 未列出"}

        **局限性**
        {limitations}

        **医生复核清单**
        {checklist}

        **面向患者说明**
        {report['patient_facing_note']}
        """
    ).strip()


def run_report_case(
    submission: CaseSubmission,
    profile: AppProfile,
    settings: SystemSettings,
    *,
    execution_bundle: dict[str, Any] | None = None,
    decision_bundle: dict[str, Any] | None = None,
    stream_callback: StreamCallback | None = None,
) -> EngineResult:
    if execution_bundle is None:
        raise ValueError("Report Generator requires completed Executor evidence in the current context.")
    if decision_bundle is None:
        raise ValueError("Report Generator requires a Decider diagnostic decision in the current context. Invoke @Decider first.")
    provider = _resolve_report_provider(settings)
    valid_evidence_ids = _known_evidence_ids(execution_bundle)
    if not valid_evidence_ids:
        raise ValueError("Report Generator requires valid Executor evidence ids in the current context.")
    raw, report = _request_validated_report(
        provider,
        submission,
        profile,
        execution_bundle=execution_bundle,
        decision_bundle=decision_bundle,
        valid_evidence_ids=valid_evidence_ids,
        stream_callback=stream_callback,
    )
    report["differential_diagnosis"] = _differentials_from_decider(decision_bundle, valid_evidence_ids=valid_evidence_ids)
    return EngineResult(
        title=f"Report Generator 医疗报告：{submission.chief_complaint or '当前病例'}",
        executive_summary="@Report Generator 已基于 Decider 判断和 Executor 证据生成 evidence-based 医疗报告。",
        department=submission.department,
        output_style=submission.output_style,
        professional_answer=_report_markdown(report),
        coding_table=[],
        cost_table=[],
        references=[{"type": "evidence_citation", "title": ",".join(item.get("evidence_ids") or []), "region": item.get("statement", "")} for item in report["evidence_based_findings"]],
        next_steps=report["doctor_review_checklist"],
        safety_note="报告草稿必须由医生审核后才能进入正式病历或医嘱系统。",
        rounds=[
            {
                "round": 1,
                "alignment": 1.0,
                "summary": "Report Generator converted Decider diagnosis and Executor evidence into a clinician-facing cited report.",
            }
        ],
        agent_trace=[
            {
                "role": REPORT_AGENT_NAME,
                "provider": provider.provider_name,
                "note": "Generated an evidence-cited medical report from decision and execution records.",
            }
        ],
        consensus_score=float((decision_bundle.get("decision") or {}).get("diagnosis_confidence") or 1.0),
        topology_used="Report Generator",
        show_process=submission.show_process,
        execution_mode="report",
        serving_provider=provider.provider_name,
        serving_model=provider.model_name,
        activated_agent=REPORT_AGENT_NAME,
        plan_steps=list((execution_bundle or {}).get("plan_steps") or []),
        plan_display_steps=list((execution_bundle or {}).get("plan_display_steps") or []),
        execution_records=list((execution_bundle or {}).get("records") or []),
        raw_model_text=raw,
        raw_provider_payload=json.dumps(report, ensure_ascii=False),
    )
