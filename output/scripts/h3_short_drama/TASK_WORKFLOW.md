# Task Workflow

## Roles

- **spark1**: receives the request, validates the project, stores prompts and
  outputs, and keeps the archive.
- **spark2**: runs the existing ComfyUI and H3 model. No ComfyUI is installed
  or started on spark1.

## Create A Task

The easiest way to create a new planning file is the interactive questionnaire.
It does not start ComfyUI and does not use a GPU:

```bash
cd /home/exalex/aiDirector
PYTHONPATH=output/scripts /home/exalex/miniconda3/envs/sol-engine/bin/python \
  output/scripts/h3_short_drama/create_task.py --out projects/my_task.json
```

Answer the questions, inspect `projects/my_task.json`, then run the validator.
The reliable input for generation is the reviewed project JSON. For an existing
project:

```bash
cd /home/exalex/aiDirector
bash output/scripts/h3_short_drama/run_project.sh \
  projects/nails.json http://127.0.0.1:8188
```

`127.0.0.1:8188` is the SSH tunnel on spark1, forwarding to ComfyUI on
spark2. The command creates a directory such as:

```text
gen/磨指甲-20260830-14/
```

It then saves the source JSON and prompts, runs quality gates, and only submits
to spark2 if validation passes. Completed files are mirrored to:

```text
/home/exalex/h3Movie/磨指甲-20260830-14/
```

## Interact In Plain Language

You can give the director request directly in the chat, for example:

- `创建一个10秒竖屏视频：夜晚酒店大堂，林晚给沈亦磨指甲。`
- `先只生成预览，不要生成正式视频。`
- `检查这个任务，不要调用GPU。`
- `继续任务 磨指甲-20260830-14。`
- `停止任务 磨指甲-20260830-14。`
- `把这个任务的提示词、参数和视频路径列出来。`

The request is first turned into a project JSON and shown for confirmation.
After confirmation, the runner follows this order:

```text
create project JSON -> validate -> show planned output -> submit one job ->
watch spark2 -> save on spark1 -> mirror archive -> report paths and errors
```

## What The User Must Confirm

Before a GPU run, only these decisions are needed:

- project title
- duration and aspect ratio
- characters and reference images
- scene/action/dialogue
- draft or final quality
- whether to generate one clip or assemble multiple clips

The system supplies technical parameters such as frame count, seed, H3 mode,
ComfyUI address, and output directory. It should not silently launch multiple
copies of the same task.

## Check And Resume

List recent archives:

```bash
ls -lt /home/exalex/h3Movie
```

Validate without generating:

```bash
cd /home/exalex/aiDirector
PYTHONPATH=output/scripts /home/exalex/miniconda3/envs/sol-engine/bin/python \
  -m h3_short_drama validate --shots projects/nails.json --no-log
```

The command exits before GPU submission when a hard gate fails. For the current
`nails.json`, it correctly reports that the N03 dialogue does not fit its
3-second time window.
