"""Test setup: no LLM calls, temporary database and sign gallery."""
from __future__ import annotations

import copy
import importlib
import json
import os

os.environ["SANAD_LOG_FILE"] = "none"   # tests log to the console only, not src/logger/logs/sanad.log

import numpy as np
import pytest

from src.agent.core import config as config_module
from src.agent.inference import llm, sign_model


@pytest.fixture(autouse=True)
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")   # rules only, never call Claude in tests
    llm.get_llm.cache_clear()
    settings = copy.deepcopy(config_module.get_config())
    settings["database"]["path"] = str(tmp_path / "sanad.db")
    settings["signs"]["gallery_dir"] = str(tmp_path / "gallery")
    for module in ("src.agent.core.config", "src.database.db", "src.agent.job_agent.graph",
                   "src.agent.job_agent.tools.search_jobs", "src.agent.interview_agent.graph",
                   "src.agent.interview_agent.tools.compose_sentence", "src.agent.inference.sign_model"):
        # import_module returns the module itself; a dotted string would hit the same-named
        # function that tools/__init__.py exports (e.g. tools.search_jobs).
        monkeypatch.setattr(importlib.import_module(module), "get_config", lambda: settings)
    sign_model.load_gallery.cache_clear()
    yield settings
    sign_model.load_gallery.cache_clear()


def hand_shape(kind: str, frames: int = 12) -> np.ndarray:
    """Synthetic 21-point hand whose *shape* changes over time (position/size are normalised away):
    'open' fans out, 'fist' flattens into a line, 'wave' rotates back and forth."""
    t = np.linspace(0, 1, frames)[:, None]
    base = np.linspace(0, 1, 21)[None, :]
    if kind == "open":
        angles = base * np.pi * (0.3 + 0.7 * t)
        x, y = np.cos(angles), np.sin(angles)
    elif kind == "fist":
        angles = base * np.pi
        x, y = np.cos(angles), np.sin(angles) * (1.0 - 0.9 * t)
    else:  # wave
        angles = base * np.pi + 1.2 * np.sin(6 * t)
        x, y = np.cos(angles), np.sin(angles)
    x, y = np.broadcast_arrays(x, y)
    return np.stack([x, y], axis=-1).astype(np.float32)


@pytest.fixture
def gallery(isolated, tmp_path):
    gallery_dir = tmp_path / "gallery"
    gallery_dir.mkdir()
    labels = {"10": "أنا", "20": "خبرة", "30": "بيانات"}
    (gallery_dir / "labels.json").write_text(json.dumps(labels, ensure_ascii=False), encoding="utf-8")
    for label_id, kind in (("10", "open"), ("20", "fist"), ("30", "wave")):
        np.save(gallery_dir / f"{label_id}__0.npy", hand_shape(kind) * 0.2 + 0.5)
    sign_model.load_gallery.cache_clear()
    return labels
