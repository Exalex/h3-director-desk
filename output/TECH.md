# H3 短剧生成 · 技术细节 (TECH)

> 硬事实速查。来源：MiniMax-H3-ComfyUI docs + 官方 skills + 各社区库源码。

## 1. 模型

- **MiniMax H3 / 海螺3.0 / Hailuo 3.0**，33B H3-Omni-Transformer（dense 单流）
- 三模块：**H3-Context-IR**（仅API，自由多模态→Context IR）/ **H3-Base**（开源，768p，FL2VA+Ref2VA）/ **H3-Regenerate-2K**（仅API，768p→2K in-context）
- 组件：H3-Encoder(Qwen3-VL-32B, layer50, 加`<d>`token) / H3-VisualVAE(f16t4d24, 16×空间,4×时序,24通道,ViT解码, 32×空间下采样) / H3-AudioVAE(立体声,32kHz→40Hz) / MM-RoPE(t,h,w) / AdaLN
- 许可：MiniMax H3 Community License（据报道不覆盖 EU/UK/韩/美——商用前自查）

## 2. 输出规格

| 项 | 值 |
|---|---|
| 时长 | 4-15s（训练包络 96-360 帧） |
| 画幅 | 21:9, 16:9, 4:3, 1:1, 3:4, 9:16（+ 2:1,3:2,5:4,4:5,2:3,1:2,9:21） |
| 分辨率 | 768px 短边（面积上限 768×1344）；2K 需 Regenerate-2K |
| 帧率 | 24 FPS |
| 音频 | 32kHz 立体声（**非 48k**） |
| 语言 | 11（中/英/日/韩/阿/法/德/意/葡/俄/西） |

## 3. 帧网格数学（关键）

- 输出帧数：**17k+5** @24fps → 5s = 124 帧；吸附公式 `n=max(5,round(dur*24)); n += (5-(n%17))%17`
- 视频 latent 时间压缩：`FRAME_PER_TOKEN=(1,4,4,4,4)` → 17k+5 px → **5k+2 latent**；`FRAME_RESCALE=5/3`
- 音频：40Hz 网格，1 帧 = 5/3 audio step；H3 对音频网格四舍五入 → 每 clip ±8.3ms（`match_tail` 消除）
- 时间压缩比 ~3.35×（124 输出帧 = 37 latent 帧）
- 可精确切分上下文窗口：`{5,22,39,56}` 帧 = `{2,7,12,17}` latent steps（必须整 latent step，`start%5==0` 相位断言）
- 画布 32 像素对齐（VAE 16px + DiT 2px patch 都须对齐）

## 4. 两套 UNET（不互通，别混）

| 工具栏 | Checkpoint | 用途 |
|---|---|---|
| Refs OFF | `minimax_h3_fl2va_*` | t2v / i2v / fl2v（首尾关键帧） |
| Refs ON | `minimax_h3_ref2va_*` | r2v / v2v / rv2v（多参考） |

参考上限（官方 model card）：参考图 ≤9；参考视频 ≤3（每 2-15s，**总 ≤15s**）；参考音频 ≤3；**全类合计 ≤12 文件**。

## 5. 提示词 schema（权威）

### 5.1 Base 模式（T2VA/I2VA/FL2VA/L2VA）— 三段
```
integrated_multimodal_description:   # 逐镜描述/运镜/角色外观服装动作/环境光线/时间标记
  [Shot 1] ...
  [Shot 2] At 00:04.500, the camera cuts to ...
overall_soundscape:                   # 现场音/物理音/音频动态(渐强/骤静)
non_diegetic_music:                   # 配器/节奏情绪/动态 (空写 N/A)
```
5 模式锚点规则：
- **T2VA**：从开场态建完整音画时间线
- **I2VA**：`<Picture 1>` 锚在 0.00，保留其身份+构图，向前发展（它是真实首帧，非灵感）
- **FL2VA**：描述两态间**连续物理路径**（单镜更可靠；别重复两张静态图描述）
- **L2VA**：推断早先态，收敛到给定尾帧（尾帧属最后镜非 Shot1）
- **Ref2VA**：先定义参考角色+retention，再写镜时间线

### 5.2 Ref2VA — 六段（顺序固定）
```
subject_definitions:
<Subject 1> is [ref图描述].
<Video 1> is the source video for the editing task.
<Audio 1> is [音频描述].
summary: [任务类型] 目标视频 [发生什么]
retention_analysis:
<Subject 1>: fully_preserved - [保留什么]
detailed_description:  [完整场景描述, 对白用 <d> 标签]
overall_soundscape: [音频]
non_diegetic_music: [音乐]
```

### 5.3 标签 + retention 词汇（逐字输出不重写）
- `<Subject N>`=可复用人/物/环境/风格/动作/姿态；`<Picture N>`=具体图/关键帧；`<Video N>`=源视频/续写源/时序；`<Audio N>`=拷贝/参考音频。同资产可多角色但独立编号。
- 视觉 retention：`fully_preserved` / `partially_preserved` / `attribute_transfer` / `weak_reference`
- 音频 retention：`fully_copy` / `partially_copy` / `reference` / `weak_reference`

### 5.4 对白（一等目标）
- 官方格式：`<d>[中文] 台词</d>`；`<scenetrans>`/`<cutoff>`（跨cut/截断）
- Director 编译规则：**`@ref1 says: 台词` → `<Subject 1> (S1) says, <d>[Lang] 台词</d>`**；**冒号是对白标志，引号不是**（`@ref1 says "hi"` = 旁白，`@ref1 says: hi` = 对白）
- **speaker ID (Sx)**：按全时间线实际说话顺序分配，同一说话人保持同一 ID，且**不出现在 retention_analysis**
- 首现全描述 + 后现短名（`called` 字段）；台词留在写的位置（不甩到镜尾）
- 8 项提交前清单：模式+参考锚对 / 每主体一稳定身份 / 首尾帧规则匹配模式 / 每 cut 加信息或用动机化运镜 / 对白精确有序绑稳定 speaker / 现场音·环境音·非现场音乐分离 / retention+音频角色显式 / 时长·FPS·分辨率·硬件兼容

### 5.5 Tips（官方）
具体(光线/服装) / 时间标记("At 3.2s") / 描述音效 / 运镜("slowly pushing in") / 服装细节 / 情绪("jaw clenches") / 镜号 / 转场。提示词正文英文，对白/歌词/场景文字保留原语言。

## 6. 关键 ComfyUI 节点参数

| 节点 | 关键参数 |
|---|---|
| H3ModelLoader | variant fl2va\|ref2va；precision bf16/fp16/fp32；offload none/model/full；use_int8_vae |
| H3TextToVideo | prompt；duration 4-15；aspect；**guidance 1-20**；**steps 10-200**；seed |
| H3ImageToVideo | + first_frame/last_frame；aspect 含 auto |
| H3ReferenceToVideo | + ref_images≤9 / ref_videos≤3 / ref_audio≤3 |
| H3VAEDecode | video_latent + audio_latent；decode_audio；output_fps=24；audio_sample_rate=32000 |
| H3ContextIR | prompt/duration/aspect/api_token/region → enhanced_prompt |
| H3Regenerate2K | video_frames+original_prompt+duration+aspect → upscaled |

**采样器**：`res_multistep` + `simple` + ~20 steps + `BasicGuider`（无 CFG）；ref2va 重参考时 `beta`/`normal` 常胜 `simple`；`shift_video=12.0` / `shift_audio=3.0`。
**VAE 精度**：flat grey（每像素同值）= 视频 VAE NaN → 启动 `--fp32-vae`（fp16 VAE 可能黑/灰）。

**Flow-matching sigma 公式（denoise 不搬 SDXL 的数学依据）**：
```
sigma = shift * t / (1 + (shift - 1) * t)
```
H3 是大 shift 的 flow matching。shift=12 时，普通 FaceDetailer 的 denoise 0.25 → 有效 sigma **0.800**（几乎重写整帧）；0.05→0.387，0.02→0.197。`steps` 与 `denoise` 独立：BasicScheduler 建 `steps/denoise` 长全范围 schedule、保留最低 `steps+1` 个 sigma，故 4 步 + turbo 又快又轻；**别用 SplitSigmas**（4 步 schedule 在 shift12 下末 split 点已是 sigma 0.800）。局部重绘推 denoise 太高 → 头相对身体漂移（内容问题，mask 遮不住）。

## 7. 加速

| 手段 | 说明 | 代价 |
|---|---|---|
| **Turbo LoRA** | 4-step（6-8 更好，>8 过锐）；strength 1.0（糊→1.05-1.2，过锐→0.8-0.95） | 伤音频细节/软画面 |
| **Spectrum** | Chebyshev ridge 预测 post-transformer 特征跳步；自适应调度；采样器保护 | 同上 + 误预测 pinned 行（链式禁用） |
| **Block Cache** | Fast 档用 | 某些设置可模糊/损伤 motion/detail |
| **双调度 sampler** | 自动检测 ModelSamplingAV；旧 ComfyUI 按 video shift12/audio shift3 | — |

> 规则：加速只用于**非对白、非链式**镜头。对白/链式镜头关 Turbo+Spectrum。

## 8. 本地硬件 profile（h3lite）

| profile | 画布 | 帧 | 步数 | Cache | 适用 |
|---|---|---|---|---|---|
| Fast | 640×352 | 124 | 4 | Block Cache | 8GB 基线/成功率 |
| Balanced | 640×352 | 124 | 6 | 关 | 8GB |
| Quality | 640×352 | 124 | 8 | 关 | 8GB |
| (中/高显存) | 864×480 (0.4MP 16:9) | — | 6-8 | 关 | 16GB |

- 显存：~8GB→Set A(W4A8 INT4)；16GB→Set B(FP8)。瓶颈=offload/CPU带宽/首编译（4060Ti16G NORMAL 77s vs 4070Laptop8G LOWV 591s）
- 模型文件：fl2va/ref2va pruned_fp8_scaled(21GB) + qwen3vl_32b 文本编码器(15GB) + video_vae_fp16(4.9GB) + audio_vae_fp32(0.6GB)；bf16 66GB 最高质；int8_convrot 34GB
- 诊断顺序：页面文件/RAM → 缺模型/节点 → 错文件夹 → CUDA/PyTorch → OOM/offload → flow/audio 图 → 提示词/参考对齐

## 9. API（云端）

```
Global: https://api.minimax.io   CN: https://api.minimaxi.com
Header: Authorization: Bearer <key>

POST /video-generation-v2-h3-context-ir   # 自由文本 → 增强结构化 prompt
POST /video-generation-v2-regeneration    # 768p + 原 context → 2K
POST /video-generation-v2-create          # 全系统一步生成
```
Jellyfish 双 provider 契约（可抄）：
- OpenAI：`POST /videos` → 轮询 `/videos/{id}`；单参考图 `input_reference`（key>first>last）
- 火山方舟：`POST contents/generations/tasks`；首/尾/关键**三帧同传**（role 化 content）；终态 succeeded/failed/cancelled

## 10. 分辨率预设（/32 对齐）

| 比例 | Native(768短边) | Fast(480短边) |
|---|---|---|
| 16:9 | 1344×768 | 864×480 |
| 9:16 | 768×1344 | 480×864 |
| 1:1 | 992×992 | 640×640 |
| 4:3 | 1024×768 | 640×480 |
| 3:4 | 768×1024 | 480×640 |
| 21:9 | 1344×576 | 1120×480 |

## 11. 状态模型（Jellyfish 三轴，可抄）

1. `shot.status`：仅 `pending`/`ready`，只由后端重算（是否完成提取确认）
2. `video-readiness`：独立维度（是否可生成视频；ready ≠ 可生成）
3. 运行时任务状态：GenerationTask 动态聚合（**不写进 shot.status**）
经验：永远别把"正在生成"写进业务实体状态字段。

## 12. ffmpeg 装配参考（ai-video-pipeline 实测）

- normalize：scale+pad 统一分辨率 + `colorbalance=rs=0.08:gs=0.04:bs=-0.06`（暖色统一）+ `eq=brightness=0.02:contrast=1.05:saturation=1.05` + 30fps
- xfade 转场：`transitions=[fade,dissolve,wipeleft,circleopen,...]` 循环，每段 0.4s
- 配音：`-i voiceover -map 0:v -map 1:a -shortest`
- BGM：`aloop=loop=-1` → `volume=0.10` → `amix`（voice 1.4）
- 硬字幕：`subtitles=sub.srt:force_style='Fontsize=18,FontName=PingFang SC'`
- 负面提示词（视频通用）：`morphing, flickering, distorted face, extra fingers, blurry, low quality, watermark, text overlay`
- Ken Burns（静图动感）：`zoompan=z='min(zoom+0.0008,1.3)'` / pan / zoom out
