"""Build the sign gallery (src/data/sign_gallery/) from the Saudi Sign Language dataset.

For each interview word, extracts MediaPipe hand keypoints from its dataset videos and saves
them as .npy files that inference/sign_model.py matches against.

Needs:  pip install mediapipe opencv-python   (mediapipe has no wheel for Python 3.13+ yet:
        use a Python 3.12 venv for this step only)
        git lfs pull --include "src/data/dataset/videos/<category>/*"   (the videos are LFS files)

Usage (from the project root):
    python -m src.agent.inference.build_gallery --words أنا خبرة عمل فريق بيانات
    python -m src.agent.inference.build_gallery --words-file src/data/sign_gallery/vocabulary.txt

Keypoint layout (the browser must send the same): per frame 42 points = left hand 21 + right hand
21 (MediaPipe Hands landmarks, x/y in 0-1 image coordinates); a missing hand is 21 zero points.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np

from src.agent.core.config import get_config, get_secret, project_path
from src.logger import get_logger

log = get_logger("inference.build_gallery")

POINTS_PER_HAND = 21


def _is_lfs_pointer(path: Path) -> bool:
    if path.stat().st_size > 1024:
        return False
    return path.read_bytes().startswith(b"version https://git-lfs")


def extract_keypoints(video: Path) -> np.ndarray:
    """Return (frames, 42, 2) hand keypoints for one video."""
    import cv2
    import mediapipe as mp

    frames = []
    capture = cv2.VideoCapture(str(video))
    with mp.solutions.hands.Hands(static_image_mode=False, max_num_hands=2,
                                  min_detection_confidence=0.5) as hands:
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            result = hands.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            points = np.zeros((2 * POINTS_PER_HAND, 2), dtype=np.float32)
            for landmarks, handedness in zip(result.multi_hand_landmarks or [],
                                             result.multi_handedness or []):
                side = 0 if handedness.classification[0].label == "Left" else 1
                coords = [(lm.x, lm.y) for lm in landmarks.landmark]
                points[side * POINTS_PER_HAND:(side + 1) * POINTS_PER_HAND] = coords
            frames.append(points)
    capture.release()
    return np.stack(frames) if frames else np.zeros((0, 2 * POINTS_PER_HAND, 2), dtype=np.float32)


def build(words: list[str], max_per_word: int = 3) -> None:
    settings = get_config()["signs"]
    dataset_dir = Path(get_secret("SIGN_DATASET_DIR") or project_path(settings["dataset_dir"]))
    gallery_dir = project_path(settings["gallery_dir"])
    gallery_dir.mkdir(parents=True, exist_ok=True)

    with (dataset_dir / "metadata" / "dataset.csv").open(encoding="utf-8-sig") as f:
        rows = [r for r in csv.DictReader(f) if r["label_ar"].strip() in set(words)]

    labels: dict[str, str] = {}
    counts: dict[str, int] = {}
    for row in rows:
        label_id = row["label_id"]
        if counts.get(label_id, 0) >= max_per_word:
            continue
        video = dataset_dir / "videos" / row["filename"]
        if not video.exists() or _is_lfs_pointer(video):
            log.warning(f"[SKIP] {row['filename']} ({row['label_ar']}): video not downloaded (git lfs pull)")
            continue
        keypoints = extract_keypoints(video)
        if not np.abs(keypoints).sum():
            log.warning(f"[SKIP] {row['filename']} ({row['label_ar']}): no hands detected")
            continue
        np.save(gallery_dir / f"{label_id}__{counts.get(label_id, 0)}.npy", keypoints)
        counts[label_id] = counts.get(label_id, 0) + 1
        labels[label_id] = row["label_ar"].strip()
        log.info(f"[OK]   {row['filename']} -> {row['label_ar']} ({len(keypoints)} frames)")

    labels_file = gallery_dir / "labels.json"
    existing = json.loads(labels_file.read_text(encoding="utf-8")) if labels_file.exists() else {}
    if labels:
        labels_file.write_text(json.dumps({**existing, **labels}, ensure_ascii=False, indent=2), encoding="utf-8")
    found = {row["label_ar"].strip() for row in rows}
    missing = [w for w in words if w not in found]
    log.info(f"[DONE] {len(labels)} words saved to {gallery_dir}")
    if missing:
        log.warning("[WARN] not in the dataset: %s", " ".join(missing))
    target = settings.get("vocabulary_size")
    if target and len({**existing, **labels}) < target:
        log.warning(f"[WARN] gallery has {len({**existing, **labels})} of {target} words (signs.vocabulary_size)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--words", nargs="*", default=[], help="Arabic labels exactly as in dataset.csv")
    parser.add_argument("--words-file", help="text file with one Arabic label per line")
    parser.add_argument("--max-per-word", type=int, default=3)
    args = parser.parse_args()
    words = list(args.words)
    if args.words_file:
        words += [w.strip() for w in Path(args.words_file).read_text(encoding="utf-8").splitlines() if w.strip()]
    if not words:
        parser.error("give --words or --words-file")
    build(list(dict.fromkeys(words)), args.max_per_word)


if __name__ == "__main__":
    main()
