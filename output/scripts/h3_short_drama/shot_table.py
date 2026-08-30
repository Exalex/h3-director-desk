"""Standardized shot-table self-check (STEP 5.5) — the 6 mandatory gates.

Returns (passed, list_of_failures). Mirrors the official 3D skill self-check.
"""
from __future__ import annotations

import re
from .data import Project, Shot, HOOK_TYPES

_STRONG_HOOKS = {"reveal", "reversal", "callback", "suspense", "chase"}
_FIVE_ELEMENTS = ("action", "camera", "spatial", "audio", "handoff")


def _shot_seconds(shot: Shot) -> int:
    return int(round(shot.duration_s))


def check_hook_density(project: Project) -> list[str]:
    fails = []
    if not project.shots:
        return fails
    shots = project.shots
    # every shot has a hook type from the controlled vocabulary
    for s in shots:
        if s.hook_type not in HOOK_TYPES:
            fails.append(f"{s.shot_id}: hook_type '{s.hook_type}' not in controlled vocabulary")
    # first & last shot carry a strong hook
    if shots[0].hook_type not in _STRONG_HOOKS:
        fails.append(f"{shots[0].shot_id}: opening shot should carry a strong hook (reveal/reversal/callback)")
    if shots[-1].hook_type not in _STRONG_HOOKS:
        fails.append(f"{shots[-1].shot_id}: closing shot should carry a strong hook")
    # every window of 3 consecutive shots has >=1 strong hook
    for i in range(len(shots) - 2):
        window = shots[i:i + 3]
        if not any(w.hook_type in _STRONG_HOOKS for w in window):
            fails.append(f"shots {window[0].shot_id}-{window[2].shot_id}: no strong hook in this 3-shot window")
    return fails


def check_single_shot_duration(project: Project) -> list[str]:
    return [f"{s.shot_id}: duration {s.duration_s}s exceeds 15s cap; split it"
            for s in project.shots if _shot_seconds(s) > 15]


def check_chars_per_shot(project: Project, char_names: set[str] | None = None) -> list[str]:
    fails = []
    for s in project.shots:
        n = len(s.char_positions)
        if n > 3:
            fails.append(f"{s.shot_id}: {n} significant characters on screen (>3 cap)")
    return fails


def check_spatial_inheritance(project: Project) -> list[str]:
    """Consecutive shots sharing a scene must inherit landmarks + lighting,
    or carry an explicit continuity note."""
    fails = []
    for i in range(1, len(project.shots)):
        prev, cur = project.shots[i - 1], project.shots[i]
        # same interior = overlapping landmark names OR no hard-cut marker
        shared = set(prev.fixed_landmarks) & set(cur.fixed_landmarks)
        hard_cut = any(m in (cur.continuity_handoff or "").upper() for m in ("HARD CUT", "TIME SKIP"))
        if not hard_cut and prev.fixed_landmarks and not shared and not cur.lighting_baseline:
            fails.append(
                f"{cur.shot_id}: spatial anchor not inherited from {prev.shot_id} "
                f"(no shared landmarks, no lighting baseline, no explicit continuity note)"
            )
    return fails


def check_per_second_coverage(project: Project) -> list[str]:
    """Every second 0..duration must have a directive covering the 5 elements."""
    fails = []
    for s in project.shots:
        dur = _shot_seconds(s)
        covered = set()
        for ps in s.per_second:
            # parse "0-1s" or "2.0-2.5s" -> integer second index it touches
            m = re.findall(r"([0-9]+(?:\.[0-9]+)?)", ps.rng)
            if len(m) >= 2:
                start, end = float(m[0]), float(m[1])
                for sec in range(int(start), max(int(start) + 1, int(end) + (1 if end % 1 else 0))):
                    covered.add(sec)
            # 5-element check
            missing = [e for e in _FIVE_ELEMENTS if not getattr(ps, e, "").strip()]
            if missing:
                fails.append(f"{s.shot_id} {ps.rng}: missing directive elements {missing}")
        for sec in range(dur):
            if sec not in covered:
                fails.append(f"{s.shot_id}: second {sec} has no per-second directive")
                break
    return fails


def check_cross_shot_continuity(project: Project) -> list[str]:
    """Reading Continuity Handoff row by row must form an unbroken chain;
    any flip of eyeline/position/prop/lighting must be marked explicitly."""
    fails = []
    for i in range(1, len(project.shots)):
        cur = project.shots[i]
        if not (cur.continuity_handoff or "").strip():
            fails.append(f"{cur.shot_id}: missing Continuity Handoff (chain broken)")
        # a flip must be marked
        text = (cur.continuity_handoff or "").upper()
        for marker in ("FLIP", "REVERSES", "MIRRORS", "FLIP EYELINE"):
            if marker in text and "HARD CUT" not in text and "TIME SKIP" not in text:
                fails.append(f"{cur.shot_id}: describes a flip without an explicit HARD CUT / time-skip marker")
    return fails


def self_check(project: Project) -> tuple[bool, list[str]]:
    failures: list[str] = []
    failures += check_hook_density(project)
    failures += check_single_shot_duration(project)
    failures += check_chars_per_shot(project)
    failures += check_spatial_inheritance(project)
    failures += check_per_second_coverage(project)
    failures += check_cross_shot_continuity(project)
    return (not failures, failures)
