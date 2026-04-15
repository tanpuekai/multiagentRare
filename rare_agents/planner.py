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

from rare_agents.display_composer import compose_plan_display
from rare_agents.models import AppProfile, CaseSubmission, EngineResult, SystemSettings


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
        if (
            provider.provider_name == planner_role.provider_name
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
        "name": "breast_ultrasound",
        "keywords": [
            "breast",
            "ultrasound",
            "bus",
            "b-us",
            "mammary",
            "bi-rads",
            "birads",
            "lesion",
            "mass",
            "hypoechoic",
            "posterior acoustic",
            "malignancy",
        ],
        "guidance": (
            "Use a lesion-first workflow for breast ultrasound. Start with lesion segmentation, compute size and shape "
            "measurements, then add separate qualitative final indicators for suspicious margins, echogenicity, "
            "posterior acoustic features, orientation, and other malignancy-associated visual evidence."
        ),
        "plan_family": "breast_ultrasound",
    },
    {
        "name": "glaucoma_fundus",
        "keywords": [
            "glaucoma",
            "fundus",
            "retina",
            "optic disc",
            "optic cup",
            "cup-to-disc",
            "vcdr",
            "rim",
            "peripapillary",
            "bayoneting",
        ],
        "guidance": (
            "Use a disc-and-cup workflow for fundus glaucoma screening. Extract optic disc and optic cup evidence, compute "
            "vertical cup-to-disc ratio, then add separate qualitative final indicators for rim thinning or notching, "
            "beta-zone peripapillary atrophy, optic disc hemorrhage, and vessel bayoneting."
        ),
        "plan_family": "glaucoma_fundus",
    },
    {
        "name": "generic_medical_image",
        "keywords": [
            "image",
            "medical",
            "xray",
            "x-ray",
            "ct",
            "mri",
            "ultrasound",
            "photo",
            "jpg",
            "jpeg",
            "png",
        ],
        "guidance": (
            "When the task is underspecified, first classify modality, anatomy, view, and image quality, then localize the "
            "dominant abnormal visual target and break the downstream plan into a small number of evidence-focused steps."
        ),
        "plan_family": "generic_medical_image",
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
                    visual_profile.get("planning_family", ""),
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
            profile_bonus = 8.0 if visual_profile and visual_profile.get("planning_family") == item["plan_family"] else 0.0
            overlap = len(query_tokens & _tokenize(" ".join([item["name"], item["guidance"], " ".join(item["keywords"])])))
            score = profile_bonus + (keyword_hits * 4.0) + overlap
            if score > 0:
                scored.append((score, item))
        if not scored:
            generic = next(profile for profile in self.corpus if profile["plan_family"] == "generic_medical_image")
            scored.append((1.0, generic))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [
            {
                "name": item["name"],
                "plan_family": item["plan_family"],
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
                f"- planning_family: {visual_profile.get('planning_family') or 'generic_medical_image'}",
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
        if action_type == "qualitative":
            normalized.setdefault("finding", finding or "target finding")
            if not isinstance(normalized.get("rv_config"), dict) or not normalized.get("rv_config"):
                normalized["rv_config"] = _rv_config(finding, image_step=normalized.get("tool_type") == "vlm")
        return normalized
    if action_type == "quantitative":
        if any(tool == 2 for tool in tools):
            seg_type = str(item.get("seg_type") or finding or "target_region")
            seg_type = re.sub(r"[^a-z0-9_]+", "_", seg_type.lower()).strip("_") or "target_region"
            return {"tool_type": "evidence_vlm", "seg_type": seg_type}
        return {"tool_type": "coding"}
    image_step = any(tool == 1 for tool in tools) and 0 in [int(value) for value in item.get("input_type", [0])]
    return {
        "tool_type": "vlm" if image_step else "text_vlm",
        "finding": finding or "target finding",
        "rv_config": _rv_config(finding, image_step=image_step),
    }


def _infer_finding_from_action(action: str) -> str:
    text = re.sub(r"\s+", " ", str(action or "")).strip()
    lowered = text.lower()
    if "echogenicity" in lowered or "echo" in lowered or "texture" in lowered:
        return "echogenicity and internal texture characterization" if "internal" in lowered or "texture" in lowered else "echogenicity"
    if "margin" in lowered or "spiculated" in lowered or "angular" in lowered:
        return "irregular or spiculated margins"
    if "posterior" in lowered or "shadow" in lowered:
        return "posterior acoustic features"
    if "orientation" in lowered or "skin plane" in lowered or "taller-than-wide" in lowered:
        return "lesion orientation"
    if "surrounding" in lowered or "perilesional" in lowered or "architectural" in lowered or "ductal" in lowered:
        return "surrounding tissue reaction"
    if "vascular" in lowered:
        return "vascularity"
    if "calcification" in lowered:
        return "calcification"
    text = re.sub(
        r"^(analyze|assess|inspect|examine|determine|identify|classify|evaluate|extract|localize|describe|interpret)\s+",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = text.strip(" .")
    if not text:
        return "target diagnostic finding"
    return text[:160]


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


def _planner_request(provider: Any, messages: list[dict[str, Any]], *, max_tokens: int) -> str:
    url = f"{_normalize_provider_endpoint(provider.endpoint).rstrip('/')}/chat/completions"
    body: dict[str, Any] = {
        "model": provider.model_name,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0,
    }
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
          "planning_family": "breast_ultrasound|glaucoma_fundus|generic_medical_image",
          "retrieval_tags": ["", ""],
          "salient_targets": ["", ""],
          "confidence": 0.0
        }}

        Rules:
        - Do NOT make a diagnosis.
        - planning_family must be breast_ultrasound for breast ultrasound lesion tasks, glaucoma_fundus for fundus glaucoma tasks, otherwise generic_medical_image.
        - retrieval_tags and salient_targets should be short, concrete phrases useful for planning.
        - confidence must be a number in [0, 1].
        """
    ).strip()


def _multimodal_user_content(prompt: str, image_payloads: list[dict[str, str]]) -> list[dict[str, Any]]:
    parts: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
    for item in image_payloads:
        parts.append({"type": "image_url", "image_url": {"url": item["data_url"]}})
    return parts


def _request_visual_profile(
    submission: CaseSubmission,
    settings: SystemSettings,
    image_payloads: list[dict[str, Any]] | None,
) -> tuple[dict[str, Any], str, str]:
    provider = _resolve_planner_provider(settings)
    payloads = _safe_image_payloads(image_payloads)
    if provider is None:
        raise ValueError("Planner provider is not configured.")
    if not payloads:
        raise ValueError("Planner visual retrieval requires uploaded image content.")
    raw = _planner_request(
        provider,
        [
            {
                "role": "system",
                "content": "You are a careful medical planning router. Return ONLY JSON.",
            },
            {
                "role": "user",
                "content": _multimodal_user_content(_visual_retrieval_prompt(submission), payloads),
            },
        ],
        max_tokens=1200,
    )
    parsed = _parse_llm_json(raw)
    if not isinstance(parsed, dict):
        raise ValueError("Planner visual retrieval did not return a JSON object.")
    profile = {
        "modality": str(parsed.get("modality", "")).strip(),
        "anatomy": str(parsed.get("anatomy", "")).strip(),
        "exam_type": str(parsed.get("exam_type", "")).strip(),
        "task_goal": str(parsed.get("task_goal", "")).strip(),
        "planning_family": str(parsed.get("planning_family", "generic_medical_image")).strip() or "generic_medical_image",
        "retrieval_tags": [str(item).strip() for item in parsed.get("retrieval_tags", []) if str(item).strip()],
        "salient_targets": [str(item).strip() for item in parsed.get("salient_targets", []) if str(item).strip()],
        "confidence": max(0.0, min(1.0, float(parsed.get("confidence", 0.0) or 0.0))),
    }
    valid_families = {item["plan_family"] for item in PLANNING_PROFILES}
    if profile["planning_family"] not in valid_families:
        raise ValueError(f"Planner visual retrieval returned unsupported planning_family: {profile['planning_family']}")
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
        - planning_family: {visual_profile.get('planning_family') or 'generic_medical_image'}
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
        - id starts from 1 and increases by 1.
        - tool is an array of integer tool ids from the available toolset.
        - action_type is "qualitative" or "quantitative".
        - input_type uses [0] for raw inputs, or prior step ids only for true causal dependencies.
        - output_type is "intermediate result" or "final indicator".
        - For non-image outputs use output_path "diagnosis.json"; only masks or images may use .png/.jpg paths.
        - Each qualitative final indicator must be a separate step with a concise abnormal finding.
        - Keep the plan compact: usually 4-7 steps.
        - If the retrieved family is breast_ultrasound, prefer lesion segmentation -> quantitative lesion metrics -> image-based malignancy indicators.
        - If the retrieved family is glaucoma_fundus, prefer disc/cup evidence -> cup-disc metric -> fundus image indicators.
        - Do NOT include report generation, decider fusion, HITL text, or human-facing SOP wording.
        - For qualitative VLM steps, include tool_config with tool_type "vlm" and an rv_config.
        - For qualitative text interpretation steps, use tool_config.tool_type = "text_vlm".
        - For quantitative evidence extraction, use tool_config.tool_type = "evidence_vlm" and include a seg_type.
        - For deterministic computation, use tool_config.tool_type = "coding".
        - When a grounded region depends on a previously localized parent region, also include relative_to_step, relationship, and parent_label.
        - Use relationship values such as same_target, inside_parent, deep_to_parent, adjacent_to_parent, or overlaps_parent only when they are visually meaningful.
        - For breast ultrasound, margin, echogenicity, texture, shape, and orientation indicators should usually use relationship "same_target" relative to the lesion segmentation step.
        - For breast ultrasound posterior acoustic indicators, use relationship "deep_to_parent" relative to the lesion segmentation step.
        - When useful, add spatial_priors and sanity_checks as short arrays to help the downstream grounding harness validate the result.
        - Quantitative evidence extraction should prefer evidence_mode "boundary_points" unless the target is a sparse landmark.
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
        cleaned.append(record)
        known_ids.add(step_id)
    return cleaned


def _append_unique(items: list[Any] | None, additions: list[str]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for item in [*(items or []), *additions]:
        text = str(item or "").strip()
        key = text.lower()
        if text and key not in seen:
            output.append(text)
            seen.add(key)
    return output


def _append_unique_ints(items: list[Any] | None, additions: list[int]) -> list[int]:
    output: list[int] = []
    seen: set[int] = set()
    for item in [*(items or []), *additions]:
        value = int(item)
        if value not in seen:
            output.append(value)
            seen.add(value)
    return output


def _step_text(step: dict[str, Any]) -> str:
    return f"{step.get('finding') or ''} {step.get('action') or ''}".lower()


def _apply_grounding_harness_defaults(
    steps: list[dict[str, Any]],
    visual_profile: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    family = str((visual_profile or {}).get("planning_family") or "").strip().lower()
    if family != "breast_ultrasound":
        return steps
    lesion_step = next(
        (
            step
            for step in steps
            if (step.get("tool_config") or {}).get("tool_type") == "evidence_vlm"
            and any(term in f"{step.get('action') or ''} {(step.get('tool_config') or {}).get('seg_type') or ''}".lower() for term in ["lesion", "mass", "target"])
        ),
        None,
    )
    if lesion_step is None:
        return steps
    lesion_id = int(lesion_step["id"])
    lesion_tool_config = lesion_step.get("tool_config") if isinstance(lesion_step.get("tool_config"), dict) else {}
    lesion_tool_config["evidence_mode"] = "boundary_points"
    lesion_tool_config["spatial_priors"] = _append_unique(
        lesion_tool_config.get("spatial_priors") or lesion_step.get("spatial_priors"),
        [
            "single dominant lesion",
            "within breast parenchyma",
            "dark hypoechoic or anechoic target when visually present",
            "not annotation text",
        ],
    )
    lesion_tool_config["sanity_checks"] = _append_unique(
        lesion_tool_config.get("sanity_checks") or lesion_step.get("sanity_checks"),
        [
            "single_connected_component",
            "compact_shape",
            "dark_target_contrast",
            "not_text_annotation",
        ],
    )
    lesion_step["tool_config"] = lesion_tool_config
    lesion_step["evidence_mode"] = "boundary_points"
    lesion_step["spatial_priors"] = lesion_tool_config["spatial_priors"]
    lesion_step["sanity_checks"] = lesion_tool_config["sanity_checks"]

    for step in steps:
        if int(step["id"]) == lesion_id:
            continue
        tool_config = step.get("tool_config") if isinstance(step.get("tool_config"), dict) else {}
        if tool_config.get("tool_type") != "vlm":
            continue
        text = _step_text(step)
        if any(term in text for term in ["margin", "echogenicity", "echo", "orientation", "shape", "texture"]):
            step["relative_to_step"] = lesion_id
            step["relationship"] = "same_target"
            step["parent_label"] = "breast lesion"
            step["input_type"] = _append_unique_ints(step.get("input_type"), [lesion_id])
            tool_config["relative_to_step"] = lesion_id
            tool_config["relationship"] = "same_target"
            tool_config["parent_label"] = "breast lesion"
        elif any(term in text for term in ["posterior", "acoustic", "enhancement", "shadow"]):
            step["relative_to_step"] = lesion_id
            step["relationship"] = "deep_to_parent"
            step["parent_label"] = "breast lesion"
            step["input_type"] = _append_unique_ints(step.get("input_type"), [lesion_id])
            step["spatial_priors"] = _append_unique(
                step.get("spatial_priors"),
                ["deep to the breast lesion", "horizontally aligned with lesion"],
            )
            step["sanity_checks"] = _append_unique(
                step.get("sanity_checks"),
                ["deep_to_parent", "horizontal_overlap_parent", "not_text_annotation"],
            )
            tool_config["relative_to_step"] = lesion_id
            tool_config["relationship"] = "deep_to_parent"
            tool_config["parent_label"] = "breast lesion"
        step["tool_config"] = tool_config
    return steps


def _request_llm_plan(
    submission: CaseSubmission,
    profile: AppProfile,
    settings: SystemSettings,
    rag_text: str,
    visual_profile: dict[str, Any] | None,
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
    )
    steps = _validate_steps(_parse_llm_json(content))
    steps = _apply_grounding_harness_defaults(steps, visual_profile)
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
) -> dict[str, Any]:
    payloads = _safe_image_payloads(image_payloads)
    visual_profile = None
    visual_stage_used = False
    planner_provider = ""
    planner_model = ""

    if submission.uploaded_images:
        if not payloads:
            raise ValueError("Planner needs the uploaded image content to perform retrieval.")
        try:
            visual_profile, planner_provider, planner_model = _request_visual_profile(submission, settings, payloads)
        except (ValueError, OSError, urllib_error.URLError, urllib_error.HTTPError, json.JSONDecodeError) as exc:
            raise ValueError(f"Planner visual retrieval failed: {exc}") from exc
        if visual_profile is None:
            raise ValueError("Planner visual retrieval did not return a task profile.")
        visual_stage_used = True

    rag_text, rag_hits = _retrieve_planning_context(submission, visual_profile)
    try:
        steps, plan_provider, plan_model, plan_provider_config = _request_llm_plan(submission, profile, settings, rag_text, visual_profile)
    except (ValueError, OSError, urllib_error.URLError, urllib_error.HTTPError, json.JSONDecodeError) as exc:
        raise ValueError(f"Planner plan generation failed: {exc}") from exc
    try:
        display_steps = compose_plan_display(
            provider=plan_provider_config,
            submission=submission,
            plan_steps=steps,
            visual_profile=visual_profile,
            rag_text=rag_text,
        )
    except (ValueError, OSError, urllib_error.URLError, urllib_error.HTTPError, json.JSONDecodeError) as exc:
        raise ValueError(f"Planner display composition failed: {exc}") from exc

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
    }


def run_planner_case(
    submission: CaseSubmission,
    profile: AppProfile,
    settings: SystemSettings,
    *,
    image_payloads: list[dict[str, Any]] | None = None,
) -> EngineResult:
    plan = compile_plan(
        submission=submission,
        profile=profile,
        settings=settings,
        image_payloads=image_payloads,
    )
    steps = plan["steps"]
    display_steps = plan["display_steps"]
    planner_provider = plan["provider"]
    planner_model = plan["model"]
    planner_note = plan["note"]
    title_seed = submission.chief_complaint or "uploaded medical image"
    executive_summary = (
        f"@Planner 已完成检索，并生成 {len(steps)} 步执行计划。"
        if submission.uploaded_images
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
    )
