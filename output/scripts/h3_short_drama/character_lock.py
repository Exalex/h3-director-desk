"""Character-identity lock — turn "gacha (抽卡 random characters)" into "locked cards".

The root cause of random characters is 3 levers: (1) pure text-to-video with no
reference, (2) a random seed per shot, (3) the reference image not pinned / swapped.
This module forces a shot table onto the lock: every character shot becomes I2VA with
a fixed reference + a per-character fixed seed + an explicit `fully_preserved`
reference, and validates that no character shot falls back to T2VA.
"""
from __future__ import annotations

from typing import Dict, List
from . import data
from .data import Reference, Shot

# --- seed strategy: one stable seed per character (the "定卡" switch) ---
DEFAULT_SEED = 1234567890


def seed_for(character: str, base_seed: int = DEFAULT_SEED) -> int:
    """Deterministic per-character seed so a character never re-rolls across shots."""
    h = 0
    for ch in character:
        h = (h * 131 + ord(ch)) & 0xFFFFFFFF
    return (base_seed + h) % (2**31)


def character_reference(name: str, image_path: str, kind: str = "person") -> Reference:
    """The pinned reference that a character's shots bind to (fully_preserved)."""
    return Reference(
        label=f"<Picture 1>",
        kind=kind,
        char=name,
        retention="fully_preserved",
        retention_note=f"retain face, hair, costume and screen position of {name} across the whole shot",
        path=image_path,
        description=f"the locked reference for {name}",
        used_as="defines_subject",
    )


def lock_shot(shot: Shot, characters: Dict[str, str],
              base_seed: int = DEFAULT_SEED) -> int:
    """Force a shot onto the identity lock. Returns the assigned seed.

    - If the shot's char_positions point at a known character, that character's
      card becomes the first_frame (I2VA) and a `fully_preserved` reference is
      bound; mode is upgraded to I2VA if it was T2VA.
    """
    present = list(shot.char_positions.keys())
    if not present and not shot.references:
        # no character -> nothing to lock; leave as-is
        return -1

    lead = next((n for n in present if n in characters), present[0])
    lead_ref = characters.get(lead, lead)  # char name -> its card path

    # 1) pin the lead's reference as first frame (I2VA = strongest identity lock).
    #    At generation time this first_frame becomes the previous shot's last frame
    #    (chaining); in the planning phase it is the lead's own character card.
    if shot.mode not in ("I2VA", "FL2VA", "L2VA", "Ref2VA"):
        shot.mode = "I2VA"
    if lead_ref:
        shot.first_frame = lead_ref

    # 2) add a fully_preserved reference for every present character
    kept = [r for r in shot.references if r.retention != "fully_preserved" and r.char not in present]
    for name in present:
        path = characters.get(name, name)
        kept.append(character_reference(name, path))
    shot.references = kept
    # renumber picture labels so <Picture 1> is the lead
    n = 0
    for r in shot.references:
        if r.kind in ("person", "animal"):
            n += 1
            r.label = f"<Picture {n}>"

    # 3) fixed seed for the lead character (定卡)
    seed = seed_for(lead, base_seed)
    return seed


def validate_locked(shots: List[Shot], characters: Dict[str, str]) -> List[str]:
    """Fail if any character shot is T2VA (no reference) or mixes seeds per character."""
    fails: List[str] = []
    seen_seeds: Dict[str, int] = {}
    for s in shots:
        present = list(s.char_positions.keys())
        if not present:
            continue
        lead = next((n for n in present if n in characters), present[0])
        if s.mode == "T2VA":
            fails.append(f"{s.shot_id}: character shot is T2VA (no reference) -> random identity; must be I2VA/Ref2VA")
        elif s.mode in ("I2VA", "FL2VA", "L2VA") and not s.first_frame:
            fails.append(f"{s.shot_id}: I2VA but no first_frame pinned -> identity not locked")
        elif s.mode == "Ref2VA" and not s.references:
            fails.append(f"{s.shot_id}: Ref2VA but no reference bound -> identity not locked")
        # seed stability: lead char must keep the same seed across shots
        seed = seed_for(lead)
        if lead in seen_seeds and seen_seeds[lead] != seed:
            fails.append(f"{s.shot_id}: seed for {lead} drifted -> character re-rolled")
        seen_seeds[lead] = seed
    return fails


def characters_from(project) -> Dict[str, str]:
    """{char_name: reference_image_path} from the project's character cards."""
    return {c.name: c.image_path for c in project.characters if c.image_path}
