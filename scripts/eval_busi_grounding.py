from __future__ import annotations

import argparse
import base64
import io
from pathlib import Path
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageOps

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rare_agents.executor import _harness_requester, _resolve_executor_provider
from rare_agents.grounding_harness import _mask_array_from_points, run_vlm_grounding_harness
from rare_agents.service import load_settings


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate BUSI lesion grounding against GT masks.")
    parser.add_argument("--dataset-root", required=True, help="Path to BUSI split directory, e.g. D:\\BUSI\\...\\benign")
    parser.add_argument("--user", default="admin", help="App user whose provider settings should be used.")
    parser.add_argument("--limit", type=int, default=3, help="Number of BUSI images to evaluate.")
    parser.add_argument("--out-dir", default="logs/busi_eval", help="Output directory for overlays and summary.")
    return parser.parse_args()


def _image_payload(image_path: Path) -> dict[str, str]:
    image = Image.open(image_path)
    image = ImageOps.exif_transpose(image).convert("RGB")
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=92, optimize=True)
    data_url = "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")
    return {
        "name": image_path.name,
        "media_type": "image/jpeg",
        "data_url": data_url,
    }


def _mask_union_for_image(image_path: Path) -> np.ndarray:
    stem = image_path.stem
    mask_paths = sorted(image_path.parent.glob(f"{stem}_mask*.png"))
    if not mask_paths:
        raise FileNotFoundError(f"No BUSI mask found for {image_path.name}")
    merged: np.ndarray | None = None
    for mask_path in mask_paths:
        mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
        if mask is None:
            raise ValueError(f"Failed to read mask: {mask_path}")
        _, binary = cv2.threshold(mask, 0, 255, cv2.THRESH_BINARY)
        merged = binary if merged is None else cv2.bitwise_or(merged, binary)
    if merged is None:
        raise ValueError(f"Mask union failed for {image_path.name}")
    return merged


def _iou(first: np.ndarray, second: np.ndarray) -> float:
    intersection = int(np.count_nonzero((first > 0) & (second > 0)))
    union = int(np.count_nonzero((first > 0) | (second > 0)))
    return float(intersection / max(1, union))


def _overlay_image(image_path: Path, pred_mask: np.ndarray, gt_mask: np.ndarray, out_path: Path) -> None:
    image = Image.open(image_path)
    image = ImageOps.exif_transpose(image).convert("RGB")
    canvas = image.copy()
    draw = ImageDraw.Draw(canvas, "RGBA")

    pred_contours, _ = cv2.findContours((pred_mask > 0).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    gt_contours, _ = cv2.findContours((gt_mask > 0).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for contour in gt_contours:
        points = [(int(pt[0][0]), int(pt[0][1])) for pt in contour]
        if len(points) >= 3:
            draw.line(points + [points[0]], fill=(72, 214, 112, 220), width=3)
    for contour in pred_contours:
        points = [(int(pt[0][0]), int(pt[0][1])) for pt in contour]
        if len(points) >= 3:
            draw.line(points + [points[0]], fill=(232, 79, 79, 220), width=3)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_path)


def main() -> None:
    args = _parse_args()
    dataset_root = Path(args.dataset_root)
    out_dir = Path(args.out_dir)
    settings = load_settings(args.user)
    provider = _resolve_executor_provider(settings)
    request_json = _harness_requester(provider)
    image_paths = sorted(
        path
        for path in dataset_root.glob("*.png")
        if "_mask" not in path.stem.lower()
    )[: max(1, int(args.limit))]
    step = {
        "id": 1,
        "action": "Locate the visible breast lesion boundary for downstream quantitative analysis.",
        "finding": "breast lesion boundary",
        "tool_config": {
            "tool_type": "evidence_vlm",
            "evidence_mode": "boundary_points",
            "spatial_priors": [
                "single dominant lesion",
                "within breast parenchyma",
                "dark hypoechoic or anechoic target when visually present",
                "not annotation text",
            ],
            "sanity_checks": [
                "single_connected_component",
                "compact_shape",
                "dark_target_contrast",
                "not_text_annotation",
            ],
        },
    }

    scores: list[tuple[str, float]] = []
    for image_path in image_paths:
        image = Image.open(image_path)
        image = ImageOps.exif_transpose(image).convert("RGB")
        gt_mask = _mask_union_for_image(image_path)
        result = run_vlm_grounding_harness(
            request_json=request_json,
            image_payload=_image_payload(image_path),
            step=step,
            target_label="breast lesion",
        )
        pred_mask = _mask_array_from_points(image.width, image.height, result["grounding"]["boundary_points"])
        score = _iou(pred_mask, gt_mask)
        scores.append((image_path.name, score))
        _overlay_image(image_path, pred_mask, gt_mask, out_dir / f"{image_path.stem}_overlay.png")
        print(
            f"{image_path.name}\tIoU={score:.4f}\t"
            f"bbox={result['grounding']['bbox']}\t"
            f"contrast={result['validation'].get('contrast', {})}\t"
            f"edge={result['validation'].get('edge_alignment', {})}"
        )

    mean_iou = sum(score for _, score in scores) / max(1, len(scores))
    print(f"MEAN_IOU\t{mean_iou:.4f}")


if __name__ == "__main__":
    main()
