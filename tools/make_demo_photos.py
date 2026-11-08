"""Generate a folder of synthetic landscape "photos" for demos and README screenshots.

No personal photos are needed. The set includes bursts of near-identical frames (with EXIF capture
times, like a real camera), a motion-blurred frame, an out-of-focus frame, an over-exposed frame and
an under-exposed frame, so every part of i-arrange has something to show.

Usage:  python tools/make_demo_photos.py [output_folder]      (default: docs/demo-photos)
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

LAND, PORT = (1500, 1000), (1000, 1500)

# name, size, sky (top, bottom), sun (x, y, r, colour), ridges [(base_y, amplitude, colour)], detail, frames, flaw
SCENES = [
    ("sunset beach",  LAND, ((255, 140, 90), (255, 214, 150)), (0.70, 0.52, 90, (255, 240, 200)),
     [(0.62, 0.02, (60, 90, 140)), (0.80, 0.02, (232, 200, 150))], "none", 4, None),
    ("mountains",     LAND, ((90, 140, 210), (200, 225, 245)), (0.25, 0.20, 60, (255, 255, 235)),
     [(0.52, 0.12, (110, 120, 150)), (0.64, 0.10, (70, 90, 110)), (0.80, 0.06, (40, 70, 60))], "trees", 3, "motion"),
    ("forest",        PORT, ((150, 190, 160), (230, 240, 210)), (0.60, 0.18, 70, (255, 250, 220)),
     [(0.50, 0.08, (60, 110, 80)), (0.70, 0.08, (35, 80, 55))], "trees", 1, None),
    ("city dusk",     LAND, ((70, 60, 130), (250, 150, 130)), (0.20, 0.30, 50, (255, 230, 190)),
     [(0.70, 0.02, (35, 35, 60))], "buildings", 3, None),
    ("desert",        LAND, ((120, 190, 240), (250, 240, 215)), (0.78, 0.22, 80, (255, 255, 245)),
     [(0.60, 0.07, (225, 170, 100)), (0.76, 0.08, (205, 140, 80))], "none", 1, "over"),
    ("lake dawn",     LAND, ((250, 170, 150), (255, 225, 190)), (0.50, 0.50, 70, (255, 245, 215)),
     [(0.52, 0.05, (90, 100, 140)), (0.58, 0.01, (130, 160, 190))], "trees", 4, None),
    ("night street",  PORT, ((15, 20, 45), (45, 40, 80)), (0.70, 0.15, 45, (240, 240, 255)),
     [(0.72, 0.02, (25, 25, 45))], "buildings", 1, "dark"),
    ("meadow",        LAND, ((130, 195, 235), (225, 240, 250)), (0.30, 0.18, 55, (255, 255, 225)),
     [(0.55, 0.05, (110, 170, 90)), (0.72, 0.05, (70, 140, 60))], "flowers", 2, None),
    ("snow peaks",    LAND, ((140, 175, 225), (235, 240, 250)), (0.80, 0.18, 55, (255, 255, 245)),
     [(0.48, 0.14, (225, 232, 245)), (0.66, 0.10, (170, 190, 215))], "none", 1, "blur"),
    ("harbour",       LAND, ((100, 170, 220), (235, 225, 205)), (0.18, 0.18, 55, (255, 250, 230)),
     [(0.60, 0.02, (60, 120, 160)), (0.78, 0.03, (45, 95, 140))], "masts", 3, None),
]


def _gradient(w: int, h: int, top, bottom) -> np.ndarray:
    t = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
    return (np.array(top, np.float32) * (1 - t) + np.array(bottom, np.float32) * t) * np.ones((1, w, 1), np.float32)


def render(scene, frame: int, seed: int) -> Image.Image:
    name, (w, h), sky, sun, ridges, detail, _frames, flaw = scene
    rng = np.random.default_rng(seed)  # same seed for every frame of a scene -> frames look alike
    img = Image.fromarray(_gradient(w, h, *sky).astype(np.uint8))
    d = ImageDraw.Draw(img)
    sx, sy, sr, sc = sun
    d.ellipse([sx * w - sr, sy * h - sr, sx * w + sr, sy * h + sr], fill=sc)
    for base, amp, col in ridges:
        xs = np.linspace(0, w, 60)
        ys = base * h + amp * h * (np.sin(xs / w * rng.uniform(3, 7) + rng.uniform(0, 6)) +
                                   0.5 * np.sin(xs / w * rng.uniform(9, 16) + rng.uniform(0, 6)))
        d.polygon([(0, h)] + list(zip(xs, ys)) + [(w, h)], fill=col)
    for _ in range(260):  # fine detail so the image has real texture to measure
        x, y = rng.uniform(0, w), rng.uniform(0.45 * h, 0.95 * h)
        s = rng.uniform(6, 22)
        shade = int(rng.uniform(-35, 35))
        if detail == "trees":
            d.polygon([(x, y - 2 * s), (x - s * 0.7, y), (x + s * 0.7, y)], fill=(30 + shade, 90 + shade, 55 + shade))
        elif detail == "buildings":
            d.rectangle([x, y - 3 * s, x + s, y], fill=(30 + shade, 30 + shade, 55 + shade))
            d.rectangle([x + 2, y - 3 * s + 3, x + 4, y - 3 * s + 6], fill=(255, 220, 130))
        elif detail == "flowers":
            d.ellipse([x, y, x + s * 0.5, y + s * 0.5], fill=(240 + shade // 4, 90 + shade, 140 + shade))
        elif detail == "masts":
            d.line([x, y, x, y - 5 * s], fill=(60, 60, 70), width=2)
            d.line([x, y - 5 * s, x + s, y - 2 * s], fill=(235, 235, 235), width=2)
    # "subject": a small figure that moves a little between burst frames
    fx, fy = w * (0.30 + 0.035 * frame), h * 0.72
    d.ellipse([fx - 14, fy - 78, fx + 14, fy - 50], fill=(35, 30, 40))
    d.rounded_rectangle([fx - 20, fy - 50, fx + 20, fy + 25], radius=14, fill=(35, 30, 40))
    arr = np.asarray(img).astype(np.float32)
    arr += rng.normal(0, 5, arr.shape)                     # film grain
    arr = np.roll(arr, (frame * 2, frame * 3), axis=(0, 1))  # hand-held sway between frames
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    if flaw == "motion" and frame == 1:
        img = img.filter(ImageFilter.BoxBlur(7))
    elif flaw == "blur":
        img = img.filter(ImageFilter.GaussianBlur(9))
    elif flaw == "over":
        img = Image.eval(img, lambda v: min(255, int(v * 2.6)))  # blown highlights
    elif flaw == "dark":
        img = Image.eval(img, lambda v: int(v * 0.12))
    return img


def main() -> None:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "docs" / "demo-photos"
    out.mkdir(parents=True, exist_ok=True)
    t = datetime(2026, 5, 17, 17, 42, 3)
    n = 1
    for si, scene in enumerate(SCENES):
        for fr in range(scene[6]):
            img = render(scene, fr, seed=100 + si)
            when = t + timedelta(seconds=si * 47 + fr * 0.4)
            exif = Image.Exif()
            ifd = exif.get_ifd(0x8769)
            ifd[0x9003] = when.strftime("%Y:%m:%d %H:%M:%S")
            ifd[0x9291] = f"{when.microsecond // 1000:03d}"
            exif[0x8769] = ifd
            img.save(out / f"DEMO{n:04d}.jpg", quality=92, exif=exif)
            n += 1
    print(f"wrote {n - 1} demo photos to {out}")


if __name__ == "__main__":
    main()
