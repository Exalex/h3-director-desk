"""Creative layer: idea -> 15-field concept -> standardized shot table.

Embeds the distilled 爆款方法论 (SDCC 7 rules + ai-script-hub 5 golden laws) and the
6-column shot-table schema as the system prompt. Dry-run safe: without an LLM key it
prints the exact prompt; with OPENAI_API_KEY (or --provider) it calls an
OpenAI-compatible /v1/chat/completions endpoint and parses JSON into data.Project.
"""
from __future__ import annotations

import json
import os
from typing import Optional
from . import data, shot_table

# --- methodology (condensed from skill/references/methodology.md) ---
METHODOLOGY = """你是一名爆款竖屏短剧编剧 + H3 分镜师。
调性检验：✅"她好厉害我也想这样" / ❌"她好惨但挺过来了"（苦情不是短剧）。
三幻想来源：能力/身份/行动。喜剧公式=奇幻触发器×极端身份错位×家庭情感×喜剧×治愈(≥3/5)。
CP是调味料不是主菜；主引擎是"看她怎么做"。
五黄金法则：①竖屏思维(半身/特写为主) ②节奏(每15-20s一个情绪点,每集≥3高潮) ③对白简洁(一句≤20字) ④爽点密集(打脸/反转/告白/揭秘交替) ⑤结尾钩子(最后一句/画面必是悬念)。
女主三关：配得感/快意恩仇/主体性。标题5铁律：情绪承诺/反差/动词/4字或长句/迭代高频词。
"""

SHOT_TABLE_SCHEMA = """标准分镜表 6 列（严格）：
1) shot_id+时长(≤15s) 2) Continuity Handoff(跨镜连续脊柱)
3) Reference Anchors: fixed_landmarks(具名地标+屏幕位置)/char_positions(每角色屏幕位置+朝向)/exited_chars/lighting_baseline + 身份绑定
4) hook_type ∈ visual-joke|reversal|suspense|tender|chase|reveal|callback|expression-beat
5) shot_description + per_second(逐秒,每条含5要素: action/camera/spatial/audio/handoff)
6) audio_track: narration/dialogue(text,speaker_id,tone,time_range,is_diegetic)/sfx
规则：每镜≤15s；单镜≤3重要角色；同场景连续镜继承地标+光线或显式标注；0s到镜时长逐秒无空洞；
跨镜Continuity Handoff成链(翻转视线/位置/道具/光线须显式 HARD CUT/time skip)；每3镜≥1强钩子(reveal/reversal/callback/suspense/chase)；首镜尾镜各带强钩子。"""


def concept_prompt(idea: str, genre: str = "", feeling: str = "") -> str:
    tpl = (METHODOLOGY +
           "\n请基于下面的点子，输出 1 个 15 字段短剧概念（JSON 数组）。\n"
           "点子：__IDEA__\n题材：__GENRE__\n目标感受：__FEELING__\n"
           "15字段：title/what_if/fantasy_trigger/her_identity/her_action/extreme_mismatch/high_concept/"
           "one_liner/comedy_engine/family_line/her_test(配得感|快意恩仇|主体性, 各 true/false)/"
           "cp_beat/episode_structure(开场钩子→中段冲突→结尾悬念)/opening_hook/risk\n只输出 JSON。")
    return tpl.replace("__IDEA__", idea).replace("__GENRE__", genre or "自动").replace("__FEELING__", feeling or "爽感+反转")


def storyboard_prompt(idea: str, aspect: str = "9:16", duration_s: int = 45,
                      genre: str = "", language: str = "中文") -> str:
    tpl = (METHODOLOGY + "\n" + SHOT_TABLE_SCHEMA +
           "\n把下面的点子做成一集 __DUR__s、__ASPECT__ 竖屏短剧的标准分镜表（3-6 镜）。\n"
           "对白语言=__LANG__。对白：一句≤20字，说话人用角色名（如 陈锋），is_diegetic=true 表示画面对白。\n"
           "点子：__IDEA__\n题材：__GENRE__\n"
           "输出 JSON：__JSON__\n"
           "首镜/尾镜带强钩子。只输出 JSON。")
    json_schema = (
        '{"title","what_if","target_feeling","aspect","duration_s","dialogue_mode","dialogue_language",'
        '"visual_style",'
        '"characters":[{"name","identity_note","image_path","do_not_change":[...]}],'
        '"scenes":[{"name","description","landmarks":[...],"light_baseline","image_path"}],'
        '"shots":[{"shot_id","duration_s","continuity_handoff","fixed_landmarks":[...],'
        '"char_positions":{...},"exited_chars":[...],"lighting_baseline","hook_type",'
        '"shot_description","per_second":[{"rng","action","camera","spatial","audio","handoff"}],'
        '"narration","dialogue":[{"text","speaker_id","tone","time_range","is_diegetic"}],'
        '"sfx":[...],"mode","video_model","resolution_tier",'
        '"references":[{"label","kind","char","retention","retention_note","path","description"}],'
        '"first_frame","last_frame","negative","continuity_type","airlock_s"}]}')
    return (tpl.replace("__DUR__", str(duration_s)).replace("__ASPECT__", aspect)
             .replace("__LANG__", language).replace("__IDEA__", idea)
             .replace("__GENRE__", genre or "自动").replace("__JSON__", json_schema))


def _chat(prompt: str, system: str = "", model: str = "deepseek-chat",
          base: str = "", key: str = "", temperature: float = 0.8) -> Optional[str]:
    import urllib.request
    body = {
        "model": model,
        "messages": ([{"role": "system", "content": system}] if system else []) +
                     [{"role": "user", "content": prompt}],
        "temperature": temperature, "max_tokens": 8192,
        # Qwen thinking can consume the whole completion budget before the
        # JSON reaches `content`; this endpoint is used for structured output.
        "chat_template_kwargs": {"enable_thinking": False},
    }
    base = base or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    key = key or os.environ.get("OPENAI_API_KEY", "")
    headers = {"Content-Type": "application/json"}
    # Local OpenAI-compatible servers such as the Spark Qwen endpoint may not
    # require authentication; do not send an empty Bearer token.
    if key:
        headers["Authorization"] = f"Bearer {key}"
    req = urllib.request.Request(
        base + "/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers=headers,
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            d = json.loads(r.read().decode("utf-8"))
        return d["choices"][0]["message"]["content"]
    except Exception as e:
        return f"LLM_ERR: {e}"


def _extract_json(text: str):
    """Strip code fences + pull first JSON object/array (Jellyfish-style repair)."""
    t = (text or "").strip()
    t = t.replace("```json", "").replace("```", "").strip()
    # first balanced { ... } or [ ... ]
    for open_c, close_c in (("{", "}"), ("[", "]")):
        i = t.find(open_c)
        if i >= 0:
            depth = 0
            for j in range(i, len(t)):
                if t[j] == open_c:
                    depth += 1
                elif t[j] == close_c:
                    depth -= 1
                    if depth == 0:
                        try:
                            return json.loads(t[i:j + 1])
                        except json.JSONDecodeError:
                            break
    try:
        return json.loads(t)
    except Exception:
        return None


def generate_storyboard(idea: str, aspect: str = "9:16", duration_s: int = 45,
                        genre: str = "", language: str = "中文",
                        dry_run: bool = False) -> dict:
    """Return the project JSON dict (or a dry-run payload without a key)."""
    prompt = storyboard_prompt(idea, aspect, duration_s, genre, language)
    if dry_run:
        return {"dry_run": True, "note": "set OPENAI_API_KEY (or pass --execute) to call LLM",
                "prompt": prompt}
    raw = _chat(prompt, temperature=0.8)
    if raw is None:
        return {"dry_run": True, "note": "no LLM key; printing prompt", "prompt": prompt}
    obj = _extract_json(raw)
    if not obj:
        return {"error": "parse failed", "raw": raw}
    # validate the shot table
    proj = data.Project(**{k: obj.get(k, v) for k, v in
                           dict(title="", what_if="", target_feeling="", aspect=aspect,
                                duration_s=duration_s, dialogue_mode="有对白",
                                dialogue_language=language, visual_style="").items()
                           if k in obj},
                        shots=[data.Shot(**s) for s in obj.get("shots", [])])
    ok, fails = shot_table.self_check(proj)
    return {"project": obj, "self_check": {"pass": ok, "failures": fails}}


def generate_concept(idea: str, genre: str = "", feeling: str = "", dry_run: bool = False) -> dict:
    prompt = concept_prompt(idea, genre, feeling)
    if dry_run:
        return {"dry_run": True, "prompt": prompt}
    raw = _chat(prompt, temperature=0.7)
    if raw is None:
        return {"dry_run": True, "prompt": prompt}
    return {"raw": raw, "parsed": _extract_json(raw)}
