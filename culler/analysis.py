"""Photo analysis: load previews (JPEG / ARW), score technical quality, group similar shots."""
from __future__ import annotations

import io
import sys
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps

IMG_EXTS = {".jpg", ".jpeg", ".arw"}
PRIMARY_ORDER = [".jpg", ".jpeg", ".arw"]  # which file of a RAW+JPEG pair is analysed
ANALYSIS_SIDE = 1200
THUMB_SIDE = 360

# Similar-shot grouping (measured on a real 156-photo shoot: same-moment frames correlate ~0.99,
# different scenes ~0.3-0.5).
GROUP_NCC = 0.88          # consecutive frames must correlate at least this much...
GROUP_ANCHOR_NCC = 0.70   # ...and stay roughly like the first frame, so a chain cannot drift away
GROUP_MAX_GAP_S = 6.0     # ...and be shot within this many seconds of the previous frame

MODEL_NAME = "face_detection_yunet_2023mar.onnx"

_tls = threading.local()


# --------------------------------------------------------------------------- face detection
def _model_path() -> Path | None:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))  # _MEIPASS inside the exe
    p = base / "assets" / "models" / MODEL_NAME
    return p if p.exists() else None


def _yunet():
    """Per-thread YuNet face detector (neural network, handles turned heads), or None if the model is missing."""
    if not hasattr(_tls, "yunet"):
        mp = _model_path()
        _tls.yunet = cv2.FaceDetectorYN.create(str(mp), "", (320, 320), 0.8, 0.3, 500) if mp else None
    return _tls.yunet


def _haar(name: str):
    attr = "haar_" + name
    if not hasattr(_tls, attr):
        setattr(_tls, attr, cv2.CascadeClassifier(cv2.data.haarcascades + name))
    return getattr(_tls, attr)


def detect_faces(rgb: np.ndarray, gray: np.ndarray):
    """Return [(x, y, w, h, landmarks_or_None)]. Falls back to a strict Haar detector without the model."""
    H, W = gray.shape
    det = _yunet()
    out = []
    if det is not None:
        det.setInputSize((W, H))
        _, res = det.detect(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
        for r in (res if res is not None else []):
            x, y, w, h = (int(round(v)) for v in r[:4])
            x, y = max(0, x), max(0, y)
            w, h = min(w, W - x), min(h, H - y)
            if w >= max(28, W // 40) and h >= 28:
                out.append((x, y, w, h, r[4:14].reshape(5, 2)))
    else:
        for (x, y, w, h) in _haar("haarcascade_frontalface_default.xml").detectMultiScale(
                cv2.equalizeHist(gray), 1.15, 9, minSize=(W // 12, W // 12)):
            out.append((int(x), int(y), int(w), int(h), None))
    return out


def _eyes_look_closed(gray: np.ndarray, face) -> bool:
    """Hint only: frontal face where neither eye patch contains a detectable open eye."""
    x, y, w, h, lm = face
    if lm is None or w < 90:
        return False
    (rx, ry), (lx, ly), (nx, _) = lm[0], lm[1], lm[2]
    eye_d = abs(lx - rx)
    if eye_d < 20 or abs(nx - (rx + lx) / 2) > 0.25 * eye_d:  # not facing the camera
        return False
    half = int(eye_d * 0.4)
    for cx, cy in ((rx, ry), (lx, ly)):
        x0, y0 = max(0, int(cx) - half), max(0, int(cy) - half)
        patch = gray[y0:int(cy) + half, x0:int(cx) + half]
        if patch.size and len(_haar("haarcascade_eye.xml").detectMultiScale(patch, 1.1, 3, minSize=(half // 2,) * 2)):
            return False
    return True


# --------------------------------------------------------------------------- loading
_FLIP_TO_ROTATE = {3: 180, 5: 90, 6: -90}  # libraw flip codes -> PIL rotate angle


def load_preview(path: str | Path, max_side: int = 1600) -> Image.Image:
    """Return an upright RGB PIL image no larger than max_side. ARW -> embedded JPEG preview."""
    p = Path(path)
    flip = 0
    if p.suffix.lower() == ".arw":
        import rawpy

        with rawpy.imread(str(p)) as raw:
            flip = raw.sizes.flip
            try:
                t = raw.extract_thumb()
                if t.format == rawpy.ThumbFormat.JPEG:
                    img = Image.open(io.BytesIO(t.data))
                else:
                    img = Image.fromarray(t.data)
                img.load()
            except (rawpy.LibRawNoThumbnailError, rawpy.LibRawUnsupportedThumbnailError):
                img = Image.fromarray(raw.postprocess(half_size=True, use_camera_wb=True))
    else:
        img = Image.open(p)
        img.draft("RGB", (max_side, max_side))  # let the JPEG decoder skip work when a small size is enough
        img.load()
        flip = 0
    has_exif_orient = img.getexif().get(274) is not None
    if has_exif_orient:
        img = ImageOps.exif_transpose(img)
    elif flip in _FLIP_TO_ROTATE:
        img = img.rotate(_FLIP_TO_ROTATE[flip], expand=True)
    img = img.convert("RGB")
    img.thumbnail((max_side, max_side))
    return img


# --------------------------------------------------------------------------- results
@dataclass
class Photo:
    path: str                      # file that was analysed
    files: list[str]               # all files sharing this stem (RAW+JPEG pair)
    name: str
    sharp_raw: float = 0.0         # sharpness (variance of Laplacian, best region / median face)
    has_face: bool = False
    n_faces: int = 0
    eyes_hint: int = 0             # faces whose eyes look closed: shown as a hint only, never a reject reason
    clip_lo: float = 0.0
    clip_hi: float = 0.0
    mean: float = 0.0
    tiny: np.ndarray | None = None  # 32x32 blurred, normalised grayscale: fingerprint for similarity
    taken: float = 0.0             # capture time (seconds, EXIF incl. sub-seconds; file mtime as fallback)
    thumb: bytes = b""
    error: str = ""
    # filled by decide()
    sharp_norm: float = 0.0        # sharpness relative to the shoot's typical photo (1.0 = typical)
    score: float = 0.0
    rank_score: float = 0.0        # un-clamped quality used to pick the best shot inside a group
    group: int = -1
    group_size: int = 1
    group_rank: int = 0
    auto_status: str = "keep"      # keep | reject
    reason: str = ""
    manual: str | None = None      # user override: keep | reject
    manual_reason: str = ""        # "duplicate" when the user marked it as a duplicate
    analyzed: bool = False         # True once the culling step has processed this photo

    @property
    def status(self) -> str:
        return self.manual or self.auto_status


def discover(folder: str | Path) -> list[tuple[Path, list[Path]]]:
    """Find photos in a folder, pairing RAW+JPEG with the same stem. Sorted by name."""
    stems: dict[str, list[Path]] = {}
    for p in sorted(Path(folder).iterdir(), key=lambda x: x.name.lower()):
        if p.is_file() and p.suffix.lower() in IMG_EXTS and not p.name.startswith("."):
            stems.setdefault(p.stem.lower(), []).append(p)
    out = []
    for files in stems.values():
        files.sort(key=lambda f: PRIMARY_ORDER.index(f.suffix.lower()))
        out.append((files[0], files))
    return out


# --------------------------------------------------------------------------- analysis
def _lap_var(gray: np.ndarray) -> float:
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def _region_sharpness(gray: np.ndarray, grid: int = 8) -> float:
    """90th percentile of per-block Laplacian variance: tolerant of blurred backgrounds (bokeh)."""
    lap = cv2.Laplacian(gray, cv2.CV_64F)
    h, w = lap.shape
    bh, bw = h // grid, w // grid
    vals = [lap[r * bh:(r + 1) * bh, c * bw:(c + 1) * bw].var() for r in range(grid) for c in range(grid)]
    return float(np.percentile(vals, 90))


def _capture_time(path: Path) -> float:
    try:
        ex = Image.open(path).getexif()
        sub = ex.get_ifd(0x8769)
        s = sub.get(0x9003) or ex.get(0x0132)
        if s:
            t = datetime.strptime(str(s).strip(), "%Y:%m:%d %H:%M:%S").timestamp()
            ss = str(sub.get(0x9291, "")).strip()
            return t + float("0." + ss) if ss.isdigit() else t
    except Exception:
        pass
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


def load_photo(path: Path, files: list[Path]) -> Photo:
    """Step 1 (loading): read the photo and make its thumbnail. No quality analysis yet."""
    ph = Photo(path=str(path), files=[str(f) for f in files], name=path.stem)
    ph.taken = _capture_time(path)
    try:
        img = load_preview(path, THUMB_SIDE)
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=80)
        ph.thumb = buf.getvalue()
    except Exception as e:
        ph.error = f"{type(e).__name__}: {e}"
    return ph


def analyze_photo(ph: Photo) -> Photo:
    """Step 3 (culling): compute sharpness / exposure / faces / fingerprint for a loaded photo."""
    if ph.error:
        ph.analyzed = True
        return ph
    try:
        img = load_preview(ph.path, ANALYSIS_SIDE)
        rgb = np.asarray(img)
        gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)

        # exposure
        ph.mean = float(gray.mean())
        ph.clip_lo = float((gray < 5).mean())
        ph.clip_hi = float((gray > 250).mean())

        # similarity fingerprint: tiny blurred grayscale, zero-mean / unit-variance (dot product = correlation)
        tiny = cv2.GaussianBlur(cv2.resize(gray, (32, 32), interpolation=cv2.INTER_AREA), (0, 0), 1)
        tiny = tiny.astype(np.float32).ravel()
        ph.tiny = (tiny - tiny.mean()) / (tiny.std() + 1e-6)

        # faces (neural detector) + closed-eyes hint
        faces = detect_faces(rgb, gray)
        ph.n_faces = len(faces)
        ph.has_face = ph.n_faces > 0

        sharp = _region_sharpness(gray)
        if ph.has_face:
            face_vars = []
            for face in faces:
                x, y, w, h = face[:4]
                crop = cv2.resize(gray[y:y + h, x:x + w], (160, 160), interpolation=cv2.INTER_AREA)
                face_vars.append(_lap_var(crop))
                if _eyes_look_closed(gray, face):
                    ph.eyes_hint += 1
            sharp = float(np.median(face_vars))
        ph.sharp_raw = sharp
    except Exception as e:  # corrupted / unreadable file
        ph.error = f"{type(e).__name__}: {e}"
    ph.analyzed = True
    return ph


def analyze(path: Path, files: list[Path]) -> Photo:
    """Convenience: load + analyze in one go (used by tests)."""
    return analyze_photo(load_photo(path, files))


# --------------------------------------------------------------------------- decisions
def _sharp_norm(photos: list[Photo]) -> None:
    """Sharpness relative to this shoot: 1.0 = the typical (median) photo of its kind (with / without faces)."""
    ok = [p for p in photos if not p.error]
    for kind in (True, False):
        subset = [p for p in ok if p.has_face == kind]
        pool = subset if len(subset) >= 8 else ok
        if not pool:
            continue
        ref = max(float(np.median([p.sharp_raw for p in pool])), 1.0)
        for p in subset:
            p.sharp_norm = float(np.clip(p.sharp_raw / ref, 0, 1.5))


def _exposure_score(p: Photo) -> float:
    s = 1.0 - min(1.0, 3.0 * p.clip_hi + 1.5 * p.clip_lo)
    if p.mean > 215 or p.mean < 40:
        s -= 0.4
    return max(0.0, s)


def _ncc(a: np.ndarray, b: np.ndarray) -> float:
    return float(a @ b) / len(a)  # fingerprints are zero-mean / unit-variance


def _groups(photos: list[Photo]) -> None:
    """Group similar shots: taken within a few seconds of each other AND visually alike (bursts, repeats)."""
    for p in photos:
        p.group, p.group_size, p.group_rank = -1, 1, 0
    seq = sorted((p for p in photos if not p.error and p.tiny is not None), key=lambda p: (p.taken, p.name))
    gid, anchor, prev = -1, None, None
    for p in seq:
        joined = (
            prev is not None
            and abs(p.taken - prev.taken) <= GROUP_MAX_GAP_S
            and _ncc(p.tiny, prev.tiny) >= GROUP_NCC
            and _ncc(p.tiny, anchor.tiny) >= GROUP_ANCHOR_NCC
        )
        if not joined:
            gid += 1
            anchor = p
        p.group = gid
        prev = p
    by_gid: dict[int, list[Photo]] = {}
    for p in seq:
        by_gid.setdefault(p.group, []).append(p)
    for g in by_gid.values():
        g.sort(key=lambda x: x.rank_score, reverse=True)
        for rank, p in enumerate(g):
            p.group_rank, p.group_size = rank, len(g)


def decide(photos: list[Photo], strictness: float = 0.5, regroup: bool = True) -> None:
    """Score photos and set auto_status/reason. strictness in 0..1 (higher = rejects more)."""
    _sharp_norm(photos)
    for p in photos:
        if p.error:
            p.score = p.rank_score = 0.0
            continue
        face_part = 1.0 if p.has_face else 0.7
        exp = _exposure_score(p)
        p.score = 100.0 * (0.6 * min(p.sharp_norm, 1.0) + 0.25 * exp + 0.15 * face_part)
        # not clamped, so frames of a burst can still be told apart; more visible faces breaks near-ties
        p.rank_score = 0.6 * p.sharp_norm + 0.25 * exp + 0.15 * face_part + 0.02 * min(p.n_faces, 3)
    if regroup:
        _groups(photos)
    blur_cut = 0.12 + 0.30 * strictness            # fraction of the shoot's typical sharpness
    q_cut = 30 + 30 * strictness
    keep_n = max(1, round(3 - 2 * strictness))     # similar shots kept per group: lenient 3, default 2, strict 1
    for p in photos:
        reasons = []
        if p.error:
            p.auto_status, p.reason = "reject", f"unreadable ({p.error})"
            continue
        if p.sharp_norm < blur_cut:
            reasons.append("blurry")
        if _exposure_score(p) < 0.45:
            reasons.append("bad exposure")
        if p.score < q_cut and not reasons:
            reasons.append("low quality")
        in_group = p.group_size > 1
        if in_group and p.group_rank >= keep_n:
            reasons.append(f"duplicate: ranked #{p.group_rank + 1} of {p.group_size} similar shots")
        p.auto_status = "reject" if reasons else "keep"
        if reasons:
            p.reason = ", ".join(reasons)
        elif in_group:
            p.reason = ("best of %d similar shots" % p.group_size) if p.group_rank == 0 \
                else f"kept: #{p.group_rank + 1} of {p.group_size} similar shots"
        else:
            p.reason = "ok"
