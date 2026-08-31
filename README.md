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

### Windows local

From PowerShell:

```powershell
python director\serve.py --host 127.0.0.1 --port 8088 --comfy http://127.0.0.1:8188
```

Or double-click `start_local.bat`. Open <http://127.0.0.1:8088/> in a browser.
Stop the service with `Ctrl+C` in the service window.

The desk itself uses only the Python standard library. `8088` is the desk UI
port; `8188` is ComfyUI's separate generation port. ComfyUI is optional for
opening and editing the desk, but it must be running at the configured address
for GPU generation. The checkout includes the editable Odyssey project JSON,
style bible, scene assets, and compiled prompt examples. It does not include
generated media, model weights, or runtime LLM configuration.

For a small local machine such as a 5800H PC, keep the desk on the local
machine and run ComfyUI + H3 on a separate LAN GPU host. See
[`docs/DEPLOYMENT_ARCHITECTURE.md`](docs/DEPLOYMENT_ARCHITECTURE.md).

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

## Local verification

The local desk can be checked without ComfyUI:

```powershell
python -m compileall -q director output\scripts\h3_short_drama
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8088/
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8088/api/projects
```

The project library reads one `project.json` manifest from each directory under
`projects/`. A project is the top-level workspace; each episode has its own
JSON, references, prompts, and generated output directory:

```text
projects/<project>/
  project.json       project manifest and episode list
  assets/            shared project materials
  episodes/<episode>/
    episode.json     this episode's storyboard and metadata
    assets/          scene references for this episode
    references/      character/reference images
    prompts/         compiled H3 prompts for this episode
    outputs/         generated clips and assembled video (ignored)
```

The bundled Odyssey project exposes three episodes in the left project
library. Switching either project or episode reloads the complete workspace;
new projects created from the desk use the same isolated directory layout.

## Troubleshooting ComfyUI port 8188

If `http://127.0.0.1:8188/` refuses the connection, ComfyUI is not running on
the local machine. Starting `director/serve.py` only starts the desk on `8088`;
it does not install or start ComfyUI.

For the documented remote setup, start ComfyUI on `spark2` first, then create
the tunnel from the control machine:

```bash
ssh -f -N -L 8188:127.0.0.1:8188 exalex@192.168.3.153 \
  -o ExitOnForwardFailure=yes -o ServerAliveInterval=30
```

The SSH account must have an authorized key/password and ComfyUI must already
be listening on `spark2:127.0.0.1:8188`. Without that external service, the
desk remains usable for project editing and validation, but video generation
will stay offline.

## Configuration

Runtime LLM settings are stored locally in `director/llm_config.json` and are
ignored by Git. Configure the OpenAI-compatible Spark endpoint in the desk's
settings panel. Do not commit API keys, model weights, generated media or local
archives.
