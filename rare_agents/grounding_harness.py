from __future__ import annotations

import base64
import io
import math
from dataclasses import dataclass
from textwrap import dedent
from typing import Any, Callable

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageOps


JsonImageRequester = Callable[[list[dict[str, Any]] | list[str], str, int, str], dict[str, Any]]
DEFAULT_MASK_SIZE = 64
REQUIRED_BOUNDARY_POINT_COUNT = 32
ANALYSIS_MAX_LONG_EDGE = 1536
PNG_VIEW_PIXEL_LIMIT = 1_200_000
JPEG_VIEW_QUALITY = 92
FOCUS_PANEL_EDGE = 448


@dataclass
class HarnessImage:
    image: Image.Image
    data_url: str
    media_type: str
    width: int
    height: int
    original_width: int = 0
    original_height: int = 0
    analysis_scale: float = 1.0


@dataclass
class HarnessView:
    name: str
    label: str
    data_url: str
    bounds: list[float] | None = None
    selectable: bool = True


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
    return [normalize_point(item) for item in value]


def map_point_from_view(point: list[float], view: HarnessView) -> list[float]:
    bounds = view.bounds or [0.0, 0.0, 1.0, 1.0]
    left, top, right, bottom = [float(item) for item in bounds]
    width = max(1e-6, right - left)
    height = max(1e-6, bottom - top)
    return [
        round(clamp01(left + float(point[0]) * width), 6),
        round(clamp01(top + float(point[1]) * height), 6),
    ]


def map_points_from_view(points: list[list[float]], view: HarnessView) -> list[list[float]]:
    return [map_point_from_view(point, view) for point in points]


def normalize_mask_size(value: object) -> list[int]:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError("Grounding mask_size must have length 2.")
    width = int(value[0])
    height = int(value[1])
    if width < 24 or height < 24 or width > 128 or height > 128:
        raise ValueError("Grounding mask_size must be between 24 and 128.")
    return [width, height]


def normalize_mask_spans(value: object, *, width: int, height: int) -> list[list[Any]]:
    if not isinstance(value, list):
        raise ValueError("Grounding mask_spans must be a list.")
    rows: list[list[Any]] = []
    previous_row = -1
    for entry in value:
        if isinstance(entry, dict):
            row_value = entry.get("row")
            runs_value = entry.get("runs", entry.get("segments", entry.get("spans")))
        elif isinstance(entry, (list, tuple)) and len(entry) == 2:
            row_value, runs_value = entry
        else:
            raise ValueError("Each mask_spans entry must be [row, runs] or an object with row/runs.")
        row = int(row_value)
        if row < 0 or row >= height:
            raise ValueError("mask_spans row is out of range.")
        if row <= previous_row:
            raise ValueError("mask_spans rows must be strictly increasing.")
        previous_row = row
        if not isinstance(runs_value, list):
            raise ValueError("mask_spans runs must be a list.")
        normalized_runs: list[list[int]] = []
        for run in runs_value:
            if not isinstance(run, (list, tuple)) or len(run) != 2:
                raise ValueError("Each mask_spans run must have length 2.")
            left = max(0, min(width - 1, int(run[0])))
            right = max(0, min(width - 1, int(run[1])))
            start, end = sorted([left, right])
            if normalized_runs and start <= normalized_runs[-1][1] + 1:
                normalized_runs[-1][1] = max(normalized_runs[-1][1], end)
            else:
                normalized_runs.append([start, end])
        if normalized_runs:
            rows.append([row, normalized_runs])
    if not rows:
        raise ValueError("mask_spans must contain at least one foreground row.")
    return rows


def canonicalize_boundary_points(points: list[list[float]]) -> list[list[float]]:
    if len(points) < 3:
        raise ValueError("Cannot canonicalize fewer than 3 boundary points.")
    ordered = [[float(point[0]), float(point[1])] for point in points]
    if _has_self_intersection(ordered):
        centroid = polygon_centroid(ordered)
        repaired = sorted(ordered, key=lambda point: math.atan2(point[1] - centroid[1], point[0] - centroid[0]))
        if not _has_self_intersection(repaired):
            ordered = repaired
    if polygon_signed_area(ordered) >= 0:
        ordered = list(reversed(ordered))
    top_index = min(range(len(ordered)), key=lambda index: (ordered[index][1], ordered[index][0]))
    rotated = ordered[top_index:] + ordered[:top_index]
    return [[round(point[0], 6), round(point[1], 6)] for point in rotated]


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


def resample_boundary_points(points: list[list[float]], *, n_points: int = REQUIRED_BOUNDARY_POINT_COUNT) -> list[list[float]]:
    if len(points) < 3:
        raise ValueError("Cannot resample fewer than 3 boundary points.")
    perimeter = polygon_perimeter(points)
    if perimeter <= 1e-9:
        raise ValueError("Cannot resample zero-perimeter boundary.")
    segments: list[tuple[list[float], list[float], float]] = []
    for index, point in enumerate(points):
        next_point = points[(index + 1) % len(points)]
        length = math.dist(point, next_point)
        if length > 1e-12:
            segments.append((point, next_point, length))
    if not segments:
        raise ValueError("Cannot resample boundary without non-zero edges.")
    samples: list[list[float]] = []
    segment_index = 0
    traversed = 0.0
    for sample_index in range(n_points):
        target = perimeter * sample_index / n_points
        while segment_index < len(segments) - 1 and traversed + segments[segment_index][2] < target:
            traversed += segments[segment_index][2]
            segment_index += 1
        start, end, length = segments[segment_index]
        ratio = max(0.0, min(1.0, (target - traversed) / length))
        samples.append(
            [
                round(clamp01(start[0] + (end[0] - start[0]) * ratio), 6),
                round(clamp01(start[1] + (end[1] - start[1]) * ratio), 6),
            ]
        )
    return samples


def polygon_centroid(points: list[list[float]]) -> list[float]:
    if len(points) < 3:
        raise ValueError("Cannot compute centroid from fewer than 3 points.")
    signed_area = 0.0
    cx = 0.0
    cy = 0.0
    for index, point in enumerate(points):
        next_point = points[(index + 1) % len(points)]
        cross = point[0] * next_point[1] - next_point[0] * point[1]
        signed_area += cross
        cx += (point[0] + next_point[0]) * cross
        cy += (point[1] + next_point[1]) * cross
    if abs(signed_area) < 1e-8:
        xs = [point[0] for point in points]
        ys = [point[1] for point in points]
        return [sum(xs) / len(xs), sum(ys) / len(ys)]
    factor = 1.0 / (3.0 * signed_area)
    return [cx * factor, cy * factor]


def polygon_signed_area(points: list[list[float]]) -> float:
    total = 0.0
    for index, point in enumerate(points):
        next_point = points[(index + 1) % len(points)]
        total += point[0] * next_point[1] - next_point[0] * point[1]
    return total * 0.5


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


def bbox_iou(first: list[float], second: list[float]) -> float:
    left = max(first[0], second[0])
    top = max(first[1], second[1])
    right = min(first[2], second[2])
    bottom = min(first[3], second[3])
    intersection = max(0.0, right - left) * max(0.0, bottom - top)
    union = area_ratio(first) + area_ratio(second) - intersection
    if union <= 0.0:
        return 0.0
    return float(intersection / union)


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
    original_width, original_height = image.size
    image = _resize_for_analysis(image)
    view_media_type = _select_view_media_type(image, media_type)
    data_url = _image_to_data_url(image, media_type=view_media_type)
    return HarnessImage(
        image=image,
        data_url=data_url,
        media_type=view_media_type,
        width=image.width,
        height=image.height,
        original_width=original_width,
        original_height=original_height,
        analysis_scale=round(image.width / max(1, original_width), 6),
    )


def _resize_for_analysis(image: Image.Image) -> Image.Image:
    width, height = image.size
    long_edge = max(width, height)
    if long_edge <= ANALYSIS_MAX_LONG_EDGE:
        return image
    return ImageOps.contain(image, (ANALYSIS_MAX_LONG_EDGE, ANALYSIS_MAX_LONG_EDGE), method=Image.Resampling.LANCZOS)


def _select_view_media_type(image: Image.Image, source_media_type: str) -> str:
    if source_media_type.lower() in {"image/jpeg", "image/jpg"}:
        return "image/jpeg"
    if image.width * image.height > PNG_VIEW_PIXEL_LIMIT:
        return "image/jpeg"
    return "image/png"


def _image_to_data_url(image: Image.Image, *, media_type: str = "image/png") -> str:
    buffer = io.BytesIO()
    if media_type == "image/jpeg":
        image.convert("RGB").save(buffer, format="JPEG", quality=JPEG_VIEW_QUALITY, optimize=True)
        return "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")
    image.convert("RGB").save(buffer, format="PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


def _clip_bounds(bounds: list[float]) -> list[float]:
    left, top, right, bottom = [clamp01(item) for item in bounds]
    left, right = sorted([left, right])
    top, bottom = sorted([top, bottom])
    if right - left < 0.02:
        center_x = (left + right) * 0.5
        left = max(0.0, center_x - 0.01)
        right = min(1.0, center_x + 0.01)
    if bottom - top < 0.02:
        center_y = (top + bottom) * 0.5
        top = max(0.0, center_y - 0.01)
        bottom = min(1.0, center_y + 0.01)
    return [round(left, 6), round(top, 6), round(right, 6), round(bottom, 6)]


def _bounds_to_pixel_box(image: Image.Image, bounds: list[float]) -> tuple[int, int, int, int]:
    clipped = _clip_bounds(bounds)
    left = int(round(clipped[0] * max(1, image.width - 1)))
    top = int(round(clipped[1] * max(1, image.height - 1)))
    right = int(round(clipped[2] * max(1, image.width - 1)))
    bottom = int(round(clipped[3] * max(1, image.height - 1)))
    right = max(right, left + 1)
    bottom = max(bottom, top + 1)
    return left, top, right, bottom


def _crop_image(image: Image.Image, bounds: list[float]) -> Image.Image:
    left, top, right, bottom = _bounds_to_pixel_box(image, bounds)
    return image.crop((left, top, right, bottom))


def _panel_label(image: Image.Image, label: str) -> Image.Image:
    canvas = image.convert("RGB").copy()
    draw = ImageDraw.Draw(canvas)
    w, h = canvas.size
    band_height = min(28, max(22, h // 18))
    draw.rectangle([0, 0, w, band_height], fill=(255, 255, 255))
    draw.text((8, max(2, band_height // 5)), label[:120], fill=(0, 0, 0))
    return canvas


def _resize_panel(image: Image.Image, *, width: int = FOCUS_PANEL_EDGE, height: int = FOCUS_PANEL_EDGE) -> Image.Image:
    return ImageOps.contain(image.convert("RGB"), (width, height))


def _draw_focus_sheet(image: Image.Image, focus_windows: list[tuple[str, list[float]]]) -> Image.Image:
    cell_width = FOCUS_PANEL_EDGE
    cell_height = FOCUS_PANEL_EDGE + 34
    columns = 2
    rows = max(1, math.ceil(len(focus_windows) / columns))
    canvas = Image.new("RGB", (columns * cell_width, rows * cell_height), (18, 18, 18))
    draw = ImageDraw.Draw(canvas)
    for index, (name, bounds) in enumerate(focus_windows, start=1):
        row = (index - 1) // columns
        column = (index - 1) % columns
        left = column * cell_width
        top = row * cell_height
        label = f"focus-{index}: {name} {_bounds_text(name, bounds, precision=4)}"
        draw.rectangle([left, top, left + cell_width - 1, top + 33], fill=(255, 255, 255))
        draw.text((left + 8, top + 8), label[:96], fill=(0, 0, 0))
        crop = _resize_panel(_crop_image(image, bounds), width=cell_width, height=FOCUS_PANEL_EDGE)
        paste_left = left + (cell_width - crop.width) // 2
        paste_top = top + 34 + (FOCUS_PANEL_EDGE - crop.height) // 2
        canvas.paste(crop, (paste_left, paste_top))
        draw.rectangle([left, top + 34, left + cell_width - 1, top + cell_height - 1], outline=(242, 185, 36), width=2)
    return canvas


def _is_effectively_grayscale(image: Image.Image) -> bool:
    array = np.asarray(image.convert("RGB"), dtype=np.int16)
    channel_delta = (
        np.abs(array[:, :, 0] - array[:, :, 1]).mean()
        + np.abs(array[:, :, 1] - array[:, :, 2]).mean()
        + np.abs(array[:, :, 0] - array[:, :, 2]).mean()
    ) / 3.0
    return float(channel_delta) < 2.0


def _bounds_text(name: str, bounds: list[float], *, precision: int = 4) -> str:
    left, top, right, bottom = bounds
    return f"{name} x={left:.{precision}f}-{right:.{precision}f} y={top:.{precision}f}-{bottom:.{precision}f}"


def _make_focus_windows(parent_bbox: list[float] | None, relationship: str) -> list[tuple[str, list[float]]]:
    windows: list[tuple[str, list[float]]] = []
    if parent_bbox:
        relation = _normalize_relation_name(relationship)
        if relation in {"deep_to_parent", "posterior_to_parent"}:
            windows.append(
                (
                    "parent-relative",
                    _clip_bounds(
                        [
                            parent_bbox[0] - 0.18,
                            parent_bbox[1] - 0.10,
                            parent_bbox[2] + 0.18,
                            parent_bbox[3] + 0.42,
                        ]
                    ),
                )
            )
            windows.append(
                (
                    "parent-context",
                    _clip_bounds(
                        [
                            parent_bbox[0] - 0.26,
                            parent_bbox[1] - 0.18,
                            parent_bbox[2] + 0.26,
                            parent_bbox[3] + 0.46,
                        ]
                    ),
                )
            )
        elif relation in {"inside_parent", "within_parent", "part_of_parent"}:
            windows.append(
                (
                    "parent-focused",
                    _clip_bounds(
                        [
                            parent_bbox[0] - 0.08,
                            parent_bbox[1] - 0.08,
                            parent_bbox[2] + 0.08,
                            parent_bbox[3] + 0.08,
                        ]
                    ),
                )
            )
            windows.append(
                (
                    "parent-context",
                    _clip_bounds(
                        [
                            parent_bbox[0] - 0.16,
                            parent_bbox[1] - 0.16,
                            parent_bbox[2] + 0.16,
                            parent_bbox[3] + 0.16,
                        ]
                    ),
                )
            )
        else:
            windows.append(
                (
                    "parent-context",
                    _clip_bounds(
                        [
                            parent_bbox[0] - 0.18,
                            parent_bbox[1] - 0.18,
                            parent_bbox[2] + 0.18,
                            parent_bbox[3] + 0.18,
                        ]
                    ),
                )
            )
    windows.extend(
        [
            ("upper-left", [0.0, 0.0, 0.62, 0.62]),
            ("upper-right", [0.38, 0.0, 1.0, 0.62]),
            ("lower-left", [0.0, 0.38, 0.62, 1.0]),
            ("lower-right", [0.38, 0.38, 1.0, 1.0]),
        ]
    )
    deduped: list[tuple[str, list[float]]] = []
    seen: set[tuple[float, float, float, float]] = set()
    for name, bounds in windows:
        clipped = _clip_bounds(bounds)
        key = tuple(clipped)
        if key in seen:
            continue
        seen.add(key)
        deduped.append((name, clipped))
    return deduped[:4]


def _build_grounding_views(
    context: HarnessImage,
    *,
    parent_bbox: list[float] | None,
    relationship: str,
) -> list[HarnessView]:
    del parent_bbox, relationship
    if _is_effectively_grayscale(context.image):
        guided_image = _draw_grid(context.image, label="full-image normalized coordinate frame")
        return [
            HarnessView(
                name="original-full",
                label="View 1: original full image; use this view to recognize the medical target",
                data_url=context.data_url,
                bounds=None,
            ),
            HarnessView(
                name="coordinate-full",
                label="View 2: same full image with dense coordinate grid; use this view to calibrate normalized x/y coordinates",
                data_url=_image_to_data_url(guided_image, media_type=context.media_type),
                bounds=None,
            )
        ]
    return [
        HarnessView(
            name="original-full",
            label="View 1: original full image; coordinates are normalized to this whole image",
            data_url=context.data_url,
            bounds=None,
        )
    ]


def _draw_grid(image: Image.Image, *, label: str) -> Image.Image:
    canvas = image.convert("RGB").copy()
    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    w, h = canvas.size
    label_bg = (255, 255, 255, 190)
    for idx in range(0, 11):
        x = round((w - 1) * idx / 10)
        y = round((h - 1) * idx / 10)
        is_major = idx in {0, 5, 10}
        line_color = (242, 185, 36, 120) if is_major else (0, 210, 235, 72)
        line_width = 2 if is_major else 1
        draw.line([(x, 0), (x, max(0, h - 1))], fill=line_color, width=line_width)
        draw.line([(0, y), (max(0, w - 1), y)], fill=line_color, width=line_width)
        text = f"{idx / 10:.1f}"
        draw.rectangle([min(max(0, x + 2), max(0, w - 34)), 0, min(max(34, x + 36), w), 14], fill=label_bg)
        draw.text((min(max(2, x + 4), max(2, w - 32)), 1), text, fill=(30, 30, 30, 255))
        draw.rectangle([0, min(max(0, y + 2), max(0, h - 16)), 34, min(max(16, y + 18), h)], fill=label_bg)
        draw.text((2, min(max(2, y + 4), max(2, h - 14))), text, fill=(30, 30, 30, 255))
    if label:
        draw.rectangle([0, max(0, h - 22), min(w, 12 + len(label) * 7), h], fill=label_bg)
        draw.text((6, max(0, h - 18)), label[:80], fill=(0, 0, 0, 255))
    return Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB")


def _mask_from_spans(mask_size: list[int], mask_spans: list[list[Any]]) -> np.ndarray:
    width, height = mask_size
    mask = np.zeros((height, width), dtype=np.uint8)
    for row, runs in mask_spans:
        for start, end in runs:
            mask[int(row), int(start) : int(end) + 1] = 255
    return mask


def _render_mask_in_full_image(
    *,
    context: HarnessImage,
    selected_view: HarnessView,
    mask_size: list[int],
    mask_spans: list[list[Any]],
) -> tuple[np.ndarray, np.ndarray]:
    local_mask = _mask_from_spans(mask_size, mask_spans)
    full_mask = np.zeros((context.height, context.width), dtype=np.uint8)
    if selected_view.bounds:
        left, top, right, bottom = _bounds_to_pixel_box(context.image, selected_view.bounds)
        target_width = max(1, right - left)
        target_height = max(1, bottom - top)
        resized = cv2.resize(local_mask, (target_width, target_height), interpolation=cv2.INTER_NEAREST)
        full_mask[top : top + target_height, left : left + target_width] = np.maximum(
            full_mask[top : top + target_height, left : left + target_width],
            resized,
        )
    else:
        resized = cv2.resize(local_mask, (context.width, context.height), interpolation=cv2.INTER_NEAREST)
        full_mask = np.maximum(full_mask, resized)
    return local_mask, full_mask


def _largest_external_contour(mask: np.ndarray) -> np.ndarray:
    binary = (mask > 0).astype(np.uint8)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not contours:
        raise ValueError("Segmentation mask has no visible contour.")
    return max(contours, key=cv2.contourArea)


def _resample_contour_points(contour: np.ndarray, *, n_points: int = 32) -> list[list[float]]:
    raw = contour.reshape(-1, 2).astype(np.float32)
    if len(raw) < 3:
        raise ValueError("Segmentation contour has fewer than 3 points.")
    closed = np.vstack([raw, raw[0]])
    diffs = np.diff(closed, axis=0)
    lengths = np.sqrt(np.sum(diffs * diffs, axis=1))
    perimeter = float(lengths.sum())
    if perimeter <= 1e-6:
        raise ValueError("Segmentation contour perimeter is zero.")
    cumulative = np.concatenate([[0.0], np.cumsum(lengths)])
    targets = np.linspace(0.0, perimeter, num=max(12, int(n_points)), endpoint=False)
    sampled: list[list[float]] = []
    segment_index = 0
    for target in targets:
        while segment_index < len(lengths) - 1 and cumulative[segment_index + 1] < target:
            segment_index += 1
        segment_length = max(lengths[segment_index], 1e-6)
        alpha = (target - cumulative[segment_index]) / segment_length
        point = closed[segment_index] + alpha * (closed[segment_index + 1] - closed[segment_index])
        sampled.append([float(point[0]), float(point[1])])
    return sampled


def _mask_component_count(mask: np.ndarray) -> int:
    binary = (mask > 0).astype(np.uint8)
    if not binary.any():
        return 0
    total, _ = cv2.connectedComponents(binary, connectivity=8)
    return max(0, int(total) - 1)


def _mask_bbox(mask: np.ndarray) -> list[float]:
    ys, xs = np.where(mask > 0)
    if xs.size == 0 or ys.size == 0:
        return []
    height, width = mask.shape[:2]
    return [
        round(float(xs.min() / max(1, width - 1)), 6),
        round(float(ys.min() / max(1, height - 1)), 6),
        round(float(xs.max() / max(1, width - 1)), 6),
        round(float(ys.max() / max(1, height - 1)), 6),
    ]


def _mask_from_polygon_points(*, width: int, height: int, points: list[list[float]]) -> np.ndarray:
    normalized = normalize_boundary_points(points)
    polygon = np.array(
        [
            [
                int(round(point[0] * max(1, width - 1))),
                int(round(point[1] * max(1, height - 1))),
            ]
            for point in normalized
        ],
        dtype=np.int32,
    )
    mask = np.zeros((height, width), dtype=np.uint8)
    if len(polygon) >= 3:
        cv2.fillPoly(mask, [polygon], 255)
    return mask


def _largest_component(mask: np.ndarray) -> np.ndarray:
    binary = (mask > 0).astype(np.uint8)
    total, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
    if total <= 2:
        return (binary * 255).astype(np.uint8)
    areas = stats[1:, cv2.CC_STAT_AREA]
    largest_label = int(np.argmax(areas) + 1)
    largest = np.zeros_like(binary)
    largest[labels == largest_label] = 1
    return (largest * 255).astype(np.uint8)


def _mask_centroid(mask: np.ndarray) -> tuple[int, int] | None:
    moments = cv2.moments((mask > 0).astype(np.uint8))
    if moments["m00"] == 0:
        return None
    cx = int(round(moments["m10"] / moments["m00"]))
    cy = int(round(moments["m01"] / moments["m00"]))
    height, width = mask.shape[:2]
    return max(0, min(width - 1, cx)), max(0, min(height - 1, cy))


def _centroid_inside_parent(mask: np.ndarray, parent_mask: np.ndarray) -> bool:
    centroid = _mask_centroid(mask)
    if centroid is None:
        return False
    cx, cy = centroid
    return bool(parent_mask[cy, cx] > 0)


def _mask_iou(first: np.ndarray, second: np.ndarray) -> float:
    intersection = np.count_nonzero(cv2.bitwise_and(first, second))
    union = np.count_nonzero(cv2.bitwise_or(first, second))
    if union <= 0:
        return 0.0
    return float(intersection / union)


def _parent_mask_from_grounding(*, width: int, height: int, parent: dict[str, Any]) -> np.ndarray | None:
    points = parent.get("boundary_points")
    if not isinstance(points, list) or len(points) < 3:
        return None
    return _mask_from_polygon_points(width=width, height=height, points=points)


def _candidate_from_mask(
    *,
    context: HarnessImage,
    selected_view: HarnessView,
    mask_size: list[int],
    mask_spans: list[list[Any]],
    conclusion: str,
    confidence: float,
    rationale: str,
) -> dict[str, Any]:
    local_mask, full_mask = _render_mask_in_full_image(
        context=context,
        selected_view=selected_view,
        mask_size=mask_size,
        mask_spans=mask_spans,
    )
    contour = _largest_external_contour(full_mask)
    sampled_pixels = _resample_contour_points(contour, n_points=32)
    points = canonicalize_boundary_points(
        [
            [
                round(float(point[0]) / max(1.0, context.width - 1.0), 6),
                round(float(point[1]) / max(1.0, context.height - 1.0), 6),
            ]
            for point in sampled_pixels
        ]
    )
    bbox = bbox_from_points(points)
    area_pixels = int(np.count_nonzero(full_mask))
    area_ratio_image = float(area_pixels / max(1, context.width * context.height))
    return {
        "conclusion": conclusion,
        "confidence": confidence,
        "rationale": rationale,
        "selected_view": selected_view.name,
        "selected_view_label": selected_view.label,
        "selected_view_bounds": list(selected_view.bounds) if selected_view.bounds else [0.0, 0.0, 1.0, 1.0],
        "mask_size": mask_size,
        "mask_spans": mask_spans,
        "mask_component_count": _mask_component_count(full_mask),
        "mask_area_ratio_image": round(area_ratio_image, 6),
        "raw_boundary_point_count": len(points),
        "local_mask_foreground_pixels": int(np.count_nonzero(local_mask)),
        "mask_bbox": _mask_bbox(full_mask),
        "bbox": bbox,
        "boundary_points": points,
    }


def _string_list(value: Any) -> list[str]:
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _segmentation_boundary_rules() -> str:
    return dedent(
        """
        ROI boundary protocol:
        - Return ordered ROI boundary points that trace the true visible lesion boundary.
        - Return 12 to 20 raw boundary point pairs in the selected_view coordinate frame; the application will resample them for display.
        - Points must run around one closed contour in clockwise or counterclockwise order with no self-intersection.
        - Include all meaningful shape changes: poles, corners, lobulations, indentations, and flat segments.
        - Even for a simple oval lesion, include intermediate points along each arc instead of only a few extremal points.
        - Trace the complete visible target instance as an outer envelope; do not trace only a rim, wall, central core, upper edge, or partial arc.
        - If the target has an internal core, rim, capsule, wall, or halo that belongs to the same target, place the contour on the outermost target-to-background transition, not on an internal core-to-rim transition.
        - Include connected low-contrast portions that belong to the same target even when their border is less salient than the central core.
        - Put the contour on the target-to-background transition, not on a surrounding artifact, shadow, enhancement band, measurement mark, or label.
        - Exclusion rules remove separate adjacent structures and artifacts; they must not shrink the requested target to its highest-contrast core.
        - If a bright rim, halo, or acoustic artifact is outside the target body, exclude it.
        - Do not return a fitted circle, ellipse, coarse box, or a sparse anchor set.
        - When these points are connected, they should directly define a valid segmentation polygon for the target.
        """
    ).strip()


def _modality_artifact_protocol() -> str:
    return dedent(
        """
        Modality-aware artifact rejection:
        - Infer the modality from the image itself and bind the ROI to the physical target, not to the diagnosis word.
        - For ultrasound-like images, a lesion, mass, cyst, or nodule ROI is the coherent bounded object body at the outermost transition to surrounding tissue.
        - For cystic, anechoic, rimmed, or walled targets, include the entire visible target body and belonging wall/rim; do not trace only the central dark core, inner fluid-wall interface, upper edge, or a partial arc.
        - Posterior acoustic shadowing, enhancement, reverberation, diffuse texture changes, and speckle-only patches are evidence context, not part of the ROI.
        - If a deeper acoustic effect lies below a smaller bounded focus, localize the bounded focus and exclude the deeper effect.
        - For non-ultrasound images, use the visible anatomical boundary appropriate to the target label and ignore labels, overlays, rulers, and background.
        """
    ).strip()


def _harness_config(step: dict[str, Any]) -> dict[str, Any]:
    tool_config = step.get("tool_config") if isinstance(step.get("tool_config"), dict) else {}
    keys = [
        "target_label",
        "target_anchor",
        "roi_definition",
        "boundary_definition",
        "include",
        "exclude",
        "target_scope",
        "evidence_mode",
        "relative_to_step",
        "relationship",
        "parent_label",
        "spatial_priors",
        "sanity_checks",
    ]
    return {key: tool_config.get(key, step.get(key)) for key in keys if tool_config.get(key, step.get(key)) not in (None, "", [], {})}


def _normalize_relation_name(value: object) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def _extract_grounding_object(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Grounding response must be a JSON object.")
    nested = payload.get("grounding") if isinstance(payload.get("grounding"), dict) else {}
    return {
        "boundary_points": payload.get("boundary_points", nested.get("boundary_points")),
        "positive_point": payload.get("positive_point", nested.get("positive_point")),
        "coarse_bbox": payload.get("coarse_bbox", payload.get("bbox", nested.get("coarse_bbox", nested.get("bbox")))),
        "selected_view": payload.get("selected_view", nested.get("selected_view")),
        "mask_size": payload.get("mask_size", nested.get("mask_size")),
        "mask_spans": payload.get("mask_spans", nested.get("mask_spans")),
        "target_understanding": payload.get("target_understanding", nested.get("target_understanding", payload.get("target_description", nested.get("target_description", "")))),
        "boundary_definition": payload.get("boundary_definition", nested.get("boundary_definition", "")),
        "excluded_regions": payload.get("excluded_regions", nested.get("excluded_regions", [])),
        "conclusion": payload.get("conclusion", ""),
        "confidence": payload.get("confidence", nested.get("confidence")),
        "rationale": payload.get("rationale", nested.get("rationale", "")),
    }


def _require_confidence(payload: dict[str, Any], *, label: str) -> float:
    if "confidence" not in payload or payload.get("confidence") is None:
        raise ValueError(f"{label} response must include confidence.")
    return clamp01(payload["confidence"])


def _resolve_selected_view(selected_view: object, views: list[HarnessView]) -> HarnessView:
    if isinstance(selected_view, int):
        index = int(selected_view) - 1
        if 0 <= index < len(views):
            return views[index]
    text = str(selected_view or "").strip().lower()
    if not text:
        raise ValueError("Grounding candidate must include selected_view.")
    for index, view in enumerate(views, start=1):
        if text in {view.name.lower(), view.label.lower(), f"view {index}", f"view_{index}", str(index)}:
            return view
    for index, view in enumerate(views, start=1):
        if view.label.lower().startswith(text):
            return view
        if text.startswith(f"view {index}") or text.startswith(f"view_{index}"):
            return view
    raise ValueError(f"Grounding candidate selected_view is unknown: {selected_view}")


def _normalize_candidate(payload: dict[str, Any], *, views: list[HarnessView], context: HarnessImage) -> dict[str, Any]:
    obj = _extract_grounding_object(payload)
    selected_view = _resolve_selected_view(obj.get("selected_view"), views)
    conclusion = str(obj.get("conclusion") or "").strip() or "localized"
    confidence = _require_confidence(obj, label="Grounding candidate")
    rationale = str(obj.get("rationale") or "").strip()
    target_understanding = str(obj.get("target_understanding") or "").strip()
    boundary_definition = str(obj.get("boundary_definition") or "").strip()
    excluded_regions = _string_list(obj.get("excluded_regions"))
    if not target_understanding:
        raise ValueError("Grounding candidate must include target_understanding.")
    if not boundary_definition:
        raise ValueError("Grounding candidate must include boundary_definition.")
    if obj.get("boundary_points") is not None:
        positive_point = normalize_point(obj.get("positive_point"))
        coarse_bbox_local = normalize_bbox(obj.get("coarse_bbox"))
        raw_local_points = normalize_boundary_points(obj["boundary_points"])
        local_points = resample_boundary_points(
            canonicalize_boundary_points(raw_local_points),
            n_points=REQUIRED_BOUNDARY_POINT_COUNT,
        )
        points = canonicalize_boundary_points(map_points_from_view(local_points, selected_view))
        positive_point = map_point_from_view(positive_point, selected_view)
        coarse_top_left = map_point_from_view([coarse_bbox_local[0], coarse_bbox_local[1]], selected_view)
        coarse_bottom_right = map_point_from_view([coarse_bbox_local[2], coarse_bbox_local[3]], selected_view)
        coarse_bbox = normalize_bbox([coarse_top_left[0], coarse_top_left[1], coarse_bottom_right[0], coarse_bottom_right[1]])
        bbox = bbox_from_points(points)
        polygon = np.array(
            [
                [
                    int(round(point[0] * max(1.0, context.width - 1.0))),
                    int(round(point[1] * max(1.0, context.height - 1.0))),
                ]
                for point in points
            ],
            dtype=np.int32,
        )
        full_mask = np.zeros((context.height, context.width), dtype=np.uint8)
        cv2.fillPoly(full_mask, [polygon], 255)
        return {
            "conclusion": conclusion,
            "confidence": confidence,
            "rationale": rationale,
            "target_understanding": target_understanding,
            "boundary_definition": boundary_definition,
            "excluded_regions": excluded_regions,
            "selected_view": selected_view.name,
            "selected_view_label": selected_view.label,
            "selected_view_bounds": list(selected_view.bounds) if selected_view.bounds else [0.0, 0.0, 1.0, 1.0],
            "raw_boundary_point_count": len(raw_local_points),
            "local_boundary_points": local_points,
            "mask_size": [],
            "mask_spans": [],
            "mask_component_count": _mask_component_count(full_mask),
            "mask_area_ratio_image": round(float(np.count_nonzero(full_mask) / max(1, context.width * context.height)), 6),
            "local_mask_foreground_pixels": 0,
            "mask_bbox": _mask_bbox(full_mask),
            "bbox": bbox,
            "coarse_bbox": coarse_bbox,
            "positive_point": positive_point,
            "boundary_points": points,
        }
    raise ValueError("Grounding candidate must include boundary_points.")


def build_harness_constraints(step: dict[str, Any], parent_output: dict[str, Any] | None) -> str:
    config = _harness_config(step)
    lines: list[str] = []
    finding = str(step.get("finding") or "").strip()
    if finding:
        lines.append(f"- Evidence focus: {finding}.")
    target_scope = str(config.get("target_scope", "") or "").strip()
    if target_scope:
        lines.append(f"- Target scope: {target_scope}.")
    target_label = str(config.get("target_label", "") or "").strip()
    if target_label:
        lines.append(f"- Explicit target label: {target_label}.")
    target_anchor = config.get("target_anchor")
    if isinstance(target_anchor, dict):
        anchor_parts: list[str] = []
        if target_anchor.get("point"):
            anchor_parts.append(f"point={target_anchor['point']}")
        if target_anchor.get("bbox"):
            anchor_parts.append(f"bbox={target_anchor['bbox']}")
        if target_anchor.get("location"):
            anchor_parts.append(f"location={target_anchor['location']}")
        if anchor_parts:
            lines.append(f"- Approximate target anchor for instance selection only: {'; '.join(anchor_parts)}.")
    roi_definition = str(config.get("roi_definition") or config.get("boundary_definition") or "").strip()
    if roi_definition:
        lines.append(f"- ROI definition: {roi_definition}.")
    include_regions = _string_list(config.get("include"))
    if include_regions:
        lines.append(f"- Include in ROI: {', '.join(include_regions)}.")
    exclude_regions = _string_list(config.get("exclude"))
    if exclude_regions:
        lines.append(f"- Exclude from ROI: {', '.join(exclude_regions)}.")
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
        lines.append(f"- Spatial priors (soft hints, not hard constraints): {', '.join(spatial_priors)}.")
    sanity_checks = _string_list(config.get("sanity_checks"))
    if sanity_checks:
        lines.append(f"- Sanity checks: {', '.join(sanity_checks)}.")
    parent = parent_grounding(parent_output)
    if parent.get("bbox"):
        lines.append(f"- Parent bbox: {parent['bbox']}.")
    return "\n".join(lines)


def _grounding_task_contract(
    *,
    target_label: str,
    step: dict[str, Any],
    parent_bbox: list[float] | None,
    relationship: str,
) -> dict[str, str]:
    tool_type = str((step.get("tool_config") or {}).get("tool_type") or "").strip().lower()
    relation = _normalize_relation_name(relationship)
    if parent_bbox and relation:
        task_kind = "localize_relative_region"
    elif tool_type == "evidence_vlm":
        task_kind = "locate_primary_target"
    else:
        task_kind = "localize_supporting_evidence"
    if relation in {"inside_parent", "within_parent", "part_of_parent", "deep_to_parent", "posterior_to_parent", "adjacent_to_parent", "overlaps_parent"}:
        target_scope = "relative_region"
    else:
        target_scope = str((step.get("target_scope") or (step.get("tool_config") or {}).get("target_scope") or "").strip() or "entity_or_local_region")
    evidence_mode = str((step.get("evidence_mode") or (step.get("tool_config") or {}).get("evidence_mode") or "").strip() or "boundary_points")
    return {
        "task_kind": task_kind,
        "target_scope": target_scope,
        "relationship": relation or "none",
        "evidence_mode": evidence_mode,
        "target_label": target_label,
    }


def _orientation(value: list[float], other: list[float], third: list[float]) -> int:
    cross = (other[1] - value[1]) * (third[0] - other[0]) - (other[0] - value[0]) * (third[1] - other[1])
    if abs(cross) < 1e-9:
        return 0
    return 1 if cross > 0 else 2


def _on_segment(value: list[float], other: list[float], third: list[float]) -> bool:
    return (
        min(value[0], third[0]) - 1e-9 <= other[0] <= max(value[0], third[0]) + 1e-9
        and min(value[1], third[1]) - 1e-9 <= other[1] <= max(value[1], third[1]) + 1e-9
    )


def _segments_intersect(a1: list[float], a2: list[float], b1: list[float], b2: list[float]) -> bool:
    o1 = _orientation(a1, a2, b1)
    o2 = _orientation(a1, a2, b2)
    o3 = _orientation(b1, b2, a1)
    o4 = _orientation(b1, b2, a2)
    if o1 != o2 and o3 != o4:
        return True
    if o1 == 0 and _on_segment(a1, b1, a2):
        return True
    if o2 == 0 and _on_segment(a1, b2, a2):
        return True
    if o3 == 0 and _on_segment(b1, a1, b2):
        return True
    if o4 == 0 and _on_segment(b1, a2, b2):
        return True
    return False


def _has_self_intersection(points: list[list[float]]) -> bool:
    total = len(points)
    if total < 4:
        return False
    edges = [(points[index], points[(index + 1) % total]) for index in range(total)]
    for index, first in enumerate(edges):
        for other_index in range(index + 1, total):
            if other_index == index:
                continue
            if other_index == (index + 1) % total:
                continue
            if index == 0 and other_index == total - 1:
                continue
            second = edges[other_index]
            if _segments_intersect(first[0], first[1], second[0], second[1]):
                return True
    return False


def _boundary_anchor_checks(points: list[list[float]]) -> list[str]:
    failed: list[str] = []
    if len(points) < 4:
        return failed
    top_index = min(range(len(points)), key=lambda index: (points[index][1], points[index][0]))
    if top_index != 0:
        failed.append("first_point_not_topmost")
    centroid = polygon_centroid(points)
    quadrants: set[tuple[int, int]] = set()
    for point in points:
        x_side = 1 if point[0] >= centroid[0] else -1
        y_side = 1 if point[1] >= centroid[1] else -1
        quadrants.add((x_side, y_side))
    if len(quadrants) < 4:
        failed.append("boundary_quadrant_coverage_incomplete")
    return failed


def _boundary_angle_checks(points: list[list[float]]) -> list[str]:
    failed: list[str] = []
    centroid = polygon_centroid(points)
    angles: list[float] = []
    for point in points:
        angle = math.atan2(point[1] - centroid[1], point[0] - centroid[0])
        if angle < 0:
            angle += 2 * math.pi
        angles.append(angle)
    if not angles:
        return failed
    ordered = sorted(angles)
    gaps = [ordered[index + 1] - ordered[index] for index in range(len(ordered) - 1)]
    gaps.append((ordered[0] + 2 * math.pi) - ordered[-1])
    max_gap = max(gaps)
    if max_gap > math.pi * 0.85:
        failed.append("boundary_angle_coverage_incomplete")
    signed_area = polygon_signed_area(points)
    if signed_area >= 0:
        failed.append("boundary_not_clockwise")
    return failed


def _boundary_global_prompt(
    *,
    target_label: str,
    step: dict[str, Any],
    parent_bbox: list[float] | None,
    relationship: str,
    views: list[HarnessView],
) -> str:
    contract = _grounding_task_contract(
        target_label=target_label,
        step=step,
        parent_bbox=parent_bbox,
        relationship=relationship,
    )
    parent_text = f"- parent_bbox: {parent_bbox}" if parent_bbox else "- parent_bbox: none"
    selectable_views = [view for view in views if view.selectable]
    image_views = [view for view in views if view.data_url]
    preferred_view = "coordinate-full" if any(view.name == "coordinate-full" for view in selectable_views) else selectable_views[0].name
    view_names = {view.name for view in selectable_views}
    if {"original-full", "coordinate-full"}.issubset(view_names):
        coordinate_guidance = (
            "The attached images are two views of the same full image with identical dimensions and identical normalized coordinates.\n"
            "Use original-full to recognize the target. Use coordinate-full only to calibrate x/y locations.\n"
            "Return selected_view=\"coordinate-full\" and trace boundary_points in this full-image coordinate frame; do not use crop-local or display-local coordinates."
        )
    elif "coordinate-full" in view_names:
        coordinate_guidance = (
            "The attached image is the full image with coordinate tick marks.\n"
            "Use it to recognize the target and calibrate x/y locations in the same full-image coordinate frame.\n"
            "Trace boundary_points in this full-image coordinate frame; do not use crop-local or display-local coordinates."
        )
    else:
        coordinate_guidance = (
            "The attached image is the original full image.\n"
            "Trace boundary_points in this full-image coordinate frame; do not use crop-local or display-local coordinates."
        )
    view_lines = "\n".join(f"- {view.name}: {view.label}" for view in selectable_views)
    image_lines = "\n".join(f"- {view.name}: {view.label}" for view in image_views)
    harness_constraints = build_harness_constraints(step, None)
    return dedent(
        f"""
        You localize one visible medical image target for a clinical agent workflow. Do not diagnose.

        Target contract:
        - target_label: {contract['target_label']}
        - step_finding: {step.get('finding') or ''}
        - step_action: {step.get('action') or ''}
        - task_kind: {contract['task_kind']}
        - target_scope: {contract['target_scope']}
        - relationship: {contract['relationship']}
        {parent_text}

        Views:
        {view_lines}

        Attached images:
        {image_lines}

        {coordinate_guidance}

        ROI contract:
        {harness_constraints or "- No additional ROI constraints supplied."}

        Single-pass procedure:
        - Use the image to translate target_label into one visible physical target. Do not localize a diagnosis word directly.
        - If step_finding describes an attribute but target_label names the parent entity, segment the parent entity boundary rather than tracing only the attribute cue.
        - If a target_anchor is supplied in the ROI contract, treat it as an approximate instance-selection cue.
        - target_anchor must not clip, shrink, or replace the final contour; if the visible target extends beyond the anchor bbox, trace the full visible target boundary.
        - If the approximate anchor slightly conflicts with the visible target boundary, trust the image boundary while keeping the same target instance.
        - step_action gives context only; do not expand the ROI to additional concepts mentioned there.
        - Before outputting coordinates, state the concrete target in target_understanding and the exact contour rule in boundary_definition.
        - The contour rule must prioritize the outermost complete visible target envelope over the most salient internal core.
        - Exclude every region listed in the ROI contract even if it is visually adjacent to the target.
        - Apply exclusions only to separate non-target regions; do not use exclusions to cut off a continuous low-contrast part of the requested target.
        - Select one coherent target body or evidence region, not scattered hints or multiple disconnected candidates.
        - If parent_bbox is provided, satisfy the relationship before tracing the target.
        - Spatial priors are secondary hints. If a prior conflicts with visible evidence, trust the image.

        {_modality_artifact_protocol()}

        Return ONLY JSON:
        {{
          "selected_view": "{preferred_view}",
          "conclusion": "localized|not_visible|uncertain",
          "confidence": 0.0,
          "target_understanding": "the concrete physical target you will segment",
          "boundary_definition": "the exact visible boundary you traced",
          "excluded_regions": ["region deliberately excluded from ROI"],
          "rationale": "short visual reason",
          "boundary_points": [[x, y], [x, y]],
          "positive_point": [x, y],
          "coarse_bbox": [x1, y1, x2, y2]
        }}

        Rules:
        - selected_view must be "{preferred_view}".
        - selected_view must be exactly one of: {', '.join(view.name for view in selectable_views)}.
        - Coordinate convention: x increases left to right; y increases top to bottom; [0,0] is the top-left corner; [1,1] is the bottom-right corner.
        - boundary_points must be normalized floats in [0, 1] relative to the selected_view image.
        - positive_point must be a normalized point clearly inside the same target.
        - coarse_bbox must tightly cover the same target and all returned boundary points.
        - target_understanding and boundary_definition are mandatory and must be specific to this image.
        - excluded_regions must list visually plausible confounders that were deliberately excluded; use [] only when no confounder is visible.
        {_segmentation_boundary_rules()}
        - Do not point to labels, ruler marks, measurement text, caliper text, or empty background.
        - Do not output mask rows or a point-only answer.
        """
    ).strip()


def _bbox_global_prompt(
    *,
    target_label: str,
    step: dict[str, Any],
    parent_bbox: list[float] | None,
    relationship: str,
    views: list[HarnessView],
) -> str:
    contract = _grounding_task_contract(
        target_label=target_label,
        step=step,
        parent_bbox=parent_bbox,
        relationship=relationship,
    )
    parent_text = f"- parent_bbox: {parent_bbox}" if parent_bbox else "- parent_bbox: none"
    selectable_views = [view for view in views if view.selectable]
    preferred_view = "coordinate-full" if any(view.name == "coordinate-full" for view in selectable_views) else selectable_views[0].name
    view_names = {view.name for view in selectable_views}
    if {"original-full", "coordinate-full"}.issubset(view_names):
        coordinate_guidance = (
            "The attached views share the same full-image coordinate frame.\n"
            "Use original-full to recognize the evidence region and coordinate-full only to calibrate the bbox coordinates."
        )
    elif "coordinate-full" in view_names:
        coordinate_guidance = (
            "The attached image is the full image with coordinate tick marks.\n"
            "Use it to recognize the evidence region and calibrate the bbox coordinates."
        )
    else:
        coordinate_guidance = (
            "The attached image is the original full image.\n"
            "Use it to recognize the evidence region and estimate normalized bbox coordinates."
        )
    view_lines = "\n".join(f"- {view.name}: {view.label}" for view in selectable_views)
    return dedent(
        f"""
        You are the executor-side grounding model for a clinical agent workflow.
        You are not diagnosing. You are executing one qualitative evidence localization task.

        Task contract:
        - target_label: {contract['target_label']}
        - step_finding: {step.get('finding') or ''}
        - step_action: {step.get('action') or ''}
        - task_kind: qualitative_evidence_check
        - target_scope: {contract['target_scope']}
        - relationship: {contract['relationship']}
        - evidence_mode: bbox_only
        - output_contract: selected_view_plus_bbox
        - coordinate_frame: normalized coordinates of the selected view
        {parent_text}

        Coordinate view:
        {view_lines}

        {coordinate_guidance}

        Evidence bbox principle:
        - This is not a segmentation task.
        - Draw one tight bounding box around the single most relevant visual evidence region for this qualitative finding.
        - If the step checks an attribute of a parent target, box the visible subregion or whole parent area that supports the conclusion.
        - Localize the concrete visual evidence for step_finding, not the whole image and not an abstract diagnosis label.
        - Do not output boundary_points, polygons, masks, point markers, or multiple boxes.

        Return ONLY JSON:
        {{
          "selected_view": "{preferred_view}",
          "conclusion": "Yes|No|Uncertain|not_visible",
          "confidence": 0.0,
          "rationale": "short visual reason tied to the boxed region",
          "bbox": [x1, y1, x2, y2]
        }}

        Rules:
        - Prefer selected_view="{preferred_view}" because it has the coordinate guide; the coordinate frame is identical to original-full.
        - selected_view must be exactly one of: {', '.join(view.name for view in selectable_views)}.
        - bbox must be normalized floats in [0, 1] relative to the selected_view image.
        - bbox must be tight enough to let a human check the evidence, but large enough to include the relevant visible context.
        - If multiple candidate evidence regions exist, choose the dominant one most relevant to target_label.
        - Do not point to labels, ruler marks, measurement text, caliper text, or empty background.
        {build_harness_constraints(step, None)}
        """
    ).strip()


def _extract_bbox_object(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("BBox grounding response must be a JSON object.")
    nested = payload.get("grounding") if isinstance(payload.get("grounding"), dict) else {}
    return {
        "bbox": payload.get("bbox", payload.get("coarse_bbox", nested.get("bbox", nested.get("coarse_bbox")))),
        "selected_view": payload.get("selected_view", nested.get("selected_view")),
        "conclusion": payload.get("conclusion", ""),
        "confidence": payload.get("confidence", nested.get("confidence")),
        "rationale": payload.get("rationale", nested.get("rationale", "")),
    }


def _normalize_bbox_candidate(payload: dict[str, Any], *, views: list[HarnessView]) -> dict[str, Any]:
    obj = _extract_bbox_object(payload)
    selected_view = _resolve_selected_view(obj.get("selected_view"), views)
    local_bbox = normalize_bbox(obj.get("bbox"))
    top_left = map_point_from_view([local_bbox[0], local_bbox[1]], selected_view)
    bottom_right = map_point_from_view([local_bbox[2], local_bbox[3]], selected_view)
    bbox = normalize_bbox([top_left[0], top_left[1], bottom_right[0], bottom_right[1]])
    return {
        "conclusion": str(obj.get("conclusion") or "").strip() or "Uncertain",
        "confidence": _require_confidence(obj, label="BBox grounding candidate"),
        "rationale": str(obj.get("rationale") or "").strip(),
        "selected_view": selected_view.name,
        "selected_view_label": selected_view.label,
        "selected_view_bounds": list(selected_view.bounds) if selected_view.bounds else [0.0, 0.0, 1.0, 1.0],
        "local_bbox": local_bbox,
        "bbox": bbox,
    }


def _validate_bbox_candidate(
    *,
    candidate: dict[str, Any],
    relationship: str,
    parent_bbox: list[float] | None,
) -> dict[str, Any]:
    failed: list[str] = []
    warnings: list[str] = []
    bbox = candidate["bbox"]
    bbox_width = bbox[2] - bbox[0]
    bbox_height = bbox[3] - bbox[1]
    bbox_area = bbox_width * bbox_height
    if bbox_width < 0.005:
        failed.append("bbox_width_too_small")
    if bbox_height < 0.005:
        failed.append("bbox_height_too_small")
    if bbox_area < 0.00002:
        failed.append("bbox_area_too_small")
    if bbox_area > 0.85:
        failed.append("bbox_area_too_large")
    if str(candidate.get("conclusion") or "").strip().lower() == "not_visible":
        failed.append("target_not_visible")
    if parent_bbox:
        relation = _normalize_relation_name(relationship)
        intersection_width = max(0.0, min(bbox[2], parent_bbox[2]) - max(bbox[0], parent_bbox[0]))
        intersection_height = max(0.0, min(bbox[3], parent_bbox[3]) - max(bbox[1], parent_bbox[1]))
        intersection_area = intersection_width * intersection_height
        if relation in {"inside_parent", "within_parent", "part_of_parent", "same_target", "same_parent_target"}:
            if not (
                parent_bbox[0] <= bbox[0] <= bbox[2] <= parent_bbox[2]
                and parent_bbox[1] <= bbox[1] <= bbox[3] <= parent_bbox[3]
            ):
                failed.append("bbox_not_inside_parent")
        if relation in {"adjacent_to_parent", "overlaps_parent"} and intersection_area <= 0:
            failed.append("bbox_not_touching_parent")
        if relation in {"deep_to_parent", "posterior_to_parent"}:
            if bbox[3] <= parent_bbox[3]:
                failed.append("bbox_not_deep_to_parent")
            if intersection_width <= 0:
                failed.append("bbox_not_horizontally_aligned_with_parent")
        warnings.append(f"bbox_parent_overlap_area:{intersection_area:.6f}")
    return {
        "valid": not failed,
        "failed_checks": failed,
        "warnings": warnings,
        "area_ratio_image": round(bbox_area, 6),
    }


def _validate_lightweight_candidate(
    *,
    context: HarnessImage,
    candidate: dict[str, Any],
    relationship: str,
    parent_bbox: list[float] | None,
    parent: dict[str, Any] | None = None,
) -> dict[str, Any]:
    failed: list[str] = []
    warnings: list[str] = []
    points = candidate["boundary_points"]
    bbox = candidate["bbox"]
    positive_point = candidate["positive_point"]
    coarse_bbox = candidate["coarse_bbox"]
    raw_point_count = int(candidate.get("raw_boundary_point_count") or len(points))
    candidate_mask = _mask_from_polygon_points(width=context.width, height=context.height, points=points)
    candidate_area_px = int(np.count_nonzero(candidate_mask))
    mask_component_count = int(candidate.get("mask_component_count") or 0)
    if mask_component_count > 1:
        warnings.append(f"segmentation_has_multiple_components:{mask_component_count}")
    if float(candidate.get("mask_area_ratio_image") or 0.0) <= 0.0:
        failed.append("segmentation_mask_empty")

    if raw_point_count < 8:
        failed.append(f"insufficient_raw_boundary_points:received_{raw_point_count}")
    elif raw_point_count < 24:
        warnings.append(f"raw_boundary_point_density:received_{raw_point_count}")
    if len(points) != REQUIRED_BOUNDARY_POINT_COUNT:
        failed.append(f"normalized_boundary_point_count_invalid:received_{len(points)}")
    unique_points = {(round(point[0], 4), round(point[1], 4)) for point in points}
    if len(unique_points) < 8:
        failed.append("boundary_points_not_diverse")
    failed.extend(_boundary_anchor_checks(points))
    failed.extend(_boundary_angle_checks(points))
    if _has_self_intersection(points):
        failed.append("boundary_self_intersection")

    positive_x = int(round(positive_point[0] * max(1, context.width - 1)))
    positive_y = int(round(positive_point[1] * max(1, context.height - 1)))
    if not inside_bbox(positive_point, bbox):
        failed.append("positive_point_outside_boundary_bbox")
    if 0 <= positive_y < candidate_mask.shape[0] and 0 <= positive_x < candidate_mask.shape[1]:
        if candidate_mask[positive_y, positive_x] == 0:
            warnings.append("positive_point_outside_boundary_polygon")
    else:
        failed.append("positive_point_outside_image")

    area = polygon_area(points)
    area_ratio_image = float(candidate_area_px / max(1, context.width * context.height))
    if candidate_area_px <= 3 or area_ratio_image < 0.00002:
        failed.append("target_area_too_small")
    if area_ratio_image > 0.85:
        failed.append("target_area_too_large")
    bbox_width = bbox[2] - bbox[0]
    bbox_height = bbox[3] - bbox[1]
    if bbox_width < 0.01:
        failed.append("target_width_too_small")
    if bbox_height < 0.01:
        failed.append("target_height_too_small")
    fill_ratio = area_ratio_image / max(bbox_width * bbox_height, 1e-6)
    if fill_ratio < 0.15:
        failed.append("boundary_bbox_fill_too_sparse")
    tolerance = 0.02
    if (
        bbox[0] < coarse_bbox[0] - tolerance
        or bbox[1] < coarse_bbox[1] - tolerance
        or bbox[2] > coarse_bbox[2] + tolerance
        or bbox[3] > coarse_bbox[3] + tolerance
    ):
        failed.append("coarse_bbox_does_not_cover_boundary")
    coarse_consistency_iou = bbox_iou(bbox, coarse_bbox)
    if coarse_consistency_iou < 0.25:
        failed.append("coarse_bbox_not_consistent_with_boundary")
    elif coarse_consistency_iou < 0.5:
        warnings.append(f"coarse_bbox_boundary_iou_low:{coarse_consistency_iou:.4f}")

    parent = parent or {}
    if parent_bbox:
        relation = _normalize_relation_name(relationship)
        parent_mask = _parent_mask_from_grounding(width=context.width, height=context.height, parent=parent)
        intersection_width = max(0.0, min(bbox[2], parent_bbox[2]) - max(bbox[0], parent_bbox[0]))
        intersection_height = max(0.0, min(bbox[3], parent_bbox[3]) - max(bbox[1], parent_bbox[1]))
        intersection_area = intersection_width * intersection_height
        bbox_area = max((bbox[2] - bbox[0]) * (bbox[3] - bbox[1]), 1e-6)
        parent_area = max((parent_bbox[2] - parent_bbox[0]) * (parent_bbox[3] - parent_bbox[1]), 1e-6)
        overlap_ratio = intersection_area / min(bbox_area, parent_area)
        horizontal_overlap = max(0.0, min(bbox[2], parent_bbox[2]) - max(bbox[0], parent_bbox[0]))
        parent_width = max(parent_bbox[2] - parent_bbox[0], 1e-6)
        if parent_mask is not None:
            inside_mask = cv2.bitwise_and(candidate_mask, parent_mask)
            inside_area = int(np.count_nonzero(inside_mask))
            parent_mask_area = int(np.count_nonzero(parent_mask))
            validation_inside_fraction = float(inside_area / max(1, candidate_area_px))
            validation_area_ratio_to_parent = float(candidate_area_px / max(1, parent_mask_area))
            validation_iou = _mask_iou(candidate_mask, parent_mask)
            if relation in {"inside_parent", "within_parent", "part_of_parent"}:
                if validation_inside_fraction < 0.98:
                    failed.append("mask_not_inside_parent")
                if not _centroid_inside_parent(candidate_mask, parent_mask):
                    failed.append("mask_centroid_outside_parent")
            if relation in {"same_target", "same_parent_target"} and validation_iou < 0.45:
                failed.append("mask_not_overlapping_parent_target")
            if relation in {"adjacent_to_parent", "overlaps_parent"} and inside_area <= 0:
                failed.append("mask_not_touching_parent")
            warnings.extend(
                [
                    f"inside_parent_fraction:{validation_inside_fraction:.4f}",
                    f"area_ratio_to_parent:{validation_area_ratio_to_parent:.4f}",
                    f"mask_iou_to_parent:{validation_iou:.4f}",
                ]
            )
        if relation in {"inside_parent", "within_parent", "part_of_parent"}:
            for boundary_point in points:
                if not inside_bbox(boundary_point, parent_bbox):
                    failed.append("boundary_outside_parent")
                    break
            if not (
                parent_bbox[0] <= bbox[0] <= bbox[2] <= parent_bbox[2]
                and parent_bbox[1] <= bbox[1] <= bbox[3] <= parent_bbox[3]
            ):
                failed.append("target_not_inside_parent")
        if relation in {"deep_to_parent", "posterior_to_parent"}:
            if bbox[1] < parent_bbox[1]:
                warnings.append("target_extends_above_parent")
            if bbox[3] <= parent_bbox[3]:
                failed.append("target_not_deep_to_parent")
            if horizontal_overlap < 0.2 * parent_width:
                failed.append("target_not_horizontally_aligned_with_parent")
        if relation in {"same_target", "same_parent_target"} and overlap_ratio < 0.5:
            failed.append("target_not_overlapping_parent_target")
        if relation in {"adjacent_to_parent", "overlaps_parent"} and intersection_area <= 0:
            failed.append("target_not_touching_parent")

    return {
        "valid": not failed,
        "failed_checks": failed,
        "warnings": warnings,
        "area_ratio_image": round(area_ratio_image, 6),
        "bbox_fill_ratio": round(fill_ratio, 6),
        "coarse_bbox_boundary_iou": round(coarse_consistency_iou, 6),
        "area_px": candidate_area_px,
        "analysis_image_size": [context.width, context.height],
    }


def run_vlm_grounding_harness(
    *,
    request_json: JsonImageRequester,
    image_payload: dict[str, str],
    step: dict[str, Any],
    target_label: str,
    parent_output: dict[str, Any] | None = None,
    n_samples: int = 3,
    repair_rounds: int = 1,
    require_boundary: bool = True,
) -> dict[str, Any]:
    del n_samples, repair_rounds, require_boundary
    context = prepare_harness_image(image_payload)
    parent = parent_grounding(parent_output)
    parent_bbox = normalize_bbox(parent["bbox"]) if parent.get("bbox") else None
    relationship = str(step.get("relationship") or "")
    views = _build_grounding_views(context, parent_bbox=parent_bbox, relationship=relationship)
    image_views = [view for view in views if view.data_url]
    candidate = _normalize_candidate(
        request_json(
            [{"name": view.name, "label": view.label, "data_url": view.data_url} for view in image_views],
            _boundary_global_prompt(
                target_label=target_label,
                step=step,
                parent_bbox=parent_bbox,
                relationship=relationship,
                views=views,
            ),
            2200,
            "You localize one medical image target for downstream agent execution. Return only strict JSON.",
        ),
        views=views,
        context=context,
    )
    validation = _validate_lightweight_candidate(
        context=context,
        candidate=candidate,
        relationship=relationship,
        parent_bbox=parent_bbox,
        parent=parent,
    )
    if str(candidate.get("conclusion") or "").strip().lower() == "not_visible":
        validation["valid"] = False
        validation.setdefault("failed_checks", []).append("target_not_visible")
    if not validation["valid"]:
        raise ValueError(f"Grounding validation failed: {', '.join(validation.get('failed_checks') or ['unknown'])}")
    grounding = {
        "bbox": candidate["bbox"],
        "boundary_points": candidate["boundary_points"],
        "mask_area_ratio_image": candidate.get("mask_area_ratio_image"),
        "mask_bbox": candidate.get("mask_bbox", candidate["bbox"]),
    }
    return {
        "conclusion": candidate["conclusion"],
        "confidence": candidate["confidence"],
        "rationale": candidate["rationale"],
        "target_understanding": candidate.get("target_understanding", ""),
        "boundary_definition": candidate.get("boundary_definition", ""),
        "excluded_regions": candidate.get("excluded_regions", []),
        "grounding": grounding,
        "validation": validation,
        "harness": {
            "enabled": True,
            "method": "vlm_boundary_full_image_one_shot",
            "coordinate_frame": "analysis_image_normalized",
            "analysis_image_size": [context.width, context.height],
            "original_image_size": [context.original_width or context.width, context.original_height or context.height],
            "analysis_scale": context.analysis_scale,
            "view_media_type": context.media_type,
            "target_label": target_label,
            "target_understanding": candidate.get("target_understanding", ""),
            "boundary_definition": candidate.get("boundary_definition", ""),
            "excluded_regions": candidate.get("excluded_regions", []),
            "selected_view": candidate["selected_view"],
            "selected_view_label": candidate["selected_view_label"],
            "selected_view_bounds": candidate["selected_view_bounds"],
            "mask_size": candidate.get("mask_size", []),
            "mask_spans": candidate.get("mask_spans", []),
            "mask_component_count": candidate.get("mask_component_count", 0),
            "mask_area_ratio_image": candidate.get("mask_area_ratio_image", 0.0),
            "raw_boundary_point_count": candidate.get("raw_boundary_point_count", len(candidate.get("boundary_points", []))),
            "local_mask_foreground_pixels": candidate.get("local_mask_foreground_pixels", 0),
            "local_boundary_points": candidate.get("local_boundary_points", []),
            "positive_point": candidate.get("positive_point"),
            "coarse_bbox": candidate.get("coarse_bbox"),
            "task_kind": _grounding_task_contract(
                target_label=target_label,
                step=step,
                parent_bbox=parent_bbox,
                relationship=relationship,
            )["task_kind"],
            "view_names": [view.name for view in views if view.selectable],
            "view_labels": [view.label for view in views],
            "image_message_names": [view.name for view in image_views],
            "parent_focus_used": bool(parent_bbox is not None),
            "validation_summary": {
                "failed_checks": validation.get("failed_checks", []),
                "warnings": validation.get("warnings", []),
            },
        },
    }


def run_vlm_bbox_grounding_harness(
    *,
    request_json: JsonImageRequester,
    image_payload: dict[str, str],
    step: dict[str, Any],
    target_label: str,
    parent_output: dict[str, Any] | None = None,
    n_samples: int = 3,
    repair_rounds: int = 1,
) -> dict[str, Any]:
    del n_samples, repair_rounds
    context = prepare_harness_image(image_payload)
    parent = parent_grounding(parent_output)
    parent_bbox = normalize_bbox(parent["bbox"]) if parent.get("bbox") else None
    relationship = str(step.get("relationship") or "")
    views = _build_grounding_views(context, parent_bbox=parent_bbox, relationship=relationship)
    image_views = [view for view in views if view.data_url]
    candidate = _normalize_bbox_candidate(
        request_json(
            [{"name": view.name, "label": view.label, "data_url": view.data_url} for view in image_views],
            _bbox_global_prompt(
                target_label=target_label,
                step=step,
                parent_bbox=parent_bbox,
                relationship=relationship,
                views=views,
            ),
            1200,
            "You localize one medical image evidence region as a bbox. Return only strict JSON.",
        ),
        views=views,
    )
    validation = _validate_bbox_candidate(
        candidate=candidate,
        relationship=relationship,
        parent_bbox=parent_bbox,
    )
    if not validation["valid"]:
        raise ValueError(f"BBox grounding validation failed: {', '.join(validation.get('failed_checks') or ['unknown'])}")
    return {
        "conclusion": candidate["conclusion"],
        "confidence": candidate["confidence"],
        "rationale": candidate["rationale"],
        "grounding": {"bbox": candidate["bbox"]},
        "validation": validation,
        "harness": {
            "enabled": True,
            "method": "vlm_bbox_full_image_one_shot",
            "coordinate_frame": "analysis_image_normalized",
            "analysis_image_size": [context.width, context.height],
            "original_image_size": [context.original_width or context.width, context.original_height or context.height],
            "analysis_scale": context.analysis_scale,
            "view_media_type": context.media_type,
            "target_label": target_label,
            "selected_view": candidate["selected_view"],
            "selected_view_label": candidate["selected_view_label"],
            "selected_view_bounds": candidate["selected_view_bounds"],
            "local_bbox": candidate["local_bbox"],
            "view_names": [view.name for view in views if view.selectable],
            "image_message_names": [view.name for view in image_views],
            "parent_focus_used": bool(parent_bbox is not None),
            "validation_summary": {
                "failed_checks": validation.get("failed_checks", []),
                "warnings": validation.get("warnings", []),
            },
        },
    }


def normalize_grounding_payload(
    payload: dict[str, Any],
    *,
    relationship: str = "",
    parent_bbox: list[float] | None = None,
) -> dict[str, Any]:
    context = HarnessImage(
        image=Image.new("RGB", (100, 100), "black"),
        data_url="",
        media_type="image/png",
        width=100,
        height=100,
    )
    candidate = _normalize_candidate(
        {"selected_view": payload.get("selected_view", "full-image"), **payload},
        views=[HarnessView(name="full-image", label="View 1: original full image", data_url="", bounds=None)],
        context=context,
    )
    validation = validate_grounding(
        grounding={
            "bbox": candidate["bbox"],
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
    boundary_points = normalize_boundary_points(grounding["boundary_points"])

    relation = _normalize_relation_name(relationship)
    if relation == "inside_parent" and parent_bbox:
        for boundary_point in boundary_points:
            if not inside_bbox(boundary_point, parent_bbox):
                failed_checks.append("boundary_outside_parent_bbox")
                break
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
        area = float(geometry.get("mask_area_ratio_image")) if geometry.get("mask_area_ratio_image") not in (None, "") else polygon_area(points)
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
