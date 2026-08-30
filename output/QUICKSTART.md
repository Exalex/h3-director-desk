# H3 短剧 · 快速上手（一页跟做）

> 把 PLAYBOOK 浓缩成一页。一集 ≈ 30-60s（3-6 个 4-15s 镜头）。跟着做，每步末尾【门】通过才往下。
> 细节查 `skill/references/*`，可执行命令查 `scripts/README.md`。

## 0. 先锁 4 项（全程复用）
画幅 **9:16 竖屏** ｜ 单集时长（30/45/60s）｜ 有对白/无对白 ｜ 对白语言（默认中文）
部署：Win+NVIDIA→ComfyUI+H3 ；Mac→Phosphene(MLX) ；显存<6GB→云端 API。

## 1. 写什么（1 分钟定方向）【门:方向】
- 调性 ✅"她好厉害我也想这样" / ❌"她好惨"。
- 三选一幻想：能力/身份/行动。喜剧公式 ≥3/5：奇幻触发器×极端身份错位×家庭情感×喜剧×治愈。
- `python -m h3_short_drama concept --idea "..." --genre "都市逆袭"`（LLM 出 15 字段概念，dry-run 安全）。

## 2. 故事 + 角色卡 + 场景卡【门:锁定】
- **8-beat 因果脊**（不是并列）；红线：主角主动 / 巧合绝不解决 / 结尾复用情感锚点。
- 角色卡（16:9，多视角+表情+do-not-change 特征）；场景卡（纯环境+连续性地标）。
- 改锁定的卡 = 重生成下游全部，先警告。

## 3. 六列分镜表（核心，强制）【门:5.5 自检】
每镜 6 列：`镜号+时长` / `Continuity Handoff` / `Reference Anchors(地标+角色位置+离场+光线)` / `Hook Type` / `逐秒指令(每秒5要素)` / `Audio&Dialogue Track`。
规则：≤15s/镜、≤3 角色/镜、同场景连续镜继承地标+光线、逐秒无空洞、跨镜连续成链、每 3 镜≥1 强钩子、首尾强钩子。
`python -m h3_short_drama storyboard --idea "..." --out P.json`（LLM 出分镜表 JSON）
`python -m h3_short_drama check --shots P.json`（**跑 6 条自检，失败回第 3 步**）

## 4. 编译 H3 提示词
`python -m h3_short_drama prompts --shots P.json`
- Base 3 段：`integrated_multimodal_description` / `overall_soundscape` / `non_diegetic_music`。
- Ref2VA 6 段（+retention 词汇逐字：`fully_preserved`…）。
- 有图写官方对齐第一行；对白 `<d>[中文] 原文</d>` + speaker `(S1)`；**台词长度匹配镜头长度**（口型）。
- 角色镜头走 I2VA（首帧锁脸）；跨镜身份用 Ref2VA。

## 5. 硬件 + 逐镜生成【门:逐镜 clip 通过】
`python -m h3_short_drama plan --vram 8 --aspect 9:16 --seconds 5 --quality fast`
- 画布 32 对齐；帧 17k+5；8GB→640×352/4步/BlockCache；16GB→768 短边。
- 逐镜：模型卡（H3 默认 / Seedance 回退）+ 分辨率卡；**对白/链式镜头关 Turbo+Spectrum**。
- 门：口型/一致性/无分镜痕迹（panel 边框/铅笔线/标签/时序标记）。

## 6. 长片拼接（单集>15s）
- **分镜切换**：首尾帧法（`Save Last Frame`→下一镜 `first_frame`）+ 硬锁前后缀。
- **同机位无缝**：latent 钉接（上段尾 22 帧 AV latent 钉成下段 never-denoised cond 行，`context22/audio24`）。
- 关 Turbo/Spectrum；**32kHz**（拼接读采样率别硬编 48k）；接缝验收 cross-correlation。
- 见 `skill/references/continuity.md`。

## 7. 小脸/串戏救急
- 中远景小脸糊 → **FaceRefine 逐帧重生成脸**（H3 固有小脸问题；denoise 别搬 SDXL）。
- 跨镜串戏 → Ref2VA + retention 词汇；连载 → Phosphene LoRA。
- 跨镜音色 → 显式音色库 + 对白安全混音。见 face-refine.md / consistency.md / audio-consistency.md。

## 8. 装配 + BGM
`python -m h3_short_drama assemble --clips a.mp4 b.mp4 ... --out final.mp4 --bgm bgm.mp3 [--sub s.srt] [--execute]`
- 一条连续 BGM，对白/重要 SFX 下 duck；**不逐镜 BGM**；不加字幕除非用户要。
- 混音：BGM vol 0.10、voice 1.4、xfade 0.4s。最终无分镜痕迹。

## 9. 终审 QC（交付前）
角色一致性 / 场景连续（地标落位）/ 情感 payoff / **对白可懂性（逐帧+音频流+可懂性三级）** / SFX 同步 / BGM 平衡 / **无分镜 artifacts** / 接缝(长片)。

## 失败回退（单镜）
1 强化 prompt 引用 Reference Anchors → 2 缩镜≤6s 拆行重跑自检 → 3 该镜切另一模型 → 4 三次败问用户（切模型/放宽/跳过/供参考视频）。**不静默混新旧资产。**
