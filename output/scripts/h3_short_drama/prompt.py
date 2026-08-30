"""H3 prompt compiler.

Turns a Shot (data.py) into a H3-compliant prompt following the official spec
distilled from MiniMax H3 skills + ComfyUI-MiniMaxH3-Director:
  - Base modes (T2VA/I2VA/FL2VA/L2VA): 3 sections
  - Ref2VA: 6 sections
  - speaker IDs (S1,S2...) assigned by speaking order across the project
  - dialogue rule: diegetic line -> <d>[Lang] text</d> with speaker; narration -> plain VO
  - retention vocabulary emitted verbatim
  - storyboard double-binding labels stripped
"""
from __future__ import annotations

import re
from .data import Project, Shot

_LABEL_RE = re.compile(r"\[(char|scene|shot|dur|hook):[^\]]*\]")


def _strip_storyboard_labels(text: str) -> str:
    """Remove [char:…] [scene:…] [shot:…] [dur:…] [hook:…] markers."""
    return _LABEL_RE.sub("", text or "").strip()


def assign_speaker_ids(project: Project) -> None:
    """Assign stable S1,S2,... by order of first appearance across all shots.

    Mirrors the Director rule: speaking order across the whole timeline; the same
    speaker keeps the same ID; IDs do NOT leak into retention_analysis.
    """
    order: list[str] = []
    for shot in project.shots:
        for line in shot.dialogue:
            key = line.speaker_id if not line.speaker_id.startswith("S") else _raw_speaker(line.speaker_id)
            if key and key not in order:
                order.append(key)
    mapping = {}
    for i, raw in enumerate(order, 1):
        mapping[raw] = f"S{i}"
    for shot in project.shots:
        for line in shot.dialogue:
            if not line.speaker_id.startswith("S"):
                line.speaker_id = mapping.get(_raw_speaker(line.speaker_id), f"S{_raw_speaker(line.speaker_id).zfill(2)}")


def _raw_speaker(speaker_id: str) -> str:
    # allow "S01" back to "01"
    m = re.fullmatch(r"S(\d+)", speaker_id)
    return m.group(1) if m else speaker_id


def _lang_tag(language: str) -> str:
    return {"中文": "Chinese", "zh": "Chinese", "en": "English", "English": "English",
            "日本語": "Japanese", "ja": "Japanese"}.get(language, "Chinese")


def _speaker_label_resolver(shot: Shot) -> "dict[str, str]":
    """Map a character's raw name -> its reference label for this shot.

    Prefers an explicit `char` binding on a Reference; falls back to substring
    match in description, then the first subject/picture reference, then '<Subject>'.
    """
    resolver: dict[str, str] = {}
    first = next((r.label for r in shot.references if r.kind in ("person", "animal")), None)
    for name in {line.speaker_id for line in shot.dialogue}:
        hit = next((r.label for r in shot.references if r.char == str(name)), None)
        if not hit:
            hit = next((r.label for r in shot.references
                        if name and (name in (r.description or ""))), None)
        resolver[str(name)] = hit or (first or "<Subject>")
    return resolver


def _dialogue_lines(shot: Shot, language: str) -> list[str]:
    out = []
    lang = _lang_tag(language)
    resolver = _speaker_label_resolver(shot)
    for line in shot.dialogue:
        label = resolver.get(line.speaker_id, "<Subject>")
        if line.is_diegetic:
            out.append(f"{label} ({line.speaker_id}) says, <d>[{lang}] {line.text}</d>")
        else:
            out.append(f"narration ({label}, voice over, mouth closed): {line.text}")
    return out


def _per_second_block(shot: Shot) -> str:
    lines = []
    for ps in shot.per_second:
        parts = []
        if ps.action:
            parts.append(ps.action)
        if ps.camera:
            parts.append(f"camera: {ps.camera}")
        if ps.spatial:
            parts.append(f"spatial: {ps.spatial}")
        if ps.audio:
            parts.append(f"audio: {ps.audio}")
        if ps.handoff:
            parts.append(f"handoff: {ps.handoff}")
        if parts:
            lines.append(f"  {ps.rng}: " + "; ".join(parts))
    return "\n".join(lines)


def _anchors_block(shot: Shot) -> str:
    out = []
    if shot.fixed_landmarks:
        out.append("Fixed landmarks: " + "; ".join(shot.fixed_landmarks))
    if shot.char_positions:
        out.append("Character positions: " + "; ".join(f"{k}={v}" for k, v in shot.char_positions.items()))
    if shot.exited_chars:
        out.append("Exited: " + "; ".join(shot.exited_chars))
    if shot.lighting_baseline:
        out.append(f"Lighting baseline: {shot.lighting_baseline}")
    if shot.continuity_handoff:
        out.append(f"Continuity handoff: {shot.continuity_handoff}")
    return "\n".join(out)


def compile_base_prompt(shot: Shot, project: Project) -> str:
    """T2VA/I2VA/FL2VA/L2VA -> 3-section H3 prompt."""
    # official image-alignment first line (I2VA/FL2VA/L2VA), blank line, then 3 fields
    align = _alignment_line(shot)
    description = []
    description.append(f"[Shot 1] {shot.shot_description}")
    if shot.per_second:
        description.append("Per-second directives:\n" + _per_second_block(shot))
    # spatial/identity anchors (continuity spine + screen positions + lighting)
    description.append(_anchors_block(shot))
    # dialogue
    dl = _dialogue_lines(shot, project.dialogue_language)
    if dl:
        description.append("Dialogue: " + " ".join(dl))
    # H3 packaging prefix (design language / motion clarity / dual-channel audio intent)
    style = project.visual_style or "clean stylized rendering, strong character design language, on-brand color palette, clean motion"
    imd = "\n".join([f"Style: {style}", *[l for l in description]]).strip()

    # overall_soundscape
    sfx = shot.sfx or []
    ambient = "ambience" if "无对白" not in project.dialogue_mode else "silent"
    soundscape = "; ".join(sfx) if sfx else ambient
    soundscape += f"; hook: {shot.hook_type}"

    music = "diegetic ambient only; no score unless the shot calls for it"

    head = (align + "\n\n") if align else ""
    return (
        f"{head}integrated_multimodal_description:\n{imd}\n\n"
        f"overall_soundscape: {soundscape}\n\n"
        f"non_diegetic_music: {music}"
    )


def _alignment_line(shot: Shot) -> str:
    if shot.mode == "I2VA":
        return ("For the target video, at 0.00 seconds into the target video, "
                "<Picture 1> (from [Shot 1]) is fully referenced.")
    if shot.mode == "FL2VA":
        return ("How the reference pictures align with the target video — "
                "Picture 1 (from Shot 1) aligns with the 0.00-second mark of the target video; "
                "Picture 2 (from Shot 1) aligns with the final-second mark of the target video.")
    if shot.mode == "L2VA":
        return ("How the reference pictures align with the target video — "
                "<Picture 1> (from [Shot 1]) aligns with the final-second mark of the target video.")
    return ""


def compile_ref_prompt(shot: Shot, project: Project) -> str:
    """Ref2VA -> 6-section H3 prompt."""
    subjects = []
    retention = []
    for ref in shot.references:
        desc = ref.description or f"{ref.kind} reference"
        subjects.append(f"<{ref.label.split('<')[1].split('>')[0]} {ref.label}> is {desc}." if False else f"{_name_of(ref.label)} is {desc}.")
        retention.append(f"{_name_of(ref.label)}: {ref.retention}" + (f" - {ref.retention_note}" if ref.retention_note else " - retain identity, costume and screen position across the shot."))

    summary = f"[{'/'.join(_task_prefix(shot))}] The target video {shot.shot_description}"

    detailed = []
    detailed.append(_anchors_block(shot))
    if shot.per_second:
        detailed.append("Per-second directives:\n" + _per_second_block(shot))
    dl = _dialogue_lines(shot, project.dialogue_language)
    if dl:
        detailed.append("Dialogue: " + " ".join(dl))

    sfx = "; ".join(shot.sfx) if shot.sfx else "ambient room tone"
    music = "diegetic only unless the shot calls for a score"

    return "\n\n".join([
        "subject_definitions:\n" + "\n".join(subjects),
        f"summary: {summary}",
        "retention_analysis:\n" + "\n".join(retention),
        "detailed_description:\n" + "\n".join(d for d in detailed if d),
        f"overall_soundscape: {sfx}; hook: {shot.hook_type}",
        f"non_diegetic_music: {music}",
    ])


def _name_of(label: str) -> str:
    # "<Subject 1>" -> "Subject 1"
    return label.strip("<>").strip()


def _task_prefix(shot: Shot) -> list[str]:
    p = []
    if shot.first_frame and shot.last_frame:
        p.append("keyframe completion")
    elif shot.last_frame:
        p.append("last-frame convergence")
    elif shot.first_frame:
        p.append("first-frame development")
    if shot.references:
        p.append("reference generation")
    return p or ["text generation"]


def compile(shot: Shot, project: Project) -> str:
    if shot.mode == "Ref2VA":
        return compile_ref_prompt(shot, project)
    return compile_base_prompt(shot, project)


def compile_all(project: Project) -> dict[str, str]:
    """Return {shot_id: prompt} for the whole project."""
    assign_speaker_ids(project)
    return {s.shot_id: compile(s, project) for s in project.shots}
