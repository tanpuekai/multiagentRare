from __future__ import annotations

import re
import json
import time
from http.client import RemoteDisconnected
from textwrap import dedent
from typing import Any
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request
from uuid import uuid4

from rare_agents.display_composer import compose_plan_display_projection
from rare_agents.grounding_harness import _build_grounding_views, prepare_harness_image
from rare_agents.models import AppProfile, CaseSubmission, EngineResult, SystemSettings
from rare_agents.provider_client import StreamCallback, request_chat_completion_stream


PLANNER_AGENT_NAME = "Planner"
PLANNER_TRIGGER_PATTERN = re.compile(r"@planner\b", re.IGNORECASE)
def is_planner_invocation(text: str) -> bool:
    return bool(PLANNER_TRIGGER_PATTERN.search(str(text or "")))


def strip_planner_mention(text: str) -> str:
    cleaned = re.sub(r"@planner\b", "", str(text or ""), flags=re.IGNORECASE)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _join_items(items: list[str]) -> str:
    return ", ".join(item for item in items if item) or "none"


def _short_error_text(error: object, *, limit: int = 160) -> str:
    clean = " ".join(str(error or "").split())
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
            if chunk.startswith("[") or chunk.startswith("{"):
                try:
                    return json.loads(chunk)
                except json.JSONDecodeError:
                    pass
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1 and end > start:
            return json.loads(text[start : end + 1])
        raise


def _extract_chat_content(payload: dict[str, Any]) -> str:
    choices = payload.get("choices")
    if isinstance(choices, list) and choices:
        message = choices[0].get("message", {}) if isinstance(choices[0], dict) else {}
        content = message.get("content")
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            parts = [item.get("text", "") for item in content if isinstance(item, dict) and item.get("type") == "text"]
            if parts:
                return "\n".join(parts).strip()
    output = payload.get("output")
    if isinstance(output, list):
        texts: list[str] = []
        for item in output:
            if not isinstance(item, dict):
                continue
            for content in item.get("content", []):
                if isinstance(content, dict) and content.get("type") == "output_text":
                    texts.append(str(content.get("text", "")))
        if texts:
            return "\n".join(texts).strip()
    raise ValueError("Planner API response did not include usable text content.")


def _resolve_planner_provider(settings: SystemSettings) -> Any | None:
    planner_role = next((role for role in settings.agent_roles if role.role_name.lower() == "planner"), None)
    if planner_role is None:
        return None
    for provider in settings.api_providers:
        role_provider_id = str(getattr(planner_role, "provider_id", "") or "").strip()
        provider_id = str(getattr(provider, "provider_id", "") or "").strip()
        if (
            ((role_provider_id and provider_id and provider_id == role_provider_id) or (not role_provider_id and provider.provider_name == planner_role.provider_name))
            and provider.enabled
            and provider.endpoint
            and provider.api_key
            and provider.model_name
        ):
            return provider
    return None


DEFAULT_TOOLSET: list[dict[str, Any]] = [
    {
        "id": 1,
        "type": "Vision Language Model (VLM)",
        "function": "Make qualitative analysis",
        "input": "Any image, text or multi-modal input",
        "output": "Qualitative analysis or description of certain features",
        "tool_category": "vlm",
    },
    {
        "id": 2,
        "type": "quantitative evidence module",
        "function": "Generate VLM boundary evidence for a target region and rasterize it into a binary mask",
        "input": "Original medical image",
        "output": "One-channel binary segmentation mask saved as an image file",
        "command": "generate_target_region_mask()",
        "tool_category": "evidence_vlm",
        "seg_type": "target_region",
    },
    {
        "id": 3,
        "type": "coding module",
        "function": "Write simple code for deterministic indicator computation from masks or extracted measurements",
        "input": "Segmentation masks, original image, or structured intermediate values",
        "output": "Quantitative measurements saved to diagnosis.json",
        "command": "compute_indicators()",
        "tool_category": "coding",
    },
]


PLANNING_PROFILES: list[dict[str, Any]] = [
    {
        "name": "primary_target_localization",
        "keywords": [
            "localize",
            "locate",
            "segment",
            "boundary",
            "contour",
            "target",
            "region",
            "structure",
            "lesion",
            "mass",
            "finding",
        ],
        "guidance": (
            "Start from the single most relevant visible object or reusable ROI. Use boundary-point grounding only when "
            "that object needs a mask for measurement or as a parent region."
        ),
        "pattern_type": "primary_target_localization",
    },
    {
        "name": "attribute_within_grounded_target",
        "keywords": [
            "margin",
            "shape",
            "texture",
            "orientation",
            "pattern",
            "surface",
            "internal",
            "property",
            "characteristic",
            "feature",
        ],
        "guidance": (
            "When a qualitative judgment refers to a property of an already grounded entity, reuse that grounded target "
            "instead of creating a new unrelated localization step."
        ),
        "pattern_type": "attribute_within_grounded_target",
    },
    {
        "name": "relative_region_evidence",
        "keywords": [
            "inside",
            "within",
            "adjacent",
            "around",
            "near",
            "deep",
            "posterior",
            "surrounding",
            "neighboring",
            "relative",
        ],
        "guidance": (
            "If qualitative evidence is defined relative to another region, create an explicit parent dependency and "
            "ground the evidence with a bbox unless a mask is required for measurement."
        ),
        "pattern_type": "relative_region_evidence",
    },
    {
        "name": "quantitative_geometry",
        "keywords": [
            "measure",
            "measurement",
            "ratio",
            "size",
            "diameter",
            "height",
            "width",
            "area",
            "perimeter",
            "quantitative",
        ],
        "guidance": (
            "Once grounded evidence exists, use a deterministic coding step for geometry, ratios, and derived indicators "
            "instead of asking the VLM to estimate those values informally."
        ),
        "pattern_type": "quantitative_geometry",
    },
    {
        "name": "multimodal_evidence_synthesis",
        "keywords": [
            "text",
            "document",
            "history",
            "report",
            "context",
            "clinical",
            "multimodal",
            "summary",
        ],
        "guidance": (
            "Keep image grounding, text interpretation, and structured aggregation as separate executable steps whenever "
            "the diagnostic task depends on both visual and non-visual evidence."
        ),
        "pattern_type": "multimodal_evidence_synthesis",
    },
]


def _tokenize(value: str) -> set[str]:
    return {
        token
        for token in re.split(r"[^a-zA-Z0-9_.-]+", value.lower())
        if len(token) >= 2
    }


class PlannerRAG:
    def __init__(self, corpus: list[dict[str, Any]] | None = None):
        self.corpus = corpus or PLANNING_PROFILES

    def retrieve(
        self,
        submission: CaseSubmission,
        visual_profile: dict[str, Any] | None = None,
        *,
        top_k: int = 3,
    ) -> list[dict[str, Any]]:
        query_parts = [
            submission.department,
            submission.output_style,
            submission.urgency,
            submission.chief_complaint,
            submission.case_summary,
            " ".join(submission.uploaded_images),
            " ".join(submission.uploaded_docs),
        ]
        if visual_profile:
            query_parts.extend(
                [
                    visual_profile.get("task_kind", ""),
                    visual_profile.get("target_scope", ""),
                    visual_profile.get("primary_target", ""),
                    visual_profile.get("modality", ""),
                    visual_profile.get("anatomy", ""),
                    visual_profile.get("exam_type", ""),
                    visual_profile.get("task_goal", ""),
                    " ".join(str(item) for item in visual_profile.get("retrieval_tags", []) if item),
                    " ".join(str(item) for item in visual_profile.get("salient_targets", []) if item),
                ]
            )
        query = " ".join(query_parts)
        lowered = query.lower()
        query_tokens = _tokenize(query)
        scored: list[tuple[float, dict[str, Any]]] = []
        for item in self.corpus:
            keyword_hits = sum(1 for keyword in item["keywords"] if keyword.lower() in lowered)
            overlap = len(query_tokens & _tokenize(" ".join([item["name"], item["guidance"], " ".join(item["keywords"])])))
            score = (keyword_hits * 4.0) + overlap
            if score > 0:
                scored.append((score, item))
        if not scored:
            scored.append((1.0, self.corpus[0]))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [
            {
                "name": item["name"],
                "pattern_type": item["pattern_type"],
                "score": round(score, 3),
                "guidance": item["guidance"],
            }
            for score, item in scored[:top_k]
        ]


def _retrieve_planning_context(
    submission: CaseSubmission,
    visual_profile: dict[str, Any] | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    hits = PlannerRAG().retrieve(submission, visual_profile)
    profile_lines: list[str] = []
    if visual_profile:
        profile_lines.extend(
            [
                "Visual task profile:",
                f"- modality: {visual_profile.get('modality') or 'unknown'}",
                f"- anatomy: {visual_profile.get('anatomy') or 'unknown'}",
                f"- exam_type: {visual_profile.get('exam_type') or 'unknown'}",
                f"- task_goal: {visual_profile.get('task_goal') or 'unspecified'}",
                f"- task_kind: {visual_profile.get('task_kind') or 'mixed_visual_review'}",
                f"- target_scope: {visual_profile.get('target_scope') or 'unknown'}",
                f"- primary_target: {visual_profile.get('primary_target') or 'unspecified'}",
                f"- salient_targets: {_join_items([str(item) for item in visual_profile.get('salient_targets', []) if item])}",
                f"- retrieval_tags: {_join_items([str(item) for item in visual_profile.get('retrieval_tags', []) if item])}",
            ]
        )
    rag_lines = [f"[{hit['name']} | score={hit['score']}]\n{hit['guidance']}" for hit in hits]
    context = "\n\n".join(["\n".join(profile_lines)] + rag_lines if profile_lines else rag_lines)
    return context, hits


def _format_toolset_for_prompt(toolset: list[dict[str, Any]]) -> str:
    lines = []
    for item in toolset:
        lines.append(
            f"{item['id']}. [tool_id: {item['id']}] [type: {item['type']}] "
            f"{item['function']} (input: {item.get('input', '')} -> output: {item.get('output', '')})"
        )
    return "\n".join(lines)


def _rv_config(finding: str | None, *, image_step: bool) -> dict[str, Any]:
    target = finding or "the target finding"
    if image_step:
        templates = [
            "Assess the provided image. Is there evidence of {finding}? Please respond in JSON format with fields: conclusion (Yes/Uncertain/No), confidence (0.00-1.00), description (brief justification).",
            "Examine the provided image for {finding}. Do you observe this finding? Please respond in JSON format with fields: conclusion (Yes/Uncertain/No), confidence (0.00-1.00), description (brief justification).",
            "Inspect the provided image. Does this image show {finding}? Please respond in JSON format with fields: conclusion (Yes/Uncertain/No), confidence (0.00-1.00), description (brief justification).",
        ]
        return {
            "rv_b_enabled": True,
            "rv_b_mode": "bbox",
            "conclusion_span": True,
            "confidence_min": 0.05,
            "question_templates": templates,
        }
    return {
        "rv_b_enabled": False,
        "conclusion_span": False,
        "confidence_min": 0.05,
        "question_templates": [
            "Based on the provided context, does the evidence support {finding}? Please respond in JSON format with fields: conclusion (Yes/No/Uncertain), confidence (0.00-1.00), description (brief justification).",
            "Using only the provided context, is there evidence of {finding}? Please respond in JSON format with fields: conclusion (Yes/No/Uncertain), confidence (0.00-1.00), description (brief justification).",
            "Interpret the provided context for {finding}. Does it indicate an abnormal condition? Please respond in JSON format with fields: conclusion (Yes/No/Uncertain), confidence (0.00-1.00), description (brief justification).",
        ],
    }


def _normalize_tool_config(item: dict[str, Any], action_type: str, tools: list[int], finding: str | None) -> dict[str, Any]:
    raw = item.get("tool_config")
    if isinstance(raw, dict) and raw.get("tool_type"):
        normalized = dict(raw)
        if normalized.get("tool_type") == "evidence_vlm":
            normalized.pop("target_anchor", None)
            target_label = _derive_target_label(
                raw_target_label=normalized.get("target_label"),
                raw_seg_type=normalized.get("seg_type"),
                action=str(item.get("action") or ""),
                finding=finding,
            )
            normalized["seg_type"] = _normalize_seg_type(
                normalized.get("seg_type"),
                action=str(item.get("action") or ""),
                finding=finding,
            )
            if (
                normalized["seg_type"] in _GENERIC_SEG_TYPES
                or len(str(normalized["seg_type"])) > 72
                or "downstream" in str(normalized["seg_type"])
            ) and not _is_generic_target_label(target_label):
                normalized["seg_type"] = _slugify_target(target_label) or "target_region"
            normalized["target_label"] = target_label
            normalized["roi_definition"] = _normalize_roi_definition("", target_label)
            normalized["include"] = _default_include_regions(target_label)
            normalized["exclude"] = _normalize_text_list(normalized.get("exclude")) or _default_exclude_regions()
            input_type_values = [int(value) for value in item.get("input_type", [0]) if str(value).strip().lstrip("-").isdigit()]
            if 0 in input_type_values and not normalized.get("relationship"):
                normalized.pop("spatial_priors", None)
            normalized["evidence_mode"] = "boundary_points"
        if normalized.get("tool_type") == "vlm":
            normalized["evidence_mode"] = "bbox"
        if action_type == "qualitative":
            normalized.setdefault("finding", finding or "target finding")
            if not isinstance(normalized.get("rv_config"), dict) or not normalized.get("rv_config"):
                normalized["rv_config"] = _rv_config(finding, image_step=normalized.get("tool_type") == "vlm")
        return normalized
    if action_type == "quantitative":
        if any(tool == 2 for tool in tools):
            target_label = _derive_target_label(
                raw_target_label=item.get("target_label"),
                raw_seg_type=item.get("seg_type"),
                action=str(item.get("action") or ""),
                finding=finding,
            )
            seg_type = _normalize_seg_type(item.get("seg_type"), action=str(item.get("action") or ""), finding=finding)
            if (
                seg_type in _GENERIC_SEG_TYPES
                or len(str(seg_type)) > 72
                or "downstream" in str(seg_type)
            ) and not _is_generic_target_label(target_label):
                seg_type = _slugify_target(target_label) or "target_region"
            return {
                "tool_type": "evidence_vlm",
                "seg_type": seg_type,
                "target_label": target_label,
                "roi_definition": _normalize_roi_definition("", target_label),
                "include": _default_include_regions(target_label),
                "exclude": _default_exclude_regions(),
                "evidence_mode": "boundary_points",
            }
        return {"tool_type": "coding"}
    image_step = any(tool == 1 for tool in tools) and 0 in [int(value) for value in item.get("input_type", [0])]
    return {
        "tool_type": "vlm" if image_step else "text_vlm",
        "finding": finding or "target finding",
        "evidence_mode": "bbox" if image_step else "",
        "rv_config": _rv_config(finding, image_step=image_step),
    }


def _infer_finding_from_action(action: str) -> str:
    text = re.sub(r"\s+", " ", str(action or "")).strip()
    text = re.sub(
        r"^(analyze|assess|inspect|examine|determine|identify|classify|evaluate|extract|localize|describe|interpret)\s+",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\bfor downstream\b.*$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bas (input|evidence)\b.*$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bfor (later|subsequent|follow-up)\b.*$", "", text, flags=re.IGNORECASE)
    text = text.strip(" .")
    if not text:
        return "target diagnostic finding"
    return text[:160]


_GENERIC_SEG_TYPES = {
    "",
    "abnormality",
    "finding",
    "lesion",
    "mass",
    "nodule",
    "object",
    "target_region",
    "target",
    "boundary_points",
    "instance_boundary",
    "boundary_point",
    "boundary",
    "mask",
    "region_mask",
    "roi",
    "sparse_landmark",
    "structure",
}


_GENERIC_TARGET_LABELS = {item.replace("_", " ") for item in _GENERIC_SEG_TYPES} | {
    "current finding",
    "diagnostic finding",
    "image finding",
    "region",
    "visible target",
}


def _compact_text(value: object, *, max_len: int = 220) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip(" .,-_")
    return text[:max_len].strip()


def _normalize_target_label_text(value: object) -> str:
    text = _compact_text(value, max_len=140)
    text = re.sub(r"^(the|a|an)\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^(complete|entire|full|requested)\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^visible\s+extent\s+of\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^boundary\s+of\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^outer\s+boundary\s+of\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+for\s+downstream.*$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+for\s+quantitative.*$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip(" .,-_")
    return text


def _slugify_target(value: str) -> str:
    slug = re.sub(r"[^a-z0-9_]+", "_", str(value or "").lower()).strip("_")
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug[:72].strip("_")


def _is_generic_target_label(value: object) -> bool:
    text = re.sub(r"[_\-]+", " ", str(value or "").lower()).strip()
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return not text or text in _GENERIC_TARGET_LABELS


def _derive_seg_phrase(action: str, finding: str | None) -> str:
    text = re.sub(r"\s+", " ", str(action or "")).strip()
    replacements = [
        r"^ground\s+the\s+",
        r"^ground\s+boundary\s+points\s+of\s+",
        r"^ground\s+boundary\s+points\s+for\s+",
        r"^ground\s+",
        r"^localize\s+",
        r"^segment\s+",
        r"^trace\s+",
        r"^identify\s+",
        r"\s+using\s+boundary-point\s+evidence.*$",
        r"\s+with\s+boundary\s+points.*$",
        r"\s+to\s+generate\s+binary\s+segmentation\s+mask.*$",
        r"\s+to\s+create\s+.*mask.*$",
        r"\s+for\s+mask\s+generation.*$",
        r"\s+for\s+quantitative.*$",
        r"\s+from\s+masks.*$",
    ]
    for pattern in replacements:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)
    text = re.sub(r"^(the|a|an)\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bboundary points\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bbinary segmentation mask\b", "", text, flags=re.IGNORECASE)
    text = text.strip(" .,-_")
    if not text:
        text = str(finding or "").strip()
    if not text:
        text = "target region"
    return text


def _derive_target_label(
    *,
    raw_target_label: object,
    raw_seg_type: object,
    action: str,
    finding: str | None,
) -> str:
    for value in [raw_target_label, _derive_seg_phrase(action, finding), raw_seg_type, finding]:
        text = _normalize_target_label_text(value)
        if text and not _is_generic_target_label(text):
            return text
    return _normalize_target_label_text(_derive_seg_phrase(action, finding)) or "target region"


def _normalize_text_list(value: object) -> list[str]:
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    return [_compact_text(item, max_len=140) for item in value if _compact_text(item, max_len=140)]


def _default_include_regions(target_label: str) -> list[str]:
    if not target_label or _is_generic_target_label(target_label):
        return []
    return ["full visible extent of the requested target"]


def _default_exclude_regions() -> list[str]:
    return ["adjacent non-target structures", "background", "text labels", "rulers", "calipers", "non-target artifacts"]


def _normalize_roi_definition(value: object, target_label: str) -> str:
    text = _compact_text(value or _default_roi_definition(target_label), max_len=260)
    if text and "target-to-surrounding" not in text.lower() and "surrounding tissue" not in text.lower():
        text = _compact_text(f"{text}. Use the outermost target-to-surrounding transition as the final contour.", max_len=340)
    return text


def _default_roi_definition(target_label: str) -> str:
    if not target_label or _is_generic_target_label(target_label):
        return ""
    return (
        f"Delineate full visible extent of {target_label}. Place boundary on target-to-surrounding-tissue transition. "
        "Do not trace only the most salient core if the target has broader visible extent."
    )


def _normalize_seg_type(raw_seg_type: object, *, action: str, finding: str | None) -> str:
    raw_text = re.sub(r"[_\-]+", " ", str(raw_seg_type or "").lower()).strip()
    raw_text = _derive_seg_phrase(raw_text, finding)
    seg_type = re.sub(r"[^a-z0-9_]+", "_", raw_text).strip("_")
    if seg_type and seg_type not in _GENERIC_SEG_TYPES:
        return seg_type
    phrase = _derive_seg_phrase(action, finding)
    normalized = re.sub(r"[^a-z0-9_]+", "_", phrase.lower()).strip("_")
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    if normalized and normalized not in _GENERIC_SEG_TYPES:
        return normalized
    return "target_region"


def _is_placeholder_finding(finding: str | None) -> bool:
    text = re.sub(r"[^a-z0-9]+", " ", str(finding or "").lower()).strip()
    if not text:
        return True
    return text in {
        "current finding",
        "current diagnostic finding",
        "target finding",
        "target diagnostic finding",
        "diagnostic finding",
        "abnormality",
        "current abnormality",
    } or bool(re.fullmatch(r"step\s+\d+", text))


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


def _visual_profile_image_payloads(image_payloads: list[dict[str, str]]) -> list[dict[str, str]]:
    views: list[dict[str, str]] = []
    for payload in image_payloads:
        context = prepare_harness_image(payload)
        for view in _build_grounding_views(context, parent_bbox=None, relationship=""):
            if not view.data_url:
                continue
            views.append(
                {
                    "name": f"{payload.get('name') or 'uploaded_image'}:{view.name}",
                    "media_type": context.media_type,
                    "label": view.label,
                    "data_url": view.data_url,
                }
            )
        if len(views) >= 4:
            break
    return views[:4]


def _clamp01_number(value: object) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return max(0.0, min(1.0, number))


def _normalize_anchor_point(value: object) -> list[float]:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        return []
    x = _clamp01_number(value[0])
    y = _clamp01_number(value[1])
    if x is None or y is None:
        return []
    return [round(x, 6), round(y, 6)]


def _normalize_anchor_bbox(value: object) -> list[float]:
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        return []
    coords = [_clamp01_number(item) for item in value]
    if any(item is None for item in coords):
        return []
    x1, y1, x2, y2 = [float(item) for item in coords]
    left, right = sorted([x1, x2])
    top, bottom = sorted([y1, y2])
    if right - left < 0.005 or bottom - top < 0.005:
        return []
    return [round(left, 6), round(top, 6), round(right, 6), round(bottom, 6)]


def _normalize_target_anchor(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    anchor: dict[str, Any] = {}
    point = _normalize_anchor_point(value.get("point"))
    bbox = _normalize_anchor_bbox(value.get("bbox"))
    location = _compact_text(value.get("location"), max_len=120)
    if point:
        anchor["point"] = point
    if bbox:
        anchor["bbox"] = bbox
    if location:
        anchor["location"] = location
    return anchor


def _planner_request(
    provider: Any,
    messages: list[dict[str, Any]],
    *,
    max_tokens: int,
    stream_callback: StreamCallback | None = None,
) -> str:
    url = f"{_normalize_provider_endpoint(provider.endpoint).rstrip('/')}/chat/completions"
    body: dict[str, Any] = {
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
            user_agent="RareMDT-Planner/0.2",
            on_delta=stream_callback,
        )
    payload = json.dumps(body).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {provider.api_key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Connection": "close",
        "User-Agent": "RareMDT-Planner/0.2",
    }
    last_error: Exception | None = None
    for attempt in range(3):
        request = urllib_request.Request(url, data=payload, headers=headers, method="POST")
        try:
            with urllib_request.urlopen(request, timeout=120) as response:
                response_payload = json.loads(response.read().decode("utf-8", errors="replace"))
            return _extract_chat_content(response_payload)
        except (urllib_error.URLError, urllib_error.HTTPError, RemoteDisconnected, TimeoutError, ConnectionError, OSError) as exc:
            last_error = exc
            if attempt == 2:
                break
            time.sleep(1.0 + attempt)
    if last_error is not None:
        raise last_error
    raise ValueError("Planner request failed.")


def _visual_retrieval_prompt(submission: CaseSubmission) -> str:
    goal = submission.chief_complaint or submission.case_summary[:160] or "generate a downstream diagnostic plan"
    return dedent(
        f"""
        You are the retrieval router for a medical planner.
        Review the uploaded medical image together with the task text, then return ONLY a JSON object.

        Task text:
        - Goal: {goal}
        - Department: {submission.department}
        - Urgency: {submission.urgency}
        - Uploaded image names: {_join_items(submission.uploaded_images)}
        - Uploaded documents: {_join_items(submission.uploaded_docs)}
        - Case summary: {submission.case_summary}

        Return this exact JSON schema:
        {{
          "modality": "",
          "anatomy": "",
          "exam_type": "",
          "task_goal": "",
          "task_kind": "locate_primary_target|assess_grounded_target|localize_relative_region|multimodal_review|mixed_visual_review",
          "target_scope": "entity|local_region|relative_region|diffuse_pattern|unknown",
          "primary_target": "",
          "primary_target_anchor": {{"point": [0.0, 0.0], "bbox": [0.0, 0.0, 0.0, 0.0], "location": ""}},
          "retrieval_tags": ["", ""],
          "salient_targets": ["", ""],
          "confidence": 0.0
        }}

        Rules:
        - Do NOT make a diagnosis.
        - task_kind must describe the kind of planning problem, not a disease name.
        - target_scope must describe what kind of region the executor is expected to ground.
        - primary_target should be the main visible physical entity or evidence region that downstream grounding should focus on first.
        - primary_target must be visually concrete rather than diagnostic or generic; prefer phrases such as "dominant hypoechoic mass body", "optic disc", "retinal hemorrhage", or "focal opacity" when supported by the image.
        - primary_target_anchor identifies the same primary target in normalized full-image coordinates.
        - primary_target_anchor.point must be a point inside the primary target when the target is visible.
        - primary_target_anchor.bbox must be a coarse bounding box around the primary target, normalized as [x1, y1, x2, y2].
        - primary_target_anchor.location must be a short visual location phrase that can disambiguate this target from similar nearby structures.
        - If a coordinate-grid view is provided, use it to calibrate primary_target_anchor coordinates in the original full-image frame.
        - retrieval_tags and salient_targets should be short, concrete phrases useful for planning.
        - confidence must be a number in [0, 1].
        """
    ).strip()


def _multimodal_user_content(prompt: str, image_payloads: list[dict[str, str]]) -> list[dict[str, Any]]:
    parts: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
    for item in image_payloads:
        label = "\n".join(part for part in [str(item.get("name", "")).strip(), str(item.get("label", "")).strip()] if part)
        if label:
            parts.append({"type": "text", "text": label})
        parts.append({"type": "image_url", "image_url": {"url": item["data_url"]}})
    return parts


def _request_visual_profile(
    submission: CaseSubmission,
    settings: SystemSettings,
    image_payloads: list[dict[str, Any]] | None,
    stream_callback: StreamCallback | None = None,
) -> tuple[dict[str, Any], str, str]:
    provider = _resolve_planner_provider(settings)
    payloads = _safe_image_payloads(image_payloads)
    if provider is None:
        raise ValueError("Planner provider is not configured.")
    if not payloads:
        raise ValueError("Planner visual retrieval requires uploaded image content.")
    profile_payloads = _visual_profile_image_payloads(payloads)
    raw = _planner_request(
        provider,
        [
            {
                "role": "system",
                "content": "You are a careful medical planning router. Return ONLY JSON.",
            },
            {
                "role": "user",
                "content": _multimodal_user_content(_visual_retrieval_prompt(submission), profile_payloads),
            },
        ],
        max_tokens=1600,
        stream_callback=stream_callback,
    )
    parsed = _parse_llm_json(raw)
    if not isinstance(parsed, dict):
        raise ValueError("Planner visual retrieval did not return a JSON object.")
    profile = {
        "modality": str(parsed.get("modality", "")).strip(),
        "anatomy": str(parsed.get("anatomy", "")).strip(),
        "exam_type": str(parsed.get("exam_type", "")).strip(),
        "task_goal": str(parsed.get("task_goal", "")).strip(),
        "task_kind": str(parsed.get("task_kind", "mixed_visual_review")).strip() or "mixed_visual_review",
        "target_scope": str(parsed.get("target_scope", "unknown")).strip() or "unknown",
        "primary_target": str(parsed.get("primary_target", "")).strip(),
        "primary_target_anchor": _normalize_target_anchor(parsed.get("primary_target_anchor")),
        "retrieval_tags": [str(item).strip() for item in parsed.get("retrieval_tags", []) if str(item).strip()],
        "salient_targets": [str(item).strip() for item in parsed.get("salient_targets", []) if str(item).strip()],
        "confidence": max(0.0, min(1.0, float(parsed.get("confidence", 0.0) or 0.0))),
    }
    return profile, provider.provider_name, provider.model_name


def _planner_prompt(
    submission: CaseSubmission,
    profile: AppProfile,
    rag_text: str,
    visual_profile: dict[str, Any] | None,
) -> str:
    toolset_text = _format_toolset_for_prompt(DEFAULT_TOOLSET)
    goal = submission.chief_complaint or submission.case_summary[:160] or "generate a downstream diagnostic execution plan"
    visual_text = dedent(
        f"""
        Visual task profile:
        - modality: {visual_profile.get('modality') or 'unknown'}
        - anatomy: {visual_profile.get('anatomy') or 'unknown'}
        - exam_type: {visual_profile.get('exam_type') or 'unknown'}
        - task_goal: {visual_profile.get('task_goal') or 'unspecified'}
        - task_kind: {visual_profile.get('task_kind') or 'mixed_visual_review'}
        - target_scope: {visual_profile.get('target_scope') or 'unknown'}
        - primary_target: {visual_profile.get('primary_target') or 'unspecified'}
        - primary_target_anchor: {json.dumps(visual_profile.get('primary_target_anchor') or {}, ensure_ascii=False)}
        - salient_targets: {_join_items([str(item) for item in visual_profile.get('salient_targets', []) if item])}
        """
        if visual_profile
        else "Visual task profile:\n- not available"
    ).strip()
    return dedent(
        f"""
        You are the task-level Planner in a medical agent workflow.
        Your job is to generate a compact executable plan for downstream agents after retrieval has already been done.

        Retrieved planning context:
        {rag_text}

        {visual_text}

        Task:
        - Hospital: {profile.hospital_name}
        - Doctor profile: {profile.user_name} {profile.title}
        - Goal: {goal}
        - Department: {submission.department}
        - Urgency: {submission.urgency}
        - Uploaded images: {_join_items(submission.uploaded_images)}
        - Uploaded documents: {_join_items(submission.uploaded_docs)}
        - Patient age: {submission.patient_age or "not provided"}
        - Patient sex: {submission.patient_sex or "not provided"}

        Case summary:
        {submission.case_summary}

        Available tools:
        {toolset_text}

        Rules:
        - Return ONLY a strict JSON array, no markdown and no explanation.
        - Each step must contain: id, tool, action_type, action, input_type, output_type, output_path.
        - Add finding for every qualitative step; quantitative steps may set finding to null.
        - Never use placeholder findings such as "current finding", "target finding", "Step 4", "abnormality", or "diagnostic finding".
        - Every qualitative finding must name the concrete visual/clinical indicator being checked.
        - A qualitative finding must never just restate the user's instruction such as "give a diagnosis", "analyze the image", or "generate a plan".
        - id starts from 1 and increases by 1.
        - tool is an array of integer tool ids from the available toolset.
        - action_type is "qualitative" or "quantitative".
        - input_type uses [0] for raw inputs, or prior step ids only for true causal dependencies.
        - output_type is "intermediate result" or "final indicator".
        - For non-image outputs use output_path "diagnosis.json"; only masks or images may use .png/.jpg paths.
        - Each qualitative final indicator must be a separate step with a concise abnormal finding.
        - Keep the plan compact: usually 4-7 steps.
        - Do not use disease-specific templates or hardcoded specialty workflows.
        - The first image-grounding step should localize the primary target or strongest evidence region needed by later steps.
        - Use the visual task profile's primary_target as the first localization seg_type when it is concrete.
        - The first localization seg_type must name a visible physical target boundary, not an abstract diagnosis, broad disease class, or generic word such as lesion/abnormality when a more concrete visible entity is available.
        - Each action must be operational and specific. Avoid vague wording such as "analyze the image" or "check the current finding".
        - Do NOT include report generation, decider fusion, HITL text, or human-facing SOP wording.
        - For qualitative VLM evidence-check steps, include tool_config with tool_type "vlm", an rv_config, and evidence_mode "bbox"; these steps must be grounded only with a bbox.
        - For qualitative VLM evidence-check steps, finding must name the concrete observable sign or property to verify in the image.
        - For qualitative text interpretation steps, use tool_config.tool_type = "text_vlm".
        - Use tool_config.tool_type = "evidence_vlm" with evidence_mode "boundary_points" only when the step needs an actual mask/contour for a visible object that will be measured or reused as a parent ROI.
        - Do not use evidence_vlm merely to show a qualitative imaging sign, artifact, enhancement, shadow, texture, margin, or pattern. Those evidence-check steps must use tool_type "vlm" and evidence_mode "bbox".
        - For evidence_vlm steps, include tool_config.target_label as a concise concrete physical ROI label that the executor can segment directly.
        - Keep target_label short. Do not put task verbs, "complete", "entire", measurement intent, or boundary instructions in target_label; put boundary semantics in roi_definition.
        - Do not set tool_config.target_label to a generic word alone, such as "lesion", "mass", "target", "abnormality", "finding", or "region". Use a specific phrase such as "dominant cystic lesion body in left breast ultrasound", "optic disc", or "focal opacity".
        - Do not copy Visual task profile coordinates into the execution plan by default; the Executor will localize from the image with its own coordinate harness.
        - Use spatial words from the visual profile only when needed to disambiguate similar targets, and keep them in spatial_priors.
        - For evidence_vlm steps, include a concise seg_type naming the target object; seg_type may be a compact slug, but target_label must remain human-readable and concrete.
        - For evidence_vlm steps, include a compact tool_config.roi_definition describing the exact boundary to trace.
        - For evidence_vlm steps, include tool_config.include and tool_config.exclude arrays when the target may be confused with artifacts, adjacent anatomy, shadows, enhancement, labels, rulers, or background.
        - In evidence_vlm include, list only physical parts of the requested target body itself.
        - target_label should name the target entity, not its imaging texture. Prefer "dominant breast ultrasound lesion" over "dominant anechoic cystic structure"; put anechoic, hypoechoic, cystic, bright, dark, smooth, irregular, or similar visual attributes in spatial_priors, finding, or roi_definition.
        - Avoid diagnostic labels in target_label when the diagnosis is not already known; use neutral visible entity names.
        - Never put contextual imaging signs, artifacts, downstream qualitative findings, shadows, posterior enhancement, labels, rulers, calipers, or surrounding tissue in evidence_vlm include. Put those in exclude or create a separate bbox-only VLM evidence step.
        - A mask/contour step must segment only the parent target body needed for measurement; signs around that target must not enlarge the ROI.
        - Example evidence_vlm tool_config shape: {{"tool_type":"evidence_vlm","seg_type":"dominant_breast_ultrasound_lesion","target_label":"dominant breast ultrasound lesion","roi_definition":"Delineate the full visible extent of the requested target. Put the boundary on the visual transition between the target and surrounding tissue. Do not trace only the brightest or most salient core if the target has a broader visible extent.","include":["full visible extent of the requested target"],"exclude":["adjacent structures","background","text labels","rulers","calipers","posterior acoustic artifacts"],"evidence_mode":"boundary_points","target_scope":"entity"}}.
        - For deterministic computation, use tool_config.tool_type = "coding".
        - Coding steps may only depend on upstream evidence_vlm mask steps that provide boundary_points; do not feed bbox-only qualitative indicators into geometry computation.
        - When a grounded region depends on a previously localized parent region, also include relative_to_step, relationship, and parent_label.
        - Use relationship values such as same_target, inside_parent, deep_to_parent, adjacent_to_parent, or overlaps_parent only when they are visually meaningful and explicit.
        - If a step evaluates an attribute of the same entity grounded earlier, reuse that target with relationship "same_target" instead of creating a fresh localization.
        - If a step evaluates a region defined relative to an earlier target, make the parent dependency explicit instead of relying on downstream inference.
        - When useful, add target_scope using one of: entity, local_region, relative_region, diffuse_pattern.
        - When useful, add spatial_priors and sanity_checks as short arrays to help the downstream grounding harness validate the result.
        - Do not ask qualitative evidence-check steps to output masks, polygons, or boundary points.
        - Do not ask localization or quantitative segmentation steps to output bbox-only evidence.
        """
    ).strip()


def _validate_steps(raw_steps: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_steps, list):
        raise ValueError("Planner output is not a JSON array.")
    cleaned: list[dict[str, Any]] = []
    required = [
        "id",
        "tool",
        "action_type",
        "action",
        "input_type",
        "output_type",
        "output_path",
    ]
    known_ids: set[int] = set()
    records_by_id: dict[int, dict[str, Any]] = {}
    for index, item in enumerate(raw_steps, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Planner step #{index} is not an object.")
        for key in required:
            if key not in item:
                raise ValueError(f"Planner step #{index} is missing {key}.")
        action_type = str(item["action_type"]).strip().lower()
        if action_type not in {"qualitative", "quantitative"}:
            raise ValueError(f"Planner step #{index} has invalid action_type.")
        output_type = str(item["output_type"]).strip().lower()
        if output_type not in {"intermediate result", "final indicator"}:
            raise ValueError(f"Planner step #{index} has invalid output_type.")
        step_id = int(item.get("id") or index)
        tools = [int(value) for value in item.get("tool") or [1]]
        input_type = [int(value) for value in item.get("input_type") or [0]]
        for parent in input_type:
            if parent != 0 and parent not in known_ids:
                raise ValueError(f"Planner step #{index} has a forward or unknown input_type dependency.")
        raw_tool_config = item.get("tool_config") if isinstance(item.get("tool_config"), dict) else {}
        raw_finding = item.get("finding")
        if raw_finding is None and isinstance(raw_tool_config, dict):
            raw_finding = raw_tool_config.get("finding")
        finding = None if raw_finding is None else str(raw_finding).strip()
        if action_type == "qualitative" and _is_placeholder_finding(finding):
            finding = _infer_finding_from_action(str(item.get("action") or ""))
        if action_type == "qualitative" and _is_placeholder_finding(finding):
            raise ValueError(f"Planner step #{index} has a placeholder finding.")
        record: dict[str, Any] = {
            "id": step_id,
            "tool": tools,
            "action_type": action_type,
            "action": str(item.get("action") or "").strip(),
            "finding": finding,
            "input_type": input_type,
            "output_type": output_type,
            "output_path": str(item.get("output_path") or "diagnosis.json").strip(),
            "tool_config": _normalize_tool_config(item, action_type, tools, finding),
        }
        for optional_key in [
            "target_label",
            "roi_definition",
            "include",
            "exclude",
            "target_scope",
            "evidence_mode",
            "relative_to_step",
            "relationship",
            "parent_label",
            "spatial_priors",
            "sanity_checks",
        ]:
            if optional_key in item:
                record[optional_key] = item[optional_key]
            elif optional_key in raw_tool_config:
                record[optional_key] = raw_tool_config[optional_key]
        if record["tool_config"].get("tool_type") == "evidence_vlm":
            for contract_key in ["target_label", "roi_definition", "include", "exclude", "evidence_mode", "target_scope"]:
                if contract_key in record["tool_config"]:
                    record[contract_key] = record["tool_config"][contract_key]
            if 0 in input_type and not record.get("relationship"):
                record.pop("spatial_priors", None)
        if record["tool_config"].get("tool_type") == "vlm" and "relative_to_step" not in record:
            nonzero_inputs = [parent for parent in input_type if parent != 0]
            if len(nonzero_inputs) == 1:
                record["relative_to_step"] = nonzero_inputs[0]
                record["relationship"] = "same_target"
        tool_type = str(record["tool_config"].get("tool_type") or "").strip()
        evidence_mode = str(record["tool_config"].get("evidence_mode") or record.get("evidence_mode") or "").strip()
        if tool_type == "evidence_vlm":
            target_label = str(record["tool_config"].get("target_label") or record.get("target_label") or "").strip()
            roi_definition = str(record["tool_config"].get("roi_definition") or record.get("roi_definition") or "").strip()
            include = record["tool_config"].get("include") or record.get("include")
            exclude = record["tool_config"].get("exclude") or record.get("exclude")
            if _is_generic_target_label(target_label):
                raise ValueError(f"Planner step #{index} evidence_vlm target_label is not concrete.")
            if evidence_mode != "boundary_points":
                raise ValueError(f"Planner step #{index} evidence_vlm must use evidence_mode boundary_points.")
            if not roi_definition:
                raise ValueError(f"Planner step #{index} evidence_vlm must define roi_definition.")
            if not isinstance(include, list) or not include:
                raise ValueError(f"Planner step #{index} evidence_vlm must define non-empty include regions.")
            if not isinstance(exclude, list) or not exclude:
                raise ValueError(f"Planner step #{index} evidence_vlm must define non-empty exclude regions.")
        if tool_type == "vlm" and evidence_mode != "bbox":
            raise ValueError(f"Planner step #{index} VLM evidence-check must use evidence_mode bbox.")
        if tool_type == "coding":
            parent_ids = [parent for parent in input_type if parent != 0]
            for parent_id in parent_ids:
                parent_record = records_by_id.get(parent_id)
                parent_tool = str((parent_record or {}).get("tool_config", {}).get("tool_type") or "").strip()
                parent_mode = str((parent_record or {}).get("tool_config", {}).get("evidence_mode") or (parent_record or {}).get("evidence_mode") or "").strip()
                if parent_tool == "vlm" and parent_mode == "bbox":
                    raise ValueError(f"Planner step #{index} coding cannot depend on bbox-only evidence step #{parent_id}.")
        cleaned.append(record)
        known_ids.add(step_id)
        records_by_id[step_id] = record
    return cleaned


def _request_llm_plan(
    submission: CaseSubmission,
    profile: AppProfile,
    settings: SystemSettings,
    rag_text: str,
    visual_profile: dict[str, Any] | None,
    stream_callback: StreamCallback | None = None,
) -> tuple[list[dict[str, Any]], str, str, Any]:
    provider = _resolve_planner_provider(settings)
    if provider is None:
        raise ValueError("Planner provider is not configured.")
    content = _planner_request(
        provider,
        [
            {
                "role": "system",
                "content": "You are the Planner agent in a clinical multi-agent system. Return ONLY JSON.",
            },
            {"role": "user", "content": _planner_prompt(submission, profile, rag_text, visual_profile)},
        ],
        max_tokens=4096,
        stream_callback=stream_callback,
    )
    steps = _validate_steps(_parse_llm_json(content))
    return steps, provider.provider_name, provider.model_name, provider


def _markdown_plan(display_steps: list[dict[str, Any]]) -> str:
    rows = "\n".join(
        f"{index}. **{step.get('title_zh') or f'步骤 {index}'}**\n"
        f"   {str(step.get('desc_zh') or '').strip()}"
        for index, step in enumerate(display_steps, start=1)
    )
    return dedent(
        f"""
        **执行计划**

        {rows}
        """
    ).strip()


def compile_plan(
    submission: CaseSubmission,
    profile: AppProfile,
    settings: SystemSettings,
    *,
    image_payloads: list[dict[str, Any]] | None = None,
    stream_callback: StreamCallback | None = None,
) -> dict[str, Any]:
    payloads = _safe_image_payloads(image_payloads)
    visual_profile = None
    visual_stage_used = False
    planner_provider_config = _resolve_planner_provider(settings)
    planner_provider = planner_provider_config.provider_name if planner_provider_config is not None else ""
    planner_model = planner_provider_config.model_name if planner_provider_config is not None else ""

    if submission.uploaded_images:
        if not payloads:
            raise ValueError("Planner needs the uploaded image content to perform retrieval.")
        try:
            visual_profile, planner_provider, planner_model = _request_visual_profile(submission, settings, payloads, stream_callback)
        except (ValueError, OSError, urllib_error.URLError, urllib_error.HTTPError, json.JSONDecodeError) as exc:
            provider_label = " / ".join(item for item in [planner_provider, planner_model] if item) or "未配置接口"
            raise ValueError(
                f"Planner 视觉检索失败：{provider_label} 当前不能完成图像输入调用。"
                f" 请到设置页的 Planner / Executor 区域测试视觉接口。原始错误：{_short_error_text(exc)}"
            ) from exc
        if visual_profile is None:
            raise ValueError("Planner visual retrieval did not return a task profile.")
        visual_stage_used = True

    rag_text, rag_hits = _retrieve_planning_context(submission, visual_profile)
    try:
        steps, plan_provider, plan_model, plan_provider_config = _request_llm_plan(
            submission,
            profile,
            settings,
            rag_text,
            visual_profile,
            stream_callback,
        )
    except (ValueError, OSError, urllib_error.URLError, urllib_error.HTTPError, json.JSONDecodeError) as exc:
        raise ValueError(f"Planner plan generation failed: {exc}") from exc
    display_quality_warnings: list[str] = []
    try:
        display_steps, display_quality_warnings = compose_plan_display_projection(
            provider=plan_provider_config,
            submission=submission,
            plan_steps=steps,
            visual_profile=visual_profile,
            rag_text=rag_text,
            stream_callback=stream_callback,
        )
    except (ValueError, OSError, urllib_error.URLError, urllib_error.HTTPError, json.JSONDecodeError) as exc:
        raise ValueError(f"Planner display structure composition failed: {exc}") from exc

    return {
        "steps": steps,
        "display_steps": display_steps,
        "references": [
            {
                "type": "planner_retrieval",
                "title": hit["name"],
                "region": f"score={hit['score']}",
            }
            for hit in rag_hits
        ],
        "provider": plan_provider or planner_provider,
        "model": plan_model or planner_model,
        "note": (
            "Completed image-aware retrieval and generated the downstream execution plan."
            if visual_stage_used
            else "Generated the downstream execution plan from the submitted task."
        ),
        "visual_stage_used": visual_stage_used,
        "display_quality_warnings": display_quality_warnings,
    }


def run_planner_case(
    submission: CaseSubmission,
    profile: AppProfile,
    settings: SystemSettings,
    *,
    image_payloads: list[dict[str, Any]] | None = None,
    stream_callback: StreamCallback | None = None,
) -> EngineResult:
    workflow_revision = uuid4().hex[:12]
    plan = compile_plan(
        submission=submission,
        profile=profile,
        settings=settings,
        image_payloads=image_payloads,
        stream_callback=stream_callback,
    )
    steps = plan["steps"]
    display_steps = plan["display_steps"]
    planner_provider = plan["provider"]
    planner_model = plan["model"]
    planner_note = plan["note"]
    title_seed = submission.chief_complaint or "uploaded medical image"
    executive_summary = (
        f"@Planner 已完成检索，并生成 {len(steps)} 步执行计划。"
        if plan.get("visual_stage_used")
        else f"@Planner 已基于当前输入生成 {len(steps)} 步执行计划。"
    )
    return EngineResult(
        title=f"Planner 计划：{title_seed}",
        executive_summary=executive_summary,
        department=submission.department,
        output_style=submission.output_style,
        professional_answer=_markdown_plan(display_steps),
        coding_table=[],
        cost_table=[],
        references=plan["references"],
        next_steps=[
            "核查每一步是否符合当前诊断任务。",
            "确认后再交给下游执行器逐步执行。",
            "如果任务目标仍然模糊，请补充疾病目标或影像类型后重新规划。",
        ],
        safety_note="当前仅为执行计划，不构成诊断或治疗建议。",
        rounds=[
            {
                "round": 1,
                "alignment": 1.0,
                "summary": "先完成检索，再生成下游执行计划。",
            }
        ],
        agent_trace=[
            {
                "role": PLANNER_AGENT_NAME,
                "provider": planner_provider,
                "note": planner_note,
            }
        ],
        consensus_score=1.0,
        topology_used="Planner",
        show_process=submission.show_process,
        execution_mode="planner",
        serving_provider=planner_provider,
        serving_model=planner_model,
        activated_agent=PLANNER_AGENT_NAME,
        plan_steps=steps,
        plan_display_steps=display_steps,
        workflow_revision=workflow_revision,
        display_quality_warnings=list(plan.get("display_quality_warnings") or []),
    )
