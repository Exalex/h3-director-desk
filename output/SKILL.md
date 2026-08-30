---
name: h3-short-drama
description: |
  用 MiniMax H3（海螺3.0）端到端生产带对白的竖屏短剧。从一句话点子到最终成片，
  覆盖爆款方法论、角色/场景一致性卡、六列标准分镜表、H3 提示词编译（T2VA/I2VA/FL2VA/L2VA/Ref2VA）、
  长片 latent 链式拼接、加速取舍、QC 终审与回退。当用户要做 AI 短剧/漫剧/对白镜头、
  需要 H3 提示词规范、多镜连贯、角色锁脸、或短剧生产 SOP 时使用。
  不用于单张图 / 单条 clip / logo / 纯提示词咨询。
---

# H3 短剧生产 Skill

把用户的短剧请求转成**可执行、可回放、可复用**的生产工作流。每步产出落盘（文件/节点），在昂贵步骤前停下来用**门（gate）**确认。

## 核心铁律
- **H3 一句 prompt 直接出画面+对白+口型+音效**（无需先 TTS 再对口型）。对白镜头首选 H3。
- **先锁定 4 项**（画幅/时长/对白/对白语言）再开工，全程复用。
- 一集 = 多个 4-15s 镜头串联；**单镜 ≤15s，超了拆**。
- 对白/链式镜头**关 Turbo+Spectrum**（伤音频/软画面/误预测 pinned 行）。
- 提示词正文英文，**对白/歌词/场景文字保留原语言**；`<d>[语言] 台词</d>`。

## 工作流（十步 + 门）
按顺序执行；每步末尾的门通过才进下一步。细节见 `references/`。

1. **STEP0 输入&画幅/时长**：收集点子/期望产出/时长/画幅/视觉调性/对白需求 → 锁画幅+时长。
2. **STEP1 项目简报**：What-if/情感前提/受众感受/交付物/画幅/时长/对白模式+语言/风险。门：方向确认。
3. **STEP2 故事大纲**：主角 Want/Need/flaw + 8-beat 因果脊 + 情感锚点 + 对白节拍。
   门（红线）：主角主动 / 危机被主角缺陷放大 / 巧合绝不解决 / 结尾复用早前情感锚点 / 对白揭示关系变化。
   方法论与 15 字段概念见 `references/methodology.md`。
4. **STEP3 角色卡**：每主要角色 16:9 参考卡（多视角+表情+do-not-change 特征 + 视觉-ID 注）。门：锁定（改=重生成下游全部）。
5. **STEP4 场景卡**：纯环境（不含人）+ 连续性地标（跨镜保持屏幕位置的固定物）。门：锁定。
6. **STEP5 标准分镜表（六列，强制）**：见 `references/shot-table.md`。
7. **STEP5.5 自检门（六条，强制）**：见 `references/shot-table.md` §自检。任一不过→回 STEP5。
8. **STEP6 分镜脚本**：每镜一节的文本分镜（默认）；重度迭代镜头抽独立节点。门：分镜确认。
9. **STEP7 逐镜生成**：模型卡（H3默认/Seedance回退/逐镜混用）+ 分辨率卡 → 逐镜渲染。
   提示词编译见 `references/prompt-spec.md`；一致性见 `references/consistency.md`。
   门：逐镜 clip 通过（口型/一致性/无分镜痕迹）。
10. **STEP8 长片拼接+BGM**：单集>15s 用 `references/continuity.md`；装配见 §8。
11. **STEP9 终审 QC**：见 `references/qc-fallback.md` §QC。交付最终资产。

## 提示词编译（速记）
- Base（T2VA/I2VA/FL2VA/L2VA）三段：`integrated_multimodal_description` / `overall_soundscape` / `non_diegetic_music`。
- Ref2VA 六段：`subject_definitions` / `summary` / `retention_analysis` / `detailed_description` / `overall_soundscape` / `non_diegetic_music`。
- 5 模式锚点、标签规则、retention 词汇、对白冒号规则、speaker ID 见 `references/prompt-spec.md`。

## references 索引
| 文件 | 何时查 |
|---|---|
| `references/prompt-spec.md` | 写 H3 提示词（3段/Ref2VA 6段/标签/retention/对白/对齐行/运镜公式/口型） |
| `references/prompt-engineering-zh.md` | 大白话→规范转换（核心公式/坑清单/goodcase 8特征/推荐模板） |
| `references/shot-table.md` | 六列分镜表 + 六条自检门 |
| `references/continuity.md` | 长片链式拼接（首尾帧/latent 钉接/4条prompt纪律/32kHz） |
| `references/consistency.md` | 一致性双路线（轻量I2VA+尾帧链/中量Ref2VA/重量LoRA/Jellyfish全局字典） |
| `references/face-refine.md` | 治 H3 小脸（逐帧重生成脸/denoise 不搬 SDXL/多人串联） |
| `references/audio-consistency.md` | 跨镜音色/对白/背景音一致（音色库/对白安全混音/多人顺序修复） |
| `references/methodology.md` | 爆款方法论（调性检验/喜剧公式/五黄金法则/15字段/5题材） |
| `references/deployment.md` | 硬件感知部署（3档profile/画布对齐/模型文件/诊断顺序） |
| `references/qc-fallback.md` | QC 终审 + 回退阶梯 + 重生成纪律 |
| `references/autonomous-studio.md` | 一人工作室·自主 agent 流程（一句话→成片无人值守，3 个人机交互点） |

## 快速判定
| 需求 | 用 |
|---|---|
| 纯文生视频 | T2VA |
| 有首帧图 | I2VA（角色镜头用 I2VA 锁身份） |
| 首尾都要锁 | FL2VA（+ 硬锁前后缀，见 continuity.md） |
| 跨镜身份保持 | Ref2VA + retention 词汇 |
| 漫剧/连载真锁脸 | Phosphene face+voice LoRA（consistency.md 重量路线） |
| 中远景小脸模糊 | FaceRefine 逐帧重生成脸（face-refine.md；H3 固有小脸问题） |
| 长片同机位无缝 | latent 钉接 context22/audio24（continuity.md 路线B） |
| 本地跑不动 | 云端 API（TECH.md §9） |
