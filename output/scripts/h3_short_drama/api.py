"""Provider clients (Jellyfish-style create + poll contract).

Supports: MiniMax Context-IR + Regenerate-2K, OpenAI Videos, Volcengine.
All calls are dry-run-safe: without an API key they return the exact request
payload (so the pipeline can print/inspect it) instead of raising.
"""
from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, Optional

MINIMAX_GLOBAL = "https://api.minimax.io"
MINIMAX_CN = "https://api.minimaxi.com"
OPENAI_BASE = "https://api.openai.com/v1"
VOLC_BASE = "https://ark.cn-beijing.volces.com/api/v3"


def _post(url: str, body: Dict[str, Any], key: str, headers: Optional[Dict[str, str]] = None):
    import urllib.request
    hdrs = {"Content-Type": "application/json"}
    if key:
        hdrs["Authorization"] = f"Bearer {key}"
    if headers:
        hdrs.update(headers)
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=hdrs, method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def _get(url: str, key: str):
    import urllib.request
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def _dryrun(payload: Dict[str, Any], note: str) -> Dict[str, Any]:
    return {"dry_run": True, "note": note, "payload": payload}


# ---- MiniMax ----
def minimax_context_ir(prompt: str, duration: int, ratio: str,
                       api_key: str = "", region: str = "global") -> Dict[str, Any]:
    """Free-form text -> enhanced structured H3 prompt (H3-Context-IR)."""
    base = MINIMAX_CN if region == "cn" else MINIMAX_GLOBAL
    body = {"model": "MiniMax-H3", "prompt": prompt, "duration": duration, "ratio": ratio}
    if not api_key:
        return _dryrun(body, "MiniMax Context-IR: set MINIMAX_API_KEY to call")
    out = _post(f"{base}/video-generation-v2-h3-context-ir", body, api_key)
    task = out.get("task", out)
    return {"enhanced_prompt": task.get("content", {}).get("prompt", ""), "raw": out}


def minimax_regenerate_2k(video_b64: str, prompt: str, duration: int, ratio: str,
                          api_key: str = "", region: str = "global") -> Dict[str, Any]:
    """768p + original context -> 2K (H3-Regenerate-2K, in-context)."""
    base = MINIMAX_CN if region == "cn" else MINIMAX_GLOBAL
    body = {"model": "MiniMax-H3", "prompt": prompt, "duration": duration,
            "ratio": ratio, "base_video": video_b64, "target_resolution": "2K"}
    if not api_key:
        return _dryrun(body, "MiniMax Regenerate-2K: set MINIMAX_API_KEY to call")
    return _post(f"{base}/video-generation-v2-regeneration", body, api_key)


# ---- OpenAI Videos ----
def openai_video(prompt: str, size: str, seconds: int, model: str = "sora",
                 input_reference_b64: str = "", seed: int = -1, api_key: str = "",
                 poll: bool = True) -> Dict[str, Any]:
    base = OPENAI_BASE
    body = {"prompt": prompt, "model": model, "size": size, "seconds": str(int(seconds)), "seed": seed}
    if input_reference_b64:
        body["input_reference"] = {"image_url": f"data:image/png;base64,{input_reference_b64}"}
    if not api_key:
        return _dryrun(body, "OpenAI Videos: set OPENAI_API_KEY to call")
    created = _post(f"{base}/videos", body, api_key)
    vid = created.get("id") or created.get("data", {}).get("id")
    if not (poll and vid):
        return created
    # poll
    for _ in range(60):
        time.sleep(2)
        st = _get(f"{base}/videos/{vid}", api_key)
        status = st.get("status") or st.get("data", {}).get("status")
        if status in ("completed", "succeeded"):
            return {"url": f"{base}/videos/{vid}/content", "status": status}
        if status in ("failed", "cancelled"):
            return {"status": status, "error": st}
    return {"status": "timeout"}


# ---- Volcengine (Ark) — three-frame content ----
def volcengine_video(content: list, ratio: str, duration: int, model: str = "",
                     seed: int = -1, api_key: str = "", poll: bool = True) -> Dict[str, Any]:
    body = {"content": content, "ratio": ratio, "duration": int(duration)}
    if model:
        body["model"] = model
    if seed >= 0:
        body["seed"] = seed
    if not api_key:
        return _dryrun(body, "Volcengine Ark: set VOLC_API_KEY to call")
    created = _post(f"{VOLC_BASE}/contents/generations/tasks", body, api_key)
    tid = created.get("id") or created.get("task_id")
    if not (poll and tid):
        return created
    for _ in range(60):
        time.sleep(2)
        st = _get(f"{VOLC_BASE}/contents/generations/tasks/{tid}", api_key)
        status = st.get("status")
        if status == "succeeded":
            url = st.get("content", {}).get("video_url") or st.get("url")
            return {"url": url, "status": status}
        if status in ("failed", "cancelled"):
            return {"status": status, "error": st}
    return {"status": "timeout"}


def build_volc_content(prompt: str, first_b64: str = "", last_b64: str = "",
                       key_b64: str = "") -> list:
    """Build the role-tagged content list (OpenAI single-ref vs Volc three-frame)."""
    content = [{"type": "text", "text": prompt}]
    if first_b64:
        content.append({"type": "image_url", "role": "first_frame",
                        "image_url": {"url": f"data:image/png;base64,{first_b64}"}})
    if last_b64:
        content.append({"type": "image_url", "role": "last_frame",
                        "image_url": {"url": f"data:image/png;base64,{last_b64}"}})
    if key_b64:
        content.append({"type": "image_url", "role": "key_frame",
                        "image_url": {"url": f"data:image/png;base64,{key_b64}"}})
    return content
