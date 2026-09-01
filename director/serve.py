#!/usr/bin/env python3
"""导演台 (Director Desk) — 本地 Web 后端.

把一个 H3 短剧制作项目(ep01.json + 角色卡 + 场景卡)的全流程封装成 JSON API,
前端是一个无构建的单页导演台。纯 stdlib,复用 output/scripts/h3_short_drama 管线。

用法:
    python director/serve.py [--port 8088] [--root <repo_root>]
    然后打开 http://127.0.0.1:8088/
"""
from __future__ import annotations

import argparse
import glob as _glob
import json
import os
import re
import sys
import threading
import time
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs, unquote

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # repo root
LLM_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "llm_config.json")
sys.path.insert(0, os.path.join(REPO, "output", "scripts"))
sys.path.insert(0, REPO)

import h3_short_drama as H3                       # noqa: E402
from h3_short_drama import data, prompt, shot_table, hardware  # noqa: E402
from h3_short_drama import assemble, comfyui_gen, validate_gates  # noqa: E402

DEFAULT_COMFY = os.environ.get("COMFY_BASE", "http://127.0.0.1:8188")
SPARK1_ARCHIVE_ROOT = os.environ.get("SPARK1_ARCHIVE_ROOT", "/home/exalex/h3Movie")

DEFAULT_LLM = {
    "provider": "spark",
    "name": "DGX Spark Qwen",
    "base_url": "http://192.168.3.75:8888/v1",
    "model": "qwen3.8-27b-sglang",
    "display_name": "Qwen3.8-27B DFlash2",
    "api_key": "",
}
try:
    _saved_llm = json.load(open(LLM_CONFIG_PATH, encoding="utf-8"))
    DEFAULT_LLM.update({k: _saved_llm[k] for k in DEFAULT_LLM if k in _saved_llm})
except Exception:
    pass

# ---- global config (overridable via query params / project) ----
CFG = {
    "comfy_base": os.environ.get("COMFY_BASE", DEFAULT_COMFY),
    "accel_base": os.environ.get("ACCEL_BASE", "http://192.168.100.11:8123"),
    "width": 768,
    "height": 1344,
    "steps": 12,
    "llm": DEFAULT_LLM,
}

# ---- long-running task registry ----
TASKS = {}
TASKS_LOCK = threading.Lock()
SERIES_LOCK = threading.Lock()
GENERATION_LOCK = threading.Lock()
WORKFLOW_LOCK = threading.Lock()

# conversational iteration: session key -> {history:[{role,content}], path}
CHAT_SESSIONS = {}
CHAT_LOCK = threading.Lock()


def new_task(kind, title, total=None):
    tid = uuid.uuid4().hex[:10]
    with TASKS_LOCK:
        TASKS[tid] = {"id": tid, "kind": kind, "title": title, "status": "running",
                      "started": time.time(), "done": None, "total": total, "cur": 0,
                      "log": [], "result": None, "error": None}
    return tid


def active_generation(rel, shot_id):
    """Return an existing running task for one episode/shot, if any."""
    key = f"{rel}::{shot_id}"
    with TASKS_LOCK:
        for task in TASKS.values():
            legacy_shot = task.get("shot_id") or task.get("title", "").removeprefix("generate ")
            is_legacy = not task.get("path") and not task.get("generation_key")
            if ((task.get("generation_key") == key) or (is_legacy and legacy_shot == shot_id)) and task.get("status") == "running":
                return task
    return None


def remote_generations(base):
    """Return queued ComfyUI jobs keyed by their SaveVideo filename prefix."""
    if not base:
        return []
    try:
        with urllib.request.urlopen(base.rstrip("/") + "/queue", timeout=2) as response:
            queue = json.loads(response.read().decode("utf-8"))
    except Exception:
        return []
    found = []
    seen = set()
    for group in ("queue_running", "queue_pending"):
        for queue_index, item in enumerate(queue.get(group, [])):
            if not isinstance(item, list) or len(item) < 3:
                continue
            prompt_id, workflow = item[1], item[2]
            if not isinstance(workflow, dict):
                continue
            for node in workflow.values():
                inputs = node.get("inputs", {}) if isinstance(node, dict) else {}
                shot_id = str(inputs.get("filename_prefix", ""))
                if (isinstance(node, dict) and node.get("class_type") == "SaveVideo"
                        and shot_id and prompt_id not in seen):
                    found.append({"id": f"comfy:{prompt_id}", "kind": "generate",
                                  "title": f"generate {shot_id}", "status": "running",
                                  "started": None, "path": "", "shot_id": shot_id,
                                  "cur": 1 if group == "queue_running" else 0, "total": 3,
                                  "error": None, "remote": True,
                                  "queue_group": group, "queue_position": queue_index + 1,
                                  "log": ["H3 正在运行" if group == "queue_running"
                                          else f"等待 GPU 调度，队列第 {queue_index + 1} 位"]})
                    seen.add(prompt_id)
    return found


def remote_generation(base, shot_id):
    """Find one queued ComfyUI job by its SaveVideo filename prefix."""
    return next((task for task in remote_generations(base) if task["shot_id"] == shot_id), None)


def task_append(tid, line):
    with TASKS_LOCK:
        if tid in TASKS:
            TASKS[tid]["log"].append(str(line))
            TASKS[tid]["log"] = TASKS[tid]["log"][-500:]


def task_progress(tid, cur, total=None):
    with TASKS_LOCK:
        if tid in TASKS:
            TASKS[tid]["cur"] = cur
            if total is not None:
                TASKS[tid]["total"] = total


def task_finish(tid, result=None, error=None):
    with TASKS_LOCK:
        if tid in TASKS:
            TASKS[tid]["status"] = "error" if error else "done"
            TASKS[tid]["done"] = time.time()
            TASKS[tid]["result"] = result
            TASKS[tid]["error"] = error


# ---------------------------------------------------------------------------
# path helpers
# ---------------------------------------------------------------------------

def _abs(rel):
    """Resolve a repo-relative path to absolute; forbid escaping repo."""
    if not rel:
        return None
    rel = unquote(rel).replace("\\", "/").lstrip("/")
    if rel.startswith(("http:", "https:", "http://")):
        return rel
    candidate = os.path.normpath(os.path.join(REPO, rel))
    if not candidate.startswith(os.path.normpath(REPO)):
        return None
    return candidate


def _find_projects():
    """Locate top-level project manifests; episodes are nested below them."""
    out = []
    for p in sorted(_glob.glob(os.path.join(REPO, "projects", "*", "project.json"))):
        rel = os.path.relpath(p, REPO).replace("\\", "/")
        try:
            with open(p, encoding="utf-8") as f:
                doc = json.load(f)
            if not isinstance(doc, dict) or doc.get("type", "project") != "project":
                continue
        except (OSError, ValueError, TypeError):
            continue
        out.append(rel)
    return out


def _project_dir(rel):
    """Return the isolated project folder for a manifest path."""
    p = _abs(rel)
    return os.path.dirname(p) if p else None


def _project_entry(rel):
    d, err = _load_project_doc(rel)
    folder = os.path.dirname(rel).replace("\\", "/")
    if err or not d:
        return {"path": rel, "folder": folder, "name": os.path.basename(folder)}
    episodes = []
    root = _project_dir(rel)
    for p in sorted(_glob.glob(os.path.join(root or "", "episodes", "**", "episode.json"), recursive=True)):
        ep_rel = os.path.relpath(p, REPO).replace("\\", "/")
        ep_doc, ep_err = _load_project_doc(ep_rel)
        if not ep_err and isinstance(ep_doc, dict) and isinstance(ep_doc.get("shots"), list):
            ep_folder = os.path.dirname(ep_rel).replace("\\", "/")
            episodes.append({"path": ep_rel, "folder": ep_folder,
                             "name": ep_doc.get("title") or os.path.basename(ep_folder),
                             "duration_s": ep_doc.get("duration_s", 0),
                             "shots": len(ep_doc.get("shots", []))})
    return {"path": rel, "folder": folder, "name": d.get("title") or os.path.basename(folder),
            "description": d.get("description", ""), "episodes": episodes,
            "assets": folder + "/assets"}


def _load_project_doc(rel):
    p = _abs(rel)
    if not p or not os.path.exists(p):
        return None, "project not found"
    try:
        return json.load(open(p, "r", encoding="utf-8")), None
    except Exception as e:
        return None, f"parse error: {e}"


def _project_output_dirs(rel):
    """Find timestamped output folders belonging to one project."""
    d, err = _load_project_doc(rel)
    if err or not d:
        return []
    title = re.sub(r"[\\/:*?\"<>|]+", "_", (d.get("title") or "project").strip()) or "project"
    local = os.path.join(_project_dir(rel) or "", "outputs")
    if os.path.isdir(local):
        return [os.path.relpath(local, REPO).replace("\\", "/")]
    pattern = os.path.join(REPO, "gen", f"{title}-*")
    dirs = [p for p in _glob.glob(pattern) if os.path.isdir(p)]
    return [os.path.relpath(p, REPO).replace("\\", "/")
            for p in sorted(dirs, key=os.path.getmtime, reverse=True)]


def _as_project(d):
    """Turn a project JSON dict into H3 data.Project."""
    chars = [data.CharacterCard(**c) for c in d.get("characters", [])]
    scenes = [data.SceneCard(**s) for s in d.get("scenes", [])]
    shots = [data.Shot.from_dict(s) for s in d.get("shots", [])]
    fields = {k: v for k, v in d.items()
              if k in ("title", "what_if", "target_feeling", "aspect", "duration_s",
                       "dialogue_mode", "dialogue_language", "visual_style")}
    return data.Project(**fields, characters=chars, scenes=scenes, shots=shots)


# ---------------------------------------------------------------------------
# stage runners
# ---------------------------------------------------------------------------

def run_check(rel):
    d, err = _load_project_doc(rel)
    if err:
        return {"error": err}
    proj = _as_project(d)
    ok, fails = shot_table.self_check(proj)
    return {"project": rel, "pass": bool(ok), "n_shots": len(proj.shots), "failures": fails}


def run_prompts(rel, out_dir=""):
    d, err = _load_project_doc(rel)
    if err:
        return {"error": err}
    proj = _as_project(d)
    comp = prompt.compile_all(proj)
    od = _abs(out_dir) if out_dir else os.path.join(_project_dir(rel) or REPO, "prompts")
    if od:
        os.makedirs(od, exist_ok=True)
        for sid, p in comp.items():
            with open(os.path.join(od, f"{sid}.txt"), "w", encoding="utf-8") as f:
                f.write(p)
    return {"project": rel, "n": len(comp),
            "prompts": {sid: {"chars": len(p), "preview": p[:1600]}
                        for sid, p in comp.items()},
            "full": comp}


def _is_blank_episode(doc):
    """Recognize the blank template so the first creative prompt creates a full episode."""
    if not isinstance(doc, dict):
        return True
    concept = str(doc.get("what_if") or "").strip()
    title = str(doc.get("title") or "").strip()
    shots = doc.get("shots") or []
    placeholder = "（待填写）"
    return (not concept or concept.startswith(placeholder) or
            (not title and not shots) or
            all(not str(s.get("shot_description") or "").strip() or
                str(s.get("shot_description") or "").startswith(placeholder)
                for s in shots if isinstance(s, dict)))


def _write_asset_plan(rel, doc):
    """Persist an asset inventory even before reference images are generated."""
    episode_dir = _project_dir(rel)
    if not episode_dir:
        return ""
    asset_dir = os.path.join(episode_dir, "assets")
    os.makedirs(asset_dir, exist_ok=True)
    plan = {
        "episode": rel,
        "status": "planned",
        "characters": [
            {"name": c.get("name", ""), "identity_note": c.get("identity_note", ""),
             "reference_path": c.get("image_path", ""),
             "status": "ready" if c.get("image_path") else "reference_pending"}
            for c in doc.get("characters", []) if isinstance(c, dict)
        ],
        "scenes": [
            {"name": s.get("name", ""), "description": s.get("description", ""),
             "landmarks": s.get("landmarks", []), "reference_path": s.get("image_path", ""),
             "status": "ready" if s.get("image_path") else "reference_pending"}
            for s in doc.get("scenes", []) if isinstance(s, dict)
        ],
    }
    target = os.path.join(asset_dir, "asset-plan.json")
    with open(target, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)
    return os.path.relpath(target, REPO).replace("\\", "/")


def run_chat_workflow(data, tid):
    """Run the workbench creative prompt through planning and prompt compilation."""
    path = data.get("path", "")
    feedback = (data.get("feedback") or "").strip()
    try:
        if not feedback:
            task_finish(tid, error="请输入故事创意")
            return
        doc, err = _load_project_doc(path)
        if err:
            task_finish(tid, error=err)
            return
        requested_mode = data.get("mode", "auto")
        mode = ("create" if requested_mode == "create" else
                "iterate" if requested_mode == "iterate" else
                "create" if _is_blank_episode(doc) else "iterate")
        mode_label = "整集创作" if mode == "create" else "当前集迭代"
        task_append(tid, f"已接收创意，模式：{mode_label}")
        task_progress(tid, 1, 5)

        result = chat_iter({"path": path, "mode": mode, "feedback": feedback})
        if result.get("error"):
            task_finish(tid, error=result["error"])
            return
        project = result["project"]
        task_append(tid, f"分镜规划完成：{len(project.get('shots', []))} 个镜头，"
                          f"{len(project.get('characters', []))} 个角色，"
                          f"{len(project.get('scenes', []))} 个场景")
        task_progress(tid, 2, 5)

        asset_path = _write_asset_plan(path, project)
        task_append(tid, f"资产清单已写入 {asset_path or '当前集 assets 目录'}")
        task_progress(tid, 3, 5)

        prompts = run_prompts(path)
        if prompts.get("error"):
            task_finish(tid, error=prompts["error"])
            return
        task_append(tid, f"已编译 {prompts.get('n', 0)} 个镜头提示词")
        task_progress(tid, 4, 5)

        check = run_check(path)
        if check.get("pass"):
            task_append(tid, "分镜规则检查通过，可进入视频生成")
        else:
            task_append(tid, f"分镜规则检查发现 {len(check.get('failures', []))} 项待修复内容")
        task_progress(tid, 5, 5)
        task_finish(tid, result={"path": path, "mode": mode, "project": project,
                                 "summary": result.get("summary"), "assets": asset_path,
                                 "prompts": prompts.get("n", 0), "check": check,
                                 "next": "规划完成后，请在视频生成阶段逐镜提交 ComfyUI"})
    except Exception as e:
        task_finish(tid, error=str(e))


def run_plan(vram, aspect="9:16", seconds=5.0, quality="fast", face=False):
    return {"plan": hardware.plan_text(float(vram), aspect, float(seconds), quality, face)}


def run_hardware():
    base = CFG["comfy_base"]
    info = {"base": base, "online": False, "system_stats": None, "error": None}
    try:
        import urllib.request
        with urllib.request.urlopen(base + "/system_stats", timeout=5) as r:
            info["system_stats"] = json.loads(r.read().decode("utf-8"))
            info["online"] = True
            CFG["_comfy_ok"] = True
    except Exception as e:
        info["error"] = str(e)
        CFG["_comfy_ok"] = False
    # accelerate REST service (spark2 :8123) — pure T2V, Sol-Attn accelerated
    accel = {"base": CFG["accel_base"], "online": False, "error": None, "note": None}
    try:
        import urllib.request
        with urllib.request.urlopen(CFG["accel_base"] + "/health", timeout=5) as r:
            accel["online"] = True
            try:
                accel["body"] = json.loads(r.read().decode("utf-8"))
            except Exception:
                accel["body"] = None
            CFG["_accel_ok"] = True
    except Exception as e:
        accel["error"] = str(e)
        CFG["_accel_ok"] = False
    info["accel"] = accel
    return info


def run_comfy_generate(rel, shot_id, tid, params):
    """Long task: generate one shot clip on live ComfyUI."""
    target = params.get("target", "auto")   # auto -> ep01.json 的 shots
    out_dir = params.get("out_dir", "")
    base = params.get("comfy_base") or CFG["comfy_base"]
    width = int(params.get("width") or CFG["width"])
    height = int(params.get("height") or CFG["height"])
    steps = int(params.get("steps") or CFG["steps"])
    timeout = int(params.get("timeout") or 3000)
    try:
        d, err = _load_project_doc(rel)
        if err:
            task_finish(tid, error=err)
            return
        proj = _as_project(d)
        shots = proj.shots
        shot = next((s for s in shots if s.shot_id == shot_id), None)
        if shot is None:
            # maybe generate all
            shot = shots[0] if shots else None
        if shot is None:
            task_finish(tid, error="shot_not_found")
            return
        task_append(tid, f"[{shot.shot_id}] {shot.mode} {width}x{height}")
        prompts = prompt.compile_all(proj)
        ptext = prompts[shot.shot_id]
        chars = None
        try:
            from h3_short_drama.character_lock import characters_from
            chars = characters_from(proj)
        except Exception:
            chars = {}
        lead = next((n for n in shot.char_positions.keys() if n in chars), None)
        first = chars.get(lead, "") if lead else ""
        if first and not os.path.exists(first):
            first = ""
        if first:
            task_append(tid, f"uploading first_frame {first}")
            first = comfyui_gen.upload_image(base, first)
        seed = shot.seed or (42 + 0 * 7919) % (2 ** 31)
        if out_dir and out_dir.startswith("auto"):
            out_dir = ""
        od = _abs(out_dir) or os.path.join(_project_dir(rel) or REPO, "outputs")
        os.makedirs(od, exist_ok=True)
        clip = os.path.join(od, f"{shot.shot_id}.mp4")
        length = max(5, int(round(shot.duration_s * 24)))
        length += (5 - (length % 17)) % 17
        task_append(tid, f"generating {shot.shot_id} length={length}f seed={seed} first={'yes' if first else 'no'}")

        backend = params.get("backend", "comfy")
        if backend == "accel" and not first:
            # pure T2V -> accelerate REST service
            _run_accel_shot(shot, tid, clip, ptext, width, height, length, seed, steps, out_dir)
            task_append(tid, f"DONE(accel) -> {clip}")
            task_progress(tid, 3, 3)
            task_finish(tid, result={"shot_id": shot.shot_id,
                                     "clip": os.path.relpath(clip, REPO).replace("\\", "/"),
                                     "seed": seed, "mode": "T2V@accel",
                                     "first_frame": "", "prompt_preview": ptext[:400]})
            return
        if backend == "accel":
            task_append(tid, "I2V 镜头(有首帧)加速服务不支持图生图 → 自动回退到 ComfyUI 保身份锁定")
        task_progress(tid, 1, 3)
        comfyui_gen.generate(base, ptext, clip, width=width,
                             height=height, length=length, seed=seed,
                             steps=steps, first_frame=first, filename=shot.shot_id,
                             timeout=timeout, verbose=False)
        task_append(tid, f"DONE -> {clip}")
        task_progress(tid, 3, 3)
        task_finish(tid, result={"shot_id": shot.shot_id, "clip": os.path.relpath(clip, REPO).replace("\\", "/"),
                                 "seed": seed, "mode": "I2V" if first else "T2V",
                                 "first_frame": first, "prompt_preview": ptext[:400]})
    except Exception as e:
        task_append(tid, f"ERROR {e}")
        task_finish(tid, error=str(e))


def _run_accel_shot(shot, tid, clip, ptext, width, height, length, seed, steps, out_dir):
    """Generate via the accelerate REST service (spark2 :8123).
    Pure T2V sync call: POST /generate {prompt,width,height,length,steps,seed}
    -> {ok, video:"/videos/h3_x.mp4", seconds}. Then download to clip.
    NOTE: this service has NO image/first-frame input, so it's T2V-only;
    callers must have already ensured `first == ""`."""
    import urllib.request
    base = CFG["accel_base"]
    task_append(tid, f"[accel] POST {base}/generate (steps={steps}, length={length}, seed={seed})")
    body = json.dumps({
        "prompt": ptext, "width": int(width), "height": int(height),
        "length": int(length), "steps": int(steps), "seed": int(seed),
    }).encode("utf-8")
    req = urllib.request.Request(base + "/generate", data=body,
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=800) as r:
        resp = json.loads(r.read().decode("utf-8"))
    if not resp.get("ok"):
        raise RuntimeError(f"accel generate failed: {resp}")
    video_url = resp.get("video") or ""
    if not video_url:
        raise RuntimeError(f"accel no video url: {resp}")
    if not video_url.startswith("http"):
        video_url = base + video_url
    task_append(tid, f"[accel] got {video_url} (took {resp.get('seconds')}s), downloading")
    os.makedirs(os.path.dirname(clip) or ".", exist_ok=True)
    urllib.request.urlretrieve(video_url, clip)
    task_append(tid, f"[accel] saved {clip}")


def run_series(rel, tid, out_dir):
    from h3_short_drama import series
    if not SERIES_LOCK.acquire(blocking=False):
        task_finish(tid, error="已有系列任务正在运行，不能重复提交")
        return
    try:
        base = CFG["comfy_base"]
        d, err = _load_project_doc(rel)
        if err:
            task_finish(tid, error=err)
            return
        title = (d.get("title") or "project").strip()
        stamp = time.strftime("%Y%m%d-%H")
        safe_title = re.sub(r"[\\/:*?\"<>|]+", "_", title) or "project"
        od = _abs(out_dir) if out_dir and out_dir != "auto" else None
        od = od or os.path.join(_project_dir(rel) or REPO, "outputs", stamp)
        os.makedirs(od, exist_ok=True)
        with open(os.path.join(od, f"{safe_title}.json"), "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
        prompt_dir = os.path.join(od, "prompts")
        os.makedirs(prompt_dir, exist_ok=True)
        proj = _as_project(d)
        findings = validate_gates.check_project(proj, d)
        validate_gates._log(findings, od, proj.title)
        errors = [x for x in findings if x.level == "error"]
        if errors:
            message = "质量门拦截: " + "；".join(f"{x.gate}/{x.shot}: {x.detail}" for x in errors[:5])
            task_append(tid, message)
            task_finish(tid, error=message)
            return
        for sid, text in prompt.compile_all(proj).items():
            with open(os.path.join(prompt_dir, f"{sid}.txt"), "w", encoding="utf-8") as f:
                f.write(text)
        task_append(tid, f"series on {base} -> {od}")
        task_progress(tid, 0, len(proj.shots))

        def on_progress(cur, total, sid, state):
            task_progress(tid, cur, total)
            task_append(tid, f"[{sid}] {state} ({cur}/{total})")

        recs = series.generate_series(base, proj.shots, proj, out_dir=od,
                                      width=CFG["width"], height=CFG["height"],
                                      steps=CFG["steps"], skip_existing=True,
                                      progress_callback=on_progress)
        archive = os.path.join(SPARK1_ARCHIVE_ROOT, os.path.basename(od))
        os.makedirs(archive, exist_ok=True)
        import shutil
        shutil.copytree(od, archive, dirs_exist_ok=True)
        task_append(tid, f"got {len(recs)} records")
        for r in recs:
            task_append(tid, json.dumps({k: v for k, v in r.items() if k != 'prompt'},
                                        ensure_ascii=False)[:300])
        task_finish(tid, result={"records": recs, "out_dir": os.path.relpath(od, REPO).replace("\\", "/"),
                                 "archive": archive})
    except Exception as e:
        task_finish(tid, error=str(e))
    finally:
        SERIES_LOCK.release()


def run_assemble(clips, out_rel, bgm="", subtitle="", mode="hardcut"):
    """Assemble clips into an episode.
    mode:
      hardcut  -> concat demuxer (clips already trimmed to edit target); 32k audio safe
      xfade    -> normalize to canvas + dissolve transitions (assemble_plan)
    Returns {out, steps, exists, cmd_head, error?}.
    """
    try:
        abs_clips = [_abs(c) for c in clips if c]
        abs_clips = [c for c in abs_clips if c and os.path.exists(c)]
        if not abs_clips:
            return {"error": "no existing clip files to assemble"}
        out = _abs(out_rel)
        os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
        cmds = []
        seen = []
        if mode == "xfade":
            cmds = assemble.assemble_plan(abs_clips, out, bgm=bgm, subtitle=subtitle,
                                          canvas=(CFG["width"], CFG["height"]))
        else:
            # hardcut via concat demuxer (32kHz-safe because we just repackage)
            lst = os.path.join(os.path.dirname(out) or ".", "_concat_list.txt")
            with open(lst, "w", encoding="utf-8") as f:
                f.write("".join(f"file '{os.path.abspath(c)}'\n" for c in abs_clips))
            # normalize audio to 32k + video to 24fps during a safe pass, then concat copy
            norm = []
            for i, c in enumerate(abs_clips):
                n = os.path.join(os.path.dirname(out) or ".", f"_hc{i:02d}.mp4")
                cmds.append(["ffmpeg", "-y", "-i", c,
                             "-r", "24", "-vf", "fps=24",
                             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
                             "-c:a", "aac", "-ar", "32000", "-ac", "2", "-b:a", "192k",
                             n])
                norm.append(n)
            with open(lst, "w", encoding="utf-8") as f:
                f.write("".join(f"file '{os.path.abspath(n)}'\n" for n in norm))
            cmds.append(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst,
                         "-c", "copy", os.path.join(os.path.dirname(out) or ".", "_hc_joined.mp4")])
            cmds.append(["cp", os.path.join(os.path.dirname(out) or ".", "_hc_joined.mp4"), out])
            # bgm mix if requested
            if bgm:
                with_bgm = f"{out}.withbgm.mp4"
                cmds.append(["ffmpeg", "-y", "-i", out, "-stream_loop", "-1", "-i", _abs(bgm),
                             "-filter_complex",
                             "[1:a]volume=0.10[bgm];[0:a][bgm]amix=inputs=2:duration=first[a]",
                             "-map", "0:v", "-map", "[a]", "-shortest",
                             "-c:v", "copy", "-c:a", "aac", "-ar", "32000", "-ac", "2",
                             with_bgm])
                cmds.append(["cp", with_bgm, out])
        executed = []
        for c in cmds:
            assemble.run([c])
            executed.append(" ".join(c if isinstance(c, list) else [c])[:140])
        return {"out": out_rel, "steps": len(executed), "mode": mode,
                "exists": os.path.exists(out), "size": os.path.getsize(out) if os.path.exists(out) else 0,
                "cmd_head": executed}
    except Exception as e:
        return {"error": str(e)}


def run_qc(rel, out_rel=""):
    """Report what QC artifacts exist + basic continuity file listing."""
    # resolve the episode dir (parent of the final mp4)
    final = _abs(out_rel) if out_rel else None
    result = {"project": rel, "frames": [], "continuity": None}
    try:
        files = []
        if final and os.path.exists(final):
            files = sorted(_glob.glob(os.path.splitext(final)[0].replace("_final", "") +
                                      "_*_f*.png"))
            files += sorted(_glob.glob(os.path.dirname(final) + "/*.png"))
        # dedupe
        seen = set()
        uniq = []
        for f in files:
            if f not in seen:
                seen.add(f)
                uniq.append(os.path.relpath(f, REPO).replace("\\", "/"))
        result["frames"] = uniq[:60]
        result["final"] = os.path.relpath(final, REPO).replace("\\", "/") if final else ""
    except Exception as e:
        result["error"] = str(e)
    return result


def dir_nodes(root_abs):
    """Return a tree node list of *.png / *.mp4 / *.json under root_abs."""
    out = []
    for root, _dirs, files in os.walk(root_abs):
        for f in sorted(files):
            if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".mp4", ".json")):
                rel = os.path.relpath(os.path.join(root, f), REPO).replace("\\", "/")
                out.append({"path": rel, "name": f,
                            "kind": "img" if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))
                            else ("vid" if f.lower().endswith(".mp4") else "json"),
                            "size": os.path.getsize(os.path.join(root, f))})
    return out


def compute_progress(rel):
    """Scan artifacts to derive per-stage readiness + a single next-step advice.

    Returns {stages: {stage_id: "done"|"pending"|"warn"}, advice: {target, label, note}}.
    """
    d, _err = _load_project_doc(rel)
    stages = {sid: "pending" for sid in
              ["bible", "board", "check", "cards", "scene", "prompts", "deploy", "gen", "qc", "final"]}
    advice = {"target": "check", "label": "运行自检", "note": "先验证分镜硬规则通过"}
    if d is not None:
        stages["bible"] = "done"; stages["board"] = "done"
        try:
            proj = _as_project(d)
            ok, fails = shot_table.self_check(proj)
            if ok:
                stages["check"] = "done"
            else:
                stages["check"] = "warn"
                advice = {"target": "check", "label": "修复自检失败", "note": f"{len(fails)} 条规则未通过"}
        except Exception:
            pass
        chars_ok = all(not c.get("image_path") or
                       (os.path.exists(_abs(c["image_path"])) )
                       for c in d.get("characters", []))
        if d.get("characters") and chars_ok:
            stages["cards"] = "done"
        else:
            stages["cards"] = "pending"
            if stages["check"] == "done":
                advice = {"target": "cards", "label": "生成角色卡", "note": "需 H3 肖像定卡"}
        if any(s.get("image_path") and os.path.exists(_abs(s["image_path"]))
               for s in d.get("scenes", [])):
            stages["scene"] = "done"
        else:
            stages["scene"] = "pending"
        pdir = os.path.join(_project_dir(rel) or REPO, "prompts")
        if os.path.isdir(pdir) and len(_glob.glob(os.path.join(pdir, "S*.txt"))) >= len(d.get("shots", [])):
            stages["prompts"] = "done"
    stages["deploy"] = "done" if CFG.get("_comfy_ok") else "warn"
    if d is not None:
        output_dirs = _project_output_dirs(rel)
        outdir = _abs(output_dirs[0]) if output_dirs else None
        if not outdir:
            return {"stages": stages, "advice": advice}
        existing = {os.path.splitext(os.path.basename(p))[0]
                    for p in _glob.glob(os.path.join(outdir, "S*.mp4"))}
        needed = {s["shot_id"] for s in d.get("shots", [])}
        have = needed & existing
        if needed and have == needed:
            stages["gen"] = "done"
        elif have:
            stages["gen"] = "warn"
            advice = {"target": "gen", "label": f"继续生成 ({len(needed - have)}/{len(needed)} 未出)", "note": "补足缺失镜头"}
        else:
            stages["gen"] = "pending"
            if stages["cards"] == "done":
                advice = {"target": "gen", "label": "生成镜头", "note": "逐镜提交 ComfyUI"}
        finals = _glob.glob(os.path.join(outdir, "EP*_final.mp4")) + \
                 _glob.glob(os.path.join(outdir, "EP*_new.mp4")) + \
                 _glob.glob(os.path.join(outdir, "EP*_desk*.mp4"))
        if finals:
            stages["final"] = "done"
        elif stages["gen"] == "done":
            advice = {"target": "final", "label": "装配成片", "note": "镜头齐全，可裁剪装配"}
        if _glob.glob(os.path.join(outdir, "qc_*.png")):
            stages["qc"] = "done"
        elif finals:
            stages["qc"] = "warn"
            advice = {"target": "qc", "label": "质检成片", "note": "抽帧核验一致性"}
    # terminal state: everything ready -> show finished
    if all(v == "done" for v in stages.values()):
        advice = {"target": "", "label": "全部就绪 ✓", "note": "10 环节均已完成，可发布或调整后重新生成"}
    return {"stages": stages, "advice": advice}


# ---------------------------------------------------------------------------
# project creation helpers
# ---------------------------------------------------------------------------

def _safe_name(name):
    """Space a project name -> safe directory token (lowercase, ascii-ish)."""
    import unicodedata
    norm = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().strip()
    norm = re.sub(r"[^a-zA-Z0-9]+", "_", norm).strip("_").lower()
    return norm or "new_project"


def blank_project(name, duration_s=15, seconds_per_shot=5, aspect="9:16",
                  dialogue_mode="有对白", dialogue_language="中文"):
    """A fully-initialized empty drama project (2 placeholder shots with all
    required fields so every director stage renders without errors)."""
    n = max(2, int(round(duration_s / max(1, seconds_per_shot))))
    shots = []
    for i in range(1, n + 1):
        shots.append({
            "shot_id": f"S{i:02d}",
            "duration_s": seconds_per_shot,
            "edit_target_s": min(seconds_per_shot, 3),
            "continuity_handoff": f"（待填写）镜头 {i} 接续上一镜的 {('角色/场景') if i > 1 else '场景建立'}",
            "fixed_landmarks": [],
            "char_positions": {},
            "exited_chars": [],
            "lighting_baseline": "",
            "hook_type": "suspense" if i in (1, n) else "expression-beat",
            "shot_description": f"（待填写）镜头 {i} 的画面描述：场景、景别、运动。",
            "per_second": [],
            "narration": "",
            "dialogue": [],
            "sfx": [],
            "mode": "T2VA" if i == 1 else "I2VA",
            "video_model": "H3",
            "resolution_tier": "768P",
            "aspect": aspect,
            "references": [],
            "first_frame": "",
            "last_frame": "",
            "negative": "morphing, flickering, distorted face, extra fingers, blurry, low quality, watermark, text overlay",
            "continuity_type": "hard_cut",
            "airlock_s": 0.0,
            "seed": 0,
        })
    return {
        "title": name or "未命名短剧",
        "what_if": "（待填写）故事的假设前提。",
        "target_feeling": "（待填写）希望观众感受到的情绪。",
        "aspect": aspect,
        "duration_s": duration_s,
        "dialogue_mode": dialogue_mode,
        "dialogue_language": dialogue_language,
        "visual_style": "clean stylized rendering, strong character design language, on-brand color palette, clean motion",
        "characters": [],
        "scenes": [],
        "shots": shots,
    }


def example_project():
    """A ready-to-edit example (odyssey ep01's 4-shot structure) for importing."""
    rel = "projects/odyssey/episodes/ep01/episode.json"
    p = _abs(rel)
    if p and os.path.exists(p):
        d = json.load(open(p, encoding="utf-8"))
        return {
            "title": "我的示例短剧（基于奥德赛分镜结构）",
            "what_if": d.get("what_if", ""), "target_feeling": d.get("target_feeling", ""),
            "aspect": d.get("aspect", "9:16"), "duration_s": d.get("duration_s", 10),
            "dialogue_mode": d.get("dialogue_mode", "无对白"), "dialogue_language": d.get("dialogue_language", "未指定"),
            "visual_style": d.get("visual_style", ""),
            "characters": d.get("characters", []), "scenes": d.get("scenes", []),
            "shots": d.get("shots", []),
        }
    return blank_project("示例短剧")


def create_project(data):
    """Create a new project directory + ep01.json. Returns {path, project, error?}."""
    name = (data.get("name") or "未命名短剧").strip()
    token = _safe_name(name)
    d = data.get("template", "blank")
    if d == "example":
        doc = example_project()
    elif d == "ai":
        return {"error": "ai_storyboard 需通过 /api/project/ai_storyboard 单独调用（需 LLM key）"}
    else:
        doc = blank_project(name,
                            float(data.get("duration_s", 15) or 15),
                            float(data.get("seconds_per_shot", 5) or 5),
                            data.get("aspect", "9:16") or "9:16",
                            data.get("dialogue_mode", "有对白"),
                            data.get("dialogue_language", "中文"))
    doc["title"] = name or "未命名短剧"
    proj_dir = os.path.join(REPO, "projects", token)
    # dedupe
    i = 2
    base = proj_dir
    while os.path.exists(proj_dir):
        proj_dir = f"{base}_{i}"; i += 1
    os.makedirs(proj_dir, exist_ok=True)
    episode_dir = os.path.join(proj_dir, "episodes", "ep01")
    for folder in ("assets", "references", "prompts", "outputs"):
        os.makedirs(os.path.join(episode_dir, folder), exist_ok=True)
    project_manifest = {"type": "project", "title": name or "未命名项目",
                        "description": "导演台项目空间", "episodes": ["ep01"]}
    with open(os.path.join(proj_dir, "project.json"), "w", encoding="utf-8") as f:
        json.dump(project_manifest, f, ensure_ascii=False, indent=2)
    rel = os.path.join("projects", os.path.basename(proj_dir), "episodes", "ep01", "episode.json").replace("\\", "/")
    with open(os.path.join(episode_dir, "episode.json"), "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    return {"path": rel, "project": doc, "dir": "projects/" + os.path.basename(proj_dir)}


def ai_storyboard(data):
    """Generate a full episode storyboard from a one-line idea via an OpenAI
    compatible LLM. Returns the project doc (in-place drafts) or an error.
    Requires env OPENAI_API_KEY / OPENAI_BASE_URL. Falls back cleanly."""
    import os as _os
    idea = (data.get("idea") or "").strip()
    if not idea:
        return {"error": "请先填写一句话点子"}
    llm = CFG["llm"]
    key = llm.get("api_key") or _os.environ.get("OPENAI_API_KEY") or _os.environ.get("DEEPSEEK_API_KEY") or ""
    base = llm.get("base_url") or _os.environ.get("OPENAI_BASE_URL") or "https://api.openai.com/v1"
    try:
        from h3_short_drama import generate
        prompt = generate.storyboard_prompt(idea, data.get("aspect", "9:16"),
                                            int(data.get("duration_s", 15) or 15),
                                            data.get("genre", ""), data.get("language", "中文"))
        model = llm.get("model") or _os.environ.get("LLM_MODEL", "deepseek-chat")
        raw = generate._chat(prompt, model=model, base=base, key=key, temperature=0.8)
        if not raw or raw.startswith("LLM_ERR"):
            return {"error": raw or "LLM 无返回"}
        obj = generate._extract_json(raw)
        if not obj:
            return {"error": "LLM 返回无法解析为 JSON"}
        return {"project": obj, "raw": raw[:4000]}
    except Exception as e:
        return {"error": f"AI 生成失败: {e}"}


def run_ai_create(data, tid):
    """Create an AI project in the background so the browser never blocks."""
    try:
        task_append(tid, "正在连接 DGX Spark Qwen…")
        task_progress(tid, 1, 4)
        result = ai_storyboard(data)
        if result.get("error"):
            task_finish(tid, error=result["error"])
            return
        task_append(tid, "Qwen 已返回，正在解析项目 JSON…")
        task_progress(tid, 2, 4)
        shell = create_project({
            "name": data.get("name") or "未命名短剧",
            "template": "blank",
            "aspect": data.get("aspect", "9:16"),
            "duration_s": data.get("duration_s", 15),
        })
        if shell.get("error"):
            task_finish(tid, error=shell["error"])
            return
        task_append(tid, "项目骨架已创建，正在保存 AI 分镜…")
        task_progress(tid, 3, 4)
        a = _abs(shell["path"])
        with open(a, "w", encoding="utf-8") as f:
            json.dump(result["project"], f, ensure_ascii=False, indent=2)
        task_progress(tid, 4, 4)
        task_finish(tid, result={"path": shell["path"], "project": result["project"],
                                 "raw": result.get("raw", "")})
    except Exception as e:
        task_finish(tid, error=str(e))


# ---------------------------------------------------------------------------
# conversational round-by-round iteration (你喂语料 -> AI 出一版 -> 你反馈 -> AI 改)
# ---------------------------------------------------------------------------

CHAT_SYSTEM = """你是专业短剧导演 + H3 竖屏短剧分镜师。你的任务是维护一个"短剧项目 JSON"，
每一轮根据用户反馈修改它，最终只输出【完整、可用的项目 JSON】，不要输出任何解释文字或代码块标记。

项目 JSON 结构必须严格遵循：
{
  "title": "剧名", "what_if": "一句话概念钩子", "target_feeling": "目标情绪",
  "aspect": "9:16", "duration_s": 总秒数, "dialogue_mode": "有对白|无对白",
  "dialogue_language": "中文", "visual_style": "英文视觉风格描述(画面质感/摄影/色调)",
  "characters": [{"name":"角色名","identity_note":"英文身份描述:年龄/体型/发型/服装/不可变特征","image_path":"","do_not_change":["face",...]}],
  "scenes": [{"name":"场景名","description":"英文描述","landmarks":["具名地标:屏幕位置",...],"light_baseline":"","image_path":""}],
  "shots": [分镜数组，见下]
}
每个 shot（严格含这些字段）:
{
  "shot_id":"S01","duration_s":5,"edit_target_s":3,
  "continuity_handoff":"跨镜衔接(英文,写清动作/机位/空间的延续)",
  "fixed_landmarks":["地标:位置",...],"char_positions":{"角色名":"屏幕位置+朝向"},
  "exited_chars":[],"lighting_baseline":"光照基线",
  "hook_type":"suspense|reversal|reveal|callback|expression-beat|chase|tender|visual-joke",
  "shot_description":"英文整镜画面描述(场景+人物+景别+运动)",
  "per_second":[{"rng":"0-1s","action":"动作/表情","camera":"机位运动","spatial":"空间位置","audio":"声音","handoff":"衔接下一秒"}, ...],
  "narration":"","dialogue":[{"text":"台词","speaker_id":"角色名","tone":"","time_range":"","is_diegetic":true}],
  "sfx":["音效1","音效2"],
  "mode":"T2VA|I2VA","video_model":"H3","resolution_tier":"768P","aspect":"9:16",
  "references":[],"first_frame":"","last_frame":"",
  "negative":"morphing, flickering, distorted face...","continuity_type":"hard_cut",
  "airlock_s":0.0,"seed":0
}
规则：
- 竖屏短剧爆款方法论：每镜≤5s；首镜/尾镜带强钩子；每3镜≥1强钩子；对白一句≤20字；单镜≤3重要角色。
- 逐秒指令必须覆盖 0 到 duration_s 的所有秒，每条含 action/camera/spatial/audio/handoff 五要素，不能有空缺。
- mode：第一镜常用 T2VA（建立场景）；引用角色卡的镜头用 I2VA 并设 first_frame=""（由后端自动绑卡）。
- 用户反馈若涉及角色/场景/风格/节奏/分镜，都要在 JSON 里落实。保留未改动的结构。"""


def _llm_chat(messages, system=CHAT_SYSTEM, temperature=0.8):
    import os as _os
    llm = CFG["llm"]
    key = llm.get("api_key") or _os.environ.get("OPENAI_API_KEY") or _os.environ.get("DEEPSEEK_API_KEY") or ""
    base = llm.get("base_url") or _os.environ.get("OPENAI_BASE_URL") or "https://api.openai.com/v1"
    model = llm.get("model") or _os.environ.get("LLM_MODEL", "deepseek-chat")
    from h3_short_drama import generate
    msgs = ([{"role": "system", "content": system}] if system else []) + messages
    # build request body manually (generate._chat only takes one prompt)
    import urllib.request
    body = {"model": model, "messages": msgs, "temperature": temperature, "max_tokens": 8192,
            "chat_template_kwargs": {"enable_thinking": False}}
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    req = urllib.request.Request(base.rstrip("/") + "/chat/completions",
                                 data=json.dumps(body).encode("utf-8"),
                                 headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=240) as r:
            d = json.loads(r.read().decode("utf-8"))
        return d["choices"][0]["message"]["content"], None
    except Exception as e:
        return None, str(e)


def _project_digest(doc):
    """Short textual digest of a project for the model to see current state."""
    lines = [f"title={doc.get('title')}", f"aspect={doc.get('aspect')} dur={doc.get('duration_s')}s "
             f"dlg={doc.get('dialogue_mode')}/{(doc.get('dialogue_language') or '')[:6]}",
             f"visual_style={str(doc.get('visual_style'))[:150]}"]
    lines.append("characters:")
    for c in doc.get("characters", []):
        lines.append(f"  - {c.get('name')}: {str(c.get('identity_note'))[:100]}")
    lines.append("scenes:")
    for s in doc.get("scenes", []):
        lines.append(f"  - {s.get('name')}: {str(s.get('description'))[:80]}")
    lines.append("shots:")
    for s in doc.get("shots", []):
        lines.append(f"  - {s.get('shot_id')} {s.get('mode')} {s.get('duration_s')}s hook={s.get('hook_type')} :: {str(s.get('shot_description'))[:90]}")
    return "\n".join(lines)


def chat_iter(data):
    """One conversational round: given feedback + current project, AI returns a
    revised full project JSON and saves it. First call creates from raw material."""
    path = data.get("path", "")
    feedback = (data.get("feedback") or "").strip()
    mode = data.get("mode", "iterate")   # create | iterate
    # session = project-relative path; persist history
    with CHAT_LOCK:
        session = CHAT_SESSIONS.setdefault(path, {"history": []})
        history = session["history"]

    a = _abs(path)
    doc = None
    if a and os.path.exists(a):
        try:
            doc = json.load(open(a, encoding="utf-8"))
        except Exception:
            doc = None

    messages = []
    if doc and mode != "create":
        # current state + history of prior feedback
        messages.append({"role": "user",
                         "content": "这是当前项目现状（勿改动未提及之处）：\n" + _project_digest(doc)})
    # append the actual user feedback for THIS round
    if mode == "create":
        user_msg = f"""请根据以下背景/语料，新建一集短剧的项目 JSON：
背景风格 / 语录料：
{feedback}
（信息不足可合理补全，竖屏短剧节奏，3-6 个镜头，含逐秒指令。）"""
    else:
        user_msg = feedback or "请基于现有项目做一次合理的打磨（无明显问题时保持结构）。"
    messages.append({"role": "user", "content": user_msg})

    raw, err = _llm_chat(messages)
    if err:
        return {"error": err}
    if not raw:
        return {"error": "LLM 无返回"}
    from h3_short_drama import generate
    obj = generate._extract_json(raw)
    if not obj:
        return {"error": "LLM 返回无法解析为项目 JSON", "raw": raw[:2000]}

    # merge: keep meta defaults if missing
    base = doc or {}
    for k, v in {"aspect": "9:16", "duration_s": 15, "dialogue_mode": "有对白",
                 "dialogue_language": "中文"}.items():
        obj.setdefault(k, base.get(k, v))
    obj.setdefault("characters", base.get("characters", []))
    obj.setdefault("scenes", base.get("scenes", []))
    obj.setdefault("shots", [])

    # save
    if a:
        os.makedirs(os.path.dirname(a), exist_ok=True)
        with open(a, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)

    # record this round in history
    with CHAT_LOCK:
        history.append({"role": "user", "content": user_msg})
        history.append({"role": "assistant", "content": _project_digest(obj)})
        history[:] = history[-20:]

    # a tiny diff summary for the front end
    summary = {"round": len(history) // 2, "n_shots": len(obj.get("shots", [])),
               "title": obj.get("title"), "cha": len(obj.get("characters", [])),
               "scenes": len(obj.get("scenes", []))}
    return {"ok": True, "path": path, "project": obj, "summary": summary,
            "digest": _project_digest(obj), "history": [h["content"] for h in history]}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False).encode("utf-8")
        elif isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        if not getattr(self, "_head_only", False):
            self.wfile.write(body)

    def do_HEAD(self):
        self._head_only = True
        self.do_GET()

    def _static(self, rel):
        p = _abs("director/" + rel)
        if not p or not os.path.isfile(p):
            return False
        _, ext = os.path.splitext(p)
        ctype = {".html": "text/html; charset=utf-8", ".js": "application/javascript; charset=utf-8",
                 ".css": "text/css; charset=utf-8", ".png": "image/png", ".jpg": "image/jpeg",
                 ".jpeg": "image/jpeg", ".webp": "image/webp", ".svg": "image/svg+xml",
                 ".mp4": "video/mp4", ".json": "application/json", ".ico": "image/x-icon",
                 ".md": "text/markdown; charset=utf-8"}.get(ext, "application/octet-stream")
        if ".mp4" in rel or ".png" in rel:
            return self._serve_file(p, ctype)
        data = open(p, "rb").read()
        self._send(200, data, ctype)
        return True

    def _serve_file(self, p, ctype):
        # range support for video seeking
        rng = self.headers.get("Range")
        size = os.path.getsize(p)
        start, end = 0, size - 1
        if rng:
            m = re.match(r"bytes=(\d*)-(\d*)", rng)
            if m and m.group(1):
                start = int(m.group(1))
            if m and m.group(2):
                end = int(m.group(2))
            end = min(end, size - 1)
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            self.send_header("Accept-Ranges", "bytes")
        else:
            self.send_response(200)
        self.send_header("Content-Type", ctype)
        length = end - start + 1
        self.send_header("Content-Length", str(length))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        if getattr(self, "_head_only", False):
            return  # HEAD: headers only, no body
        with open(p, "rb") as f:
            f.seek(start)
            self.wfile.write(f.read(length))
        return True

    def _api(self, path, qs):
        if path == "/api/config/llm":
            public = {k: v for k, v in CFG["llm"].items() if k != "api_key"}
            public["api_key_set"] = bool(CFG["llm"].get("api_key"))
            return self._send(200, public)
        if path == "/api/director":
            return self._director(qs)
        if path == "/api/projects":
            return self._send(200, {"projects": [_project_entry(p) for p in _find_projects()]})
        if path == "/api/project":
            rel = qs.get("path", [""])[0]
            d, err = _load_project_doc(rel)
            if err:
                return self._send(404, {"error": err})
            return self._send(200, d)
        if path == "/api/stage/check":
            return self._send(200, run_check(qs.get("path", [""])[0]))
        if path == "/api/stage/prompts":
            return self._send(200, run_prompts(qs.get("path", [""])[0],
                                               qs.get("out", [""])[0]))
        if path == "/api/stage/plan":
            return self._send(200, run_plan(qs.get("vram", ["12"])[0], qs.get("aspect", ["9:16"])[0],
                                            qs.get("seconds", ["5"])[0], qs.get("quality", ["fast"])[0],
                                            "face" in qs))
        if path == "/api/hardware":
            return self._send(200, run_hardware())
        if path == "/api/stage/qc":
            return self._send(200, run_qc(qs.get("path", [""])[0], qs.get("out", [""])[0]))
        if path == "/api/files":
            root = qs.get("path", [""])[0]
            a = _abs(root)
            if not a or not os.path.isdir(a):
                return self._send(200, {"files": []})
            return self._send(200, {"files": dir_nodes(a)})
        if path.startswith("/api/task/"):
            tid = path.split("/")[-1]
            with TASKS_LOCK:
                return self._send(200, TASKS.get(tid, {"error": "no such task"}))
        if path == "/api/tasks":
            with TASKS_LOCK:
                tasks = [{"id": t["id"], "kind": t["kind"], "title": t["title"], "status": t["status"],
                      "started": t["started"], "path": t.get("path", ""),
                      "shot_id": t.get("shot_id") or t.get("title", "").removeprefix("generate "), "cur": t["cur"],
                      "total": t["total"], "error": t["error"], "log": t.get("log", [])[-8:]}
                     for t in TASKS.values()]
                known_shots = {t.get("shot_id") for t in tasks if t.get("status") == "running"}
                for remote in remote_generations(CFG["comfy_base"]):
                    if remote["shot_id"] not in known_shots:
                        tasks.append(remote)
                        known_shots.add(remote["shot_id"])
                return self._send(200, {"tasks": sorted(
                    tasks, key=lambda x: x["started"] or 0, reverse=True)[:30]})
        if path == "/api/media":
            return self._serve_media(qs)
        return self._send(404, {"error": "unknown api: " + path})

    def _serve_media(self, qs):
        rel = qs.get("path", [""])[0]
        a = _abs(rel)
        if not a or not os.path.isfile(a):
            return self._send(404, {"error": "file not found"})
        _, ext = os.path.splitext(a)
        ctype = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                 ".webp": "image/webp", ".mp4": "video/mp4", ".gif": "image/gif"}.get(ext,
                                                                                      "application/octet-stream")
        return self._serve_file(a, ctype)

    def _director(self, qs):
        """Overall director-desk state: pipeline readiness + project summary."""
        rel = qs.get("path", [""])[0] or (_find_projects()[0] if _find_projects() else "")
        state = {
            "comfy": run_hardware(),
            "projects": [_project_entry(p) for p in _find_projects()],
            "project": rel,
            "output_dir": (_project_output_dirs(rel) or [""])[0],
        }
        if rel:
            d, err = _load_project_doc(rel)
            if not err:
                proj = _as_project(d)
                state["summary"] = {
                    "title": proj.title, "what_if": proj.what_if or "",
                    "target_feeling": proj.target_feeling or "",
                    "aspect": proj.aspect, "duration_s": proj.duration_s,
                    "dialogue_mode": proj.dialogue_mode, "dialogue_language": proj.dialogue_language,
                    "n_shots": len(proj.shots),
                    "shots": [{"id": s.shot_id, "mode": s.mode, "duration_s": s.duration_s,
                               "edit_target_s": s.edit_target_s, "hook": s.hook_type,
                               "seed": s.seed, "first_frame": s.first_frame,
                               "desc": (s.shot_description or "")[:120]}
                              for s in proj.shots],
                    "characters": [{"name": c.name, "image_path": c.image_path,
                                    "do_not_change": c.do_not_change}
                                   for c in proj.characters],
                    "scenes": [{"name": s.name, "image_path": s.image_path} for s in proj.scenes],
                }
                state["progress"] = compute_progress(rel)
        return self._send(200, state)

    def do_GET(self):
        u = urlparse(self.path)
        path = u.path
        qs = parse_qs(u.query)
        if path.startswith("/api/"):
            return self._api(path, qs)
        if path == "/" or path == "/index.html":
            if self._static("index.html"):
                return
        if path.startswith("/assets/"):
            if self._static(path[len("/"):]):
                return None
        # try repo-relative file preview (media)
        a = _abs(path)
        if a and os.path.isfile(a):
            _, ext = os.path.splitext(a)
            ctype = {".png": "image/png", ".jpg": "image/jpeg", ".mp4": "video/mp4",
                     ".webp": "image/webp", ".gif": "image/gif"}.get(ext)
            if ctype:
                return self._serve_file(a, ctype)
        return self._send(404, {"error": "not found: " + path})

    def do_POST(self):
        u = urlparse(self.path)
        qs = parse_qs(u.query)
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b""
        try:
            data = json.loads(body.decode("utf-8")) if body else {}
        except Exception:
            data = {}
        self._post(u.path, qs, data)

    def _post(self, path, qs, data):
        if path == "/api/config/llm":
            allowed = set(DEFAULT_LLM)
            CFG["llm"].update({k: str(v) for k, v in data.items() if k in allowed})
            with open(LLM_CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(CFG["llm"], f, ensure_ascii=False, indent=2)
            return self._send(200, {"ok": True, "display_name": CFG["llm"]["display_name"]})
        # ---- generate one shot (long task) ----
        if path == "/api/stage/generate":
            rel = data.get("path", "")
            shot_id = data.get("shot_id", "")
            out_dir = data.get("out_dir", "")
            params = {
                "out_dir": out_dir,
                "comfy_base": data.get("comfy", CFG["comfy_base"]),
                "width": int(data.get("width", CFG["width"]) or CFG["width"]),
                "height": int(data.get("height", CFG["height"]) or CFG["height"]),
                "steps": int(data.get("steps", CFG["steps"]) or CFG["steps"]),
                "timeout": int(data.get("timeout", 3000) or 3000),
                "backend": data.get("backend", "comfy"),
            }
            # A browser can reopen the modal or double-submit while ComfyUI is
            # still working. Reuse the existing task instead of queueing a
            # second GPU job for the same episode and shot.
            with GENERATION_LOCK:
                existing = active_generation(rel, shot_id)
                if existing:
                    return self._send(202, {"task": existing["id"], "status": "existing",
                                            "message": f"{shot_id} 已在生成中"})
                remote = remote_generation(params["comfy_base"], shot_id)
                if remote:
                    return self._send(202, {"task": None, "status": "existing", "remote": True,
                                            "message": f"{shot_id} 已在 ComfyUI 队列中"})
                tid = new_task("generate", f"generate {shot_id or 'auto'}")
                with TASKS_LOCK:
                    TASKS[tid]["generation_key"] = f"{rel}::{shot_id}"
                    TASKS[tid]["path"] = rel
                    TASKS[tid]["shot_id"] = shot_id
            t = threading.Thread(target=run_comfy_generate,
                                 args=(rel, shot_id, tid, params), daemon=True)
            t.start()
            return self._send(202, {"task": tid, "status": "started"})
        # ---- series (long task) ----
        if path == "/api/stage/series":
            rel = data.get("path", "")
            out_dir = data.get("out_dir", "auto")
            tid = new_task("series", f"series {rel}")
            t = threading.Thread(target=run_series, args=(rel, tid, out_dir), daemon=True)
            t.start()
            return self._send(202, {"task": tid, "status": "started"})
        # ---- assemble ----
        if path == "/api/stage/assemble":
            clips = data.get("clips", [])
            out = data.get("out", "gen/EP_final.mp4")
            res = run_assemble(clips, out, data.get("bgm", ""), data.get("subtitle", ""),
                               mode=data.get("mode", "hardcut"))
            return self._send(200, res)
        if path == "/api/stage/save_project":
            rel = data.get("path", "")
            doc = data.get("project")
            a = _abs(rel)
            if not a or not doc:
                return self._send(400, {"error": "bad save request"})
            with open(a, "w", encoding="utf-8") as f:
                json.dump(doc, f, ensure_ascii=False, indent=2)
            return self._send(200, {"saved": rel})
        # ---- patch a project section (shots / characters / scenes) ----
        if path == "/api/stage/patch":
            rel = data.get("path", "")
            field = data.get("field")           # shots | characters | scenes
            value = data.get("value")
            a = _abs(rel)
            if not a or not os.path.exists(a):
                return self._send(400, {"error": "project not found"})
            if field not in ("shots", "characters", "scenes", "meta"):
                return self._send(400, {"error": "field must be shots|characters|scenes|meta"})
            doc, err = _load_project_doc(rel)
            if err:
                return self._send(400, {"error": err})
            if field == "meta":
                if not isinstance(value, dict):
                    return self._send(400, {"error": "meta value must be object"})
                for k, v in value.items():
                    if k in ("title", "what_if", "target_feeling", "aspect", "duration_s",
                             "dialogue_mode", "dialogue_language", "visual_style"):
                        doc[k] = v
            else:
                if not isinstance(value, list):
                    return self._send(400, {"error": f"{field} value must be list"})
                doc[field] = value
            with open(a, "w", encoding="utf-8") as f:
                json.dump(doc, f, ensure_ascii=False, indent=2)
            return self._send(200, {"saved": rel, "field": field, "n": len(value) if isinstance(value, list) else len(doc)})
        # ---- create a new project (blank template or example) ----
        if path == "/api/project/new":
            res = create_project(data)
            if res.get("error"):
                return self._send(400, res)
            return self._send(200, res)
        # ---- AI storyboard from an idea (needs LLM key) ----
        if path == "/api/project/ai_storyboard":
            tid = new_task("ai_create", f"AI 创建 {data.get('name') or '未命名短剧'}", total=4)
            t = threading.Thread(target=run_ai_create, args=(data, tid), daemon=True)
            t.start()
            return self._send(202, {"task": tid, "status": "started"})
        # ---- conversational round-by-round iteration ----
        if path == "/api/chat/iter":
            res = chat_iter(data)
            return self._send(200, res)
        # ---- workbench creative workflow (LLM -> assets -> prompts -> check) ----
        if path == "/api/chat/workflow":
            rel = data.get("path", "")
            if not rel or not _abs(rel) or not os.path.isfile(_abs(rel)):
                return self._send(400, {"error": "请先选择一个有效集数"})
            with WORKFLOW_LOCK:
                with TASKS_LOCK:
                    existing = next((t for t in TASKS.values()
                                     if t.get("kind") == "chat_workflow" and
                                     t.get("path") == rel and t.get("status") == "running"), None)
                if existing:
                    return self._send(202, {"task": existing["id"], "status": "existing",
                                            "message": "当前集的自动创作仍在进行中"})
                tid = new_task("chat_workflow", "自动创作当前集", total=5)
                with TASKS_LOCK:
                    TASKS[tid]["path"] = rel
            t = threading.Thread(target=run_chat_workflow, args=(data, tid), daemon=True)
            t.start()
            return self._send(202, {"task": tid, "status": "started"})
        return self._send(404, {"error": "unknown POST " + path})


def main():
    ap = argparse.ArgumentParser(description="H3 导演台本地后端")
    ap.add_argument("--port", type=int, default=8088)
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--comfy", default=CFG["comfy_base"])
    a = ap.parse_args()
    CFG["comfy_base"] = a.comfy
    srv = ThreadingHTTPServer((a.host, a.port), Handler)
    print(f"导演台已启动: http://{a.host}:{a.port}/  (ComfyUI: {a.comfy})")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
