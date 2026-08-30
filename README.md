# H3 Director Desk

An operator-friendly web desk for creating and producing H3 short-drama
projects. The control service runs on **spark1**; the existing ComfyUI/H3
installation remains on **spark2**.

## Architecture

```text
browser on LAN
        |
        v
spark1: director/serve.py        project editing, validation, task monitor
        |
        +-- SSH tunnel 127.0.0.1:8188 --> spark2:127.0.0.1:8188
                                             ComfyUI + H3 GPU generation
```

The director desk does not install or run ComfyUI on spark1.

## Start

Keep an SSH tunnel from spark1 to spark2:

```bash
ssh -f -N -L 8188:127.0.0.1:8188 exalex@192.168.3.153 \
  -o ExitOnForwardFailure=yes -o ServerAliveInterval=30
```

Start the desk on spark1:

```bash
cd /home/exalex/aiDirector
/home/exalex/miniconda3/envs/sol-engine/bin/python director/serve.py \
  --host 0.0.0.0 --port 8088 --comfy http://127.0.0.1:8188
```

Open from the LAN:

```text
http://192.168.3.75:8088/
```

## Project Flow

1. Select an existing project in the left project switcher, or click **New
   Project**.
2. Create the project namespace first.
3. Enter the natural-language prompt in the following dialogue step.
4. Review the generated project and storyboard.
5. Run validation before submitting GPU work.
6. Submit one serial generation task and monitor its progress.

Each run is archived as:

```text
gen/<project-title>-YYYYMMDD-HH/
```

and mirrored locally on spark1 under:

```text
/home/exalex/h3Movie/<project-title>-YYYYMMDD-HH/
```

## Main Source Files

- `director/serve.py`: HTTP API, task registry, project switching, Qwen and
  spark2 orchestration
- `director/index.html`: desk layout and project controls
- `director/assets/app.js`: client state, project switching, task polling
- `director/assets/panels.js`: workflow panels
- `director/assets/style.css`: desk styling
- `output/scripts/h3_short_drama/`: H3 project model, prompt compiler,
  validation, ComfyUI generation and assembly

## Configuration

Runtime LLM settings are stored locally in `director/llm_config.json` and are
ignored by Git. Configure the OpenAI-compatible Spark endpoint in the desk's
settings panel. Do not commit API keys, model weights, generated media or local
archives.
