#!/usr/bin/env bash
set -euo pipefail

# Standard project runner. ComfyUI remains on spark2; this script only
# orchestrates from the control node and stores each run in its own directory.
PROJECT_JSON="${1:?usage: run_project.sh <project.json> [comfy_base]}"
COMFY_BASE="${2:-http://127.0.0.1:8188}"
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
PY="/home/exalex/miniconda3/envs/sol-engine/bin/python"
SPARK1_ARCHIVE_ROOT="${SPARK1_ARCHIVE_ROOT:-/home/exalex/h3Movie}"

TITLE="$($PY -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["title"])' "$PROJECT_JSON")"
STAMP="$(date +%Y%m%d-%H)"
OUT_DIR="$ROOT/gen/${TITLE}-${STAMP}"

mkdir -p "$OUT_DIR"
echo "[run] project: $TITLE"
echo "[run] output:  $OUT_DIR"
echo "[run] comfy:   $COMFY_BASE (ComfyUI must be on spark2)"

cp "$PROJECT_JSON" "$OUT_DIR/${TITLE}.json"
PYTHONPATH="$ROOT/output/scripts" "$PY" -m h3_short_drama.pipeline prompts \
  --shots "$PROJECT_JSON" --out "$OUT_DIR/prompts"
PYTHONPATH="$ROOT/output/scripts" "$PY" -m h3_short_drama.validate_gates \
  "$PROJECT_JSON" --log-dir "$OUT_DIR"

PYTHONPATH="$ROOT/output/scripts" "$PY" - "$PROJECT_JSON" "$COMFY_BASE" "$OUT_DIR" <<'PY'
import sys
from h3_short_drama import series

project_json, comfy_base, out_dir = sys.argv[1:]
records = series.run_from_json(comfy_base.rstrip("/"), project_json, out_dir=out_dir)
failed = [r for r in records if r.get("error")]
for record in records:
    if record.get("error"):
        print(f"[run] FAILED {record['shot_id']}: {record['error']}")
    elif record.get("episode"):
        print(f"[run] EPISODE {record['episode']}")
    elif record.get("clip"):
        print(f"[run] CLIP {record['clip']}")
if failed:
    raise SystemExit(1)
PY

if [[ -n "${H3MOVIE_USER:-}" && -n "${H3MOVIE_SHARE:-}" ]]; then
  "/home/exalex/LLM/h3/syncenv/bin/python" \
    /home/exalex/LLM/h3/sync_h3movie.py "$OUT_DIR"
else
  # spark1 is the control node and the local archive. No Windows/SMB setup is
  # needed: keep a second local copy under the stable h3Movie archive root.
  mkdir -p "$SPARK1_ARCHIVE_ROOT"
  rsync -a "$OUT_DIR/" "$SPARK1_ARCHIVE_ROOT/$(basename "$OUT_DIR")/"
  echo "[run] spark1 archive: $SPARK1_ARCHIVE_ROOT/$(basename "$OUT_DIR")"
fi

echo "[run] complete: $OUT_DIR"
