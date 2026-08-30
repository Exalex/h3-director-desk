"""Auto-generate a continuous short-drama (连续剧) on a live ComfyUI H3.

Chains the proven single-shot generator across a shot table:
  for each shot:
    compile H3 prompt -> (lock identity) -> generate clip -> extract last frame
    next shot's first_frame = this shot's last frame   (尾帧链 continuity)
then assembles the clips into episode videos.

The first shot can be T2V (no reference) or I2V (a character card as first_frame).
Every later shot is I2V from the previous shot's last frame, so identity + story
carry forward shot-to-shot.
"""
from __future__ import annotations

import json
import os
from typing import List, Optional
from . import comfyui_gen as cg
from . import prompt as _prompt


def generate_series(base: str, shots, project, out_dir: str = "series_out",
                    width: int = 480, height: int = 832, steps: int = 20,
                    base_seed: int = 42, assemble: bool = True,
                    verbose: bool = True, shot_loras: Optional[dict] = None,
                    shot_steps: Optional[dict] = None,
                    skip_existing: bool = False, progress_callback=None) -> List[dict]:
    """Generate all shots as a chained short drama. Returns per-shot records.

    shot_loras: {shot_id: [(lora_name, sm, sc), ...]} — optional LoRA injection per shot.
    shot_steps: {shot_id: steps} — per-shot step override (e.g. 8 w/ Turbo, 20 w/o).
    skip_existing: if the shot's out_mp4 already exists, keep it (resume-friendly).
    """
    os.makedirs(out_dir, exist_ok=True)
    from .character_lock import characters_from
    chars = characters_from(project)

    clips = []
    prev_frame = None
    for i, shot in enumerate(shots):
        sid = shot.shot_id
        if progress_callback:
            progress_callback(i, len(shots), sid, "starting")
        prompt_text = _prompt.compile(shot, project)
        # Explicit per-character fixed seed wins (定卡); otherwise auto per-shot seed.
        seed = shot.seed if getattr(shot, "seed", 0) else (base_seed + i * 7919) % (2**31)

        # first frame: locked character card > previous shot's last frame (continuity
        # spine) > None (T2V). A shot featuring a locked character is a HARD CUT to
        # that character (I2VA from its card); the tail-frame chain is reserved for
        # same-subject continuation shots.
        first = _lead_card(shot, chars) or prev_frame
        if first and not _is_comfy_name(first) and not os.path.exists(first):
            first = None  # no character card on disk -> T2V this shot
        if first and os.path.exists(first) and not _is_comfy_name(first):
            first = cg.upload_image(base, first)
            if verbose:
                print(f"[series] {sid} uploaded first_frame -> {first}")

        out_mp4 = os.path.join(out_dir, f"{sid}.mp4")
        out_png = os.path.join(out_dir, f"{sid}_last.png")
        st = (shot_steps or {}).get(sid, steps)
        loras = (shot_loras or {}).get(sid)
        if skip_existing and os.path.exists(out_mp4) and os.path.getsize(out_mp4) > 100_000:
            if verbose:
                print(f"[series] {sid} EXISTS -> skip")
            # keep the tail-frame chain alive even when skipping (fix: was breaking I2V chaining)
            if i + 1 < len(shots):
                prev_frame = cg.extract_last_frame(out_mp4, out_png)
            clips.append({"shot_id": sid, "clip": out_mp4, "skipped": True})
            if progress_callback:
                progress_callback(i + 1, len(shots), sid, "skipped")
            continue
        if verbose:
            print(f"[series] {sid} {shot.mode} {width}x{height}x{shot.duration_s}s "
                  f"seed={seed} steps={st} first_frame={bool(first)} loras={bool(loras)}")
        try:
            cg.generate(base, prompt_text, out_mp4, width=width, height=height,
                        length=_frame_count(shot.duration_s), seed=seed, steps=st,
                        first_frame=first or "", filename=sid, timeout=3600, verbose=verbose,
                        loras=loras)
        except Exception as e:
            clips.append({"shot_id": sid, "error": str(e), "clip": None})
            if verbose:
                print(f"[series] {sid} FAILED: {e}")
            prev_frame = None
            continue

        # extract last frame to chain into the next shot
        if i + 1 < len(shots):
            prev_frame = cg.extract_last_frame(out_mp4, out_png)
        clips.append({"shot_id": sid, "clip": out_mp4,
                      "seed": seed, "first_frame": first, "prompt": prompt_text})
        if progress_callback:
            progress_callback(i + 1, len(shots), sid, "done")
        if verbose:
            print(f"[series] {sid} OK -> {out_mp4}")

    # assemble into an episode
    ep = None
    if assemble:
        ok = [c for c in clips if c.get("clip")]
        if ok:
            ep = os.path.join(out_dir, "episode.mp4")
            if verbose:
                print(f"[series] assembling {len(ok)} clips -> {ep}")
            _assemble_clips([c["clip"] for c in ok], ep)
            clips.append({"episode": ep})
    return clips


def _lead_card(shot, chars: dict) -> Optional[str]:
    lead = next((n for n in shot.char_positions.keys() if n in chars), None)
    return chars.get(lead) if lead else None


def _frame_count(seconds: float) -> int:
    """Snap to the 17k+5 grid (124 = ~5s)."""
    n = max(5, int(round(seconds * 24)))
    n += (5 - (n % 17)) % 17
    return min(n, 360)


def _is_comfy_name(s: str) -> bool:
    return s and not os.path.exists(s)


def _assemble_clips(clips: List[str], out: str):
    from . import assemble as asm
    cmds = asm.assemble_plan(clips, out, canvas=(480, 832))
    for c in cmds:
        if c and c[0] == "cp":
            import shutil
            shutil.copyfile(c[1], c[2])
            continue
        import subprocess
        subprocess.run(c, check=False, capture_output=True)


def run_from_json(base: str, project_json: str, out_dir: str = "series_out") -> List[dict]:
    from . import data
    d = json.load(open(project_json, "r", encoding="utf-8"))
    shots = [data.Shot.from_dict(s) for s in d.get("shots", [])]
    proj = data.Project(**{k: d.get(k, v) for k, v in
                           dict(title="", what_if="", aspect="9:16", duration_s=45,
                                dialogue_mode="有对白", dialogue_language="中文",
                                visual_style="").items() if k in d}, shots=shots)
    return generate_series(base, shots, proj, out_dir=out_dir)
