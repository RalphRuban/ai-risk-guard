"""Convert the opaque AUREX logo PNG into transparent web assets.

Chroma-keys the near-navy background (RGB ~2,13,30, matching the app void
color #020B1A) to transparency with soft edges, then downsamples to the
sizes used across the UI and favicon.

Outputs:
    frontend/public/aurex-logo.png   (512x512, RGBA)
    frontend/public/favicon.png      (64x64, RGBA)

Run: python tools/make_aurex_logo.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "Aurex Logo.png"
UI_OUT = ROOT / "frontend" / "public" / "aurex-logo.png"
FAVICON_OUT = ROOT / "frontend" / "public" / "favicon.png"

UI_SIZE = 512
FAVICON_SIZE = 64


def key_out_background(img: Image.Image, tolerance: int = 42, feather: int = 2) -> Image.Image:
    """Return an RGBA copy with near-navy background pixels made transparent."""
    rgba = img.convert("RGBA")
    arr = np.asarray(rgba).astype(np.int16)
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]

    # Background sampled from the four corners of the source image.
    bg = np.median(
        [
            arr[0, 0, :3],
            arr[0, -1, :3],
            arr[-1, 0, :3],
            arr[-1, -1, :3],
        ],
        axis=0,
    ).astype(np.int16)

    dist = np.abs(r - bg[0]) + np.abs(g - bg[1]) + np.abs(b - bg[2])
    mask = (dist <= tolerance).astype(np.float32)

    # Soft edge: linear falloff between tolerance and tolerance + feather.
    soft_edge = tolerance + feather
    edge = (soft_edge - dist) / float(feather)
    mask = np.clip(np.maximum(mask, np.where((dist > tolerance) & (dist < soft_edge), edge, 0)), 0, 1)

    alpha = rgba.getchannel("A").convert("L")
    alpha_arr = np.asarray(alpha).astype(np.float32) / 255.0
    alpha_arr = alpha_arr * (1.0 - mask)
    rgba.putalpha(Image.fromarray((alpha_arr * 255).astype(np.uint8), mode="L"))
    return rgba.filter(ImageFilter.GaussianBlur(0.4))


def _report(name: str, img: Image.Image) -> None:
    arr = np.asarray(img.convert("RGBA"))
    alpha = arr[..., 3]
    corners = [arr[0, 0, 3], arr[0, -1, 3], arr[-1, 0, 3], arr[-1, -1, 3]]
    opaque = int((alpha > 250).sum())
    total = alpha.size
    print(f"{name}: {img.width}x{img.height} alpha_bbox={img.getbbox()} "
          f"corner_alpha={corners} opaque%={100 * opaque / total:.1f}")


def main() -> None:
    if not SOURCE.exists():
        raise SystemExit(f"Missing source logo: {SOURCE}")

    with Image.open(SOURCE) as src:
        _report("source", src)
        transparent = key_out_background(src)

    ui = transparent.resize((UI_SIZE, UI_SIZE), Image.Resampling.LANCZOS)
    ui.save(UI_OUT, optimize=True)
    _report("ui", ui)
    print(f"wrote {UI_OUT} ({UI_OUT.stat().st_size} bytes)")

    favicon = transparent.resize((FAVICON_SIZE, FAVICON_SIZE), Image.Resampling.LANCZOS)
    favicon.save(FAVICON_OUT, optimize=True)
    _report("favicon", favicon)
    print(f"wrote {FAVICON_OUT} ({FAVICON_OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()