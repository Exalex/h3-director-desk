# H3 短剧 · 实现工作流（IMPLEMENTATION_WORKFLOW）

> 依据现行源码 `output/scripts/h3_short_drama/`（pipeline / data / prompt / character_lock / comfyui_gen / series / assemble / shot_table / advance / api / generate）逐行核对编写；CLI 入口 `python -m h3_short_drama <子命令>`，ComfyUI 默认地址 `http://192.168.3.153:8188`。

---

## 1. 总览：用户做什么、程序做什么

用户只做两件事：**提供原料** + **在 4 个关卡点头**，中间全部由程序自动执行。

| 谁 | 做什么 |
|---|---|
| 用户 | ① 故事点子（一句话即可）② 人物长相 ③ 时长 + 画幅 ④ 视觉风格；有参考图就提供 |
| 用户 | 在 4 个确认关卡做创意决策；最终验收拍板 |
| 程序 | 8 步流水线：大纲 → 角色卡（锁定）→ 场景卡 → 拆分镜 → 编译 H3 提示词 → 逐镜生成（尾帧链）→ 拼集 + BGM → QC |

每步产物落盘：项目 JSON、逐镜 prompt txt、逐镜 mp4 + 尾帧 png、装配命令序列。

## 2. 四个确认点（关卡）

| # | 关卡 | 确认内容 | 之后 |
|---|---|---|---|
| 1 | 方向/故事 | 故事骨架、主角设定、时长/画幅/风格/对白设置 | 进入角色卡/场景卡 |
| 2 | 角色/场景资产锁定 | 角色卡、场景卡；**一旦锁定人物即定** | 进入分镜；改卡 = 下游全部重生成（先警告） |
| 3 | 分镜/提示词 | 每镜几秒、每镜干什么、对白位置、钩子排布 | 进入逐镜生成 |
| 4 | 成片签字 | 成片视频 + QC 报告（逐镜通过/不通过 + 证据帧） | 交付；指出问题只重做该镜，**不混新旧资产** |

## 3. 用户输入字段

**必给 4 项**（缺则按默认 9:16 / 45s / 有对白 / 中文 补齐，并在关卡 1 复核）：故事点子、人物长相、时长 + 画幅、视觉风格。可选：对白模式/语言、参考素材、集数。

**项目级字段**（对应 `data.Project`；`_load_project` 只收这 8 个字段，其余忽略）：

| 字段 | 含义 | 默认 |
|---|---|---|
| title / what_if | 标题 / 一句话故事 | 必填 |
| target_feeling | 目标感受 | "" |
| aspect | 画幅（9:16 等 13 种） | 9:16 |
| duration_s | 单集总时长 | 45 |
| dialogue_mode | 有对白/无对白 | 有对白 |
| dialogue_language | 对白语言 | 未指定 |
| visual_style | 视觉风格 | "" |
| characters[] / scenes[] / shots[] | 角色卡 / 场景卡 / 分镜行 | [] |

**镜头级字段**（对应 `data.Shot`，`Shot.from_dict` 忽略未知键）：
- 结构：`shot_id`、`duration_s`(≤15s)、`continuity_handoff`(跨镜连续脊柱)、`fixed_landmarks[]`、`char_positions{}`、`exited_chars[]`、`lighting_baseline`、`hook_type`
- 逐秒：`per_second[]` 每条 `{rng, action, camera, spatial, audio, handoff}` 五要素
- 音频：`narration`、`dialogue[] {text, speaker_id, tone, time_range, is_diegetic}`、`sfx[]`
- 生成参数：`mode`(T2VA/I2VA/FL2VA/L2VA/Ref2VA)、`video_model`(H3/Seedance2)、`resolution_tier`、`aspect`、`references[] {label, kind, char, retention, path...}`、`first_frame`、`last_frame`、`negative`、`continuity_type`、`airlock_s`、`seed`(0=自动)、`edit_target_s`

## 4. 项目加载：pipeline._load_project 与 data.Project/Shot

`_load_project(path)` 做四件事：
1. `json.load` 读项目 JSON（UTF-8）；
2. 由 `characters`/`scenes` 构造 `CharacterCard`/`SceneCard` 列表；
3. 逐行 `Shot.from_dict` 构造 `Shot`——只保留 dataclass 字段，未知键忽略，`per_second`/`dialogue`/`references` 逐元素重建；
4. `Project` 只接受 8 个项目级字段（第 3 节），多余键被过滤。

配套检查：`check` 子命令跑 `shot_table.self_check` 六条规则（钩子密度、单镜≤15s、单镜≤3 角色、空间继承、逐秒无空洞、跨镜连续成链）；`advance` 输出剧情推进脊报告（建立→推进→交接→钩子 + 断链检测）。

## 5. 提示词编译：prompt.compile / compile_all

`compile_all(project)` 先 `assign_speaker_ids`（按全项目说话顺序给说话人编号 S1, S2…，同一说话人编号不变），再逐镜 `compile`。
`compile` 按 mode 分派：**基础模式（T2VA/I2VA/FL2VA/L2VA）→ 三段 H3 prompt**；Ref2VA → 六段（subject_definitions / summary / retention_analysis / detailed_description / overall_soundscape / non_diegetic_music，retention 词汇逐字输出）。

基础模式三段：
1. **integrated_multimodal_description**：I2VA/FL2VA/L2VA 先写官方对齐首行（Picture 1 对齐目标视频 0.00s / 末秒标记），随后 `Style:` + `[Shot 1] shot_description` + `Per-second directives:` + 锚点块（landmarks/char_positions/exited/lighting/handoff）+ `Dialogue:`；
2. **overall_soundscape**：sfx 连接 + hook 类型（无对白项目 → silent）；
3. **non_diegetic_music**：固定 "diegetic ambient only; no score unless the shot calls for it"。

四个关键映射：
- **per_second**：逐条输出 `  0-3s: action; camera: …; spatial: …; audio: …; handoff: …`（只含非空要素）；
- **dialogue**：画内对白 → `<Picture 1> (S1) says, <d>[Chinese] 台词</d>`；旁白 → `narration (<Picture 1>, voice over, mouth closed): 台词`；
- **speaker**：角色名 → S# 的全局映射（首次出现顺序），编号不泄漏进 retention 分析；
- **reference**：说话人标签按 `char` 绑定 → description 子串 → 第一个 person/animal 参考 → 兜底 `<Subject>` 解析；锁定后 `<Picture 1>` 固定是 lead 角色。

## 6. 角色锁定：character_lock（seed / reference / lock / validate）

锁定针对「抽卡式随机人物」的三个杠杆：纯文生视频无参考、每镜随机 seed、参考图未钉住。

- `seed_for(name, base_seed=1234567890)`：角色名确定性哈希 → 每角色一个固定 seed（「定卡」），跨镜头永不重抽；
- `character_reference(name, path)`：生成 `<Picture 1>` 参考，`retention="fully_preserved"`，note 写明「全程保留脸/发/服装/屏幕位置」；
- `lock_shot(shot, {角色名: 卡路径})`：取 lead 角色 → T2VA 升级为 I2VA → 把 lead 角色卡钉为 `first_frame` → 每个在场角色加 fully_preserved 参考 → 重新编号使 `<Picture 1>` 为 lead；
- `validate_locked`：角色镜仍为 T2VA、I2VA/FL2VA/L2VA 无 first_frame、Ref2VA 无参考、同一 lead 角色 seed 漂移，均报错；
- `characters_from(project)`：从带 image_path 的角色卡取 `{name: image_path}`。

`lock` 子命令：逐镜 lock_shot → validate → 可选 `--out` 回写锁定后的项目 JSON。

## 7. ComfyUI 生成：comfyui_gen（build / queue / poll / download / upload / generate / extract）

四个固定模型文件（源码常量）：

| 节点 | 文件 / 参数 |
|---|---|
| UNETLoader | `minimax_h3_fl2va_pruned_fp8_scaled.safetensors`，weight_dtype=default |
| CLIPLoader | `qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors`，**type=minimax** |
| VAELoader（视频） | `minimax_h3_video_vae_fp16.safetensors` |
| VAELoader（音频） | `minimax_h3_audio_vae_fp32.safetensors` |

节点接线（API 工作流节点号）：
- `6` **MiniMaxH3ImageToVideo**：clip/vae/prompt/width/height/length，可选 + first_frame/last_frame；
- `10` **CLIPTextEncode**：**空负面**（text=""）；
- `7` **KSampler**：positive=6、negative=10、latent_image=6(1)，**cfg=1.0、euler、simple、denoise=1.0**，seed/steps；
- `8` **VAEDecode**（视频 VAE 解码）与 `13` **VAEDecodeAudio**（音频 VAE 解码），均取 7 的 samples —— 双 VAEDecode；
- `11` **CreateVideo**：fps=24.0，视频(8) + 音频(13)；
- `9` **SaveVideo**：filename_prefix、mp4、pix_fmt=auto、codec=auto；
- I2V 额外加 `20/21` **LoadImage**（首/末帧为已上传到 ComfyUI 的图名）。

七个函数一一对应：
- `build_t2v` / `build_i2v` → API 格式工作流 dict；
- `queue` → `POST /prompt` 返回 prompt_id（服务端拒绝即抛错）；
- `poll` → `GET /history/{id}` 每 5s 轮询至 1800s，success/error/fatal 终止，汇总 images/videos/gifs 输出；
- `download` → `GET /view?filename&subfolder&type=output` 取回 mp4；
- `upload_image` → multipart `POST /upload/image`，返回 ComfyUI 图名（带 subfolder 前缀则 `sub/name`）；
- `generate` → build → queue → poll → 挑 .mp4 → download，返回本地路径；
- `extract_last_frame` → `ffmpeg -sseof -0.1 -frames:v 1` 抓尾帧 png（尾帧链用）。

## 8. 系列生成：series 尾帧循环与 17k+5 帧

`series.run_from_json` / `generate_series` 逐镜循环：
1. `prompt.compile` 出 H3 prompt；
2. seed：显式 `shot.seed`（定卡）优先，否则 `(base_seed + i*7919) % 2**31`；
3. first_frame 优先级：**lead 角色卡 > 上一镜尾帧 > None（T2V）**；本地路径先 `upload_image`；卡文件不在盘上则该镜降级 T2V；
4. `length = _frame_count(duration_s)`：24fps 取整后对齐 **17k+5 帧网格**（`n=max(5, round(sec*24)); n += (5-(n%17))%17; min(n,360)`），5s → 124 帧；
5. `cg.generate` 出单镜 mp4；失败则记录 error、**断链（prev_frame=None）继续下一镜**，不中断整集；
6. 成功且非末镜 → `extract_last_frame` 出尾帧 png，**下一镜 first_frame = 本镜尾帧（尾帧链）**；
7. 全部完成后 `assemble_plan`（canvas 480x832）把成功片段拼成 `episode.mp4`。

## 9. 装配：assemble（ffprobe / normalize / xfade / 32kHz）

三条硬规则：**H3 音频是 32kHz（绝不硬编 48k）；match_tail 把音频裁/垫到与视频完全等长（消除每接缝 ±8.3ms 累积）；xfade 0.4s 转场、BGM 在对白下 duck**。
- `probe`：`ffprobe -show_streams -show_format -of json` → width/height/fps/sample_rate/duration；
- `normalize_cmd`：scale+pad 到统一画布（默认 832x1472，均为 32 的倍数）+ colorbalance/eq 暖色统一 + fps=24 + libx264 yuv420p crf18；
- `match_tail_audio`：`atrim` 到视频时长，`-ar 32000 -ac 2 aac 192k`；
- `build_xfade`：`xfade`（fade/dissolve/wipeleft/circleopen/slideright/fadefast 循环）+ `acrossfade`，输出固定 24fps / 32kHz；
- `assemble_plan`：逐镜 normalize `_norm_XX` → 链式 xfade `_join_XX`（offset = 累计时长 − 已用 0.4s，由 probe 实测）→ BGM（vol 0.10，amix）→ 可选烧字幕 → 改名到 out；
- `run`：按序执行（cp 用 shutil.copyfile 跨平台复制，不走 shell）。

## 10. 总体流程（ASCII）

```
 用户给 故事/人物/时长/风格
        |
 [关卡1 方向确认]
        |
 LLM: concept(15字段) -> storyboard(六列标准分镜表 JSON)
        |
 shot_table.self_check 六条 ---- FAIL -> 修表重查
        |
 character_lock: seed/卡/reference/validate -> [关卡2 资产锁定]
        |
 prompt.compile_all: 三段prompt(逐秒/对白/S#/<Picture #>) -> [关卡3 分镜确认]
        |
 series 逐镜循环:
   first_frame = lead卡 | 上镜尾帧 | 无(T2V)
   -> comfyui_gen: build -> queue(/prompt) -> poll(/history) -> download(/view)
   -> ffmpeg 抽尾帧
        |
 assemble: ffprobe -> normalize -> xfade 0.4s -> BGM duck -> 32kHz -> episode.mp4
        |
 [关卡4 成片签字] ---- 有问题 -> 只重做该镜(最新资产, 不混新旧)
        |
      交付
```

## 11. 最小 JSON 示例（check/prompts/lock/series 可直接吃）

```json
{
  "title": "午夜来电 · 第一集",
  "what_if": "一个深夜女主播，突然收到她三年前失踪姐姐的直播私信。",
  "target_feeling": "悬疑 + 反转钩子",
  "aspect": "9:16",
  "duration_s": 30,
  "dialogue_mode": "有对白",
  "dialogue_language": "中文",
  "visual_style": "dark moody, warm desk lamp vs cold screen glow, shallow depth",
  "characters": [
    {"name": "小满", "identity_note": "24岁, 圆脸, 黑色低发髻, 米色卫衣; do-not-change: 脸/发髻/卫衣",
     "image_path": "assets/xaoman.png", "do_not_change": ["face", "bun", "hoodie"]}
  ],
  "scenes": [
    {"name": "直播房间", "description": "小卧室直播间, 一盏暖台灯, 笔记本直播位, 黑窗",
     "landmarks": ["desk-lamp: left third", "laptop-screen: center", "city-window: top"],
     "light_baseline": "key: warm lamp left, fill: cold screen"}
  ],
  "shots": [
    {"shot_id": "S01", "duration_s": 5,
     "continuity_handoff": "小满直播中; 手机桌上亮屏震动 -> 下一镜接起",
     "fixed_landmarks": ["desk-lamp: left third", "laptop-screen: center"],
     "char_positions": {"小满": "center, midground, facing camera"},
     "exited_chars": [],
     "lighting_baseline": "key: warm lamp left, fill: cold screen",
     "hook_type": "suspense",
     "shot_description": "小满对镜头聊天, 手机在桌上亮起并震动。",
     "per_second": [
       {"rng": "0-3s", "action": "对镜头聊天, 微笑比划", "camera": "static, medium",
        "spatial": "小满居中, 台灯左", "audio": "她的声音 + 房间底噪", "handoff": "聊天基线"},
       {"rng": "3-5s", "action": "手机震动, 小满目光定住", "camera": "push to face",
        "spatial": "手机下三分位", "audio": "震动声切房间音", "handoff": "盯住手机"}
     ],
     "dialogue": [
       {"text": "家人们, 礼物都收下啦, 谢谢!", "speaker_id": "小满", "tone": "欢快",
        "time_range": "0-3s", "is_diegetic": true}
     ],
     "sfx": ["phone-buzz", "room-tone"],
     "mode": "I2VA", "video_model": "H3", "resolution_tier": "768P",
     "first_frame": "assets/xaoman.png"}
  ]
}
```

跑法：`python -m h3_short_drama check --shots P.json` → `prompts --shots P.json` → `lock --shots P.json` → `series --shots P.json --out-dir series_out`。

## 12. 诚实限制（今天代码做不到 / 做不稳的）

1. **照片需本地路径并上传**：`upload_image`/`series` 只认本地文件（或 ComfyUI 图名）；角色卡 `image_path` 必须是运行机上的有效路径，生成前经 multipart 上传到 ComfyUI。云图 URL 不支持；卡文件不在盘上时该镜**静默降级 T2V**（日志可见 `first_frame=False`）。
2. **T2V 会漂移**：无参考的纯文生视频，脸/发/服装不保证稳定；锁定机制（卡参考 + 定 seed + fully_preserved）只显著降低漂移，不消除；镜头越长、动作越复杂越容易漂。
3. **尾帧链只解决接缝**：上一镜尾帧 → 下一镜首帧，只保证相邻两镜衔接点不跳（且仅限同主体连续镜）；不保证整集身份一致，不防场景/光线漂移；某镜失败即断链重开（后续变 T2V），漂移会累积。有角色出场的镜头实际是硬切到该角色卡，尾帧链只服务同主体续拍。
4. **Ref2VA 当前未在本地闭环**：六段 Ref2VA prompt（subject_definitions/retention_analysis）能编译，但 `comfyui_gen` 的 ComfyUI 工作流只接了 `first_frame/last_frame`（LoadImage），未把 Ref2VA 的主体参考图/视频/音频接进图里；Ref2VA 目前只在 API 侧可用（MiniMax Context-IR、火山三帧，见 api.py），本地 ComfyUI 上不成环。
