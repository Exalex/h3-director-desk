# Generation Output Convention

Every new run gets its own directory:

```text
gen/<project-title>-YYYYMMDD-HH/
```

For example: `gen/磨指甲-20260830-14/`.

The directory contains the complete run, not only the final MP4:

- source project JSON and compiled prompts
- per-shot MP4 files
- extracted last-frame PNG files
- `episode.mp4` when assembly is requested
- `.gates.jsonl` with quality-gate failures, if any

Use `output/scripts/h3_short_drama/run_project.sh` for new runs. It validates
the project before submitting work to ComfyUI on spark2, generates into the
timestamped directory, and then calls `sync_h3movie.py` when SMB credentials
are configured.

ComfyUI is not installed or started on spark01. The control process on spark01
uses the existing SSH tunnel to spark2:

```text
spark01:127.0.0.1:8188 -> spark2:127.0.0.1:8188
```

The default archive is also mirrored locally on spark1:

```text
/home/exalex/h3Movie/<project-title>-YYYYMMDD-HH/
```

Override it when needed with `SPARK1_ARCHIVE_ROOT`. This does not install or
run ComfyUI on spark1. It only copies completed project files on the control
node. The old Windows SMB uploader remains available but is not part of the
default workflow.

Windows sync configuration, if explicitly needed later, is runtime-only:

```text
H3MOVIE_HOST=192.168.3.98
H3MOVIE_SHARE=<share that maps to C:\\Users\\79475\\Desktop\\h3Movie>
H3MOVIE_USER=79475
H3MOVIE_PASS=<password>
```
