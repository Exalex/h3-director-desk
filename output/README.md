# H3 短剧生成 · 交付物索引

> 项目目标：H3(MiniMax H3/海螺3.0) 短剧生成诀窍 + GitHub 库下载解析对比 + 迭代 100 轮，
> 最终沉淀为 打法 + 脚本 + skill + 流程图 + 技术细节。

## 核心交付物（output/）
| 文件 | 内容 | 状态 |
|---|---|---|
| **QUICKSTART.md** | 一页跟做：锁4项→定方向→角色/场景卡→六列分镜表+自检→编译提示词→硬件+生成→拼接→救急→装配→QC→回退（每步带可执行命令） | ✅ |
| **PLAYBOOK.md** | 打法：部署决策 + 爆款方法论 + 十步 SOP + 分镜表 6 列 + 自检 6 条 + 长片拼接 + 一致性 + QC + 回退 + 成本 | ✅ |
| **SKILL.md** + `skill/references/` | Agent skill（对齐官方 MiniMax skill 结构）：主 SKILL + 7 个 references(prompt-spec/shot-table/continuity/consistency/methodology/deployment/qc-fallback) | ✅ |
| **FLOWCHART.md** | 6 张 mermaid：端到端 SOP / 单镜数据流 / 长片链式 / 一致性双路线 / 回退阶梯 / Jellyfish 一致性检查 | ✅ |
| **TECH.md** | 技术细节：模型/输出规格/帧网格数学/双 UNET/提示词 schema/节点参数/加速/硬件 profile/API/分辨率预设/状态模型/ffmpeg | ✅ |
| **COMPARE.md** | 19 库对比矩阵（分层 + 全清单 + 关键差异） | ✅ |
| **scripts/** | 可执行 Python 管线（已验证运行） | ✅ |
| **USER_WORKFLOW.md** | 小白版用户交接协议：用户需要提供什么、哪些步骤自动执行、4个确认关卡、可复制输入模板 | ✅ |
| **IMPLEMENTATION_WORKFLOW.md** | 代码级大白话：从输入 JSON、提示词编译、角色锁定、ComfyUI 节点、逐镜尾帧链到 ffmpeg 拼集；含伪代码、流程图、模型文件和限制 | ✅ |

## 证据（notes/）
- round-001 ~ 006+（每轮 总结/反思/发散）
- analysis-methodology.md / analysis-jellyfish.md / analysis-continuity.md（子代理 + 亲自读码的源码级报告）
- 官方 22 个 skill 文件已抓入 `libraries/MiniMax-H3-official-skill/`

## 库（libraries/，19 库 + 官方 skills）
MiniMax-H3-ComfyUI / ComfyUI-MiniMaxH3-Easy / ComfyUI-H3-Motion-Context / ComfyUI-Spectrum-MiniMax-H3 / ComfyUI-H3-FaceRefine / ComfyUI-MiniMaxH3-Director / ComfyUI_MiniMaxH3_Director / AIMixer-ComfyUI_MiniMaxH3_Director / ComfyUI-MiniMax-H3-Promptor / ComfyUI-H3-Prompt-Builder / h3lite / Phosphene / ComfyUI-MiniMax-H3-Turbo / comfyui-minimax-h3-audio-T8 / TE-Speed-MiniMaxH3-OSS / Jellyfish / Short-Drama-Concept-Creator / ai-script-hub / ai-video-pipeline / MiniMax-H3-official-skill
