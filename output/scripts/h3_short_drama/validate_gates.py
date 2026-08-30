"""Deterministic quality gates for H3 short-drama projects.

Two families of gates, all script-checked (never a model judgment):

  T01..T06 — the existing shot-table self-checks (shot_table.self_check):
             hook density / 15s cap / 3-char cap / spatial inheritance /
             per-second coverage / cross-shot handoff chain.
  G01..G08 — gates ported from the shuohao-skills methodology
             (novel-storyboard's "17 quality gates" idea, adapted to this
             pipeline's data model):
    G01 frame grid      duration snaps to the H3 17k+5 frame grid
    G02 gen continuity  first shot anchors; later shots must chain (I2VA)
                        or hard-cut with a character card
    G03 dialogue fit    spoken duration (chars / speech-rate) fits the window
    G04 time ranges     dialogue time_range valid, within shot, non-overlapping
    G05 speakers        dialogue speakers exist in characters[]
    G06 character cards image_path on disk for every used character
    G07 H3 prompt       compiled prompt has required sections, the I2VA
                        alignment line, and every dialogue line verbatim
    G08 references      reference labels unique per shot, '<Kind n>' form

Run BEFORE burning GPU time: failures cost milliseconds here, ~30 minutes
in ComfyUI. Results accumulate in <project_dir>/.gates.jsonl so `stats`
shows which gate fires most often (the shuohao meta-loop: fix the rule,
not just the data).

Usage
-----
    python -m h3_short_drama.validate_gates <project.json> [--no-log] [--log-dir DIR]
    python -m h3_short_drama.validate_gates stats <project_dir>
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from dataclasses import dataclass
from typing import List, Optional

from .data import Project, Shot
from . import prompt as _prompt
from . import shot_table
from .series import _frame_count

ZH_CHARS_PER_SEC = 4.0     # conservative Mandarin speech rate
EN_WORDS_PER_SEC = 2.6
FIT_TOLERANCE = 1.20       # dialogue may overfill a window by up to 20%
GRID_TOL_S = 0.40          # |snapped_frames/24 - duration| must stay under this
_RNG_RE = re.compile(r"^\s*([\d.]+)\s*[-–]\s*([\d.]+)\s*s?")


@dataclass
class Finding:
    gate: str
    level: str            # "error" | "warn"
    shot: str
    detail: str


def _load(path: str):
    d = json.load(open(path, "r", encoding="utf-8"))
    from .data import CharacterCard, SceneCard

    chars = [CharacterCard(**c) for c in d.get("characters", [])]
    scenes = [SceneCard(**s) for s in d.get("scenes", [])]
    shots = [Shot.from_dict(s) for s in d.get("shots", [])]
    proj = Project(**{k: d.get(k, v) for k, v in
                      dict(title="", what_if="", aspect="9:16", duration_s=45,
                           dialogue_mode="有对白", dialogue_language="中文",
                           visual_style="").items() if k in d},
                      characters=chars, scenes=scenes, shots=shots)
    return proj, d


def _speech_seconds(text: str, language: str) -> float:
    if not text:
        return 0.0
    core = re.sub(r"[\s,，.。!！?？:：;；、…—~\"'“”‘’（）()【】\[\]]", "", text)
    if language in ("en", "English", "en-US"):
        return len(core.split()) / EN_WORDS_PER_SEC
    return len(core) / ZH_CHARS_PER_SEC


def _parse_rng(s: str):
    m = _RNG_RE.match(s or "")
    if not m:
        return None
    return float(m.group(1)), float(m.group(2))


def _lead_character(shot: Shot, char_names: set) -> Optional[str]:
    for name in shot.char_positions:
        if name in char_names:
            return name
    return None


def check_project(proj: Project, raw: dict) -> List[Finding]:
    f: List[Finding] = []
    shots = proj.shots
    char_names = {c.name for c in proj.characters}

    if not shots:
        return [Finding("T00", "error", "-", "no shots in project")]

    # --- T01..T06: the existing six shot-table gates -----------------------
    ok, fails = shot_table.self_check(proj)
    for msg in fails:
        sid = msg.split(":")[0]
        f.append(Finding("T01-T06", "error", sid, msg))

    used_cards: set = set()

    for i, s in enumerate(shots):
        sid = s.shot_id

        # G01 frame grid
        if s.duration_s > 0:
            frames = _frame_count(s.duration_s)
            actual = frames / 24.0
            if abs(actual - s.duration_s) > GRID_TOL_S:
                f.append(Finding("G01", "error", sid,
                                 f"duration {s.duration_s}s -> {frames} frames = {actual:.2f}s, "
                                 f"off the 17k+5 grid by {abs(actual - s.duration_s):.2f}s"))

        # G02 generation continuity (mode + anchor feasibility)
        lead = _lead_character(s, char_names)
        if lead:
            used_cards.add(lead)
        if i == 0:
            if s.mode in ("I2VA", "FL2VA", "L2VA") and not s.first_frame and not lead:
                f.append(Finding("G02", "error", sid,
                                 f"mode={s.mode} but no first_frame and no character card to anchor"))
            elif s.mode not in ("T2VA", "I2VA", "FL2VA", "L2VA", "Ref2VA"):
                f.append(Finding("G02", "error", sid, f"unsupported mode for opening shot: {s.mode}"))
        else:
            if s.mode in ("I2VA", "FL2VA", "L2VA"):
                pass  # runner chains the previous shot's last frame
            elif s.mode == "T2VA":
                if not lead:
                    f.append(Finding("G02", "error", sid,
                                     "T2VA after shot 0 with no character card -> continuity break "
                                     "(faces/props reset). Use I2VA (last-frame chain) or add a character card."))
            elif s.mode == "Ref2VA" and not s.references:
                f.append(Finding("G02", "error", sid, "Ref2VA without any references"))
            else:
                f.append(Finding("G02", "error", sid, f"unsupported mode: {s.mode}"))

        # G03 dialogue fit
        for line in s.dialogue:
            est = _speech_seconds(line.text, proj.dialogue_language)
            rng = _parse_rng(line.time_range)
            if rng:
                window = rng[1] - rng[0]
                if est > window * FIT_TOLERANCE:
                    f.append(Finding("G03", "error" if est > window else "warn", sid,
                                     f"dialogue {line.text!r} needs ~{est:.1f}s but window "
                                     f"{line.time_range} is {window:.1f}s (speaker={line.speaker_id})"))
            if est > s.duration_s:
                f.append(Finding("G03", "error", sid,
                                 f"dialogue {line.text!r} needs ~{est:.1f}s > shot length {s.duration_s}s"))
        total = sum(_speech_seconds(l.text, proj.dialogue_language) for l in s.dialogue)
        if total > s.duration_s * FIT_TOLERANCE:
            f.append(Finding("G03", "warn", sid,
                             f"all dialogue in shot ~{total:.1f}s exceeds {s.duration_s}s x {FIT_TOLERANCE}"))

        # G04 time ranges
        windows = []
        for line in s.dialogue:
            rng = _parse_rng(line.time_range)
            if not rng:
                if line.text:
                    f.append(Finding("G04", "warn", sid,
                                     f"dialogue {line.text[:12]!r} has no parseable time_range ({line.time_range!r})"))
                continue
            a, b = rng
            if a >= b:
                f.append(Finding("G04", "error", sid, f"invalid time_range {line.time_range!r}"))
            elif b > s.duration_s + 0.01:
                f.append(Finding("G04", "error", sid,
                                 f"time_range {line.time_range} exceeds shot length {s.duration_s}s"))
            windows.append((a, b, line.text[:12]))
        for (a1, b1, t1), (a2, b2, t2) in zip(windows, windows[1:]):
            if a2 < b1 - 0.01:
                f.append(Finding("G04", "error", sid, f"overlapping dialogue windows: {t1!r} & {t2!r}"))

        # G05 speakers
        for line in s.dialogue:
            bound = any(r.char == line.speaker_id for r in s.references)
            if line.speaker_id not in char_names and not bound:
                f.append(Finding("G05", "warn", sid,
                                 f"speaker {line.speaker_id!r} not in characters[] and not bound to a reference"))

        # G08 reference labels
        labels = [r.label for r in s.references]
        if len(labels) != len(set(labels)):
            f.append(Finding("G08", "error", sid, f"duplicate reference labels: {labels}"))
        for lab in labels:
            if not re.fullmatch(r"<[A-Za-z]+ \d+>", lab):
                f.append(Finding("G08", "warn", sid, f"reference label {lab!r} not in '<Kind n>' form"))

    # G06 character cards on disk
    for c in proj.characters:
        if c.image_path and not os.path.exists(c.image_path):
            lvl = "error" if c.name in used_cards else "warn"
            f.append(Finding("G06", lvl, "-",
                             f"character card missing on disk: {c.name} -> {c.image_path}"))

    # G07 compiled H3 prompt cross-check (shuohao: 逐字对账)
    try:
        compiled = _prompt.compile_all(proj)
    except Exception as e:
        f.append(Finding("G07", "error", "-", f"prompt compile crashed: {e}"))
        compiled = {}
    for s in shots:
        p = compiled.get(s.shot_id, "")
        if not p:
            continue
        if s.mode == "Ref2VA":
            for sec in ("subject_definitions:", "summary:", "retention_analysis:",
                        "detailed_description:", "overall_soundscape:", "non_diegetic_music:"):
                if sec not in p:
                    f.append(Finding("G07", "error", s.shot_id, f"Ref2VA prompt missing section {sec!r}"))
        else:
            for sec in ("integrated_multimodal_description:", "overall_soundscape:", "non_diegetic_music:"):
                if sec not in p:
                    f.append(Finding("G07", "error", s.shot_id, f"prompt missing section {sec!r}"))
            if s.mode == "I2VA" and "0.00 seconds into the target video" not in p:
                f.append(Finding("G07", "error", s.shot_id,
                                 "I2VA prompt missing the official 0.00s alignment line"))
        for line in s.dialogue:
            if line.text and line.text not in p:
                f.append(Finding("G07", "error", s.shot_id,
                                 f"dialogue {line.text!r} not found verbatim in compiled prompt"))

    return f


def _log(findings: List[Finding], project_dir: str, title: str):
    if not findings:
        return
    path = os.path.join(project_dir, ".gates.jsonl")
    with open(path, "a", encoding="utf-8") as fh:
        for x in findings:
            fh.write(json.dumps(
                {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "project": title,
                 "gate": x.gate, "shot": x.shot, "level": x.level, "detail": x.detail},
                ensure_ascii=False) + "\n")


def main(argv: Optional[List[str]] = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        print(__doc__)
        return 2

    if argv[0] == "stats":
        d = argv[1] if len(argv) > 1 else "."
        path = os.path.join(d, ".gates.jsonl")
        if not os.path.exists(path):
            print("no .gates.jsonl here yet")
            return 0
        counts: dict = {}
        total = 0
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            total += 1
            key = (r.get("gate"), r.get("level"))
            counts[key] = counts.get(key, 0) + 1
        print(f"gate failures accumulated: {total} ({path})")
        for (gate, lvl), n in sorted(counts.items(), key=lambda kv: -kv[1]):
            print(f"  {gate:8s} {lvl:5s} x{n}")
        return 0

    proj_path = argv[0]
    no_log = "--no-log" in argv
    log_dir = os.path.dirname(os.path.abspath(proj_path))
    if "--log-dir" in argv:
        pos = argv.index("--log-dir")
        if pos + 1 >= len(argv):
            raise SystemExit("--log-dir requires a directory")
        log_dir = os.path.abspath(argv[pos + 1])
        os.makedirs(log_dir, exist_ok=True)
    proj, raw = _load(proj_path)
    findings = check_project(proj, raw)
    errs = [x for x in findings if x.level == "error"]
    warns = [x for x in findings if x.level == "warn"]
    for x in findings:
        mark = "FAIL" if x.level == "error" else "warn"
        print(f"[{mark}] {x.gate} {x.shot}: {x.detail}")
    if not findings:
        print(f"OK: all gates passed ({len(proj.shots)} shots, {proj.title or 'untitled'})")
    else:
        print(f"-> {len(errs)} error(s), {len(warns)} warning(s) in {proj.title or 'untitled'}")
    if not no_log:
        _log(findings, log_dir, proj.title)
    return 1 if errs else 0


if __name__ == "__main__":
    raise SystemExit(main())
