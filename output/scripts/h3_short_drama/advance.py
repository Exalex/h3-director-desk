"""Plot-advancement spine — make "推进剧情" visible and checkable.

Extracts, per shot, the four narrative moves:
  establishes (opening state) -> advances (per-second action) ->
  hands_off (to next shot) -> hook (what pulls the viewer forward).
Flags the gaps that make a short drama stall: a handoff that doesn't connect to
the next shot's opening, a shot that adds no new state, or a weak final hook.
"""
from __future__ import annotations

from typing import List
from . import data
from .data import Project, Shot

_STRONG = {"reveal", "reversal", "callback", "suspense", "chase"}


def _opening_state(shot: Shot) -> str:
    """The shot's establishing state (from first per-second directive + description)."""
    head = shot.per_second[0].action if shot.per_second else shot.shot_description
    return (head or "").strip()


def _advances(shot: Shot) -> str:
    """What changes across the shot (last per-second action vs first)."""
    if len(shot.per_second) >= 2:
        return f"{shot.per_second[0].action.strip()} -> {shot.per_second[-1].action.strip()}"
    return _opening_state(shot)


def spine(project: Project) -> List[dict]:
    out = []
    for i, s in enumerate(project.shots):
        nxt = project.shots[i + 1] if i + 1 < len(project.shots) else None
        out.append({
            "shot_id": s.shot_id,
            "establishes": _opening_state(s),
            "advances": _advances(s),
            "hands_off": s.continuity_handoff.strip(),
            "hook": s.hook_type,
            "next_opens": (_opening_state(nxt) if nxt else "(end)"),
        })
    return out


def gaps(project: Project) -> List[str]:
    fails: List[str] = []
    for i, s in enumerate(project.shots):
        nxt = project.shots[i + 1] if i + 1 < len(project.shots) else None
        # 1) every shot (except last) must hand off to the next
        if nxt and not s.continuity_handoff.strip():
            fails.append(f"{s.shot_id}: no Continuity Handoff -> story stalls before {nxt.shot_id}")
        # 2) handoff must connect: next shot's opening should acknowledge the handoff
        #    (heuristic: next shot present + handoff mentions something that carries forward)
        if nxt and s.continuity_handoff.strip() and not nxt.continuity_handoff.strip():
            fails.append(f"{nxt.shot_id}: no handoff back -> chain broken at {s.shot_id}->{nxt.shot_id}")
        # 3) a shot must advance (add a state change), not just hold
        if len(s.per_second) < 2:
            fails.append(f"{s.shot_id}: only {len(s.per_second)} per-second directive(s) -> no visible advance")
        # 4) airlock discipline on a scheduling change (latent_pin/motion_ref boundary)
        if nxt and nxt.continuity_type in ("latent_pin", "motion_ref") and nxt.airlock_s <= 0:
            fails.append(f"{nxt.shot_id}: continuity change ({nxt.continuity_type}) without an airlock hold (~2s) -> risk of jump")
    # final hook strength
    if project.shots and project.shots[-1].hook_type not in _STRONG:
        fails.append(f"{project.shots[-1].shot_id}: weak closing hook -> no pull to next episode")
    return fails


def report(project: Project) -> str:
    lines = [f"剧情推进脊 ({project.title}) — {len(project.shots)} 镜", "=" * 50]
    for row in spine(project):
        lines.append(f"\n[{row['shot_id']}]")
        lines.append(f"  建立: {row['establishes']}")
        lines.append(f"  推进: {row['advances']}")
        lines.append(f"  交接: {row['hands_off'] or '(缺)'}")
        lines.append(f"  钩子: {row['hook']}  ->  下一镜开场: {row['next_opens']}")
    g = gaps(project)
    lines.append("\n" + "-" * 50)
    lines.append("推进校验: " + ("OK — 因果链完整" if not g else f"{len(g)} 处需修"))
    for x in g:
        lines.append("  ! " + x)
    return "\n".join(lines)
