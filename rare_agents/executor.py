from __future__ import annotations

import json
import re
import time
from http.client import RemoteDisconnected
from textwrap import dedent
from typing import Any, Callable
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request

from rare_agents.display_composer import compose_execution_display_projection
from rare_agents.grounding_harness import (
    clamp01,
    build_harness_constraints,
    compute_measurements,
    parent_grounding,
    run_vlm_bbox_grounding_harness,
    run_vlm_grounding_harness,
)
from rare_agents.models import AppProfile, CaseSubmission, EngineResult, SystemSettings
from rare_agents.provider_client import StreamCallback, request_chat_completion_stream


EXECUTOR_AGENT_NAME = "Executor"
EXECUTOR_TRIGGER_PATTERN = re.compile(r"@executor\b", re.IGNORECASE)


def is_executor_invocation(text: str) -> bool:
    return bool(EXECUTOR_TRIGGER_PATTERN.search(str(text or "")))


def strip_executor_mention(text: str) -> str:
    cleaned = re.sub(r"@executor\b", "", str(text or ""), flags=re.IGNORECASE)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


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


def _extract_chat_content(payload: dict[str, Any]) -> str:
    choices = payload.get("choices")
    if isinstance(choices, list) and choices:
        message = choices[0].get("message", {}) if isinstance(choices[0], dict) else {}
        content = message.get("content")
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            texts: list[str] = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    texts.append(str(item.get("text", "")))
            if texts:
                return "\n".join(texts).strip()
    raise ValueError("Executor API response did not include usable text content.")


def _parse_llm_json(raw: str) -> Any:
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


def _resolve_executor_provider(settings: SystemSettings) -> Any:
    executor_role = next((role for role in settings.agent_roles if role.role_name.lower() == "executor"), None)
    if executor_role is None:
        raise ValueError("Executor role is not configured.")
    for provider in settings.api_providers:
        role_provider_id = str(getattr(executor_role, "provider_id", "") or "").strip()
        provider_id = str(getattr(provider, "provider_id", "") or "").strip()
        if (
            ((role_provider_id and provider_id and provider_id == role_provider_id) or (not role_provider_id and provider.provider_name == executor_role.provider_name))
            and provider.enabled
            and provider.endpoint
            and provider.api_key
            and provider.model_name
        ):
            return provider
    raise ValueError("Executor provider is not configured.")


def _safe_image_payloads(image_payloads: list[dict[str, Any]] | None) -> list[dict[str, str]]:
    cleaned: list[dict[str, str]] = []
    for item in image_payloads or []:
        if not isinstance(item, dict):
            continue
        data_url = str(item.get("data_url", "")).strip()
        if not data_url.startswith("data:image/"):
            continue
        cleaned.append(
            {
                "name": str(item.get("name", "")).strip(),
                "media_type": str(item.get("media_type", "")).strip(),
                "data_url": data_url,
            }
        )
        if len(cleaned) >= 2:
            break
    return cleaned


def _executor_request(
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
            user_agent="RareMDT-Executor/0.1",
            on_delta=stream_callback,
        )
    payload = json.dumps(body).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {provider.api_key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Connection": "close",
        "User-Agent": "RareMDT-Executor/0.1",
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
    raise ValueError("Executor request failed.")


def _image_content(prompt: str, image_payload: dict[str, str]) -> list[dict[str, Any]]:
    return [
        {"type": "image_url", "image_url": {"url": image_payload["data_url"]}},
        {"type": "text", "text": prompt},
    ]


def _image_data_url_content(prompt: str, data_urls: Any) -> list[dict[str, Any]]:
    if isinstance(data_urls, str):
        return [
            {"type": "image_url", "image_url": {"url": data_urls}},
            {"type": "text", "text": prompt},
        ]
    if isinstance(data_urls, list) and any(isinstance(item, dict) for item in data_urls):
        content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
        for item in data_urls:
            if not isinstance(item, dict):
                continue
            url = str(item.get("data_url", "")).strip()
            if not url:
                continue
            label = str(item.get("label", "")).strip()
            name = str(item.get("name", "")).strip()
            if label or name:
                content.append({"type": "text", "text": "\n".join(part for part in [name, label] if part)})
            content.append({"type": "image_url", "image_url": {"url": url}})
        return content
    urls = [str(item).strip() for item in data_urls if str(item).strip()] if isinstance(data_urls, list) else []
    content = [{"type": "image_url", "image_url": {"url": url}} for url in urls]
    content.append({"type": "text", "text": prompt})
    return content


def _request_json_with_image(
    provider: Any,
    *,
    data_url: Any,
    prompt: str,
    max_tokens: int,
    system_prompt: str,
    stream_callback: StreamCallback | None = None,
) -> dict[str, Any]:
    raw = _executor_request(
        provider,
        [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": _image_data_url_content(prompt, data_url),
            },
        ],
        max_tokens=max_tokens,
        stream_callback=stream_callback,
    )
    parsed = _parse_llm_json(raw)
    if not isinstance(parsed, dict):
        raise ValueError("Image JSON request must return a JSON object.")
    return parsed


def _harness_requester(provider: Any, stream_callback: StreamCallback | None = None):
    def request_json(data_url: Any, prompt: str, max_tokens: int, system_prompt: str) -> dict[str, Any]:
        return _request_json_with_image(
            provider,
            data_url=data_url,
            prompt=prompt,
            max_tokens=max_tokens,
            system_prompt=system_prompt,
            stream_callback=stream_callback,
        )

    return request_json


def _request_vision_probe(provider: Any, image_payload: dict[str, str], stream_callback: StreamCallback | None = None) -> dict[str, Any]:
    parsed = _request_json_with_image(
        provider,
        data_url=image_payload["data_url"],
        system_prompt="You verify visual access to a medical image. Return only strict JSON and do not diagnose.",
        prompt=dedent(
            """
            Verify that you can inspect the uploaded medical image.

            Return ONLY JSON:
            {
              "modality": "",
              "anatomy": "",
              "visible_text": ["", ""],
              "primary_visual_targets": ["", ""],
              "image_quality": "",
              "confidence": 0.0
            }

            Rules:
            - Do not infer a final diagnosis.
            - Mention only image-specific visible information.
            - If the image is not visible, set confidence to 0 and leave image-specific fields empty.
            """
        ).strip(),
        max_tokens=900,
        stream_callback=stream_callback,
    )
    probe = {
        "modality": str(parsed.get("modality", "")).strip(),
        "anatomy": str(parsed.get("anatomy", "")).strip(),
        "visible_text": [str(item).strip() for item in parsed.get("visible_text", []) if str(item).strip()][:6],
        "primary_visual_targets": [str(item).strip() for item in parsed.get("primary_visual_targets", []) if str(item).strip()][:6],
        "image_quality": str(parsed.get("image_quality", "")).strip(),
        "confidence": clamp01(parsed.get("confidence", 0.0)),
    }
    evidence_fields = [
        probe["modality"],
        probe["anatomy"],
        " ".join(probe["visible_text"]),
        " ".join(probe["primary_visual_targets"]),
    ]
    if probe["confidence"] < 0.2 or sum(1 for item in evidence_fields if item) < 2:
        raise ValueError("Executor vision probe failed; the configured VLM did not demonstrate image access.")
    return probe


def _request_grounding(
    provider: Any,
    *,
    step: dict[str, Any],
    image_payload: dict[str, str],
    target_label: str,
    prompt: str,
    relationship: str = "",
    parent_output: dict[str, Any] | None = None,
    harness_text: str = "",
    max_tokens: int = 2200,
    require_boundary: bool = True,
    stream_callback: StreamCallback | None = None,
) -> dict[str, Any]:
    del prompt, relationship, harness_text, max_tokens
    if not require_boundary:
        return run_vlm_bbox_grounding_harness(
            request_json=_harness_requester(provider, stream_callback),
            image_payload=image_payload,
            step=step,
            target_label=target_label,
            parent_output=parent_output,
        )
    return run_vlm_grounding_harness(
        request_json=_harness_requester(provider, stream_callback),
        image_payload=image_payload,
        step=step,
        target_label=target_label,
        parent_output=parent_output,
        require_boundary=require_boundary,
    )


_GENERIC_GROUNDING_LABELS = {
    "",
    "abnormality",
    "finding",
    "image finding",
    "lesion",
    "mass",
    "nodule",
    "object",
    "region",
    "target region",
    "target",
    "boundary points",
    "boundary point",
    "instance boundary",
    "boundary",
    "region mask",
    "mask",
    "roi",
    "sparse landmark",
    "structure",
    "visible target",
}


def _clean_grounding_target_text(value: str) -> str:
    text = re.sub(r"[_\-]+", " ", str(value or "")).strip()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"^(ground|localize|segment|trace|identify)\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^(the|a|an)\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^(complete|entire|full|requested)\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^visible\s+extent\s+of\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^boundary\s+of\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^outer\s+boundary\s+of\s+", "", text, flags=re.IGNORECASE)
    for splitter in [
        r"\s+with\s+",
        r"\s+as\s+",
        r"\s+for\s+",
        r"\s+using\s+",
        r"\s+to\s+",
    ]:
        parts = re.split(splitter, text, maxsplit=1, flags=re.IGNORECASE)
        if len(parts) > 1 and len(parts[0].split()) >= 2:
            text = parts[0]
            break
    text = re.sub(
        r"\b(boundary|boundaries|points|point|mask|masks|segmentation|binary|evidence|region|roi|rasterize|rasterized)\b",
        " ",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\s+", " ", text).strip(" .,-_")
    return text


def _is_generic_grounding_label(value: object) -> bool:
    text = re.sub(r"[_\-]+", " ", str(value or "").lower()).strip()
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return not text or text in _GENERIC_GROUNDING_LABELS


def _derive_grounding_target_label(step: dict[str, Any]) -> str:
    tool_config = step.get("tool_config") if isinstance(step.get("tool_config"), dict) else {}
    target_label = _clean_grounding_target_text(str(tool_config.get("target_label") or step.get("target_label") or ""))
    if target_label and not _is_generic_grounding_label(target_label):
        return target_label
    seg_type = _clean_grounding_target_text(str(tool_config.get("seg_type") or ""))
    if seg_type and not _is_generic_grounding_label(seg_type):
        return seg_type
    finding = str(step.get("finding") or "").strip()
    if finding and not _is_generic_grounding_label(finding):
        return finding
    action = str(step.get("action") or "").strip()
    text = re.sub(r"\s+", " ", action)
    for pattern in [
        r"^ground\s+the\s+",
        r"^ground\s+boundary\s+points\s+of\s+",
        r"^ground\s+boundary\s+points\s+for\s+",
        r"^ground\s+",
        r"^localize\s+",
        r"^segment\s+",
        r"^trace\s+",
        r"^identify\s+",
        r"\s+using\s+boundary-point\s+evidence.*$",
        r"\s+to\s+generate\s+binary\s+segmentation\s+mask.*$",
        r"\s+for\s+quantitative.*$",
        r"\s+from\s+masks.*$",
    ]:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bboundary points\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bbinary segmentation mask\b", "", text, flags=re.IGNORECASE)
    text = text.strip(" .,-_")
    return text or "target region"


def _run_evidence_vlm_step(
    step: dict[str, Any],
    *,
    provider: Any,
    image_payload: dict[str, str],
    outputs: dict[int, dict[str, Any]],
    stream_callback: StreamCallback | None = None,
) -> dict[str, Any]:
    parent_output = outputs.get(int(step.get("relative_to_step") or 0)) if step.get("relative_to_step") else None
    target_label = _derive_grounding_target_label(step)
    evidence = _request_grounding(
        provider,
        step=step,
        image_payload=image_payload,
        target_label=target_label,
        prompt="Localize the requested target region for quantitative downstream analysis.",
        relationship=str(step.get("relationship") or ""),
        parent_output=parent_output,
        harness_text=build_harness_constraints(step, parent_output),
        max_tokens=1800,
        require_boundary=True,
        stream_callback=stream_callback,
    )
    return {
        "artifact_type": "grounding",
        "target_label": target_label,
        "logical_output_path": step.get("output_path"),
        "conclusion": "localized",
        "confidence": evidence["confidence"],
        "rationale": evidence["rationale"],
        "target_understanding": evidence.get("target_understanding", ""),
        "boundary_definition": evidence.get("boundary_definition", ""),
        "excluded_regions": evidence.get("excluded_regions", []),
        "grounding": evidence["grounding"],
        "validation": evidence.get("validation", {}),
        "harness": evidence.get("harness", {}),
    }


def _is_measurement_coding_step(step: dict[str, Any]) -> bool:
    text = f"{step.get('finding') or ''} {step.get('action') or ''}".lower()
    measurement_terms = {
        "area",
        "aspect",
        "calculate",
        "compute",
        "diameter",
        "height",
        "length",
        "measure",
        "metric",
        "perimeter",
        "quantify",
        "ratio",
        "size",
        "width",
    }
    synthesis_terms = {
        "assessment",
        "bi-rads",
        "birads",
        "classification",
        "diagnosis",
        "recommendation",
        "report",
        "synthesize",
    }
    return any(term in text for term in measurement_terms) and not any(term in text for term in synthesis_terms)


def _run_structured_coding_step(step: dict[str, Any], *, outputs: dict[int, dict[str, Any]]) -> dict[str, Any]:
    parent_ids = [int(parent) for parent in step.get("input_type", []) if int(parent) != 0]
    parents = [outputs[parent] for parent in parent_ids if parent in outputs]
    if len(parents) != len(parent_ids):
        missing = [parent for parent in parent_ids if parent not in outputs]
        raise ValueError(f"Coding step is missing upstream parent output(s): {', '.join(str(item) for item in missing)}")
    evidence_items: list[dict[str, Any]] = []
    confidences: list[float] = []
    for parent in parents:
        evidence = parent.get("evidence") if isinstance(parent.get("evidence"), dict) else {}
        confidence = evidence.get("confidence")
        if isinstance(confidence, (int, float)):
            confidences.append(float(confidence))
        evidence_items.append(
            {
                "step_id": parent.get("step_id"),
                "artifact_type": evidence.get("artifact_type"),
                "finding": parent.get("finding"),
                "conclusion": evidence.get("conclusion"),
                "confidence": evidence.get("confidence"),
                "rationale": evidence.get("rationale"),
                "measurements": evidence.get("measurements"),
                "has_grounding": bool((evidence.get("grounding") or {}).get("bbox")),
            }
        )
    if not evidence_items:
        raise ValueError("Coding step has no upstream evidence to aggregate.")
    if not confidences:
        raise ValueError("Structured coding step requires at least one upstream confidence-bearing evidence item.")
    aggregate_confidence = round(sum(confidences) / len(confidences), 6)
    return {
        "artifact_type": "structured_coding",
        "logical_output_path": step.get("output_path"),
        "conclusion": "structured_evidence_aggregated",
        "confidence": aggregate_confidence,
        "rationale": "Aggregated upstream measurements and indicators according to the executable plan.",
        "structured_inputs": evidence_items,
        "structured_assessment": {
            "action": step.get("action"),
            "input_step_ids": parent_ids,
            "measurement_steps": [item for item in evidence_items if item.get("measurements")],
            "indicator_steps": [item for item in evidence_items if not item.get("measurements")],
        },
    }


def _run_coding_step(step: dict[str, Any], *, outputs: dict[int, dict[str, Any]]) -> dict[str, Any]:
    parents = [outputs[parent] for parent in step.get("input_type", []) if parent in outputs]
    if not _is_measurement_coding_step(step):
        return _run_structured_coding_step(step, outputs=outputs)
    return {
        "artifact_type": "measurements",
        "logical_output_path": step.get("output_path"),
        "measurements": compute_measurements(parents),
    }


def _run_text_vlm_step(
    step: dict[str, Any],
    *,
    provider: Any,
    outputs: dict[int, dict[str, Any]],
    stream_callback: StreamCallback | None = None,
) -> dict[str, Any]:
    parents = [outputs[parent] for parent in step.get("input_type", []) if parent in outputs]
    context = {
        "upstream_evidence": [parent.get("evidence", {}) for parent in parents],
        "finding": step.get("finding"),
        "action": step.get("action"),
    }
    raw = _executor_request(
        provider,
        [
            {
                "role": "system",
                "content": "You are a careful clinical evidence interpreter. Return only JSON.",
            },
            {
                "role": "user",
                "content": dedent(
                    f"""
                    Interpret the structured upstream evidence for this step.

                    Step target: {step.get('finding') or step.get('action')}
                    Upstream evidence:
                    {json.dumps(context, ensure_ascii=False, indent=2)}

                    Return JSON:
                    {{
                      "conclusion": "Yes|No|Uncertain",
                      "confidence": 0.0,
                      "rationale": ""
                    }}
                    """
                ).strip(),
            },
        ],
        max_tokens=1200,
        stream_callback=stream_callback,
    )
    parsed = _parse_llm_json(raw)
    if not isinstance(parsed, dict):
        raise ValueError("Text interpretation response must be a JSON object.")
    return {
        "artifact_type": "text_interpretation",
        "logical_output_path": step.get("output_path"),
        "conclusion": str(parsed.get("conclusion", "")).strip() or "Uncertain",
        "confidence": clamp01(parsed.get("confidence", 0.0)),
        "rationale": str(parsed.get("rationale", "")).strip(),
    }


def _relationship_from_step_or_context(step: dict[str, Any], outputs: dict[int, dict[str, Any]]) -> tuple[str, dict[str, Any] | None]:
    relationship = str(step.get("relationship") or "").strip().lower()
    relative_to_step = step.get("relative_to_step")
    if not relative_to_step:
        return relationship, None
    parent_id = int(relative_to_step)
    if parent_id not in outputs:
        raise ValueError(f"Executor step {step.get('id')} references missing parent step {parent_id}.")
    return relationship, outputs[parent_id]


def _run_same_target_indicator_step(
    step: dict[str, Any],
    *,
    provider: Any,
    image_payload: dict[str, str],
    parent_output: dict[str, Any],
    stream_callback: StreamCallback | None = None,
) -> dict[str, Any]:
    finding = str(step.get("finding") or step.get("action") or "target finding").strip()
    parent = parent_grounding(parent_output)
    raw = _executor_request(
        provider,
        [
            {
                "role": "system",
                "content": "You assess one imaging finding inside a pre-validated grounded region. Return only JSON.",
            },
            {
                "role": "user",
                "content": _image_content(
                    dedent(
                        f"""
                        Assess the requested finding using only the already grounded region of interest.

                        Finding: {finding}
                        Step action: {step.get('action') or ''}
                        Grounded region bbox: {parent.get('bbox')}
                        Grounded boundary points: {parent.get('boundary_points')}

                        Return ONLY JSON:
                        {{
                          "conclusion": "Yes|No|Uncertain",
                          "confidence": 0.0,
                          "rationale": "brief evidence tied to the grounded region"
                        }}

                        Rules:
                        - Do not output new coordinates.
                        - Do not create a final diagnosis.
                        - The conclusion must explicitly refer to the requested finding.
                        """
                    ).strip(),
                    image_payload,
                ),
            },
        ],
        max_tokens=1200,
        stream_callback=stream_callback,
    )
    parsed = _parse_llm_json(raw)
    if not isinstance(parsed, dict):
        raise ValueError("Same-target indicator response must be a JSON object.")
    if not parent.get("bbox"):
        raise ValueError("Same-target indicator requires parent bbox evidence.")
    return {
        "artifact_type": "grounded_indicator",
        "logical_output_path": step.get("output_path"),
        "conclusion": str(parsed.get("conclusion", "")).strip() or "Uncertain",
        "confidence": clamp01(parsed.get("confidence", 0.0)),
        "rationale": str(parsed.get("rationale", "")).strip(),
        "grounding": {
            "bbox": parent["bbox"],
        },
        "validation": {"valid": True, "source": "same_target_parent_grounding"},
        "harness": {
            "enabled": True,
            "method": "reuse_validated_parent_grounding_for_same_target_indicator",
            "parent_step_id": step.get("relative_to_step"),
            "relationship": "same_target",
        },
    }


def _run_vlm_step(
    step: dict[str, Any],
    *,
    provider: Any,
    image_payload: dict[str, str],
    outputs: dict[int, dict[str, Any]],
    stream_callback: StreamCallback | None = None,
) -> dict[str, Any]:
    relationship, parent_output = _relationship_from_step_or_context(step, outputs)
    if relationship == "same_target" and parent_output is not None:
        return _run_same_target_indicator_step(
            step,
            provider=provider,
            image_payload=image_payload,
            parent_output=parent_output,
            stream_callback=stream_callback,
        )
    finding = str(step.get("finding") or step.get("action") or "target finding").strip()
    return {
        "artifact_type": "grounded_indicator",
        "logical_output_path": step.get("output_path"),
        **_request_grounding(
            provider,
            step=step,
            image_payload=image_payload,
            target_label=finding,
            prompt="Assess the requested imaging finding and ground the most relevant visual evidence.",
            relationship=relationship,
            parent_output=parent_output,
            harness_text=build_harness_constraints(step, parent_output),
            max_tokens=2200,
            require_boundary=False,
            stream_callback=stream_callback,
        ),
    }


def _execute_step(
    step: dict[str, Any],
    *,
    provider: Any,
    image_payload: dict[str, str] | None,
    outputs: dict[int, dict[str, Any]],
    stream_callback: StreamCallback | None = None,
) -> dict[str, Any]:
    tool_type = str((step.get("tool_config") or {}).get("tool_type") or "")
    if tool_type == "evidence_vlm":
        if image_payload is None:
            raise ValueError("Executor needs an image to run grounding steps.")
        evidence = _run_evidence_vlm_step(
            step,
            provider=provider,
            image_payload=image_payload,
            outputs=outputs,
            stream_callback=stream_callback,
        )
    elif tool_type == "coding":
        evidence = _run_coding_step(step, outputs=outputs)
    elif tool_type == "text_vlm":
        evidence = _run_text_vlm_step(step, provider=provider, outputs=outputs, stream_callback=stream_callback)
    elif tool_type == "vlm":
        if image_payload is None:
            raise ValueError("Executor needs an image to run VLM evidence steps.")
        evidence = _run_vlm_step(
            step,
            provider=provider,
            image_payload=image_payload,
            outputs=outputs,
            stream_callback=stream_callback,
        )
    else:
        raise ValueError(f"Unsupported executor tool type: {tool_type or 'unknown'}")

    record = {
        "step_id": int(step.get("id") or 0),
        "status": "completed",
        "action": str(step.get("action") or "").strip(),
        "finding": step.get("finding"),
        "tool_type": tool_type,
        "output_type": step.get("output_type"),
        "evidence": evidence,
    }
    return record


def _executor_markdown(records: list[dict[str, Any]]) -> str:
    rows = []
    for index, record in enumerate(records, start=1):
        display = record.get("display") if isinstance(record.get("display"), dict) else {}
        conclusion = str(display.get("conclusion_zh") or "").strip()
        detail = str(display.get("desc_zh") or "").strip() or "已生成结构化证据。"
        if conclusion:
            detail = f"{conclusion} {detail}"
        rows.append(f"{index}. **{display.get('title_zh') or f'步骤 {index}'}**\n   {detail}")
    return "\n".join(rows)


def _emit_progress(progress_callback: Callable[[dict[str, Any]], None] | None, payload: dict[str, Any]) -> None:
    if progress_callback is None:
        return
    progress_callback(payload)


def run_executor_case(
    submission: CaseSubmission,
    profile: AppProfile,
    settings: SystemSettings,
    *,
    image_payloads: list[dict[str, Any]] | None = None,
    plan_bundle: dict[str, Any] | None = None,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
    stream_callback: StreamCallback | None = None,
) -> EngineResult:
    del profile
    provider = _resolve_executor_provider(settings)
    safe_images = _safe_image_payloads(image_payloads)
    primary_image = safe_images[0] if safe_images else None
    try:
        vision_probe = _request_vision_probe(provider, primary_image, stream_callback) if primary_image is not None else None
    except (ValueError, OSError, urllib_error.URLError, urllib_error.HTTPError, json.JSONDecodeError) as exc:
        provider_label = " / ".join(item for item in [provider.provider_name, provider.model_name] if item) or "未配置接口"
        raise ValueError(
            f"Executor 视觉接口失败：{provider_label} 当前不能完成图像输入调用。"
            f" 请到设置页的 Planner / Executor 区域测试视觉接口。原始错误：{str(exc).strip()}"
        ) from exc
    if plan_bundle is None:
        raise ValueError("Executor requires a planner-generated execution plan in the current context. Invoke @Planner first.")
    plan = {
        "steps": list(plan_bundle.get("steps") or []),
        "display_steps": list(plan_bundle.get("display_steps") or []),
        "references": list(plan_bundle.get("references") or []),
        "provider": str(plan_bundle.get("provider") or ""),
        "model": str(plan_bundle.get("model") or ""),
        "note": str(plan_bundle.get("note") or "Loaded the existing planner-generated execution plan from context."),
    }
    if not plan["steps"]:
        raise ValueError("Executor did not find executable plan steps in the current context. Invoke @Planner first.")

    outputs: dict[int, dict[str, Any]] = {}
    records: list[dict[str, Any]] = []
    _emit_progress(
        progress_callback,
        {
            "status": "running",
            "stage": "ready",
            "active_step_id": None,
            "records": records,
            "plan_display_steps": plan["display_steps"],
        },
    )
    for step in plan["steps"]:
        step_id = int(step.get("id") or 0)
        _emit_progress(
            progress_callback,
            {
                "status": "running",
                "stage": "executing",
                "active_step_id": step_id,
                "records": records,
                "plan_display_steps": plan["display_steps"],
            },
        )
        try:
            record = _execute_step(
                step,
                provider=provider,
                image_payload=primary_image,
                outputs=outputs,
                stream_callback=stream_callback,
            )
        except Exception as exc:
            _emit_progress(
                progress_callback,
                {
                    "status": "failed",
                    "stage": "failed",
                    "active_step_id": None,
                    "failed_step_id": step_id,
                    "records": records,
                    "plan_display_steps": plan["display_steps"],
                },
            )
            raise ValueError(f"Executor step {step.get('id')} failed: {exc}") from exc
        if vision_probe and isinstance(record.get("evidence"), dict) and record["evidence"].get("grounding"):
            record["evidence"]["vision_probe"] = vision_probe
        outputs[int(step["id"])] = record
        records.append(record)
        _emit_progress(
            progress_callback,
            {
                "status": "running",
                "stage": "executing",
                "active_step_id": None,
                "records": records,
                "plan_display_steps": plan["display_steps"],
            },
        )
    _emit_progress(
        progress_callback,
        {
            "status": "running",
            "stage": "rendering",
            "active_step_id": None,
            "records": records,
            "plan_display_steps": plan["display_steps"],
        },
    )
    display_quality_warnings: list[str] = []
    try:
        display_records, display_quality_warnings = compose_execution_display_projection(
            provider=provider,
            submission=submission,
            plan_steps=plan["steps"],
            records=records,
            stream_callback=stream_callback,
        )
    except (ValueError, OSError, urllib_error.URLError, urllib_error.HTTPError, json.JSONDecodeError) as exc:
        raise ValueError(f"Executor display structure composition failed: {exc}") from exc
    display_by_id = {int(item["step_id"]): item for item in display_records}
    for record in records:
        step_id = int(record["step_id"])
        if step_id not in display_by_id:
            raise ValueError(f"Executor display composition missed step {step_id}.")
        record["display"] = display_by_id[step_id]
    _emit_progress(
        progress_callback,
        {
            "status": "completed",
            "stage": "completed",
            "active_step_id": None,
            "records": records,
            "plan_display_steps": plan["display_steps"],
        },
    )

    return EngineResult(
        title=f"Executor 执行：{submission.chief_complaint or '当前任务'}",
        executive_summary=f"@Executor 已按计划完成 {len(records)} 个步骤，并为每一步生成结构化证据。",
        department=submission.department,
        output_style=submission.output_style,
        professional_answer=_executor_markdown(records),
        coding_table=[],
        cost_table=[],
        references=plan["references"],
        next_steps=[
            "检查每一步证据是否足够支撑对应判断。",
            "将执行记录交给 Decider 做最终证据融合。",
            "如需复核影像区域，可基于 grounding 结果进行人工核查。",
        ],
        safety_note="当前输出为执行与证据记录，不构成最终诊断结论。",
        rounds=[
            {
                "round": 1,
                "alignment": 1.0,
                "summary": "Executor 先验证视觉输入，再通过 grounding harness 完成定位、量化和证据判读。",
            }
        ],
        agent_trace=[
            {
                "role": "Planner",
                "provider": plan["provider"],
                "note": plan["note"],
            },
            {
                "role": EXECUTOR_AGENT_NAME,
                "provider": provider.provider_name,
                "note": "Executed the planned diagnostic steps and recorded evidence for each step.",
            },
        ],
        consensus_score=1.0,
        topology_used="Executor",
        show_process=submission.show_process,
        execution_mode="executor",
        serving_provider=provider.provider_name,
        serving_model=provider.model_name,
        activated_agent=EXECUTOR_AGENT_NAME,
        plan_steps=plan["steps"],
        plan_display_steps=plan["display_steps"],
        execution_records=records,
        display_quality_warnings=display_quality_warnings,
    )
