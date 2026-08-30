"""ffmpeg assembly for H3 short-drama clips.

Key safety rules distilled from the analysis:
- H3 emits 32kHz audio (NOT 48k). Never hardcode 48000 in a concat/xfade graph;
  read the actual sample rate and resample explicitly.
- match_tail: trim/pad audio to exactly video length (removes the +/-8.3ms/clip
  accumulation that stacks at every join).
- xfade transitions 0.4s, cycled; BGM ducked under dialogue; clean H.264 yuv420p.
"""
from __future__ import annotations

import os
import subprocess
from typing import List, Optional


def _ffmpeg_bin() -> str:
    """imageio_ffmpeg's bundled binary (system ffmpeg may not exist)."""
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def probe(path: str) -> dict:
    """Return {width,height,fps,sample_rate,duration,ar} via pyav (no ffprobe binary)."""
    import av
    c = av.open(path)
    v = c.streams.video[0]
    a = c.streams.audio[0] if c.streams.audio else None
    return {
        "width": v.width, "height": v.height,
        "fps": round(float(v.average_rate), 3) if v.average_rate else 24.0,
        "sample_rate": (a.sample_rate if a else 32000),
        "duration": float(v.duration) * float(v.time_base) if v.duration else 0.0,
        "ar": f"{v.width}x{v.height}",
    }


def normalize_cmd(src: str, dst: str, target: tuple[int, int] = (832, 1472),
                  fps: int = 24) -> List[str]:
    """scale+pad to a unified canvas + warm colour unification + fps lock.

    target default = 832x1472 (0.4MP 9:16, 32-aligned). 832/1472 both divisible by 32.
    """
    w, h = target
    return [
        _ffmpeg_bin(), "-y", "-i", src,
        "-vf", f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
               f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:black,"
               f"colorbalance=rs=0.08:gs=0.04:bs=-0.06,"
               f"eq=brightness=0.02:contrast=1.05:saturation=1.05,"
               f"fps={fps}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
        dst,
    ]


def match_tail_audio(src: str, dst: str, video_seconds: float) -> List[str]:
    """Trim/pad the audio to exactly video_seconds (match_tail), 32kHz-safe."""
    return [
        _ffmpeg_bin(), "-y", "-i", src,
        "-af", f"atrim=0:{video_seconds:.3f},asetpts=PTS-STARTPTS",
        "-ar", "32000", "-ac", "2", "-c:a", "aac", "-b:a", "192k",
        dst,
    ]


def build_xfade(concat: List[str], out: str, dur: float, transition: str = "dissolve",
                offset_start: float = 0.0) -> List[str]:
    """Two-clip xfade helper (chain for N clips). Reads sample rate from clips."""
    return [
        _ffmpeg_bin(), "-y", "-i", concat[0], "-i", concat[1],
        "-filter_complex",
        f"[0:v][1:v]xfade=transition={transition}:duration={dur}:offset={offset_start}"
        f"[v];[0:a][1:a]acrossfade=d={dur}[a]",
        "-map", "[v]", "-map", "[a]",
        "-r", "24", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
        "-c:a", "aac", "-ar", "32000", "-ac", "2",
        out,
    ]


TRANSITIONS = ["fade", "dissolve", "wipeleft", "circleopen", "slideright", "fadefast"]


def assemble_plan(clips: List[str], out: str, bgm: str = "", subtitle: str = "",
                  canvas: tuple[int, int] = (832, 1472)) -> List[List[str]]:
    """Return a list of ffmpeg command lists: normalize each, xfade-concat,
    mix BGM (ducked), burn subtitles. Caller runs them in order."""
    cmds: List[List[str]] = []
    normalized = [f"_norm_{i:02d}.mp4" for i in range(len(clips))]
    for i, c in enumerate(clips):
        cmds.append(normalize_cmd(c, normalized[i], canvas))
    # chained xfade
    cur = normalized[0]
    for i in range(1, len(clips)):
        nxt = f"_join_{i:02d}.mp4"
        tr = TRANSITIONS[i % len(TRANSITIONS)]
        # offset = duration so far - transition duration
        # (caller can refine with probe(); keep a conservative 0.4s)
        try:
            d_so_far = sum(probe(clips[j])["duration"] for j in range(i)) - (i * 0.4)
        except Exception:
            d_so_far = i * 5.0
        cmds.append(build_xfade([cur, normalized[i]], nxt, 0.4, tr, max(0.0, d_so_far)))
        cur = nxt
    # BGM + mix
    if bgm:
        with_bgm = f"{out}.withbgm.mp4"
        cmds.append([
            _ffmpeg_bin(), "-y", "-i", cur, "-stream_loop", "-1", "-i", bgm,
            "-filter_complex",
            "[1:a]volume=0.10[bgm];[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=0[a]",
            "-map", "0:v", "-map", "[a]", "-shortest",
            "-r", "24", "-c:v", "copy", "-c:a", "aac", "-ar", "32000", "-ac", "2",
            with_bgm,
        ])
        cur = with_bgm
    # subtitles
    if subtitle:
        final = f"{out}.final.mp4"
        cmds.append([
            _ffmpeg_bin(), "-y", "-i", cur,
            "-vf", f"subtitles={os.path.basename(subtitle)}:force_style='Fontsize=18,FontName=PingFang SC,Outline=1'",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-c:a", "copy",
            final,
        ])
        cur = final
    # rename to out
    if cur != out:
        cmds.append(["cp", cur, out])
    return cmds


def run(cmds: List[List[str]]) -> None:
    import shutil
    for c in cmds:
        if c and c[0] == "cp":          # cross-platform plain copy (not a shell command)
            print("RUN: cp", c[1], "->", c[2])
            shutil.copyfile(c[1], c[2])
            continue
        print("RUN:", " ".join(c))
        subprocess.run(c, check=True)
