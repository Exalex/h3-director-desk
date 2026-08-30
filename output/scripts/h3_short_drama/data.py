"""Data model for the H3 short-drama pipeline.

Pure-stdlib dataclasses mirroring the schema distilled from:
- official MiniMax H3 skills (3d-animation-short-generator shot table)
- ComfyUI-MiniMaxH3-Director (timeline_data / subjects / retention)
- Jellyfish (shot detail enums / provider contracts)
"""
from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import Dict, List, Optional

# --- enums (string constants, match H3/ComfyUI) ---
ASPECTS = ["21:9", "16:9", "4:3", "1:1", "3:4", "9:16", "2:1", "3:2", "5:4", "4:5", "2:3", "1:2", "9:21"]
H3_MODES = ["T2VA", "I2VA", "FL2VA", "L2VA", "Ref2VA"]
RETENTION_VISUAL = ["fully_preserved", "partially_preserved", "attribute_transfer", "weak_reference"]
RETENTION_AUDIO = ["fully_copy", "partially_copy", "reference", "weak_reference"]
HOOK_TYPES = ["visual-joke", "reversal", "suspense", "tender", "chase", "reveal", "callback", "expression-beat"]
CONTINUITY = ["hard_cut", "latent_pin", "motion_ref"]

CAMERA_SHOTS = ["ECU", "CU", "MCU", "MS", "MLS", "LS", "ELS"]          # 景别
CAMERA_ANGLES = ["EYE_LEVEL", "HIGH_ANGLE", "LOW_ANGLE", "BIRD_EYE", "DUTCH", "OVER_SHOULDER"]
CAMERA_MOVEMENTS = ["STATIC", "PAN", "TILT", "DOLLY_IN", "DOLLY_OUT", "TRACK", "CRANE", "HANDHELD", "STEADICAM", "ZOOM_IN", "ZOOM_OUT"]
VIDEO_MODELS = ["H3", "Seedance2"]


@dataclass
class Reference:
    """A reference asset bound to a shot (Ref2VA subject/picture/video/audio)."""
    label: str                       # "<Subject 1>", "<Picture 2>", "<Video 1>", "<Audio 1>"
    kind: str = "person"             # person/animal/object/environment/clothing/prop/interface/effect/style/action/expression/pose
    retention: str = "fully_preserved"
    retention_note: str = ""
    path: str = ""                   # image/video/audio file
    description: str = ""
    char: str = ""                   # character name this reference binds to (for dialogue speaker mapping)
    used_as: str = "frame_anchor"    # frame_anchor | storyboard | defines_subject


@dataclass
class PerSecond:
    """One second's directive. Must cover the 5 required elements."""
    rng: str                         # "0-1s" or "2.0-2.5s"
    action: str = ""                 # 1. action/pose/expression
    camera: str = ""                 # 2. camera movement
    spatial: str = ""                # 3. spatial position
    audio: str = ""                  # 4. audio cue
    handoff: str = ""                # 5. handoff to next second/shot


@dataclass
class DialogueLine:
    text: str
    speaker_id: str = "S1"          # stable speaker id
    tone: str = ""
    time_range: str = ""
    is_diegetic: bool = True         # on-screen dialogue vs narration


@dataclass
class Shot:
    """One row of the standardized shot table."""
    shot_id: str
    duration_s: int
    continuity_handoff: str
    fixed_landmarks: List[str] = field(default_factory=list)
    char_positions: Dict[str, str] = field(default_factory=dict)
    exited_chars: List[str] = field(default_factory=list)
    lighting_baseline: str = ""
    hook_type: str = "expression-beat"
    shot_description: str = ""
    per_second: List[PerSecond] = field(default_factory=list)
    narration: str = ""
    dialogue: List[DialogueLine] = field(default_factory=list)
    sfx: List[str] = field(default_factory=list)
    # generation params
    mode: str = "I2VA"               # T2VA/I2VA/FL2VA/L2VA/Ref2VA
    video_model: str = "H3"
    resolution_tier: str = "768P"    # 768P | 2K | draft
    aspect: str = "9:16"
    references: List[Reference] = field(default_factory=list)
    first_frame: str = ""
    last_frame: str = ""
    negative: str = "morphing, flickering, distorted face, extra fingers, blurry, low quality, watermark, text overlay"
    continuity_type: str = "hard_cut"  # hard_cut | latent_pin | motion_ref
    airlock_s: float = 0.0
    seed: int = 0                      # explicit fixed seed (定卡); 0 = auto per-shot seed
    edit_target_s: float = 0.0         # edit/trim target in seconds (0 = use duration_s)

    @classmethod
    def from_dict(cls, d: dict) -> "Shot":
        """Parse a shot dict, ignoring unknown keys (e.g. free-form metadata)."""
        keep = {f.name for f in fields(cls)}
        d = {k: v for k, v in d.items() if k in keep}
        d["per_second"] = [PerSecond(**p) for p in d.get("per_second", [])]
        d["dialogue"] = [DialogueLine(**x) for x in d.get("dialogue", [])]
        d["references"] = [Reference(**r) for r in d.get("references", [])]
        return cls(**d)


@dataclass
class CharacterCard:
    name: str
    identity_note: str              # visual-ID anchor: age/body/hair/costume/prop/do-not-change
    image_path: str = ""
    do_not_change: List[str] = field(default_factory=list)


@dataclass
class SceneCard:
    name: str
    description: str
    landmarks: List[str] = field(default_factory=list)   # fixed landmarks w/ screen position
    light_baseline: str = ""
    image_path: str = ""


@dataclass
class Project:
    title: str
    what_if: str
    target_feeling: str = ""
    aspect: str = "9:16"
    duration_s: int = 45
    dialogue_mode: str = "有对白"
    dialogue_language: str = "未指定"
    visual_style: str = ""
    characters: List[CharacterCard] = field(default_factory=list)
    scenes: List[SceneCard] = field(default_factory=list)
    shots: List[Shot] = field(default_factory=list)
