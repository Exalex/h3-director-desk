#!/usr/bin/env python3
"""Interactive creator for a small H3 short-drama project JSON.

This creates the planning file only. It does not start ComfyUI or use a GPU.
Run run_project.sh separately after reviewing the JSON.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def ask(label: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{label}{suffix}: ").strip()
    return value or default


def main() -> int:
    ap = argparse.ArgumentParser(description="create a project JSON without starting generation")
    ap.add_argument("--out", default="projects/new_project.json")
    args = ap.parse_args()

    title = ask("项目名", "新短剧")
    description = ask("一句话描述", "夜晚酒店大堂，两个人进行一个安静的动作")
    duration = float(ask("视频时长（建议 10.1）", "10.1"))
    female = ask("女角色名", "林晚")
    male = ask("男角色名", "沈亦")
    female_card = ask("女角色卡路径", "/home/exalex/ComfyUI/input/role_female.png")
    male_card = ask("男角色卡路径", "/home/exalex/ComfyUI/input/role_male.png")
    dialogue = ask("女角色台词（可留空）", "")
    dialogue_time = ask("台词时间范围", "6-8s" if dialogue else "")

    end = f"{duration:g}"
    lines = [
        {"rng": f"0-3s", "action": "两人进入并站定", "camera": "medium static shot",
         "spatial": f"{female} left, {male} right", "audio": "soft room tone", "handoff": "双方就位"},
        {"rng": f"3-6s", "action": "女角色拿出道具并接近男角色", "camera": "push in",
         "spatial": "hands move toward center", "audio": "quiet object movement", "handoff": "动作准备完成"},
        {"rng": f"6-{end}s", "action": "两人完成核心动作并保持关系连续", "camera": "close shot",
         "spatial": "hands centered", "audio": "clear action sound", "handoff": "动作完成"},
    ]
    shot = {
        "shot_id": "S01", "duration_s": duration, "continuity_handoff": "action begins and resolves",
        "fixed_landmarks": ["hotel lobby", "sofa center"],
        "char_positions": {female: "left, center action", male: "right, seated"},
        "lighting_baseline": "warm hotel lobby at night", "hook_type": "reveal",
        "shot_description": description, "per_second": lines,
        "dialogue": ([{"text": dialogue, "speaker_id": female, "tone": "quiet and focused",
                        "time_range": dialogue_time, "is_diegetic": True}] if dialogue else []),
        "sfx": ["room ambience", "action sound"], "mode": "I2VA", "video_model": "H3",
        "resolution_tier": "768P", "aspect": "9:16",
        "first_frame": female_card, "references": [],
    }
    data = {
        "title": title, "what_if": description, "target_feeling": "quiet tension",
        "aspect": "9:16", "duration_s": duration, "dialogue_mode": "有对白" if dialogue else "无对白",
        "dialogue_language": "中文", "visual_style": "cinematic live-action, consistent character design",
        "characters": [
            {"name": female, "identity_note": "female lead, preserve face, hair and costume",
             "image_path": female_card, "do_not_change": ["face", "hair", "costume"]},
            {"name": male, "identity_note": "male lead, preserve face, hair and costume",
             "image_path": male_card, "do_not_change": ["face", "hair", "costume"]},
        ],
        "scenes": [], "shots": [shot],
    }
    out = Path(args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"已创建任务文件: {out}")
    print("下一步先检查，再生成：")
    print(f"  PYTHONPATH=output/scripts python -m h3_short_drama validate --shots {out} --no-log")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
