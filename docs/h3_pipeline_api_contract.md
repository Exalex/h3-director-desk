# H3 短剧本地管线 → Web 导演台后端 API 设计契约

依据真实源码逐行核对（源码路径 `output/scripts/h3_short_drama/`）。后端应把下面每个"可复用管线函数"包一层 JSON HTTP 接口。所有路径常量、默认值、行为均与现有代码**精确一致**；标注"(签名)"的函数是 CLI 命令级入口，后缀 `_cmd_*`。

---

## 1. 数据模型摘要（data.py，dataclass，纯 stdlib）

### 枚举常量（字符串常量）
| 常量 | 取值 |
|---|---|
| `ASPECTS` | `["21:9","16:9","4:3","1:1","3:4","9:16","2:1","3:2","5:4","4:5","2:3","1:2","9:21"]` |
| `H3_MODES` | `["T2VA","I2VA","FL2VA","L2VA","Ref2VA"]` |
| `RETENTION_VISUAL` | `["fully_preserved","partially_preserved","attribute_transfer","weak_reference"]` |
| `RETENTION_AUDIO` | `["fully_copy","partially_copy","reference","weak_reference"]` |
| `HOOK_TYPES` | `["visual-joke","reversal","suspense","tender","chase","reveal","callback","expression-beat"]` |
| `CONTINUITY` | `["hard_cut","latent_pin","motion_ref"]` |
| `CAMERA_SHOTS` | `["ECU","CU","MCU","MS","MLS","LS","ELS"]` |
| `CAMERA_ANGLES` | `["EYE_LEVEL","HIGH_ANGLE","LOW_ANGLE","BIRD_EYE","DUTCH","OVER_SHOULDER"]` |
| `CAMERA_MOVEMENTS` | `["STATIC","PAN","TILT","DOLLY_IN","DOLLY_OUT","TRACK","CRANE","HANDHELD","STEADICAM","ZOOM_IN","ZOOM_OUT"]` |
| `VIDEO_MODELS` | `["H3","Seedance2"]` |

### `Reference`（必填字段在前，后为带默认值字段）
| 字段 | 类型 | 默认 |
|---|---|---|
| `label` | str | (必填) 如 `"<Subject 1>" / "<Picture 2>" / "<Video 1>" / "<Audio 1>"` |
| `kind` | str | `"person"` |
| `retention` | str | `"fully_preserved"` |
| `retention_note` | str | `""` |
| `path` | str | `""` |
| `description` | str | `""` |
| `char` | str | `""` |
| `used_as` | str | `"frame_anchor"`（`frame_anchor \| storyboard \| defines_subject`） |

### `PerSecond`（每秒指令，需覆盖 5 要素）
| 字段 | 类型 | 默认 |
|---|---|---|
| `rng` | str | (必填) 如 `"0-1s"` / `"2.0-2.5s"` |
| `action` | str | `""` |
| `camera` | str | `""` |
| `spatial` | str | `""` |
| `audio` | str | `""` |
| `handoff` | str | `""` |

### `DialogueLine`
| 字段 | 类型 | 默认 |
|---|---|---|
| `text` | str | (必填) |
| `speaker_id` | str | `"S1"` |
| `tone` | str | `""` |
| `time_range` | str | `""` |
| `is_diegetic` | bool | `True` |

### `Shot`（核心；含生成参数）
| 字段 | 类型 | 默认 |
|---|---|---|
| `shot_id` | str | (必填) |
| `duration_s` | int | (必填) |
| `continuity_handoff` | str | (必填) |
| `fixed_landmarks` | List[str] | `[]` |
| `char_positions` | Dict[str,str] | `{}` |
| `exited_chars` | List[str] | `[]` |
| `lighting_baseline` | str | `""` |
| `hook_type` | str | `"expression-beat"` |
| `shot_description` | str | `""` |
| `per_second` | List[PerSecond] | `[]` |
| `narration` | str | `""` |
| `dialogue` | List[DialogueLine] | `[]` |
| `sfx` | List[str] | `[]` |
| `mode` | str | `"I2VA"` |
| `video_model` | str | `"H3"` |
| `resolution_tier` | str | `"768P"`（`768P \| 2K \| draft`） |
| `aspect` | str | `"9:16"` |
| `references` | List[Reference] | `[]` |
| `first_frame` | str | `""` |
| `last_frame` | str | `""` |
| `negative` | str | `"morphing, flickering, distorted face, extra fingers, blurry, low quality, watermark, text overlay"` |
| `continuity_type` | str | `"hard_cut"` |
| `airlock_s` | float | `0.0` |
| `seed` | int | `0`（0=自动每镜 seed；>0=定卡） |
| `edit_target_s` | float | `0.0`（0=用 duration_s 剪） |
- **反序列化**：`Shot.from_dict(d)` 忽略未知键；嵌套 `per_second/dialogue/references` 自动构造子对象。

### `CharacterCard`
| 字段 | 类型 | 默认 |
|---|---|---|
| `name` | str | (必填) |
| `identity_note` | str | (必填) 视觉ID锚点 |
| `image_path` | str | `""` |
| `do_not_change` | List[str] | `[]` |

### `SceneCard`
| 字段 | 类型 | 默认 |
|---|---|---|
| `name` | str | (必填) |
| `description` | str | (必填) |
| `landmarks` | List[str] | `[]` |
| `light_baseline` | str | `""` |
| `image_path` | str | `""` |

### `Project`
| 字段 | 类型 | 默认 |
|---|---|---|
| `title` | str | (必填) |
| `what_if` | str | (必填) |
| `target_feeling` | str | `""` |
| `aspect` | str | `"9:16"` |
| `duration_s` | int | `45` |
| `dialogue_mode` | str | `"有对白"` |
| `dialogue_language` | str | `"未指定"` |
| `visual_style` | str | `""` |
| `characters` | List[CharacterCard] | `[]` |
| `scenes` | List[SceneCard] | `[]` |
| `shots` | List[Shot] | `[]` |

> 序列化注意：dataclass 输出用 `vars(o)`（**不递归**）即可；ep01.json 的 `characters/scenes` 用 `vars(c)`，`shots` 用 `vars(s)`。Node `Shot` 含嵌套对象不需递归展开（`json.dump` 用 `default=str` 兜底）。

---

## 2. 可复用管线函数清单

> 标注约定：**【副作用】** = 网络API调用 / LLM / 磁盘 / ffmpeg / ComfyUI；**【时长】** = 同步短任务(ms级) / 秒级 / 长任务(分钟~数十分钟，后端必须放后台线程+状态轮询)。

### 2.1 pipeline.py（Orchestrator + CLI）— 总入口 `main(argv)->int`，`_load_project(path)->data.Project`

`_load_project(path)`：从 JSON 文件读入并构造 `Project`（characters/scenes/shots 全量反序列化）。
- 【副作用】读盘。**【时长】** 秒级。**线程安全** 是（纯构建，但注意它 hold 一个 file handle 直到函数结束）。

11 个 `cmd_*`（均为 CLI 层；后端可直接复用内部函数而非这些——此处列出其"实质"）：

| 命令 | 实质 | 副作用 | 时长 |
|---|---|---|---|
| `cmd_check(args)` | `_load_project` + `shot_table.self_check(proj)`，返回 `0/2` | 读盘 | 秒级 |
| `cmd_prompts(args)` | `prompt.compile_all(proj)`；可选写 `{shot_id}.txt` 到 `--out` 目录 | **写盘**(可选) | 秒级 |
| `cmd_plan(args)` | `hardware.plan_text(vram,aspect,seconds,quality,face)` 打印 | 无 | 秒级 |
| `cmd_assemble(args)` | 对每个 clip 打印 `probe()`，`assemble.assemble_plan()`；`--execute` 时 `assemble.run()` | **调 ffmpeg**(execute时) + **写盘**(中间文件) | 秒级~分钟级 |
| `cmd_run(args)` | check + compile_all + 对每镜生成 provider spec：H3/Seedance2→`api.openai_video(...poll=False)`；否则→`build_volc_content`+`api.volcengine_video(...poll=False)`。dry-run 只打 payload，不提交 | **调 api**(poll=False 不阻塞) | 秒级 |
| `cmd_concept(args)` | `generate.generate_concept(...,dry_run=?)` | **需 OPENAI_API_KEY** 才真调 LLM | 秒级~几十秒 |
| `cmd_storyboard(args)` | `generate.generate_storyboard(...,dry_run=?)`；execute 时把 project 写 JSON | **需 LLM** / 读写盘 | 秒级~几十秒 |
| `cmd_lock(args)` | `_load_project` + `character_lock.characters_from` + 逐镜 `lock_shot` + `validate_locked`；可选写锁定后 JSON | **写盘**(可选) | 秒级 |
| `cmd_advance(args)` | `advance.report(proj)` 打印剧情推进脊 | 读盘 | 秒级 |
| `cmd_comfy(args)` | `comfyui_gen.generate(...)` 单镜生成；可选先 `upload_image` | **调 ComfyUI + FFMPEG extract + 写盘** | **长任务**（默认 timeout=1800s） |
| `cmd_series(args)` | `series.run_from_json(base,shots,out_dir)` 连续剧生成 | **调 ComfyUI 逐镜 + ffmpeg + 写盘** | **长任务** |

### 2.2 prompt.py（编译器，无网络/无盘）
- **`assign_speaker_ids(project)->None`**：按全剧首次出现顺序把 `speaker_id` 稳定映射为 S1,S2…（原地改 project）。无副作用。毫秒级。
- **`compile(shot, project)->str`**：`shot.mode=="Ref2VA"`→`compile_ref_prompt`（6段），否则→`compile_base_prompt`（3段）。
- **`compile_all(project)->dict[str,str]`**：先 `assign_speaker_ids` 再 `{shot_id: compile(...)}`。无副作用（会原地改 speaker_id）。秒级。
- `compile_base_prompt`/`compile_ref_prompt`/`_per_second_block`/`_anchors_block`/`_dialogue_lines` 为内部函数。
- 说明：H3 提示词模板细节（diegetic→`<d>[Lang] text</d>`、narration→VO、retention 词汇原文输出、storyboard 标签 `[char:]` 等剥除）见源码，后端无需重写，直接调用即可。

### 2.3 shot_table.py（6 规则自检，纯计算）
- **`self_check(project)->tuple[bool,list[str]]`**：聚合 6 个 gate（钩子密度/单镜≤15s/单镜≤3角色/空间继承/逐秒覆盖/跨镜连续），返回 `(是否通过, [失败信息])`。
- 明细 gate 函授：`check_hook_density`、`check_single_shot_duration`、`check_chars_per_shot(project,char_names=None)`、`check_spatial_inheritance`、`check_per_second_coverage`、`check_cross_shot_continuity`，每个返回 `list[str]`。
- 无副作用。线程安全。毫秒~秒级。

### 2.4 hardware.py（profile 规划器，纯计算）
- **`plan_text(vram_gb:float, aspect:str, seconds:float, quality:str, face:bool)->str`**：打印友好文本（profile/canvas/frames/steps/block_cache/offload/lora/validate 警告）。CLI `plan` 用它。
- **`pick_profile(vram_gb, aspect="16:9", seconds=5.0, quality="fast", for_face=False)->Profile`**：返回 `Profile(name,width,height,frames,steps,block_cache,offload,lora,note)`。
- **`align_frame_count(seconds, fps=24)->int`**：取 `n=max(5,round(秒*fps))`，再 `n += (5-(n%17))%17` → **17k+5 帧网格**。
- `validate(profile,aspect)->list[str]`（32 对齐 + 17k+5 校验）；`canvas_for_aspect/aspect,short_edge,align=True)`；`align32(w,h)`。
- 无副作用。线程安全。毫秒级。

### 2.5 api.py（云厂商 Provider 客户端，dry-run 安全 —— **本后端大概率不需要**，仅列出防漏）
- 常量：`MINIMAX_GLOBAL=https://api.minimax.io`、`MINIMAX_CN=https://api.minimaxi.com`、`OPENAI_BASE=https://api.openai.com/v1`、`VOLC_BASE=https://ark.cn-beijing.volces.com/api/v3`。
- **`openai_video(prompt,size,seconds,model="sora",input_reference_b64="",seed=-1,api_key="",poll=True)->dict`**：无 key 返回 `{"dry_run":True,...payload}`；`poll=True` 时最多 60 次×2s 轮询。
- **`volcengine_video(content,ratio,duration,model="",seed=-1,api_key="",poll=True)->dict`**。
- **`minimax_context_ir(prompt,duration,ratio,api_key="",region="global")`**、**`minimax_regenerate_2k(video_b64,prompt,duration,ratio,api_key="",region="global")`**。
- **`build_volc_content(prompt,first_b64,last_b64,key_b64)->list`**：构造 role-tagged 三帧 content 列表。
- 【副作用】需对应 API KEY 才真发起 HTTP；poll=True 时秒~2分钟级。**线程安全** 是（每次独立 urllib）。本地 ComfyUI 方式无需这些。

### 2.6 assemble.py（ffmpeg 装配）
- **`probe(path)->dict`**：ffprobe 读 `{width,height,fps,sample_rate,duration,ar}`；sample_rate 缺省 32000、fps 缺省 24.0。**【副作用】**调用 `ffprobe` 子进程。秒级。非线程安全需谨慎（subprocess 并发 ok）。
- **`assemble_plan(clips:list[str], out, bgm="", subtitle="", canvas=(832,1472))->list[list[str]]`**：返回一串 ffmpeg 命令列表（不执行）。内部：每 clip `normalize_cmd`→`_norm_XX.mp4`；链式 `build_xfade`→`_join_XX.mp4`（过渡 `TRANSITIONS=[fade,dissolve,wipeleft,circleopen,slideright,fadefast]` 循环，0.4s）；可选 BGM `{out}.withbgm.mp4`；可选字幕 `{out}.final.mp4`；最终 `cp cur out`。**【副作用】**内部为算 offset 调 `probe()`（ffprobe）。秒级。
- **`run(cmds)->None`**：顺序执行每个命令（`subprocess.run(check=True)`），`cp` 用 `shutil.copyfile`。**【副作用】**调 ffmpeg + 写盘 + 调 cp。**分钟级/CPU密集**（取决于时长、分辨率）。
- `normalize_cmd(src,dst,target=(832,1472),fps=24)`、`match_tail_audio`、`build_xfade` 为内部；默认 canvas `832x1472`（0.4MP 9:16、32 对齐；832/1472 均可被 32 整除）。
- **临时文件命名规律**：`_norm_{i:02d}.mp4`（i 从 0 起）、`_join_{i:02d}.mp4`（i 从 1 起）、`{out}.withbgm.mp4`、`{out}.final.mp4`、最后 `cp` 到 `out`。注意这些中间文件生成在工作目录（相对名），**未清理**——后端应放进独立 job 工作目录并考虑清理。
- **装配与 QC 关联**：ep01 生产驱动(`odyssey_ep01.py`)用的是" trim 各 clip 到 `edit_target_s` + hard-cut concat"而非 xfade；trim 文件命名 `{shot_id}_trim{int(t)}.mp4`，concat 列表 `concat_list.txt`，最终 `EP01_final.mp4`。

### 2.7 comfyui_gen.py（**本地最后一公里生成器** —— 后端主生成引擎）
- 常量：`DEFAULT="http://192.168.3.153:8188"`、`MODEL="minimax_h3_fl2va_pruned_fp8_scaled.safetensors"`、`CLIP_ENC="qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors"`、`VAE_VIDEO="minimax_h3_video_vae_fp16.safetensors"`、`VAE_AUDIO="minimax_h3_audio_vae_fp32.safetensors"`。
- **`build_t2v(prompt,width=480,height=832,length=124,seed=42,steps=20,filename="h3_clip")->dict`**：构造 API-format H3 工作流（无参考）。纯构造，无副作用，毫秒级。
- **`build_i2v(prompt,width=480,height=832,length=124,seed=42,steps=20,filename="h3_i2v",first_frame="",last_frame="")->dict`**：T2V 基础上加 `LoadImage` 节点注入 first/last_frame（**要求是已上传的 ComfyUI 图片名**）。纯构造。
- **`queue(base,workflow)->str`**：POST `{base}/prompt` → 返回 `prompt_id`。**【副作用】**HTTP。秒级。
- **`poll(base,prompt_id,timeout=1800,interval=5)->dict`**：轮询 `{base}/history/{prompt_id}`，完成返回 `{status,outputs,files,messages}`；超时返回 `{"status":"timeout"}`。**【副作用】**HTTP（循环）。**长任务**（最多 1800s）。后端应把它映射为"任务轮询"：**不要**在前端等待，让后端起后台任务，前端用 GET 轮询。
- **`download(base,filename,out_path,subfolder="")->str`**：GET `{base}/view?...&type=output` → 写盘 `out_path`，返回路径。**【副作用】**HTTP + **写盘**。秒~几十秒。
- **`upload_image(base,local_path,subfolder="",overwrite=True)->str`**：multipart POST `{base}/upload/image` → 返回 ComfyUI 图片名（有 subfolder 则 `{subfolder}/{name}`）。**【副作用】**HTTP + **读盘上传**。秒级。
- **`generate(base,prompt,out_path,width=480,height=832,length=124,seed=42,steps=20,first_frame="",last_frame="",filename="h3_clip",timeout=1800,verbose=True)->str`**：**全流程生成** → build workflow（有 first_frame 走 I2V，否则 T2V）→ `queue` → `poll` → 失败抛 `RuntimeError` → `download` 找到 `.mp4` 并保存，返回路径。**【副作用】**调 **ComfyUI**(需在线) + **写盘**。**【长任务】**（H3 一镜数分钟，timeout=1800s）。**线程安全**：逐次独立，可并行多镜，但**依赖同一台 ComfyUI 的排队能力**（建议后端做并发上限）。
- **`extract_last_frame(video_path,out_png)->str`**：ffmpeg `-sseof -0.1 -frames:v 1` 抓尾帧→png（供尾帧链）。**【副作用】**调 ffmpeg + **写盘**。秒级。
- **关键**：`generate` 内部阻塞轮询到完成——**必须放后台线程**，绝不能直接在 HTTP 请求里同步跑。

### 2.8 character_lock.py（身份定卡）
- **`DEFAULT_SEED = 1234567890`**。
- **`seed_for(character, base_seed=DEFAULT_SEED)->int`**：确定性每角色 seed：`h=(h*131+ord(c))&0xFFFFFFFF` over chars；`(base_seed+h)%(2**31)`。无副作用。毫秒。
- **`character_reference(name,image_path,kind="person")->Reference`**：构造 `fully_preserved` 的 `<Picture 1>` 引用。纯构造。
- **`lock_shot(shot, characters:dict[str,str], base_seed=DEFAULT_SEED)->int`**：把镜头强制上身份锁：无角色返回 -1；否则若非 I2VA/FL2VA/L2VA/Ref2VA 升级为 I2VA；首角色卡设为 `first_frame`；为每个在场角色附加 `fully_preserved` 引用并重编号 Picture 标签；**返回该镜 lead 角色的定卡 seed**（注意：**不写回 shot.seed**，只返回）。无网络/无盘。秒级。**有副作用**（原位改 shot）。
- **`validate_locked(shots, characters)->list[str]`**：校验无角色镜退回 T2VA、I2VA 有首帧、Ref2VA 有引用、seed 不漂移。
- **`characters_from(project)->dict[str,str]`**：`{name: image_path}` 只含 `image_path` 非空角色卡。

### 2.9 series.py（连续剧自动生成 —— 尾帧链）
- **`generate_series(base, shots, project, out_dir="series_out", width=480, height=832, steps=20, base_seed=42, assemble=True, verbose=True)->list[dict]`**：逐镜：`prompt.compile` → seed=`shot.seed` 或 `(base_seed + i*7919)%2**31` → 首帧=`该镜角色卡`或`上一镜尾帧` → 上传/`cg.generate` → `extract_last_frame` 链给下一镜 → 可选 `_assemble_clips`(canvas=(480,832)) 拼 `episode.mp4`。产出 `[{shot_id,clip,seed,first_frame,prompt}]`（失败项含 `error`），最后附 `{episode:path}`。**【副作用】**调 **ComfyUI 逐镜**+ffmpeg+**写盘**。**【长任务】**（N 镜×每镜 1-数分钟）。**不阻塞**：必须后台线程。线程安全：可整集串行（尾帧链天然串行），多集可并行但共享一台 ComfyUI。
- **`run_from_json(base, project_json, out_dir="series_out")->list[dict]`**：读 JSON → `Shot.from_dict` 列表 + 组装 `Project` → `generate_series`。**【副作用】**读盘 + 上述长任务。
- **`_frame_count(seconds)->int`**：17k+5 帧网格（同 hardware.align_frame_count，`min(n,360)` 封顶；124≈5s）。

### 2.10 generate.py（创意层：点子→分镜，走 LLM —— 可选接入）
- **`generate_concept(idea, genre="", feeling="", dry_run=False)->dict`**：LLM 生成 15 字段概念。dry_run→`{"dry_run":True,"prompt":...}`；无 key→同 dry_run；真调 →`{"raw":..., "parsed":...}`。
- **`generate_storyboard(idea, aspect="9:16", duration_s=45, genre="", language="中文", dry_run=False)->dict`**：LLM 生成标准分镜，**解析为 project 并跑 `shot_table.self_check`**，返回 `{"project":obj,"self_check":{"pass":..,"failures":[..]}}` 或 `{"error":"parse failed","raw":..}`。
- `concept_prompt`/`storyboard_prompt`/`_chat`/`_extract_json` 为内部。`_chat`：OpenAI 兼容 `/v1/chat/completions`（`default model="deepseek-chat"`，`base` 缺省 `OPENAI_BASE_URL` 或 `https://api.openai.com/v1`，`key` 缺省 `OPENAI_API_KEY`，timeout=120s）。**【副作用】**需要 **OPENAI_API_KEY**（或自定义 base）才真调 LLM；**秒~一两分钟**（max_tokens=4096, timeout=120s）。**线程安全** 是。

### 2.11 advance.py（剧情推进校验，纯计算）
- **`spine(project)->list[dict]`**：每镜 `{shot_id,establishes,advances,hands_off,hook,next_opens}`。
- **`gaps(project)->list[str]`**：推进断裂校验。
- **`report(project)->str`**：文本报告（CLI `advance` 用）。均无副作用、毫秒级。

---

## 3. 关键路径与常量（后端配置清单）

| 项 | 值 | 来源 |
|---|---|---|
| 默认 ComfyUI base | `http://192.168.3.153:8188` | `comfyui_gen.DEFAULT`、`pipeline.py` CLI `--base` 默认、`odyssey_ep01.BASE` |
| ComfyUI 模型 | `minimax_h3_fl2va_pruned_fp8_scaled.safetensors`（UNET）、`qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors`（CLIP）、`minimax_h3_video_vae_fp16.safetensors`（视频VAE）、`minimax_h3_audio_vae_fp32.safetensors`（音频VAE） | `comfyui_gen.MODEL/CLIP_ENC/VAE_VIDEO/VAE_AUDIO` |
| 生成默认画幅 | `480x832`(comfy 单镜/系列，9:16)；装配 canvas `832x1472`（0.4MP 9:16，32 对齐）；ep01 生产用 `480x832` | comfyui/series/assemble |
| 默认帧数 | `length=124`（≈5s @24fps），CLI 分镜 `--len 124` | comfyui/pipeline |
| 帧数网格 | **17k+5**：`n=max(5,round(秒*24)); n+=(5-(n%17))%17`，`min(n,360)` 封顶 | `hardware.align_frame_count` / `series._frame_count` / odyssey |
| 9:16 画幅常量 | compose `(480,832)`(生成)、`(832,1472)`(装配)、`(352/480/768)`(hardware short_edge) | 各模块 |
| 默认 seed 规则 | 定卡：`shot.seed` 优先；否则每镜 `(base_seed + i*7919)%(2**31)`（series base_seed=42；odyssey 用 42）；角色定卡 `seed_for(name,base_seed=1234567890)=(base_seed+h)%2**31` | series/character_lock |
| H3 默认 steps | `20`（comfy/cli/hardware quality）；profile 里 fast=4/balanced=6/quality=8 | 各模块 |
| ffmpeg 音频 | 32kHz（H3 输出 32k，切勿硬编 48k），aac 192k，双声道 | assemble |
| ffmpeg 视频 | libx264 yuv420p crf18 fps24 | assemble |
| 生成超时 | `generate timeout=1800`（comfy 默认）；odyssey 用 3000s | comfyui/odyssey |
| LLM | `OPENAI_API_KEY` / `OPENAI_BASE_URL`（默认 https://api.openai.com/v1），model `deepseek-chat`，send timeout=120s | generate._chat |
| xfade 过渡 0.4s 循环 | `TRANSITIONS=[fade,dissolve,wipeleft,circleopen,slideright,fadefast]` | assemble |

---

## 4. 装配与 QC

### 装配临时文件命名规律（assemble.py）
- 归一化：`_norm_{i:02d}.mp4`（i=0,1,2…）
- 链式 xfade：`_join_{i:02d}.mp4`（i=1,2…）
- BGM：`{out}.withbgm.mp4`；字幕：`{out}.final.mp4`；最终 `cp ... -> out`
- 全部生成于当前工作目录（相对名），**无清理**。
- ep01 生产路径（`odyssey_ep01.py`，非 xfade 而是 trim+hard-cut concat）：
  - trim：`{shot_id}_trim{int(edit_target_s)}.mp4`
  - concat 列表：`concat_list.txt`，最终 `EP01_final.mp4`

### QC 抽帧比对（research/qc_continuity.py）
- 思路：`PIL.Image.open(...).convert("RGB").resize((240,416))` → `np.float32`。
- 相似度：`sim(a,b)` 返回 `(mean_abs_diff, cosine_similarity)`：
  - `mad = np.mean(np.abs(a-b))`
  - `cos = dot(a,b)/(||a||*||b||+1e-8)`
- 判定：`cos>0.97`→「HIGH continuity」；`>0.9`→「medium (plot advanced)」；否则「drift / change」。
- 典型比对对（contiguity）：
  - `seam`: 前镜尾帧 `S01_last.png` vs 后镜首帧 `s02_first.png`（**接缝连续性**）
  - `drift first->last`: 同镜首帧 vs 尾帧（镜内漂移）
- **后端 QC 建议接口**：上传两个 PNG（或传入两个路径）→ 返回 `{mad, cos_sim, verdict}`。此 QC 依赖 `numpy` + `Pillow`，与主管线库分离，可独立挂到 `/qc/similarity`。

---

## 后端封装建议速览（供实现工程师参考，非本契约主体）

- **纯计算（可直接同步返回）**：`shot_table.self_check`、`prompt.compile_all`、`hardware.plan_text/pick_profile`、`advance.report/spine/gaps`、`character_lock.*`、`comfyui_gen.build_t2v/build_i2v`。
- **薄 I/O（秒级，可同步）**：`assemble.probe`、`api.*`(dry-run/poll=False)、`comfyui_gen.queue/upload_image/download`、`extract_last_frame`、`generate.*`(需 LLM)。
- **长任务（必须后台线程 + 任务ID + 状态轮询）**：
  - `comfyui_gen.generate`（单镜，ComfyUI 在线，timeout 1800s）
  - `series.generate_series / run_from_json`（整集，逐镜链式，数分钟~数十分钟）
  - `assemble.run`（装配，分钟级，无 ComfyUI）
- **长任务串行/并发**：`generate_series` 因尾帧链**天然串行**（前镜尾帧→下镜首帧）；多镜并行生成可用 `cg.generate`（但共享一台 ComfyUI 排队）；后端应设并发上限并对 ComfyUI 离线/超时做 `503`/状态 `comfy_offline`。
- **每镜 seed 结算**：先 `character_lock.lock_shot`（int 返回定卡 seed）再存回 `shot.seed`，或直接在 series 里按 `shot.seed 或 (base_seed+i*7919)%2**31`。

---

## 附录：本契约实际读取的文件路径

- `D:\workspace\deepseekSpace\aiDirector\output\scripts\h3_short_drama\__init__.py`
- `D:\workspace\deepseekSpace\aiDirector\output\scripts\h3_short_drama\pipeline.py`
- `D:\workspace\deepseekSpace\aiDirector\output\scripts\h3_short_drama\data.py`
- `D:\workspace\deepseekSpace\aiDirector\output\scripts\h3_short_drama\prompt.py`
- `D:\workspace\deepseekSpace\aiDirector\output\scripts\h3_short_drama\shot_table.py`
- `D:\workspace\deepseekSpace\aiDirector\output\scripts\h3_short_drama\hardware.py`
- `D:\workspace\deepseekSpace\aiDirector\output\scripts\h3_short_drama\api.py`
- `D:\workspace\deepseekSpace\aiDirector\output\scripts\h3_short_drama\assemble.py`
- `D:\workspace\deepseekSpace\aiDirector\output\scripts\h3_short_drama\comfyui_gen.py`
- `D:\workspace\deepseekSpace\aiDirector\output\scripts\h3_short_drama\character_lock.py`
- `D:\workspace\deepseekSpace\aiDirector\output\scripts\h3_short_drama\series.py`
- `D:\workspace\deepseekSpace\aiDirector\output\scripts\h3_short_drama\advance.py`
- `D:\workspace\deepseekSpace\aiDirector\output\scripts\h3_short_drama\generate.py`
- `D:\workspace\deepseekSpace\aiDirector\projects\odyssey\ep01.json`
- `D:\workspace\deepseekSpace\aiDirector\research\odyssey_ep01.py`
- `D:\workspace\deepseekSpace\aiDirector\research\qc_continuity.py`
