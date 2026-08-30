"""Live ComfyUI H3 client — the last-mile generator (proven wiring).

Builds the H3 API-format workflow (the exact node wiring confirmed working on the
target server), queues it via POST /prompt, polls /history, and downloads the mp4.
Supports T2V and I2V (first_frame upload) so short-drama shots can be chained.
"""
from __future__ import annotations

import base64
import json
import os
import time
import urllib.request
from typing import Dict, Optional

DEFAULT = "http://192.168.3.153:8188"
MODEL = "minimax_h3_fl2va_pruned_fp8_scaled.safetensors"
CLIP_ENC = "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors"
VAE_VIDEO = "minimax_h3_video_vae_fp16.safetensors"
VAE_AUDIO = "minimax_h3_audio_vae_fp32.safetensors"


_TRANSIENT_MARKS = ("10055", "10060", "10054", "10035", "10061",
                    "timed out", "Temporary failure", "Connection reset", "WinError")


def _is_transient(err: Exception) -> bool:
    """Socket-level LAN hiccups (WSAENOBUFS 10055, timeouts, resets) are transient;
    HTTP errors (server responded) are NOT — retrying a POST would double-queue."""
    code = getattr(err, "code", None)
    if code is not None:
        return False
    text = str(err)
    return any(m in text for m in _TRANSIENT_MARKS)


def _req(url: str, data: Optional[bytes] = None, headers: Optional[Dict[str, str]] = None,
         timeout: int = 300, retries: int = 6) -> bytes:
    """HTTP request with retry on transient LAN errors (observed on this network:
    WinError 10055/10060 under load). Backoff 5s..30s; re-raises after `retries`."""
    last: Optional[Exception] = None
    for attempt in range(max(1, retries)):
        req = urllib.request.Request(url, data=data, method="POST" if data else "GET",
                                     headers=headers or {})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.URLError as e:
            if not _is_transient(e) or attempt == retries - 1:
                raise
            last = e
            time.sleep(5 * (attempt + 1))
    if last:
        raise last


def _get_json(url: str, timeout: int = 60):
    return json.loads(_req(url, timeout=timeout).decode("utf-8"))


def build_t2v(prompt: str, width: int = 480, height: int = 832, length: int = 124,
              seed: int = 42, steps: int = 20, filename: str = "h3_clip",
              loras: Optional[list] = None) -> Dict:
    """API-format H3 T2V (no reference) workflow — proven wiring.

    loras: optional [(lora_name, strength_model, strength_clip), ...] injected as
    chained LoraLoader nodes between UNET/CLIP and the sampler (identity/site LoRAs).
    """
    wf = {
        "3": {"class_type": "UNETLoader",
              "inputs": {"unet_name": MODEL, "weight_dtype": "default"}},
        "4": {"class_type": "CLIPLoader",
              "inputs": {"clip_name": CLIP_ENC, "type": "minimax"}},
        "5": {"class_type": "VAELoader", "inputs": {"vae_name": VAE_VIDEO}},
        "6": {"class_type": "MiniMaxH3ImageToVideo",
              "inputs": {"clip": ["4", 0], "vae": ["5", 0], "prompt": prompt,
                         "width": width, "height": height, "length": length}},
        "10": {"class_type": "CLIPTextEncode",
               "inputs": {"clip": ["4", 0], "text": ""}},
        "7": {"class_type": "KSampler",
              "inputs": {"model": ["3", 0], "positive": ["6", 0], "negative": ["10", 0],
                         "latent_image": ["6", 1], "seed": seed, "steps": steps,
                         "cfg": 1.0, "sampler_name": "euler", "scheduler": "simple",
                         "denoise": 1.0}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["7", 0], "vae": ["5", 0]}},
        "12": {"class_type": "VAELoader", "inputs": {"vae_name": VAE_AUDIO}},
        "13": {"class_type": "VAEDecodeAudio", "inputs": {"samples": ["7", 0], "vae": ["12", 0]}},
        "11": {"class_type": "CreateVideo",
               "inputs": {"images": ["8", 0], "fps": 24.0, "audio": ["13", 0]}},
        "9": {"class_type": "SaveVideo",
              "inputs": {"filename_prefix": filename, "format": "mp4", "pix_fmt": "auto",
                         "video": ["11", 0], "codec": {"codec": "auto", "encoding": {}}}},
    }
    if loras:
        # chain LoraLoader nodes: UNET->Lora1->...->LoraN->KSampler; clip chain likewise
        pm, pc = ["3", 0], ["4", 0]
        for i, (lname, sm, sc) in enumerate(loras):
            nid = str(100 + i)
            wf[nid] = {"class_type": "LoraLoader", "inputs": {
                "model": pm, "clip": pc, "lora_name": lname,
                "strength_model": sm, "strength_clip": sc}}
            pm, pc = [nid, 0], [nid, 1]
        wf["7"]["inputs"]["model"] = pm
        wf["6"]["inputs"]["clip"] = pc
        wf["10"]["inputs"]["clip"] = pc
    return wf


def build_i2v(prompt: str, width: int = 480, height: int = 832, length: int = 124,
              seed: int = 42, steps: int = 20, filename: str = "h3_i2v",
              first_frame: str = "", last_frame: str = "",
              loras: Optional[list] = None) -> Dict:
    """H3 I2V/FL2V workflow with a first_frame (and optional last_frame).

    first_frame/last_frame are already-uploaded ComfyUI image names
    (from upload_image()). If a local path is passed, caller should upload first.
    """
    wf = build_t2v(prompt, width, height, length, seed, steps, filename, loras)
    extra_inputs = {}
    if first_frame:
        wf["20"] = {"class_type": "LoadImage", "inputs": {"image": first_frame}}
        extra_inputs["first_frame"] = ["20", 0]
    if last_frame:
        wf["21"] = {"class_type": "LoadImage", "inputs": {"image": last_frame}}
        extra_inputs["last_frame"] = ["21", 0]
    wf["6"]["inputs"].update(extra_inputs)
    return wf


def queue(base: str, workflow: Dict) -> str:
    """POST /prompt -> prompt_id."""
    body = json.dumps({"prompt": workflow}).encode("utf-8")
    out = json.loads(_req(base + "/prompt", data=body,
                          headers={"Content-Type": "application/json"}).decode("utf-8"))
    if "error" in out:
        raise RuntimeError(f"queue rejected: {out.get('error')} {out.get('node_errors')}")
    return out["prompt_id"]


def poll(base: str, prompt_id: str, timeout: int = 1800, interval: int = 5) -> Dict:
    """Poll /history until the prompt completes; return {status, outputs}.

    Transient network errors (server under load, flaky LAN) are retried within
    the timeout window instead of aborting the whole run — the job may well
    still be generating server-side.
    """
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            hist = _get_json(base + f"/history/{prompt_id}", timeout=60)
        except Exception:
            time.sleep(interval)
            continue
        if prompt_id in hist:
            e = hist[prompt_id]
            status = e.get("status", {}).get("status_str", "unknown")
            if status in ("success", "error", "fatal"):
                files = []
                for o in (e.get("outputs") or {}).values():
                    for f in (o.get("images") or []) + (o.get("videos") or []) + (o.get("gifs") or []):
                        files.append(f)
                return {"status": status, "outputs": e.get("outputs", {}), "files": files,
                        "messages": e.get("status", {}).get("messages", [])}
        time.sleep(interval)
    return {"status": "timeout", "outputs": {}, "files": []}


def download(base: str, filename: str, out_path: str, subfolder: str = "") -> str:
    """Fetch a produced file via /view -> out_path."""
    q = f"filename={filename}&subfolder={subfolder}&type=output"
    data = _req(f"{base}/view?{q}", timeout=300)
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(data)
    return out_path


def upload_image(base: str, local_path: str, subfolder: str = "", overwrite: bool = True) -> str:
    """Multipart-upload an image to ComfyUI; return its name for LoadImage."""
    import uuid
    boundary = "----h3boundary" + uuid.uuid4().hex
    name = os.path.basename(local_path)
    if not name.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
        name = os.path.splitext(name)[0] + ".png"
    payload = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="image"; filename="{name}"\r\n'
        "Content-Type: image/png\r\n\r\n"
    ).encode() + open(local_path, "rb").read() + (
        f"\r\n--{boundary}\r\n"
        f'Content-Disposition: form-data; name="overwrite"\r\n\r\n{"true" if overwrite else "false"}\r\n'
        f"--{boundary}--\r\n"
    ).encode()
    req = urllib.request.Request(
        base + "/upload/image", data=payload, method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(req, timeout=120) as r:
        out = json.loads(r.read().decode("utf-8"))
    if out.get("subfolder"):
        return f"{out['subfolder']}/{out['name']}"
    return out["name"]


def generate(base: str, prompt: str, out_path: str, width: int = 480, height: int = 832,
             length: int = 124, seed: int = 42, steps: int = 20,
             first_frame: str = "", last_frame: str = "", filename: str = "h3_clip",
             timeout: int = 1800, verbose: bool = True, loras: Optional[list] = None) -> str:
    """Full T2V/I2V generation -> out_path. Returns the saved file path."""
    wf = (build_i2v(prompt, width, height, length, seed, steps, filename, first_frame, last_frame, loras)
          if first_frame else
          build_t2v(prompt, width, height, length, seed, steps, filename, loras))
    pid = queue(base, wf)
    if verbose:
        print(f"[comfy] queued {pid} ({'I2V' if first_frame else 'T2V'} {width}x{height}x{length} seed={seed})")
    res = poll(base, pid, timeout=timeout)
    if verbose:
        print(f"[comfy] status={res['status']} files={res.get('files')}")
    if res["status"] != "success":
        raise RuntimeError(f"H3 generation failed: {res.get('messages', res.get('status'))}")
    f = next((f for f in res["files"] if str(f.get("filename", "")).endswith(".mp4")),
             res["files"][0])
    return download(base, f["filename"], out_path, f.get("subfolder", ""))


def extract_last_frame(video_path: str, out_png: str) -> str:
    """Grab the last frame of a clip -> png (for 尾帧链 chaining). Uses ffmpeg."""
    import subprocess
    ff = _ffmpeg_bin()
    subprocess.run([ff, "-y", "-sseof", "-0.1", "-i", video_path,
                    "-frames:v", "1", "-q:v", "2", out_png],
                   check=False, capture_output=True)
    return out_png


def _ffmpeg_bin() -> str:
    """imageio_ffmpeg's bundled binary (system ffmpeg may not exist)."""
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"
