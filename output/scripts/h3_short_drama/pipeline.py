"""Orchestrator + CLI for the H3 short-drama pipeline.

Commands:
  check    --shots P.json                     run the 6-rule self-check
  prompts  --shots P.json [--out DIR]         compile every shot to an H3 prompt
  plan     --vram N --aspect 9:16 --seconds S [--quality fast] [--face]
  assemble --clips a.mp4 b.mp4 ... --out F [--bgm B.mp3] [--sub S.srt]
  run      --shots P.json                     full dry-run: check + prompts + specs

All provider calls are dry-run-safe (no API key -> prints the exact payload).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from . import data, prompt, shot_table, hardware, api, assemble


def _load_project(path: str) -> data.Project:
    d = json.load(open(path, "r", encoding="utf-8"))
    chars = [data.CharacterCard(**c) for c in d.get("characters", [])]
    scenes = [data.SceneCard(**s) for s in d.get("scenes", [])]
    shots = [data.Shot.from_dict(s) for s in d.get("shots", [])]
    proj_fields = {k: v for k, v in d.items() if k in ("title", "what_if", "target_feeling",
               "aspect", "duration_s", "dialogue_mode", "dialogue_language", "visual_style")}
    proj = data.Project(**proj_fields, characters=chars, scenes=scenes, shots=shots)
    return proj


def cmd_check(args):
    proj = _load_project(args.shots)
    ok, fails = shot_table.self_check(proj)
    print(f"shot-table self-check: {'PASS' if ok else 'FAIL'} ({len(proj.shots)} shots)")
    for f in fails:
        print("  ! " + f)
    if ok:
        print("shot-table self-check: passed")
    return 0 if ok else 2


def cmd_validate(args):
    from . import validate_gates

    return validate_gates.main([args.shots] + (["--no-log"] if args.no_log else []))


def cmd_prompts(args):
    proj = _load_project(args.shots)
    prompts = prompt.compile_all(proj)
    if args.out:
        os.makedirs(args.out, exist_ok=True)
        for sid, p in prompts.items():
            with open(os.path.join(args.out, f"{sid}.txt"), "w", encoding="utf-8") as f:
                f.write(p)
        print(f"wrote {len(prompts)} prompts to {args.out}/")
    else:
        for sid, p in prompts.items():
            print(f"\n===== {sid} =====\n{p}")
    return 0


def cmd_plan(args):
    print(hardware.plan_text(args.vram, args.aspect, args.seconds, args.quality, args.face))
    return 0


def cmd_assemble(args):
    clips = args.clips
    print("probe:", [assemble.probe(c) for c in clips])
    cmds = assemble.assemble_plan(clips, args.out, bgm=args.bgm, subtitle=args.sub,
                                  canvas=(args.w, args.h))
    if args.execute:
        assemble.run(cmds)
    else:
        for c in cmds:
            print("CMD:", " ".join(c))
    return 0


def cmd_run(args):
    proj = _load_project(args.shots)
    ok, fails = shot_table.self_check(proj)
    print(f"[check] {'PASS' if ok else 'FAIL'}: " + "; ".join(fails[:5]))
    prompts = prompt.compile_all(proj)
    for sid in prompts:
        print(f"[prompt] {sid} -> {len(prompts[sid])} chars")
    # per-shot provider spec (dry-run safe)
    for s in proj.shots:
        p = prompts[s.shot_id]
        if s.video_model.upper() in ("H3", "SEEDANCE2"):
            spec = api.openai_video(p, "portrait_720", s.duration_s,
                                    api_key=os.environ.get("OPENAI_API_KEY", ""),
                                    input_reference_b64="", poll=False)
        else:
            spec = api.build_volc_content(p)
            spec = api.volcengine_video(spec, s.aspect, s.duration_s,
                                        api_key=os.environ.get("VOLC_API_KEY", ""), poll=False)
        print(f"[spec] {s.shot_id} mode={s.mode} model={s.video_model} "
              f"{'DRY-RUN' if spec.get('dry_run') else 'submitted'}")
    print("[next] generate clips, then: assemble --clips ... --out final.mp4")
    return 0


def cmd_concept(args):
    from . import generate
    res = generate.generate_concept(args.idea, args.genre, args.feeling, dry_run=True)
    print(res["prompt"])
    if not args.execute:
        print("\n[dry-run] set OPENAI_API_KEY and pass --execute to call the LLM.")
    else:
        res2 = generate.generate_concept(args.idea, args.genre, args.feeling, dry_run=False)
        print(json.dumps(res2, ensure_ascii=False, indent=2))
    return 0


def cmd_storyboard(args):
    from . import generate
    res = generate.generate_storyboard(
        args.idea, args.aspect, args.duration, args.genre, args.language, dry_run=True)
    print(res["prompt"])
    if args.execute:
        live = generate.generate_storyboard(
            args.idea, args.aspect, args.duration, args.genre, args.language, dry_run=False)
        if live.get("error"):
            print("ERROR:", live["error"])
            print(live.get("raw", "")[:2000])
            return 1
        proj = live["project"]
        print("\n[project] self-check:", json.dumps(live["self_check"], ensure_ascii=False))
        if args.out:
            with open(args.out, "w", encoding="utf-8") as f:
                json.dump(proj, f, ensure_ascii=False, indent=2)
            print("wrote", args.out)
    else:
        print("\n[dry-run] set OPENAI_API_KEY and pass --execute to call the LLM.")
    return 0


def cmd_lock(args):
    from . import character_lock as cl
    proj = _load_project(args.shots)
    chars = cl.characters_from(proj)
    if not chars:
        print("no character cards with image_path; lock needs a reference per character")
        return 1
    for s in proj.shots:
        cl.lock_shot(s, chars, base_seed=args.base_seed)
    fails = cl.validate_locked(proj.shots, chars)
    print(f"[lock] {len(proj.shots)} shots, {len(chars)} locked character(s)")
    for s in proj.shots:
        lead = list(s.char_positions.keys())[0] if s.char_positions else "-"
        if lead in chars:
            print(f"  {s.shot_id}: mode={s.mode} first_frame={s.first_frame or '(none)'} "
                  f"seed={cl.seed_for(lead, args.base_seed)} refs={len(s.references)}")
    print(f"[lock] identity-lock: {'OK' if not fails else 'FAIL'}")
    for f in fails:
        print("  ! " + f)
    if args.out:
        import json
        d = {"title": proj.title, "aspect": proj.aspect, "duration_s": proj.duration_s,
             "dialogue_mode": proj.dialogue_mode, "dialogue_language": proj.dialogue_language,
             "visual_style": proj.visual_style,
             "characters": [vars(c) for c in proj.characters],
             "scenes": [vars(c) for c in proj.scenes],
             "shots": [vars(s) for s in proj.shots]}
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2, default=str)
        print("wrote", args.out)
    return 0 if not fails else 2


def cmd_advance(args):
    from . import advance as av
    proj = _load_project(args.shots)
    print(av.report(proj))
    return 0


def cmd_comfy(args):
    from . import comfyui_gen as cg
    base = args.base.rstrip("/")
    first = args.first_frame or ""
    if first and not first.startswith(("http", "//")) and os.path.exists(first):
        first = cg.upload_image(base, first)
        print(f"[comfy] uploaded first_frame -> {first}")
    out = args.out or "h3_clip.mp4"
    try:
        path = cg.generate(base, args.prompt, out, width=args.w, height=args.h,
                           length=args.len, seed=args.seed, steps=args.steps,
                           first_frame=first, last_frame=args.last_frame,
                           filename=args.filename, timeout=args.timeout)
        print(f"[comfy] DONE -> {path}")
        return 0
    except Exception as e:
        print(f"[comfy] ERROR: {e}")
        return 1


def cmd_series(args):
    from . import series
    base = args.base.rstrip("/")
    recs = series.run_from_json(base, args.shots, out_dir=args.out_dir)
    print("\n[series] results:")
    for r in recs:
        if "error" in r:
            print(f"  {r['shot_id']}: FAILED {r['error']}")
        elif "episode" in r:
            print(f"  episode -> {r['episode']}")
        else:
            print(f"  {r['shot_id']}: {r['clip']}")
    return 0


def main(argv=None):
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
    argv = argv if argv is not None else sys.argv[1:]
    ap = argparse.ArgumentParser(prog="h3_short_drama")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("check"); p.add_argument("--shots", required=True)
    p = sub.add_parser("validate"); p.add_argument("--shots", required=True); p.add_argument("--no-log", action="store_true")
    p = sub.add_parser("prompts"); p.add_argument("--shots", required=True); p.add_argument("--out")
    p = sub.add_parser("plan"); p.add_argument("--vram", type=float, required=True)
    p.add_argument("--aspect", default="9:16"); p.add_argument("--seconds", type=float, default=5.0)
    p.add_argument("--quality", default="fast", choices=["fast", "balanced", "quality"])
    p.add_argument("--face", action="store_true")
    p = sub.add_parser("assemble"); p.add_argument("--clips", nargs="+", required=True)
    p.add_argument("--out", required=True); p.add_argument("--bgm"); p.add_argument("--sub")
    p.add_argument("--w", type=int, default=832); p.add_argument("--h", type=int, default=1472)
    p.add_argument("--execute", action="store_true")
    p = sub.add_parser("run"); p.add_argument("--shots", required=True)

    p = sub.add_parser("concept"); p.add_argument("--idea", required=True)
    p.add_argument("--genre", default=""); p.add_argument("--feeling", default="爽感+反转")
    p.add_argument("--execute", action="store_true")
    p = sub.add_parser("storyboard"); p.add_argument("--idea", required=True)
    p.add_argument("--aspect", default="9:16"); p.add_argument("--duration", type=int, default=45)
    p.add_argument("--genre", default=""); p.add_argument("--language", default="中文")
    p.add_argument("--out"); p.add_argument("--execute", action="store_true")

    p = sub.add_parser("lock"); p.add_argument("--shots", required=True)
    p.add_argument("--base-seed", type=int, default=1234567890)
    p.add_argument("--out")

    p = sub.add_parser("advance"); p.add_argument("--shots", required=True)

    p = sub.add_parser("comfy"); p.add_argument("prompt"); p.add_argument("--base", default="http://192.168.3.153:8188")
    p.add_argument("--w", type=int, default=480); p.add_argument("--h", type=int, default=832)
    p.add_argument("--len", type=int, default=124); p.add_argument("--seed", type=int, default=42)
    p.add_argument("--steps", type=int, default=20); p.add_argument("--out")
    p.add_argument("--first-frame"); p.add_argument("--last-frame"); p.add_argument("--filename", default="h3_clip")
    p.add_argument("--timeout", type=int, default=1800)

    p = sub.add_parser("series"); p.add_argument("--shots", required=True)
    p.add_argument("--base", default="http://192.168.3.153:8188")
    p.add_argument("--out-dir", default="series_out")

    args = ap.parse_args(argv)
    fn = {"check": cmd_check, "validate": cmd_validate, "prompts": cmd_prompts, "plan": cmd_plan,
          "assemble": cmd_assemble, "run": cmd_run,
          "concept": cmd_concept, "storyboard": cmd_storyboard,
          "lock": cmd_lock, "advance": cmd_advance,
          "comfy": cmd_comfy, "series": cmd_series}[args.cmd]
    return fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
