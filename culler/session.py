"""Save / restore a culling session so a folder can be reopened without re-analysing it.

Stored next to the photos as one small JSON file. It holds each photo's analysis numbers, the strictness
setting and every manual override. The photos themselves are never touched.
"""
from __future__ import annotations

import base64
import json
import os
from datetime import datetime
from pathlib import Path

import numpy as np

from .analysis import Photo

FILE_NAME = "i-arrange-session.json"
LEGACY_FILE_NAME = "photo-culler-session.json"  # saved before the rename: still readable
APP_TAGS = ("i-arrange", "PhotoCuller")
FORMAT_VERSION = 1
_METRICS = ("sharp_raw", "has_face", "n_faces", "eyes_hint", "clip_lo", "clip_hi", "mean")


def session_path(folder: str | Path) -> Path:
    return Path(folder) / FILE_NAME


def save(folder: str | Path, photos: list[Photo], strictness: float) -> Path:
    entries = {}
    for p in photos:
        if not p.analyzed:
            continue
        e = {k: getattr(p, k) for k in _METRICS}
        e["error"] = p.error
        e["manual"] = p.manual
        e["manual_reason"] = p.manual_reason
        e["status"] = p.status  # informational: what the user saw when saving
        if p.tiny is not None:
            e["tiny"] = base64.b64encode(np.asarray(p.tiny, dtype=np.float16).tobytes()).decode("ascii")
        entries[p.name] = e
    data = {
        "app": "i-arrange",
        "format": FORMAT_VERSION,
        "saved_at": datetime.now().isoformat(timespec="seconds"),
        "strictness": strictness,
        "photos": entries,
    }
    path = session_path(folder)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data), encoding="utf-8")
    os.replace(tmp, path)  # never leave a half-written session behind
    return path


def load(folder: str | Path) -> dict | None:
    path = session_path(folder)
    if not path.exists():
        path = Path(folder) / LEGACY_FILE_NAME
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("app") not in APP_TAGS or data.get("format") != FORMAT_VERSION or "photos" not in data:
            return None
        return data
    except (OSError, ValueError):
        return None


def apply(photos: list[Photo], data: dict) -> list[Photo]:
    """Fill the loaded photos from a saved session. Returns the photos the session knows nothing about."""
    saved = data["photos"]
    missing = []
    for p in photos:
        e = saved.get(p.name)
        if e is None:
            missing.append(p)
            continue
        for k in _METRICS:
            setattr(p, k, e[k])
        p.error = e.get("error", "") or p.error
        p.manual = e.get("manual")
        p.manual_reason = e.get("manual_reason", "")
        if e.get("tiny"):
            p.tiny = np.frombuffer(base64.b64decode(e["tiny"]), dtype=np.float16).astype(np.float32)
        p.analyzed = True
    return missing


def summary(photos: list[Photo], data: dict) -> tuple[str, int, int]:
    """(saved-at text, photos matched, manual changes) for the 'load saved culling?' prompt."""
    saved = data["photos"]
    matched = [p for p in photos if p.name in saved]
    manual = sum(1 for p in matched if saved[p.name].get("manual"))
    try:
        when = datetime.fromisoformat(data["saved_at"]).strftime("%d %b %Y, %H:%M")
    except (KeyError, ValueError):
        when = "earlier"
    return when, len(matched), manual
