# H3 短剧生成 · 打法 (PLAYBOOK)

> 目标：一人 / 一人+agent 用 **MiniMax H3（海螺3.0）** 稳定产出带对白的竖屏短剧。
> 本打法融合 20 个库的源码级结论 + 官方 3D 短剧 skill，是**可执行 SOP**。
> 适用：对白驱动的真人/漫剧/3D 短剧；单集 ≈ 30-90s（多个 5-15s 镜头串联）。
> 不适用：单张图 / 单条 clip / logo / 纯咨询。

---

## 0. 决策速查（先回答 4 个问题）

| 问题 | 选择 |
|---|---|
| 画幅 | 竖屏 **9:16**（短剧默认）；电影感 16:9 |
| 单集时长 | 30-60s（默认，推荐）/ 15-30 / 60-90 / 90-180 |
| 对白 | 有对白（H3 强项，首选）/ 旁白 / 无对白 |
| 对白语言 | 只有用户明确指定才用该语言；否则标注"未指定" |

> 核心铁律：**H3 一句 prompt 直接出画面+对白+口型+音效**（无需先 TTS 再对口型）。对白镜头首选 H3；多镜锁脸叙事可混 LTX+角色LoRA。

---

## 1. 部署决策（选一条路，别混）

| 场景 | 路线 | 说明 |
|---|---|---|
| **本地 Windows+NVIDIA** | ComfyUI + H3 节点 | 首选已验证路线 |
| **本地 Mac/Apple Silicon** | Phosphene(MLX) | 双引擎 LTX-2.5 + H3；可训角色 LoRA |
| **显存 <6GB** | 放弃本地 | 走云端 API（OpenAI/火山）或降模型 |

本地 3 档 profile（h3lite）：
- **Fast**：W4A8/4B/Turbo，**640×352**，124 帧(≈5s)，**4 步**，Block Cache（成功率基线）
- **Balanced**：同画布，6 步，关 Block Cache
- **Quality**：同画布，8 步，关 Block Cache
- 画布 32 像素对齐（VAE 16px + DiT 2px patch）；0.4MP 16:9 → 864×480；短屏 9:16 → 480×864(Fast) / 768×1344(Native)
- **中文提示词 ≥30-50 字**（超短名词式会被 seed 主导）；先便宜画布预览验证
- **音频策略**："无对白"≠静音（保留环境音）；仅"完全静音"才移除音频流

> 显存 <16GB 别把低显存 W4A8 640×352 当"最终人脸质量"；要可识别/说话人脸 → I2VA 清晰首帧，跨镜身份用 Ref2VA。

---

## 2. 写什么（爆款方法论，来自 SDCC + ai-script-hub）

**调性检验**（判对没判错，直接可执行）：
- ✅ "天哪她好厉害，我也想这样" → 对
- ❌ "唉她好惨，但还好她挺过来了" → 错，换掉

**喜剧公式**：奇幻触发器 × 极端身份错位 × 家庭/情感关系 × 喜剧 × 治愈（≥3/5 要素）。

**五黄金法则**（system prompt 级）：
1. 竖屏思维：半身/特写为主，避免大场景全景
2. 节奏：每 15-20s 一个情绪点，每集 ≥3 高潮
3. 对白：简洁，一句 ≤20 字
4. 爽点密集：打脸/反转/告白/揭秘交替
5. 结尾钩子：最后一句/画面必是悬念

**女主三关**：配得感（本来就值得）/ 快意恩仇（当场怼回）/ 主体性（她做选择）。

**输出 15 字段概念**：奇幻触发器 / 她是谁 / 她做什么 / 极端身份错位 / 高概念 / 一句话梗概 / 喜剧引擎 / 家庭情感线 / 女主三关(✓✗) / CP磕点 / 每集结构(开场钩子→中段冲突→结尾悬念) / 开场钩子 / 风险提示。

---

## 3. SOP 十步（一集短剧）

> 每步末尾 = **门（gate）**：通过才进下一步。对应官方 3D skill 的 choice-card 纪律。

### STEP 0 输入 & 画幅/时长
收集：一句话点子、期望产出、时长、画幅、视觉调性、对白需求。锁定画幅+时长（后面全程复用）。

### STEP 1 项目简报
工作标题 / What-if / 情感前提 / 目标受众感受 / 计划交付物 / 画幅 / 时长 / 对白模式+语言 / 初始风险。门：方向确认。

### STEP 2 故事大纲
主角 Want/Need/flaw / 核心世界规则 / **8-beat 因果故事脊** / 情感锚点与 payoff / 对白节拍。
门（红线检查）：主角是主动的 / 危机被主角缺陷放大 / 巧合绝不解决问题 / 结尾复用早前情感锚点 / 反派压力非扁平脸谱 / 对白揭示关系变化而非说教主题。

### STEP 3 角色卡（一致性锚点①）
每个主要角色一张 16:9 参考卡（含可读标签供下游绑定）：
- 角色名标签（中/英）、角色定位（主角/对手/配角）
- 3/4 主视角 + 正/侧/背视角 + 表情
- 材质/服装/道具细节 + 重要道具标签
- **视觉-ID 注**：年龄带、体型、发型、服装色、标志道具、**do-not-change 特征**
门：锁定角色（改锁定的角色=要重生成下游全部，警告用户）。

### STEP 4 场景卡（一致性锚点②）
场景卡**只画环境**（不含人物/剪影/手/脸）。含：环境总览、关键光态(昼夜)、情绪子空间、**连续性地标**（同一场景跨镜必须保持屏幕位置的固定物：门框/中岛/沙发/树/邮箱）、环境内重要道具。门：锁定场景。

### STEP 5 标准分镜表（六列，核心）
见 §4。这是**强制步骤，不能跳过或替代**。

### STEP 5.5 分镜表自检门（六条，强制）
见 §5。任一不过 → 回 STEP 5 改，重跑。

### STEP 6 分镜脚本（默认文本版）
一本文本分镜文档，每镜一节（默认）。重度迭代的镜头可抽出独立节点。铅笔图分镜仅用户 opt-in 时作可视化（不覆盖文本版）。门：分镜确认 + 选分镜模式。

### STEP 7 视频模型 + 分辨率 + 逐镜生成
- **模型卡**：H3(默认) / Seedance 2.0(高性能表演回退) / 逐镜混用(分镜表逐行标 video_model)。
- **分辨率卡**：H3 首过 768P / 质量 2K(需 Regenerate-2K API)；Seedance 1080p/720p。
- 逐镜渲染：用对应文本分镜节 + 精确角色卡 + 精确场景卡；**剥离所有分镜双绑定标签**（`[char:…] [scene:…] [shot:…] [dur:…] [hook:…]`）；H3 前缀强调 packaging/设计语言/motion clarity/双声道音意图，per-second 指令可近乎原样送入。
- 门：逐镜 clip 通过（含 §7 一致性检查）。

### STEP 8 长片拼接 + BGM + 最终输出
见 §6（若单集 >15s）+ §8（BGM/装配）。

### STEP 9 终审
见 §9 QC 清单。

---

## 4. 分镜表 · 六列 schema（官方 3D skill 标准）

表名 `标准镜头信息表` / `standard-shot-table`，**严格 6 列此顺序**：

| 列 | 内容 |
|---|---|
| **1. Shot ID & Duration** | 镜号+时长，如 `S03 / 6s`（≤15s/镜，超了拆） |
| **2. Continuity Handoff** | 本镜如何从上镜结尾图/道具位/视线/姿态/声音桥/情绪自然延续，**且**如何为下镜开场布景（跨镜连续性脊柱） |
| **3. Reference Anchors（空间+身份）** | 4 子字段全必填：`Fixed Landmarks`（场景卡具名地标+屏幕相对位置，如 door-frame: right third）/ `Character Positions(camera view)`（每角色的屏幕位置+朝向+初始姿态）/ `Exited Character Status`（上镜在、本镜不在的角色，其画外位置+原因）/ `Lighting Baseline`（继承 key/fill/rim + 逐镜修饰）+ 身份绑定（精确角色卡名+场景卡名） |
| **4. Hook Type** | 受控词表：visual-joke / reversal / suspense / tender / chase / reveal / callback / expression-beat（用于钩子密度自检） |
| **5. Shot Description（逐秒指令）** | 景别/运镜/荷兰角/表演风格/SFX/负面 + **视频模型生成注**（H3 vs Seedance 提示词形态不同）+ **Per-Second Directives** 子节（0-1s/1-2s/… 子秒用 2.0-2.5s）；**每秒必须覆盖 5 要素**：①动作/姿态/表情 ②运镜 ③空间位置 ④音频 cue ⑤到下一秒/镜的 handoff |
| **6. Audio & Dialogue Track** | 该镜完整音频脚本(时序)：`Narration` / `Dialogue`(台词+说话人+语气+时间) / `SFX`(时序锚定) / `Performance Note`(旁白时 `narrator-mouth-closed: true`) |

**全表规则**：
- 每镜用 Continuity Handoff 继承上镜图像态、布景下镜。
- 逐秒指令要能直接生成分镜面板，避免"continues moving"这类无身体/机位/道具的模糊。
- 景别交替特写/大特写，避免重复构图；荷兰角用于追逐/失衡/意外/滑稽。
- 对白语言仅用户明确要才用；含对白的镜头，说话每秒记录嘴开/闭（画外旁白默认闭，画面对白默认开）。
- 离镜角色至少在 `Exited Character Status` 跟踪 1 镜，连续 2 镜画外后丢弃。

---

## 5. 分镜表自检 · 六条（强制门）

1. **钩子密度**：每镜有 Hook Type；每连续 3 镜至少 1 个 reveal/reversal/callback；首镜与尾镜各带强钩子。
2. **单镜时长**：无镜 >15s（超了拆）。
3. **单镜角色数**：无镜 >3 个重要角色（有画面动作或对白者）。
4. **空间锚继承**：同内景 ≥2 镜时，下镜 Fixed Landmarks + Lighting Baseline 须匹配上镜或含显式连续性注（如 door-frame from right third to center as camera orbits left）。
5. **逐秒覆盖**：0s 到镜时长每秒都有 Per-Second Directives，且每条含 5 要素，子秒不留时间空洞。
6. **跨镜连续**：逐行读 Continuity Handoff 成连续链，无镜起始态与上镜结尾矛盾；任何翻转视线/角色位置/道具态/光线须显式标注（如 `HARD CUT — time skip: 2h`）。

全过 → 打 `shot-table self-check: passed` 戳，进分镜脚本。任一失败 → 回 STEP 5，列出失败行。

---

## 6. 长片拼接 SOP（单集 >15s，Motion-Context 内幕）

H3 单镜 4-15s，长片 = 多个 in-range 窗口拼接。两条路线：

**路线 A：首尾帧法（简单，适合分镜切换）**
- 每镜 `Save Last Frame` → 下一镜 `first_frame`（fl2v 硬件锁首尾）。
- 每镜 prompt 前后缀**硬锁**（AIMixer FLF_PROMPT_PREFIX）："完全保持首尾帧。视频第一帧必须与给定首帧画面一致，最后一帧必须与给定尾帧画面一致；首尾帧是硬锁定关键帧，不是软参考，禁止改动首尾画面、主体外观与机位。"

**路线 B：latent 钉接（运动级无缝，适合同机位长镜头）**
- 上段 **sampler 输出 AV latent 尾 22 帧**（音频 24 帧）直接切片 → 钉成下段 0..N-1 never-denoised cond 行 → 采样 → Trim 裁前 22 帧 + match_tail。
- 参数：`context_length=22`（5/22/39/56，必 latent step 整数），`audio_context_length=24`。
- 上段 latent 必须跨 run 走磁盘（Save/Load Latent，`clip_00002.safetensors`，重拍覆盖自身 reject = retry-safe）。

**拼接 prompt 纪律（4 条，免费提升观感）**：
1. 模型把矛盾渲染成**并集** → 切镜指令写时间序而非并列。
2. **气闸(airlock)**：换调度时，下镜开头 ~2s 保持上镜结尾取景、无对白，再切。
3. 给 hold 一点事做（呼吸/重心/眼神），空 hold 会渲染成 freeze。
4. head 模式交付比采样短 22 帧(0.92s) → 时间码对采样版写。

**拼接硬约束**：
- **关 Turbo/Spectrum**（伤音频/软画面/误预测 pinned 行；对白镜头必关）。
- **32kHz 陷阱**：H3 输出 32kHz 非 48；拼接脚本必须读采样率，硬编 48000 会静默毁长片尾。
- 分辨率中途不能变（latent 不能 resize）。
- 接缝验收四件套：cross-correlation(延续/模仿/漂移+lag ms) + 电平/room-tone + 采样率 + freeze。
- 质量沿链衰减主要在音频（复印机效应）；重启链选自然音乐过渡处。

---

## 7. 一致性（不串戏）双路线

**轻量（零成本，~80% 一致）**：
- 角色卡（FLUX/图生图参考肖像）→ 角色镜头走 **I2VA**（非 T2VA）
- **尾帧链**：每镜从上镜末帧开始
- **cutaway 藏漂移**：键盘/空镜/屏幕特写插在主镜之间

**中量（官方 Ref2VA）**：
- 多参考图（≤9）+ **retention 词汇表**（`fully_preserved`/`partially_preserved`/`attribute_transfer`/`weak_reference`，逐字输出不重写）
- `<Subject N>` 绑定图与角色；首现全描述，后现短名（`@refN` 替换 + 去重）
- kind 说明句："the shape, colour and markings of <Picture 2> are retained"

**重量（Phosphene LoRA，漫剧/连载，真锁脸）**：
- 15-50 张图/角色（推荐 ~37）；本地 Gemma 打标（**"只写变化：姿态/构图/服装/场景/光线/机位/情绪，不写面部/发色/年龄/族裔，不写 trigger word"**）
- face LoRA：rank32/alpha32/5000 步/lr1e-4/576px（步数随 epochs×图数缩放）；flow matching
- voice LoRA：face 训完链式，4s 切片配图像 latent，rank16/250 步
- 产物 bundle.json（名字/代词/face 强度/voice 强度），跨集复用；prompt 必含 trigger word

**人脸精修（FaceRefine，治 H3 固有小脸问题）**：
- H3 小脸渲染差是**头在画面里的占比**问题，不是分辨率（720p+ 照样烂）；提分辨率没用，要逐帧重生成脸。
- 流程：Face Track+Crop（脸填满 canvas）→ H3 Inject Video Latent(img2img) → NativeAudioLock(喂分离人声锁口型) → Per-Frame Denoise(小脸强/大脸轻) → Stitch Back(只贴脸区+colour-match)。
- 诀窍：`crop_factor 2.5`/canvas 768/`smooth_window 21`+`size_smooth_window 51`/gaussian；**H3 denoise 值不能从 SDXL 搬**（flow matching 大 sigma shift，denoise 0.25 在 shift12 下=有效 sigma 0.8 重写整帧）；base denoise 与乘子一起调；**多人逐人串联**。详见 skill/references/face-refine.md。

**通用（Jellyfish 强约束，纯 prompt 最稳）**：
- **name-based 全局实体字典 + 精确字符串引用 + 全集校验**：先字典后引用；全角/半角/空格/标点原样；禁同义名/括号变体漂移；群体角色建同名条目；输出前"全集校验补齐缺失"。
- 候选确认中间态（pending→linked/ignored）：AI 猜测与业务真值用状态机隔离。

---

## 8. 装配 + BGM（STEP 8）

- 按分镜表顺序拼接；生成**一条连续 BGM** 匹配故事情绪/节奏/喜剧点/追逐律动/结尾调。
- BGM 在**对白/反应/重要 SFX 下 duck**；保留已有 clip 音频/SFX（除非用户要替换）。
- **不要逐镜生成 BGM**；不加字幕/文字除非用户明确要。
- 最终视频**无分镜痕迹**（无 panel 边框/铅笔线/箭头/标签/手写/时序标记/双绑定标签）。
- 混音参考（ai-video-pipeline 实测）：BGM volume 0.08-0.10，voice 1.4-1.5，amix；xfade 转场 0.4s 循环(fade/dissolve/wipe/circleopen)。

---

## 9. QC 终审（STEP 9）

- 角色一致性（对照 §7）
- 场景连续性（对照 Reference Anchors：每个地标是否落在表里说的位置）
- 情感锚点 payoff / 镜头目的清晰
- 对白可懂性（**逐帧+音频流+可懂性三级验证**；有音频流≠台词清晰）
- Foley/SFX 同步（对照 Audio & Dialogue Track）
- BGM 平衡
- **无分镜 artifacts**（panel 边框/铅笔线/箭头/标签/手写/时序标记/双绑定标签）
- 缺失/弱镜头；任何需重生成资产
- 接缝验收（长片）：cross-correlation + 电平 + 采样率(32kHz!) + freeze

---

## 10. 回退阶梯（STEP 7 失败/漂移）

**H3**：
1. 重试：引用精确 Reference Anchors 块强化 prompt
2. 重试：镜头缩到 ≤6s，被删秒拆成相邻新行，重跑 STEP 5.5
3. 重试：该镜切 Seedance 2.0（混用模式存在的原因——性能回退一键非重构）
4. 三次失败后停下问用户：只这镜切 Seedance / 放宽需求(删道具/简化动作/降钩子) / 跳过并标 placeholder / 手动供参考视频

**Seedance**（用户显式选或 H3 已 3 败）：
1. 强化 prompt 引用 Reference Anchors
2. 丢参考图改纯文本
3. 缩镜 ≤6s 拆行
4. 三次失败后问用户：切 H3 / 放宽 / 跳过 / 供参考视频

**漂移**：渲染 clip 偏离批准 Reference Anchors（door-frame 落错边/角色从错边出/光线翻转）→ 强化 prompt 引用精确 Reference Anchors 块重渲染；持续漂移 → 该镜切另一模型混用路径；**不静默把修正/未修正 clip 混进装配**。

**重生成纪律**：任何资产重生成后，下游必须用**最新批准版本**（角色卡改了→下游 shot table/分镜/clip/装配/合成全引用新版；shot table 改了→分镜/clip/装配用新版且重跑 5.5；不静默混新旧）。

---

## 11. 成本 & 提速

- 单集 30s ≈ 3 镜头 ≈ $2（主要成本=视频生成；图 FLUX 免费；TTS/Suno 各 1 次/部）
- 剧本层 <¥0.01（DeepSeek）；**一抽四/一抽八**批量抽卡提效率（H3 便宜时）
- 加速只用于**非对白、非链式**镜头（Turbo 4-8 步 / Spectrum 跳步）；对白/链式镜头关加速
- 本地路线（Phosphene）：推理/训练全本地零 API 费（代价 64GB Mac + 27.5GB 起权重）；H3 出对白镜头省掉"先 TTS 再对口型"两步

---

## 12. 快速命令（本地已配置环境）

```powershell
# 复跑路径（一条命令，别再逐个调 doctor/plan/preflight/generate/status）
python scripts/h3_fastpath.py --comfyui <ComfyUI路径> `
  --prompt-text "<改写后的H3提示词>" --resolution 640x352 --video-seconds 5 --json

# I2VA（首帧参考）
python scripts/h3_fastpath.py --comfyui <路径> --mode i2va `
  --first-frame <首帧.png> --prompt-text "<I2VA提示词>" --json
# FL2VA：--mode fl2va --first-frame <首> --last-frame <尾>
# L2VA：--mode l2va --last-frame <尾>
```
