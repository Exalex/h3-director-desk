"""H3 short-drama production pipeline.

Modules: data (schema) / prompt (compiler) / shot_table (6-rule self-check)
/hardware (profile planner) / api (providers, dry-run safe) / assemble (ffmpeg)
/pipeline (CLI).

Run: python -m h3_short_drama <check|prompts|plan|assemble|run> ...
"""
from . import data, prompt, shot_table, hardware, api, assemble, generate, character_lock, advance, comfyui_gen, series, pipeline

__all__ = ["data", "prompt", "shot_table", "hardware", "api", "assemble", "generate", "character_lock", "advance", "comfyui_gen", "series", "pipeline"]
