"""Hardware-aware H3 profile planner (distilled from h3lite).

Pick a (canvas, steps, cache, offload) profile from VRAM + target, and verify
the 32-pixel alignment + 17k+5 frame grid.
"""
from __future__ import annotations

from dataclasses import dataclass
from .data import ASPECTS


@dataclass
class Profile:
    name: str                 # Fast / Balanced / Quality / Native
    width: int
    height: int
    frames: int               # 17k+5 aligned
    steps: int
    block_cache: bool
    offload: str              # none / model / full
    lora: str                 # turbo / none
    note: str = ""


def align_frame_count(seconds: float, fps: int = 24) -> int:
    """H3 output grid: n = max(5, round(dur*fps)); n += (5-(n%17))%17 -> 17k+5."""
    n = max(5, int(round(seconds * fps)))
    n += (5 - (n % 17)) % 17
    return n


def align32(w: int, h: int) -> tuple[int, int]:
    return (w // 32) * 32, (h // 32) * 32


def canvas_for_aspect(aspect: str, short_edge: int, align: bool = True) -> tuple[int, int]:
    parts = aspect.split(":")
    a, b = int(parts[0]), int(parts[1])
    if a >= b:
        w, h = short_edge * a // b, short_edge
    else:
        w, h = short_edge, short_edge * b // a
    if align:
        w, h = align32(w, h)
    return w, h


def pick_profile(vram_gb: float, aspect: str = "16:9", seconds: float = 5.0,
                 quality: str = "fast", for_face: bool = False) -> Profile:
    """Return a concrete generation profile.

    quality: fast/balanced/quality; for_face forces Native (>=768 short edge).
    """
    frames = align_frame_count(seconds)
    if for_face or quality == "quality" and vram_gb >= 16:
        short = 768
        name = "Native"
        steps = 8 if quality == "quality" else 6
        cache = False
        offload = "none" if vram_gb >= 24 else "model"
    else:
        short = 480 if vram_gb < 16 else 768
        low = 352 if short == 480 else 480
        name = "Fast" if quality == "fast" else "Balanced"
        steps = {"fast": 4, "balanced": 6, "quality": 8}[quality]
        cache = quality == "fast"
        offload = "none" if vram_gb >= 16 else ("model" if vram_gb >= 12 else "full")
        # low-VRAM 8GB baseline is 640x352 / 4 steps / block cache
        if vram_gb < 10 and quality == "fast":
            w, h = canvas_for_aspect(aspect, 480)
            if vram_gb < 9:
                w, h = canvas_for_aspect(aspect, 352)
            return Profile(name="Fast", width=w, height=h, frames=frames,
                           steps=4, block_cache=True, offload="full",
                           lora="turbo", note="8GB baseline / success-rate priority")
    w, h = canvas_for_aspect(aspect, short)
    return Profile(name=name, width=w, height=h, frames=frames, steps=steps,
                   block_cache=cache, offload=offload,
                   lora="turbo" if (name == "Fast") else "none",
                   note="face/hero shots: keep Turbo+BlockCache off; dialogue shots: same")


def validate(profile: Profile, aspect: str) -> list[str]:
    fails = []
    if profile.width % 32 != 0 or profile.height % 32 != 0:
        fails.append(f"canvas {profile.width}x{profile.height} not 32-aligned (VAE16 + DiT2 patch)")
    if profile.frames % 17 != 5:
        fails.append(f"frames {profile.frames} not on the 17k+5 grid")
    return fails


def plan_text(vram_gb: float, aspect: str, seconds: float, quality: str, face: bool) -> str:
    p = pick_profile(vram_gb, aspect, seconds, quality, face)
    lines = [f"profile={p.name}", f"canvas={p.width}x{p.height} ({aspect})",
             f"frames={p.frames} (~{p.frames/24:.1f}s @24fps)", f"steps={p.steps}",
             f"block_cache={'on' if p.block_cache else 'off'}", f"offload={p.offload}",
             f"lora={p.lora}"]
    for f in validate(p, aspect):
        lines.append(f"  ! {f}")
    return "\n".join(lines)
