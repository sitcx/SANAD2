"""Sign recognition: matches the candidate's hand keypoints against the gallery.

Gallery = keypoints of the interview vocabulary in src/data/sign_gallery/ (signs.gallery_dir).
Method = normalised MediaPipe keypoints + DTW nearest-neighbour (no training).

Gallery layout (written by inference/build_gallery.py):
    sign_gallery/labels.json          {"<label_id>": "<label_ar>", ...}
    sign_gallery/<label_id>__<n>.npy  one example, shape (frames, points, 2|3)

Browser keypoints use the same shape: a list of frames, each a list of [x, y(, z)] points.
"""
from __future__ import annotations

import json
from functools import lru_cache

import numpy as np

from src.agent.core.config import get_config, project_path
from src.logger import get_logger, log_step

log = get_logger("sign_model")


def normalize_keypoints(keypoints) -> np.ndarray:
    """(frames, points, dims) -> (frames, points*2), centred and scaled per frame.

    Removes where the hands are in the camera and how big they look, keeping only the shape.
    Frames with no detected hand (all zeros) are dropped.
    """
    arr = np.asarray(keypoints, dtype=np.float32)
    if arr.ndim == 2:  # already flattened (frames, points*2)
        arr = arr.reshape(arr.shape[0], -1, 2)
    if arr.ndim != 3 or arr.shape[0] == 0:
        raise ValueError(f"expected keypoints shaped (frames, points, dims), got {arr.shape}")
    arr = arr[:, :, :2]  # x, y only: webcam depth is too noisy
    arr = arr[np.abs(arr).sum(axis=(1, 2)) > 0]
    if arr.shape[0] == 0:
        raise ValueError("no frames with detected hands")
    centred = arr - arr.mean(axis=1, keepdims=True)
    scale = np.linalg.norm(centred, axis=2).max(axis=1)[:, None, None]
    centred = centred / np.where(scale > 1e-6, scale, 1.0)
    return centred.reshape(centred.shape[0], -1)


def dtw_distance(a: np.ndarray, b: np.ndarray) -> float:
    """Dynamic-time-warping distance between two sequences, divided by path length."""
    cost = np.linalg.norm(a[:, None, :] - b[None, :, :], axis=2)
    n, m = cost.shape
    acc = np.full((n + 1, m + 1), np.inf, dtype=np.float64)
    acc[0, 0] = 0.0
    for i in range(1, n + 1):
        row = cost[i - 1]
        for j in range(1, m + 1):
            acc[i, j] = row[j - 1] + min(acc[i - 1, j], acc[i, j - 1], acc[i - 1, j - 1])
    return float(acc[n, m] / (n + m))


@lru_cache(maxsize=1)
def load_gallery() -> dict:
    """Load gallery keypoints: {label_id: {"label_ar": str, "examples": [arrays]}}."""
    gallery_dir = project_path(get_config()["signs"]["gallery_dir"])
    labels_file = gallery_dir / "labels.json"
    if not labels_file.exists():
        log.warning("[WARN] sign gallery is empty (%s missing); run inference/build_gallery.py", labels_file)
        return {}
    labels = json.loads(labels_file.read_text(encoding="utf-8"))
    gallery: dict = {}
    for path in sorted(gallery_dir.glob("*.npy")):
        label_id = path.stem.split("__")[0]
        if label_id not in labels:
            continue
        try:
            example = normalize_keypoints(np.load(path))
        except ValueError:
            continue
        entry = gallery.setdefault(label_id, {"label_ar": labels[label_id], "examples": []})
        entry["examples"].append(example)
    log.info("[OK]    sign gallery loaded: %d words", len(gallery))
    return gallery


@log_step(summary=lambda top: f"best={top[0]['label_ar']} score={top[0]['score']}" if top else "no match")
def match_sign(keypoints, top_k: int = 5) -> list[dict]:
    """Return the top_k closest words: [{"label_ar": ..., "score": ...}] (0-1, higher = closer)."""
    gallery = load_gallery()
    if not gallery:
        return []
    query = normalize_keypoints(keypoints)
    best: list[tuple[float, str, str]] = []
    for label_id, entry in gallery.items():
        dists = [dtw_distance(query, ex) for ex in entry["examples"] if ex.shape[1] == query.shape[1]]
        if dists:
            best.append((min(dists), label_id, entry["label_ar"]))
    best.sort()
    return [{"label_id": lid, "label_ar": label, "score": round(1.0 / (1.0 + 4.0 * d), 3)}
            for d, lid, label in best[:top_k]]
