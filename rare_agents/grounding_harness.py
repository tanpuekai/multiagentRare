from __future__ import annotations

import base64
import io
import math
from dataclasses import dataclass
from textwrap import dedent
from typing import Any, Callable

import cv2
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageOps


JsonImageRequester = Callable[[str, str, int, str], dict[str, Any]]


@dataclass
class HarnessImage:
    image: Image.Image
    data_url: str
    media_type: str
    width: int
    height: int


@dataclass
class CropContext:
    data_url: str
    crop_box_px: list[int]
    crop_box_norm: list[float]
    width: int
    height: int
    parent_overlay: bool = False
    label: str = ""


def clamp01(value: object) -> float:
    return max(0.0, min(1.0, float(value)))


def normalize_point(value: object) -> list[float]:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError("Grounding point must have length 2.")
    return [round(clamp01(value[0]), 6), round(clamp01(value[1]), 6)]


def normalize_bbox(value: object) -> list[float]:
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        raise ValueError("Grounding bbox must have length 4.")
    x1, y1, x2, y2 = [clamp01(item) for item in value]
    left, right = sorted([x1, x2])
    top, bottom = sorted([y1, y2])
    if right <= left or bottom <= top:
        raise ValueError("Grounding bbox has zero area.")
    return [round(left, 6), round(top, 6), round(right, 6), round(bottom, 6)]


def normalize_boundary_points(value: object) -> list[list[float]]:
    if not isinstance(value, list) or len(value) < 3:
        raise ValueError("Grounding boundary must contain at least 3 points.")
    return [normalize_point(item) for item in value[:48]]


def bbox_from_points(points: list[list[float]]) -> list[float]:
    if len(points) < 3:
        raise ValueError("Cannot compute bbox from fewer than 3 points.")
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return [round(min(xs), 6), round(min(ys), 6), round(max(xs), 6), round(max(ys), 6)]


def polygon_area(points: list[list[float]]) -> float:
    total = 0.0
    for index, point in enumerate(points):
        next_point = points[(index + 1) % len(points)]
        total += point[0] * next_point[1] - next_point[0] * point[1]
    return abs(total) * 0.5


def polygon_perimeter(points: list[list[float]]) -> float:
    total = 0.0
    for index, point in enumerate(points):
        next_point = points[(index + 1) % len(points)]
        total += math.dist(point, next_point)
    return total


def parent_grounding(parent_output: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(parent_output, dict):
        return {}
    evidence = parent_output.get("evidence")
    if not isinstance(evidence, dict):
        return {}
    grounding = evidence.get("grounding")
    return grounding if isinstance(grounding, dict) else {}


def inside_bbox(point: list[float], bbox: list[float]) -> bool:
    return bbox[0] <= point[0] <= bbox[2] and bbox[1] <= point[1] <= bbox[3]


def area_ratio(bbox: list[float]) -> float:
    return max(0.0, (bbox[2] - bbox[0]) * (bbox[3] - bbox[1]))


def _decode_data_url(data_url: str) -> tuple[str, bytes]:
    if not data_url.startswith("data:image/") or "," not in data_url:
        raise ValueError("Grounding harness requires a data:image data URL.")
    header, payload = data_url.split(",", 1)
    media_type = header[5:].split(";", 1)[0] or "image/png"
    return media_type, base64.b64decode(payload)


def prepare_harness_image(image_payload: dict[str, str]) -> HarnessImage:
    media_type, raw = _decode_data_url(str(image_payload.get("data_url", "")).strip())
    image = Image.open(io.BytesIO(raw))
    image = ImageOps.exif_transpose(image).convert("RGB")
    data_url = _image_to_data_url(image)
    return HarnessImage(
        image=image,
        data_url=data_url,
        media_type=media_type,
        width=image.width,
        height=image.height,
    )


def _image_to_data_url(image: Image.Image) -> str:
    buffer = io.BytesIO()
    image.convert("RGB").save(buffer, format="JPEG", quality=88, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


def _draw_grid(image: Image.Image, *, label: str) -> Image.Image:
    canvas = image.convert("RGB").copy()
    draw = ImageDraw.Draw(canvas)
    w, h = canvas.size
    frame_color = (242, 185, 36)
    tick_color = (245, 224, 151)
    label_bg = (255, 255, 255)
    draw.rectangle([0, 0, max(0, w - 1), max(0, h - 1)], outline=frame_color, width=2)
    for idx in range(0, 9):
        x = round(w * idx / 8)
        y = round(h * idx / 8)
        text = f"{idx}/8"
        tick = 10 if idx in {0, 4, 8} else 6
        draw.line([(x, 0), (x, tick)], fill=tick_color, width=2)
        draw.line([(x, max(0, h - tick)), (x, max(0, h - 1))], fill=tick_color, width=2)
        draw.line([(0, y), (tick, y)], fill=tick_color, width=2)
        draw.line([(max(0, w - tick), y), (max(0, w - 1), y)], fill=tick_color, width=2)
        draw.rectangle([min(max(0, x + 2), max(0, w - 32)), 0, min(max(22, x + 30), w), 14], fill=label_bg)
        draw.text((min(max(2, x + 3), max(2, w - 30)), 1), text, fill=(30, 30, 30))
        draw.rectangle([0, min(max(0, y + 2), max(0, h - 16)), 22, min(max(14, y + 16), h)], fill=label_bg)
        draw.text((2, min(max(2, y + 3), max(2, h - 14))), text, fill=(30, 30, 30))
    if label:
        draw.rectangle([0, max(0, h - 22), min(w, 12 + len(label) * 7), h], fill=label_bg)
        draw.text((6, max(0, h - 18)), label[:80], fill=(0, 0, 0))
    return canvas


def _points_to_px(points: list[list[float]], width: int, height: int) -> list[tuple[int, int]]:
    return [
        (
            int(round(clamp01(point[0]) * max(1, width - 1))),
            int(round(clamp01(point[1]) * max(1, height - 1))),
        )
        for point in points
    ]


def _bbox_to_px(bbox: list[float], width: int, height: int) -> list[int]:
    return [
        int(round(bbox[0] * max(1, width - 1))),
        int(round(bbox[1] * max(1, height - 1))),
        int(round(bbox[2] * max(1, width - 1))),
        int(round(bbox[3] * max(1, height - 1))),
    ]


def _bbox_from_px(box: list[int], width: int, height: int) -> list[float]:
    return [
        round(box[0] / max(1, width - 1), 6),
        round(box[1] / max(1, height - 1), 6),
        round(box[2] / max(1, width - 1), 6),
        round(box[3] / max(1, height - 1), 6),
    ]


def _sort_polygon_points(points: list[list[float]]) -> list[list[float]]:
    if len(points) < 3:
        return points
    cx = sum(point[0] for point in points) / len(points)
    cy = sum(point[1] for point in points) / len(points)
    ranked = sorted(points, key=lambda point: math.atan2(point[1] - cy, point[0] - cx))
    return [[round(point[0], 6), round(point[1], 6)] for point in ranked]


def _point_inside_polygon(point: list[float], polygon: list[list[float]]) -> bool:
    x, y = point
    inside = False
    j = len(polygon) - 1
    for i in range(len(polygon)):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        intersects = (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / max(1e-9, yj - yi) + xi
        if intersects:
            inside = not inside
        j = i
    return inside


def _polygon_centroid(points: list[list[float]]) -> list[float]:
    if not points:
        raise ValueError("Cannot compute centroid from empty polygon.")
    signed_area = 0.0
    cx = 0.0
    cy = 0.0
    for index, point in enumerate(points):
        next_point = points[(index + 1) % len(points)]
        cross = point[0] * next_point[1] - next_point[0] * point[1]
        signed_area += cross
        cx += (point[0] + next_point[0]) * cross
        cy += (point[1] + next_point[1]) * cross
    signed_area *= 0.5
    if abs(signed_area) < 1e-9:
        return [
            round(sum(point[0] for point in points) / len(points), 6),
            round(sum(point[1] for point in points) / len(points), 6),
        ]
    return [
        round(clamp01(cx / (6.0 * signed_area)), 6),
        round(clamp01(cy / (6.0 * signed_area)), 6),
    ]


def _rasterize_mask(width: int, height: int, points: list[list[float]]) -> Image.Image:
    if len(points) < 3:
        raise ValueError("Cannot rasterize a mask without at least 3 points.")
    mask = Image.new("L", (width, height), 0)
    ImageDraw.Draw(mask).polygon(_points_to_px(points, width, height), fill=255)
    return mask


def _mask_area(mask: Image.Image) -> int:
    return int(mask.histogram()[255])


def _mask_iou(first: Image.Image, second: Image.Image) -> float:
    first_bin = first.convert("1")
    second_bin = second.convert("1")
    intersection = ImageChops.logical_and(first_bin, second_bin).convert("L").histogram()[255]
    union = ImageChops.logical_or(first_bin, second_bin).convert("L").histogram()[255]
    return float(intersection / max(1, union))


def _mask_array_from_points(width: int, height: int, points: list[list[float]]) -> np.ndarray:
    if len(points) < 3:
        raise ValueError("Cannot rasterize a mask without at least 3 points.")
    mask = np.zeros((height, width), dtype=np.uint8)
    polygon = np.array(_points_to_px(points, width, height), dtype=np.int32)
    cv2.fillPoly(mask, [polygon], 255)
    return mask


def _mask_image_from_array(mask: np.ndarray) -> Image.Image:
    return Image.fromarray(mask.astype(np.uint8), mode="L")


def _mask_iou_array(first: np.ndarray, second: np.ndarray) -> float:
    intersection = int(np.count_nonzero((first > 0) & (second > 0)))
    union = int(np.count_nonzero((first > 0) | (second > 0)))
    return float(intersection / max(1, union))


def _mask_bbox_px(mask: np.ndarray) -> list[int]:
    ys, xs = np.where(mask > 0)
    if xs.size == 0 or ys.size == 0:
        return []
    return [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]


def _mask_bbox(mask: np.ndarray) -> list[float]:
    box = _mask_bbox_px(mask)
    if not box:
        return []
    height, width = mask.shape[:2]
    return _bbox_from_px(box, width, height)


def _mask_centroid(mask: np.ndarray) -> list[float]:
    moments = cv2.moments((mask > 0).astype(np.uint8))
    if moments["m00"] == 0:
        raise ValueError("Cannot compute centroid from an empty mask.")
    height, width = mask.shape[:2]
    cx = float(moments["m10"] / moments["m00"])
    cy = float(moments["m01"] / moments["m00"])
    return [
        round(clamp01(cx / max(1.0, width - 1.0)), 6),
        round(clamp01(cy / max(1.0, height - 1.0)), 6),
    ]


def _point_inside_mask(point: list[float], mask: np.ndarray) -> bool:
    height, width = mask.shape[:2]
    px = int(round(clamp01(point[0]) * max(1, width - 1)))
    py = int(round(clamp01(point[1]) * max(1, height - 1)))
    px = max(0, min(width - 1, px))
    py = max(0, min(height - 1, py))
    return bool(mask[py, px] > 0)


def _keep_largest_component(mask: np.ndarray) -> tuple[np.ndarray, bool]:
    binary = (mask > 0).astype(np.uint8)
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
    if num_labels <= 2:
        return mask, False
    largest_label = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    cleaned = np.zeros_like(mask)
    cleaned[labels == largest_label] = 255
    return cleaned, True


def _centroid_inside_parent(mask: np.ndarray, parent_mask: np.ndarray) -> bool:
    moments = cv2.moments((mask > 0).astype(np.uint8))
    if moments["m00"] == 0:
        return False
    cx = int(round(moments["m10"] / moments["m00"]))
    cy = int(round(moments["m01"] / moments["m00"]))
    height, width = parent_mask.shape[:2]
    cx = max(0, min(width - 1, cx))
    cy = max(0, min(height - 1, cy))
    return bool(parent_mask[cy, cx] > 0)


def _boundary_points_from_mask(mask: np.ndarray, *, max_points: int = 16) -> list[list[float]]:
    contours, _ = cv2.findContours((mask > 0).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not contours:
        return []
    contour = max(contours, key=cv2.contourArea).reshape(-1, 2)
    if contour.shape[0] < 3:
        return []
    count = max(8, min(max_points, contour.shape[0]))
    sample_indices = np.linspace(0, contour.shape[0] - 1, count, dtype=int)
    sampled = contour[sample_indices]
    height, width = mask.shape[:2]
    points = [
        [
            round(clamp01(float(x) / max(1.0, width - 1.0)), 6),
            round(clamp01(float(y) / max(1.0, height - 1.0)), 6),
        ]
        for x, y in sampled
    ]
    return _sort_polygon_points(points)


def _parent_mask_from_grounding(
    parent_output: dict[str, Any] | None,
    *,
    width: int,
    height: int,
) -> np.ndarray | None:
    parent = parent_grounding(parent_output)
    points = parent.get("boundary_points")
    if isinstance(points, list) and len(points) >= 3:
        return _mask_array_from_points(width, height, normalize_boundary_points(points))
    bbox = parent.get("bbox")
    if isinstance(bbox, list) and len(bbox) == 4:
        x1, y1, x2, y2 = _bbox_to_px(normalize_bbox(bbox), width, height)
        mask = np.zeros((height, width), dtype=np.uint8)
        cv2.rectangle(mask, (x1, y1), (x2, y2), 255, thickness=-1)
        return mask
    return None


def _mask_compactness(mask: np.ndarray) -> float:
    contours, _ = cv2.findContours((mask > 0).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return 0.0
    contour = max(contours, key=cv2.contourArea)
    area = float(cv2.contourArea(contour))
    perimeter = float(cv2.arcLength(contour, True))
    if perimeter <= 0.0:
        return 0.0
    return float(4.0 * math.pi * area / max(perimeter * perimeter, 1e-9))


def _is_primary_dark_lesion_step(step: dict[str, Any], target_label: str, parent_mask: np.ndarray | None) -> bool:
    if parent_mask is not None:
        return False
    text = _joined_step_text(step, target_label)
    return (
        _contrast_expectation(step, target_label) == "dark"
        and "lesion" in text
        and any(term in text for term in ["single dominant lesion", "dominant", "mass", "target"])
    )


def _dedupe_proposals(candidates: list[dict[str, Any]], *, max_candidates: int = 5) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for candidate in sorted(candidates, key=lambda item: float(item.get("score", 0.0)), reverse=True):
        current_mask = candidate["mask_array"]
        if any(_mask_iou_array(current_mask, existing["mask_array"]) > 0.6 for existing in selected):
            continue
        selected.append(candidate)
        if len(selected) >= max_candidates:
            break
    for index, item in enumerate(selected, start=1):
        item["proposal_id"] = index
    return selected


def _generate_dark_component_proposals(
    context: HarnessImage,
    *,
    step: dict[str, Any],
    target_label: str,
    max_candidates: int = 5,
) -> list[dict[str, Any]]:
    gray = np.asarray(ImageOps.grayscale(context.image), dtype=np.uint8)
    blurred = cv2.medianBlur(gray, 5)
    image_area = float(gray.size)
    usable_height = max(1, int(round(gray.shape[0] * 0.82)))
    search_region = blurred[:usable_height, :]
    threshold_values = sorted({int(np.percentile(search_region, percentile)) for percentile in (5, 7, 9, 11, 13, 15, 18, 21, 24)})
    kernel_open = np.ones((3, 3), dtype=np.uint8)
    kernel_close = np.ones((5, 5), dtype=np.uint8)
    candidate_pool: list[dict[str, Any]] = []

    for threshold in threshold_values:
        _, binary = cv2.threshold(blurred, threshold, 255, cv2.THRESH_BINARY_INV)
        binary[usable_height:, :] = 0
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel_open)
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel_close)
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats((binary > 0).astype(np.uint8), connectivity=8)
        for label_id in range(1, num_labels):
            x = int(stats[label_id, cv2.CC_STAT_LEFT])
            y = int(stats[label_id, cv2.CC_STAT_TOP])
            w = int(stats[label_id, cv2.CC_STAT_WIDTH])
            h = int(stats[label_id, cv2.CC_STAT_HEIGHT])
            area_px = int(stats[label_id, cv2.CC_STAT_AREA])
            area_ratio_image = area_px / max(1.0, image_area)
            if area_ratio_image < 0.0008 or area_ratio_image > 0.18:
                continue
            aspect_ratio = max(w, h) / max(1.0, min(w, h))
            if aspect_ratio > 4.0:
                continue
            component_mask = np.zeros_like(binary)
            component_mask[labels == label_id] = 255
            compactness = _mask_compactness(component_mask)
            bbox = _mask_bbox(component_mask)
            if not bbox or bbox[1] > 0.78:
                continue
            contrast = _contrast_stats(context.image, component_mask, bbox)
            edge_alignment = _edge_alignment_stats(context.image, component_mask)
            if not contrast.get("available"):
                continue
            target_minus_surrounding = float(contrast["target_minus_surrounding"])
            if target_minus_surrounding > -8.0:
                continue
            border_penalty = 0.0
            if x <= 2 or y <= 2 or x + w >= context.width - 2:
                border_penalty = 0.12
            edge_bonus = 0.0
            if edge_alignment.get("available"):
                edge_bonus = min(0.2, max(0.0, (float(edge_alignment["boundary_vs_image"]) - 1.0) / 5.0))
            score = (
                min(0.5, max(0.0, -target_minus_surrounding / 140.0))
                + min(0.22, area_ratio_image / 0.08)
                + min(0.18, compactness / 2.5)
                + edge_bonus
                - border_penalty
            )
            candidate_pool.append(
                {
                    "bbox": bbox,
                    "mask_array": component_mask,
                    "area_ratio_image": round(area_ratio_image, 6),
                    "compactness": round(compactness, 6),
                    "contrast": contrast,
                    "edge_alignment": edge_alignment,
                    "score": round(score, 6),
                    "source_threshold": threshold,
                }
            )

    return _dedupe_proposals(candidate_pool, max_candidates=max_candidates)


def _render_proposal_overlay(context: HarnessImage, proposals: list[dict[str, Any]], *, label: str) -> str:
    canvas = context.image.convert("RGB").copy()
    draw = ImageDraw.Draw(canvas)
    colors = [
        (229, 57, 53),
        (30, 136, 229),
        (67, 160, 71),
        (251, 140, 0),
        (123, 31, 162),
    ]
    for index, proposal in enumerate(proposals):
        bbox = proposal["bbox"]
        color = colors[index % len(colors)]
        x1, y1, x2, y2 = _bbox_to_px(bbox, context.width, context.height)
        draw.rectangle([x1, y1, x2, y2], outline=color, width=3)
        tag = str(proposal["proposal_id"])
        draw.rectangle([x1, max(0, y1 - 20), x1 + 18, y1], fill=(255, 255, 255))
        draw.text((x1 + 4, max(0, y1 - 17)), tag, fill=color)
    canvas = _draw_grid(canvas, label=label)
    return _image_to_data_url(canvas)


def _request_proposal_selection(
    *,
    request_json: JsonImageRequester,
    context: HarnessImage,
    proposals: list[dict[str, Any]],
    step: dict[str, Any],
    target_label: str,
) -> dict[str, Any]:
    proposal_image_url = _render_proposal_overlay(context, proposals, label="candidate proposals")
    proposal_lines = "\n".join(
        f"- Proposal {item['proposal_id']}: bbox={item['bbox']}, area_ratio_image={item['area_ratio_image']}, compactness={item['compactness']}, contrast={item['contrast'].get('target_minus_surrounding')}"
        for item in proposals
    )
    prompt = dedent(
        f"""
        Select the single proposal that best matches the requested target.

        Target: {target_label}
        Step action: {step.get('action') or ''}

        Candidate proposals:
        {proposal_lines}

        Return ONLY JSON:
        {{
          "selected_id": 1,
          "confidence": 0.0,
          "rationale": "short visual justification"
        }}

        Rules:
        - Choose exactly one proposal id from the visible overlay.
        - Prefer the single dominant requested lesion rather than a smaller satellite, duct, vessel, artifact, or annotation.
        - Use the image appearance first; the proposal stats are only supporting context.
        - Do not diagnose.
        """
    ).strip()
    parsed = request_json(
        proposal_image_url,
        prompt,
        900,
        "You choose the best medical image proposal for downstream boundary refinement. Return only strict JSON.",
    )
    selected_id = int(parsed.get("selected_id"))
    selected = next((item for item in proposals if int(item["proposal_id"]) == selected_id), None)
    if selected is None:
        raise ValueError(f"Proposal selector returned invalid proposal id: {selected_id}")
    return {
        "selected_id": selected_id,
        "confidence": clamp01(parsed.get("confidence", 0.0)),
        "rationale": str(parsed.get("rationale", "")).strip(),
        "proposal": selected,
        "proposals": proposals,
    }


def _string_list(value: Any) -> list[str]:
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _harness_config(step: dict[str, Any]) -> dict[str, Any]:
    tool_config = step.get("tool_config") if isinstance(step.get("tool_config"), dict) else {}
    keys = [
        "evidence_mode",
        "relative_to_step",
        "relationship",
        "parent_label",
        "spatial_priors",
        "sanity_checks",
    ]
    return {key: tool_config.get(key, step.get(key)) for key in keys if tool_config.get(key, step.get(key)) not in (None, "", [], {})}


def _joined_step_text(step: dict[str, Any], target_label: str) -> str:
    config = _harness_config(step)
    return " ".join(
        str(item or "")
        for item in [
            target_label,
            step.get("action"),
            step.get("finding"),
            " ".join(_string_list(config.get("spatial_priors"))),
            " ".join(_string_list(config.get("sanity_checks"))),
        ]
    ).lower()


def _contrast_expectation(step: dict[str, Any], target_label: str) -> str | None:
    text = _joined_step_text(step, target_label)
    if any(term in text for term in ["enhancement brighter than surrounding", "brighter than surrounding", "posterior acoustic enhancement", "enhancement present"]):
        return "bright"
    if "dark_target_contrast" in text or any(term in text for term in ["hypoechoic", "anechoic", "dark lesion", "dark target"]):
        return "dark"
    if any(term in text for term in ["posterior shadow", "acoustic shadow", "shadow deep to"]):
        return "dark"
    return None


def _needs_dark_target_validation(step: dict[str, Any], target_label: str) -> bool:
    return _contrast_expectation(step, target_label) == "dark"


def _needs_bright_target_validation(step: dict[str, Any], target_label: str) -> bool:
    return _contrast_expectation(step, target_label) == "bright"


def _needs_not_text_validation(step: dict[str, Any], target_label: str) -> bool:
    text = _joined_step_text(step, target_label)
    return "not_text_annotation" in text or any(term in text for term in ["lesion", "mass", "optic", "disc", "cup"])


def _prefers_single_dominant_target(step: dict[str, Any], target_label: str) -> bool:
    text = _joined_step_text(step, target_label)
    return "single dominant lesion" in text or ("dominant" in text and any(term in text for term in ["lesion", "mass", "target"]))


def _expanded_rect_around_bbox(bbox: list[float], width: int, height: int, *, scale: float) -> list[int]:
    x1, y1, x2, y2 = _bbox_to_px(bbox, width, height)
    bw = max(2, x2 - x1)
    bh = max(2, y2 - y1)
    cx = (x1 + x2) / 2
    cy = (y1 + y2) / 2
    half_w = bw * scale / 2
    half_h = bh * scale / 2
    return [
        max(0, int(round(cx - half_w))),
        max(0, int(round(cy - half_h))),
        min(width - 1, int(round(cx + half_w))),
        min(height - 1, int(round(cy + half_h))),
    ]


def _contrast_stats(image: Image.Image, mask: np.ndarray, bbox: list[float]) -> dict[str, Any]:
    gray = np.asarray(ImageOps.grayscale(image), dtype=np.uint8)
    height, width = gray.shape[:2]
    region_box = _expanded_rect_around_bbox(bbox, width, height, scale=3.2)
    region_mask = np.zeros((height, width), dtype=np.uint8)
    cv2.rectangle(region_mask, (region_box[0], region_box[1]), (region_box[2], region_box[3]), 255, thickness=-1)
    annulus = cv2.subtract(region_mask, mask)
    target_area = int(np.count_nonzero(mask))
    annulus_area = int(np.count_nonzero(annulus))
    if target_area == 0 or annulus_area == 0:
        return {"available": False}
    target_mean = float(gray[mask > 0].mean())
    annulus_mean = float(gray[annulus > 0].mean())
    return {
        "available": True,
        "target_mean_gray": round(target_mean, 3),
        "surrounding_mean_gray": round(annulus_mean, 3),
        "target_minus_surrounding": round(target_mean - annulus_mean, 3),
    }


def _edge_alignment_stats(image: Image.Image, mask: np.ndarray) -> dict[str, Any]:
    gray = np.asarray(ImageOps.grayscale(image), dtype=np.uint8)
    grad_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    grad_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    magnitude = cv2.magnitude(grad_x, grad_y)
    border = cv2.morphologyEx((mask > 0).astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((3, 3), dtype=np.uint8))
    border_values = magnitude[border > 0]
    if border_values.size == 0:
        return {"available": False}
    image_mean = float(magnitude.mean())
    boundary_mean = float(border_values.mean())
    return {
        "available": True,
        "boundary_grad_mean": round(boundary_mean, 3),
        "image_grad_mean": round(image_mean, 3),
        "boundary_vs_image": round(boundary_mean / max(image_mean, 1e-6), 3),
    }


def _normalize_relation_name(value: object) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def _relation_focus_crop_box(
    *,
    context: HarnessImage,
    focus_bbox: list[float],
    parent_bbox: list[float] | None,
    relationship: str,
    scale: float,
) -> list[int]:
    width, height = context.width, context.height
    if parent_bbox is None:
        return _expanded_rect_around_bbox(focus_bbox, width, height, scale=scale)
    px1, py1, px2, py2 = _bbox_to_px(parent_bbox, width, height)
    pw = max(8, px2 - px1)
    ph = max(8, py2 - py1)
    relation = _normalize_relation_name(relationship)
    if relation in {"inside_parent", "within_parent", "part_of_parent"}:
        pad = max(int(round(max(pw, ph) * 0.3)), 20)
        return [
            max(0, px1 - pad),
            max(0, py1 - pad),
            min(width - 1, px2 + pad),
            min(height - 1, py2 + pad),
        ]
    if relation in {"deep_to_parent", "posterior_to_parent"}:
        lateral_pad = max(int(round(pw * 0.45)), 24)
        top_pad = max(int(round(ph * 0.35)), 18)
        bottom_pad = max(int(round(ph * 1.4)), 48)
        return [
            max(0, px1 - lateral_pad),
            max(0, py1 - top_pad),
            min(width - 1, px2 + lateral_pad),
            min(height - 1, py2 + bottom_pad),
        ]
    if relation in {"adjacent_to_parent", "overlaps_parent"}:
        pad = max(int(round(max(pw, ph) * 0.6)), 28)
        return [
            max(0, px1 - pad),
            max(0, py1 - pad),
            min(width - 1, px2 + pad),
            min(height - 1, py2 + pad),
        ]
    return _expanded_rect_around_bbox(focus_bbox, width, height, scale=scale)


def _overlay_parent_contour(crop: Image.Image, crop_box: list[int], parent_mask: np.ndarray | None) -> tuple[Image.Image, bool]:
    if parent_mask is None:
        return crop, False
    x1, y1, x2, y2 = crop_box
    parent_crop = parent_mask[y1 : y2 + 1, x1 : x2 + 1]
    if parent_crop.size == 0 or int(np.count_nonzero(parent_crop)) == 0:
        return crop, False
    crop_bgr = cv2.cvtColor(np.asarray(crop.convert("RGB")), cv2.COLOR_RGB2BGR)
    overlay = crop_bgr.copy()
    contours, _ = cv2.findContours((parent_crop > 0).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return crop, False
    cv2.drawContours(overlay, contours, -1, (0, 255, 0), 2)
    blended = cv2.addWeighted(overlay, 0.4, crop_bgr, 0.6, 0)
    return Image.fromarray(cv2.cvtColor(blended, cv2.COLOR_BGR2RGB)), True


def _validate_candidate(
    *,
    context: HarnessImage,
    candidate: dict[str, Any],
    step: dict[str, Any],
    target_label: str,
    parent_bbox: list[float] | None,
    parent_mask: np.ndarray | None,
) -> dict[str, Any]:
    points = candidate["boundary_points"]
    mask_array = _mask_array_from_points(context.width, context.height, points)
    config = _harness_config(step)
    relationship = _normalize_relation_name(config.get("relationship"))
    failed: list[str] = []
    warnings: list[str] = []
    adjustments: list[str] = []
    inside_fraction: float | None = None
    area_ratio_to_parent: float | None = None

    if "single_connected_component" in _string_list(config.get("sanity_checks")):
        mask_array, removed = _keep_largest_component(mask_array)
        if removed:
            adjustments.append("kept_largest_component")

    area_px = int(np.count_nonzero(mask_array))
    area_ratio_image = area_px / max(1, context.width * context.height)
    if len(points) < 8:
        failed.append("insufficient_boundary_points")
    if area_ratio_image < 0.00002:
        failed.append("mask_too_small")
    if area_ratio_image > 0.45:
        failed.append("mask_too_large")

    if parent_mask is not None and parent_mask.shape == mask_array.shape:
        parent_area = int(np.count_nonzero(parent_mask))
        inside_mask = cv2.bitwise_and(mask_array, parent_mask)
        inside_area = int(np.count_nonzero(inside_mask))
        inside_fraction = float(inside_area / max(1, area_px))
        area_ratio_to_parent = float(area_px / max(1, parent_area))
        if relationship in {"inside_parent", "within_parent", "part_of_parent"} and inside_fraction < 0.98:
            failed.append("inside_parent")
            if inside_area > 0:
                mask_array = inside_mask
                adjustments.append("clipped_to_parent")
        if "centroid_within_parent" in _string_list(config.get("sanity_checks")) and not _centroid_inside_parent(mask_array, parent_mask):
            failed.append("centroid_within_parent")
        if "size_ratio_to_parent" in _string_list(config.get("sanity_checks")) and area_ratio_to_parent > 0.9:
            failed.append("size_ratio_to_parent")

    area_px = int(np.count_nonzero(mask_array))
    area_ratio_image = area_px / max(1, context.width * context.height)
    points = _boundary_points_from_mask(mask_array)
    if len(points) < 8:
        failed.append("insufficient_boundary_points_after_harness")
    bbox = _mask_bbox(mask_array) or candidate["bbox"]
    try:
        point = candidate["positive_point"]
        if not _point_inside_mask(point, mask_array):
            point = _mask_centroid(mask_array)
            adjustments.append("positive_point_replaced_by_mask_centroid")
        if not inside_bbox(point, bbox):
            failed.append("positive_point_outside_bbox")
    except ValueError:
        point = candidate["positive_point"]
        failed.append("empty_mask")

    if _needs_not_text_validation(step, target_label) and bbox and bbox[1] > 0.78:
        failed.append("target_overlaps_bottom_text_annotation_zone")

    if parent_bbox and bbox:
        if relationship in {"deep_to_parent", "posterior_to_parent", "adjacent_to_parent"}:
            parent_center_x = (parent_bbox[0] + parent_bbox[2]) / 2
            target_center_x = (bbox[0] + bbox[2]) / 2
            target_center_y = (bbox[1] + bbox[3]) / 2
            if relationship in {"deep_to_parent", "posterior_to_parent"}:
                if bbox[3] <= parent_bbox[3] + 0.005:
                    failed.append("target_not_deep_to_parent")
                if target_center_y <= parent_bbox[3]:
                    failed.append("target_center_not_deep_to_parent")
            horizontal_span = max(min(bbox[2], parent_bbox[2]) - max(bbox[0], parent_bbox[0]), 0.0)
            if relationship in {"deep_to_parent", "posterior_to_parent"} and horizontal_span < 0.2 * max(parent_bbox[2] - parent_bbox[0], 1e-6):
                failed.append("target_not_horizontally_overlapping_parent")
            if abs(parent_center_x - target_center_x) > max(parent_bbox[2] - parent_bbox[0], 0.08) * 1.5:
                failed.append("target_not_horizontally_aligned_with_parent")

    compactness = 0.0
    perimeter = polygon_perimeter(points)
    normalized_area = polygon_area(points)
    if perimeter > 0:
        compactness = 4 * math.pi * normalized_area / max(perimeter * perimeter, 1e-9)
    if "compact_shape" in _string_list(config.get("sanity_checks")) and compactness < 0.12:
        failed.append("mask_not_compact")

    contrast = _contrast_stats(context.image, mask_array, bbox)
    edge_alignment = _edge_alignment_stats(context.image, mask_array)
    if _needs_dark_target_validation(step, target_label):
        if not contrast.get("available"):
            failed.append("dark_target_contrast_unavailable")
        elif float(contrast["target_minus_surrounding"]) > -8.0:
            failed.append("dark_target_contrast_failed")
    elif _needs_bright_target_validation(step, target_label):
        if not contrast.get("available"):
            failed.append("bright_target_contrast_unavailable")
        elif float(contrast["target_minus_surrounding"]) < 8.0:
            failed.append("bright_target_contrast_failed")
    elif contrast.get("available") and abs(float(contrast["target_minus_surrounding"])) < 2.0:
        warnings.append("weak_local_contrast")
    if edge_alignment.get("available") and float(edge_alignment["boundary_vs_image"]) < 1.05:
        warnings.append("weak_boundary_edge_alignment")

    validation = {
        "valid": not failed,
        "failed_checks": failed,
        "warnings": warnings,
        "applied_adjustments": adjustments,
        "area_px": area_px,
        "area_ratio_image": round(area_ratio_image, 6),
        "compactness": round(compactness, 6),
        "contrast": contrast,
        "edge_alignment": edge_alignment,
        "inside_parent_fraction": round(inside_fraction, 6) if inside_fraction is not None else None,
        "area_ratio_to_parent": round(area_ratio_to_parent, 6) if area_ratio_to_parent is not None else None,
    }
    candidate["bbox"] = bbox
    candidate["positive_point"] = point
    candidate["boundary_points"] = points
    candidate["mask_array"] = mask_array
    candidate["mask"] = _mask_image_from_array(mask_array)
    candidate["validation"] = validation
    return validation


def _extract_grounding_object(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Grounding response must be a JSON object.")
    nested = payload.get("grounding") if isinstance(payload.get("grounding"), dict) else {}
    return {
        "boundary_points": payload.get("boundary_points", nested.get("boundary_points")),
        "coarse_bbox": payload.get("coarse_bbox", payload.get("bbox", nested.get("coarse_bbox", nested.get("bbox")))),
        "positive_point": payload.get("positive_point", nested.get("positive_point")),
        "conclusion": payload.get("conclusion", ""),
        "confidence": payload.get("confidence", nested.get("confidence", 0.0)),
        "rationale": payload.get("rationale", nested.get("rationale", "")),
    }


def _normalize_candidate(
    payload: dict[str, Any],
    *,
    crop_context: CropContext | None = None,
) -> dict[str, Any]:
    obj = _extract_grounding_object(payload)
    points = _sort_polygon_points(normalize_boundary_points(obj["boundary_points"]))
    point = normalize_point(obj["positive_point"])
    bbox = normalize_bbox(obj["coarse_bbox"]) if obj.get("coarse_bbox") else bbox_from_points(points)
    if crop_context is not None:
        points = [_map_point_from_crop(item, crop_context) for item in points]
        point = _map_point_from_crop(point, crop_context)
        bbox = bbox_from_points(points)
    else:
        bbox = bbox_from_points(points)
    return {
        "conclusion": str(obj.get("conclusion") or "").strip() or "localized",
        "confidence": clamp01(obj.get("confidence", 0.0)),
        "rationale": str(obj.get("rationale") or "").strip(),
        "bbox": bbox,
        "positive_point": point,
        "boundary_points": points,
    }


def _map_point_from_crop(point: list[float], crop_context: CropContext) -> list[float]:
    x1, y1, x2, y2 = crop_context.crop_box_norm
    x = x1 + clamp01(point[0]) * max(1e-9, x2 - x1)
    y = y1 + clamp01(point[1]) * max(1e-9, y2 - y1)
    return [round(clamp01(x), 6), round(clamp01(y), 6)]


def _crop_context_from_bbox(
    context: HarnessImage,
    bbox: list[float],
    *,
    label: str,
    pad_ratio: float = 2.0,
    parent_bbox: list[float] | None = None,
    parent_mask: np.ndarray | None = None,
    relationship: str = "",
) -> CropContext:
    width, height = context.width, context.height
    crop_box = _relation_focus_crop_box(
        context=context,
        focus_bbox=bbox,
        parent_bbox=parent_bbox,
        relationship=relationship,
        scale=1.0 + pad_ratio,
    )
    if crop_box[2] <= crop_box[0] or crop_box[3] <= crop_box[1]:
        raise ValueError("Grounding crop has invalid dimensions.")
    crop = context.image.crop((crop_box[0], crop_box[1], crop_box[2] + 1, crop_box[3] + 1))
    crop, parent_overlay = _overlay_parent_contour(crop, crop_box, parent_mask)
    crop = _draw_grid(crop, label=label)
    return CropContext(
        data_url=_image_to_data_url(crop),
        crop_box_px=crop_box,
        crop_box_norm=_bbox_from_px(crop_box, width, height),
        width=crop.width,
        height=crop.height,
        parent_overlay=parent_overlay,
        label=label,
    )


def build_harness_constraints(step: dict[str, Any], parent_output: dict[str, Any] | None) -> str:
    config = _harness_config(step)
    lines: list[str] = []
    evidence_mode = str(config.get("evidence_mode", "") or "").strip()
    if evidence_mode:
        lines.append(f"- Evidence mode: {evidence_mode}.")
    relationship = str(config.get("relationship", "") or "").strip()
    if relationship:
        lines.append(f"- Relationship constraint: {relationship}.")
    if config.get("parent_label"):
        lines.append(f"- Parent label: {config['parent_label']}.")
    spatial_priors = _string_list(config.get("spatial_priors"))
    if spatial_priors:
        lines.append(f"- Spatial priors: {', '.join(spatial_priors)}.")
    sanity_checks = _string_list(config.get("sanity_checks"))
    if sanity_checks:
        lines.append(f"- Sanity checks: {', '.join(sanity_checks)}.")
    parent = parent_grounding(parent_output)
    if parent.get("bbox"):
        lines.append(f"- Parent bbox: {parent['bbox']}.")
    return "\n".join(lines)


def _coarse_prompt(
    *,
    target_label: str,
    step: dict[str, Any],
    prompt_variant: int,
    parent_bbox: list[float] | None,
) -> str:
    templates = [
        "Find the full visible boundary of the requested target.",
        "Localize the requested target by tracing its outer contour.",
        "Identify the target region and include its top, bottom, left, and right extremes.",
    ]
    parent_text = f"\nParent normalized bbox: {parent_bbox}" if parent_bbox else ""
    contrast_expectation = _contrast_expectation(step, target_label)
    contrast_rule = ""
    if contrast_expectation == "dark":
        contrast_rule = "- If this target is dark or hypoechoic, place the contour on the dark structure itself, not on surrounding tissue or below-lesion artifact.\n"
    elif contrast_expectation == "bright":
        contrast_rule = "- If this target is bright relative to surrounding tissue, place the contour on the brighter evidence region itself.\n"
    return dedent(
        f"""
        {templates[prompt_variant % len(templates)]}

        Target: {target_label}
        Step action: {step.get('action') or ''}
        {parent_text}

        The image has visible border rulers with 8 subdivisions per side. Use the rulers only as a spatial aid; do not trace the frame or labels.

        Return ONLY JSON:
        {{
          "conclusion": "localized|not_visible|uncertain",
          "confidence": 0.0,
          "rationale": "short visual evidence",
          "boundary_points": [[x,y], ...],
          "positive_point": [x,y],
          "coarse_bbox": [x1,y1,x2,y2]
        }}

        Rules:
        - Coordinates are normalized to the full shown image.
        - boundary_points must contain 8 to 20 points around the actual visible target boundary.
        - Include points near the target's top, bottom, left, and right extremes.
        - The bbox must tightly cover the same boundary.
        - If multiple plausible structures are visible, choose the single dominant target requested by the task rather than a small satellite, duct, vessel, or artifact.
        - Do not outline labels, measurement text, ruler marks, or background.
        {contrast_rule}\
        - Rationale should describe visual appearance, not crop-relative quadrant language.
        {build_harness_constraints(step, None)}
        """
    ).strip()


def _refine_prompt(
    *,
    target_label: str,
    step: dict[str, Any],
    crop_context: CropContext,
    prompt_variant: int,
    failed_checks: list[str] | None = None,
) -> str:
    repair_text = ""
    if failed_checks:
        repair_text = f"\nPrevious localization failed these checks: {', '.join(failed_checks)}. Correct the localization."
    contrast_expectation = _contrast_expectation(step, target_label)
    contrast_rule = ""
    if contrast_expectation == "dark":
        contrast_rule = "- Put the contour on the darker target and avoid adjacent brighter tissue.\n"
    elif contrast_expectation == "bright":
        contrast_rule = "- Put the contour on the brighter target evidence region and avoid the darker lesion itself.\n"
    return dedent(
        f"""
        Refine the target boundary in this cropped medical image.

        Target: {target_label}
        Step action: {step.get('action') or ''}
        Crop box in the original image: {crop_context.crop_box_norm}
        Prompt variant: {prompt_variant}
        {repair_text}

        Return ONLY JSON:
        {{
          "conclusion": "localized|not_visible|uncertain",
          "confidence": 0.0,
          "rationale": "short visual evidence",
          "boundary_points": [[x,y], ...],
          "positive_point": [x,y],
          "coarse_bbox": [x1,y1,x2,y2]
        }}

        Rules:
        - Coordinates are normalized to THIS CROP, not the original image.
        - boundary_points must contain 8 to 20 points around the actual visible target boundary.
        - If multiple plausible structures are visible, delineate the dominant requested target, not a secondary small focus.
        - Trace the image target boundary, not the border ruler, annotation text, or the previous approximate box.
        - If the target is a lesion, put the boundary on the lesion-tissue transition.
        - If the target is posterior acoustic change, place it deep to the parent lesion and aligned with it.
        {contrast_rule}\
        - If a green parent contour is visible, use it as context and delineate only the requested child target.
        - Rationale should describe visual appearance, not crop-relative quadrant language.
        """
    ).strip()


def _candidate_failure_summary(candidates: list[dict[str, Any]]) -> str:
    if not candidates:
        return "no candidates were generated"
    parts = []
    for index, candidate in enumerate(candidates, start=1):
        validation = candidate.get("validation") or {}
        failed = validation.get("failed_checks") or ["unknown_failure"]
        parts.append(f"sample {index}: {', '.join(str(item) for item in failed)}")
    return "; ".join(parts)


def _run_candidate_sample(
    *,
    request_json: JsonImageRequester,
    context: HarnessImage,
    grid_data_url: str,
    step: dict[str, Any],
    target_label: str,
    parent_bbox: list[float] | None,
    parent_mask: np.ndarray | None,
    sample_idx: int,
    repair_rounds: int,
    guided_bbox: list[float] | None = None,
    guided_proposal: dict[str, Any] | None = None,
) -> dict[str, Any]:
    relationship = _normalize_relation_name(_harness_config(step).get("relationship"))
    if guided_bbox is None:
        coarse_raw = request_json(
            grid_data_url,
            _coarse_prompt(target_label=target_label, step=step, prompt_variant=sample_idx, parent_bbox=parent_bbox),
            1800,
            "You localize medical image evidence. Return only strict JSON.",
        )
        coarse = _normalize_candidate(coarse_raw)
        focus_bbox = coarse["bbox"]
    else:
        coarse = {
            "bbox": normalize_bbox(guided_bbox),
            "confidence": 1.0,
            "rationale": "guided proposal",
        }
        focus_bbox = coarse["bbox"]
    crop_context = _crop_context_from_bbox(
        context,
        parent_bbox if parent_bbox and relationship in {"inside_parent", "within_parent", "part_of_parent", "deep_to_parent", "posterior_to_parent", "adjacent_to_parent", "overlaps_parent"} else focus_bbox,
        label=f"crop sample {sample_idx + 1}",
        pad_ratio=2.4,
        parent_bbox=parent_bbox,
        parent_mask=parent_mask,
        relationship=relationship,
    )
    refined_raw = request_json(
        crop_context.data_url,
        _refine_prompt(target_label=target_label, step=step, crop_context=crop_context, prompt_variant=sample_idx),
        1800,
        "You refine medical image evidence localization. Return only strict JSON.",
    )
    candidate = _normalize_candidate(refined_raw, crop_context=crop_context)
    candidate["sample_id"] = sample_idx
    if guided_bbox is not None:
        candidate["guided_bbox"] = normalize_bbox(guided_bbox)
    if guided_proposal is not None:
        candidate["guided_proposal_id"] = guided_proposal.get("proposal_id")
        candidate["guided_proposal_score"] = guided_proposal.get("score")
    validation = _validate_candidate(
        context=context,
        candidate=candidate,
        step=step,
        target_label=target_label,
        parent_bbox=parent_bbox,
        parent_mask=parent_mask,
    )
    for repair_idx in range(max(0, repair_rounds)):
        if validation["valid"]:
            break
        repair_crop = _crop_context_from_bbox(
            context,
            candidate["bbox"],
            label=f"repair sample {sample_idx + 1}",
            pad_ratio=3.0,
            parent_bbox=parent_bbox,
            parent_mask=parent_mask,
            relationship=relationship,
        )
        repaired_raw = request_json(
            repair_crop.data_url,
            _refine_prompt(
                target_label=target_label,
                step=step,
                crop_context=repair_crop,
                prompt_variant=sample_idx + 100 + repair_idx,
                failed_checks=validation.get("failed_checks", []),
            ),
            1800,
            "You repair failed medical image evidence localization. Return only strict JSON.",
        )
        repaired = _normalize_candidate(repaired_raw, crop_context=repair_crop)
        repaired["sample_id"] = sample_idx
        repaired["repaired"] = True
        validation = _validate_candidate(
            context=context,
            candidate=repaired,
            step=step,
            target_label=target_label,
            parent_bbox=parent_bbox,
            parent_mask=parent_mask,
        )
        candidate = repaired
    return candidate


def run_vlm_grounding_harness(
    *,
    request_json: JsonImageRequester,
    image_payload: dict[str, str],
    step: dict[str, Any],
    target_label: str,
    parent_output: dict[str, Any] | None = None,
    n_samples: int = 3,
    repair_rounds: int = 1,
) -> dict[str, Any]:
    context = prepare_harness_image(image_payload)
    parent = parent_grounding(parent_output)
    parent_bbox = normalize_bbox(parent["bbox"]) if parent.get("bbox") else None
    parent_mask = _parent_mask_from_grounding(parent_output, width=context.width, height=context.height)
    guided_proposals: list[dict[str, Any]] = []
    if _is_primary_dark_lesion_step(step, target_label, parent_mask):
        guided_proposals = _generate_dark_component_proposals(context, step=step, target_label=target_label)
        if not guided_proposals:
            raise ValueError("Primary lesion proposal harness did not find any plausible dark target candidates.")
    grid_data_url = _image_to_data_url(_draw_grid(context.image, label="full image ruler"))
    candidates: list[dict[str, Any]] = []

    for sample_idx in range(max(1, n_samples)):
        guided_proposal = guided_proposals[min(sample_idx, len(guided_proposals) - 1)] if guided_proposals else None
        try:
            candidate = _run_candidate_sample(
                request_json=request_json,
                context=context,
                grid_data_url=grid_data_url,
                step=step,
                target_label=target_label,
                parent_bbox=parent_bbox,
                parent_mask=parent_mask,
                sample_idx=sample_idx,
                repair_rounds=repair_rounds,
                guided_bbox=guided_proposal["bbox"] if guided_proposal is not None else None,
                guided_proposal=guided_proposal,
            )
        except Exception as exc:
            candidate = {
                "sample_id": sample_idx,
                "validation": {
                    "valid": False,
                    "failed_checks": [f"candidate_exception:{type(exc).__name__}:{exc}"],
                },
            }
        candidates.append(candidate)

    valid_candidates = [candidate for candidate in candidates if (candidate.get("validation") or {}).get("valid")]
    if not valid_candidates:
        raise ValueError(f"Grounding harness rejected all VLM candidates: {_candidate_failure_summary(candidates)}")

    iou_matrix: list[list[float]] = []
    for first in valid_candidates:
        row: list[float] = []
        for second in valid_candidates:
            row.append(_mask_iou_array(first["mask_array"], second["mask_array"]))
        iou_matrix.append(row)

    scores: list[float] = []
    dominant_target = _prefers_single_dominant_target(step, target_label)
    max_area_ratio = max(float((candidate.get("validation") or {}).get("area_ratio_image") or 0.0) for candidate in valid_candidates) or 1.0
    proposal_guided_mode = any(candidate.get("guided_proposal_id") for candidate in valid_candidates)
    consensus_weight = 0.45 if proposal_guided_mode else 1.0
    for idx, candidate in enumerate(valid_candidates):
        peer_ious = [score for jdx, score in enumerate(iou_matrix[idx]) if jdx != idx]
        mean_iou = float(sum(peer_ious) / len(peer_ious)) if peer_ious else 1.0
        validation = candidate.get("validation") or {}
        contrast = validation.get("contrast") or {}
        edge_alignment = validation.get("edge_alignment") or {}
        area_ratio_value = float(validation.get("area_ratio_image") or 0.0)
        contrast_bonus = 0.0
        if contrast.get("available") and _needs_dark_target_validation(step, target_label):
            contrast_bonus = min(0.25, max(0.0, -float(contrast["target_minus_surrounding"]) / 120.0))
        edge_bonus = 0.0
        if edge_alignment.get("available"):
            edge_bonus = min(0.2, max(0.0, (float(edge_alignment["boundary_vs_image"]) - 1.0) / 5.0))
        area_bonus = 0.0
        if dominant_target:
            area_bonus = min(0.18, 0.18 * area_ratio_value / max(max_area_ratio, 1e-6))
        proposal_bonus = min(0.25, max(0.0, float(candidate.get("guided_proposal_score") or 0.0) / 4.0))
        scores.append(consensus_weight * mean_iou + 0.05 * float(candidate.get("confidence") or 0.0) + contrast_bonus + edge_bonus + area_bonus + proposal_bonus)
        candidate["selection_score"] = round(scores[-1], 6)
        candidate["mean_peer_iou"] = round(mean_iou, 6)

    primary_index = max(range(len(valid_candidates)), key=lambda index: scores[index])
    primary = valid_candidates[primary_index]
    grounding = {
        "bbox": primary["bbox"],
        "positive_point": primary["positive_point"],
        "boundary_points": primary["boundary_points"],
    }
    return {
        "conclusion": primary["conclusion"],
        "confidence": primary["confidence"],
        "rationale": primary["rationale"],
        "grounding": grounding,
        "validation": primary["validation"],
        "harness": {
            "enabled": True,
            "method": "vlm_ruler_crop_multisample_mask_harness",
            "coordinate_frame": "analysis_image_normalized",
            "analysis_image_size": [context.width, context.height],
            "target_label": target_label,
            "n_samples_total": len(candidates),
            "n_valid_samples": len(valid_candidates),
            "primary_sample_id": primary.get("sample_id"),
            "primary_was_repaired": bool(primary.get("repaired")),
            "parent_focus_used": bool(parent_mask is not None),
            "dominant_target_prior": dominant_target,
            "proposal_selection": {
                "mode": "deterministic_ranked_proposals"
                if guided_proposals
                else "none",
                "selected_id": primary.get("guided_proposal_id"),
                "selected_bbox": primary.get("guided_bbox"),
                "candidates": [
                    {
                        "proposal_id": item["proposal_id"],
                        "bbox": item["bbox"],
                        "score": item["score"],
                        "area_ratio_image": item["area_ratio_image"],
                        "compactness": item["compactness"],
                        "contrast": item["contrast"],
                    }
                    for item in guided_proposals
                ],
            }
            if guided_proposals
            else None,
            "valid_sample_scores": [round(score, 6) for score in scores],
            "valid_sample_mean_ious": [candidate.get("mean_peer_iou", 1.0) for candidate in valid_candidates],
            "iou_matrix": [[round(value, 6) for value in row] for row in iou_matrix],
            "valid_samples": [
                {
                    "sample_id": candidate.get("sample_id"),
                    "bbox": candidate.get("bbox"),
                    "area_ratio_image": (candidate.get("validation") or {}).get("area_ratio_image"),
                    "selection_score": candidate.get("selection_score"),
                    "contrast": (candidate.get("validation") or {}).get("contrast"),
                    "edge_alignment": (candidate.get("validation") or {}).get("edge_alignment"),
                    "failed_checks": (candidate.get("validation") or {}).get("failed_checks", []),
                }
                for candidate in valid_candidates
            ],
            "candidate_failures": [
                {
                    "sample_id": candidate.get("sample_id"),
                    "failed_checks": (candidate.get("validation") or {}).get("failed_checks", []),
                }
                for candidate in candidates
            ],
        },
    }


def normalize_grounding_payload(
    payload: dict[str, Any],
    *,
    relationship: str = "",
    parent_bbox: list[float] | None = None,
) -> dict[str, Any]:
    candidate = _normalize_candidate(payload)
    validation = validate_grounding(
        grounding={
            "bbox": candidate["bbox"],
            "positive_point": candidate["positive_point"],
            "boundary_points": candidate["boundary_points"],
        },
        relationship=relationship,
        parent_bbox=parent_bbox,
    )
    if not validation["valid"]:
        raise ValueError(f"Grounding validation failed: {', '.join(validation['failed_checks'])}")
    return {
        "conclusion": candidate["conclusion"],
        "confidence": candidate["confidence"],
        "rationale": candidate["rationale"],
        "grounding": {
            "bbox": candidate["bbox"],
            "positive_point": candidate["positive_point"],
            "boundary_points": candidate["boundary_points"],
        },
        "validation": validation,
    }


def validate_grounding(
    *,
    grounding: dict[str, Any],
    relationship: str = "",
    parent_bbox: list[float] | None = None,
) -> dict[str, Any]:
    failed_checks: list[str] = []
    bbox = normalize_bbox(grounding["bbox"])
    point = normalize_point(grounding["positive_point"])
    boundary_points = normalize_boundary_points(grounding["boundary_points"])

    if not inside_bbox(point, bbox):
        failed_checks.append("positive_point_outside_bbox")
    relation = _normalize_relation_name(relationship)
    if relation == "inside_parent" and parent_bbox:
        for boundary_point in boundary_points:
            if not inside_bbox(boundary_point, parent_bbox):
                failed_checks.append("boundary_outside_parent_bbox")
                break
        if not inside_bbox(point, parent_bbox):
            failed_checks.append("positive_point_outside_parent_bbox")
        if area_ratio(bbox) > area_ratio(parent_bbox):
            failed_checks.append("bbox_larger_than_parent")

    return {
        "valid": not failed_checks,
        "failed_checks": failed_checks,
    }


def compute_measurements(parent_outputs: list[dict[str, Any]]) -> dict[str, float]:
    if not parent_outputs:
        raise ValueError("Coding step has no upstream evidence.")

    if len(parent_outputs) == 1:
        geometry = parent_grounding(parent_outputs[0])
        points = geometry.get("boundary_points") or []
        bbox = geometry.get("bbox") or bbox_from_points(points)
        area = polygon_area(points)
        perimeter = polygon_perimeter(points)
        width = max(bbox[2] - bbox[0], 1e-6)
        height = max(bbox[3] - bbox[1], 1e-6)
        return {
            "area_ratio": round(area, 6),
            "bbox_width": round(width, 6),
            "bbox_height": round(height, 6),
            "aspect_ratio": round(width / height, 6),
            "perimeter": round(perimeter, 6),
            "circularity": round((4 * math.pi * area) / max(perimeter * perimeter, 1e-6), 6),
        }

    first_bbox = parent_grounding(parent_outputs[0]).get("bbox")
    second_bbox = parent_grounding(parent_outputs[1]).get("bbox")
    if not first_bbox or not second_bbox:
        raise ValueError("Coding step needs grounded parent regions.")
    first_height = max(first_bbox[3] - first_bbox[1], 1e-6)
    second_height = max(second_bbox[3] - second_bbox[1], 1e-6)
    ratio = second_height / first_height
    return {
        "vertical_extent_ratio": round(ratio, 6),
        "parent_height": round(first_height, 6),
        "child_height": round(second_height, 6),
    }
