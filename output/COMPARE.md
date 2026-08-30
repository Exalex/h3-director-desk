# H3 短剧生成 — 库对比矩阵 (COMPARE)

> 目标: 把 19+1 个 GitHub 库按"维度"横向对比, 提炼每个库在"一人 H3 短剧工作室"里能贡献什么。
> 星数为 2026-08-18 抓取; 路径 `libraries/<name>`。图例: ★★★ 核心/权威 · ★★ 有用 · ★ 参考。

## 1. 分层视图 (一人剧组 7 个岗位 → 库)

| 岗位/环节 | 首选库 | 备选 | 贡献 |
|---|---|---|---|
| 剧本/创意 | Short-Drama-Concept-Creator | ai-script-hub | 爆款判断框架 + 梗概→分镜 |
| 提示词规范 | MiniMax-H3-official-skill (官方) | MiniMax-H3-ComfyUI docs | 3段/Ref2VA 6段 + retention + speaker ID |
| 分镜/一致性卡 | Jellyfish | 3d-animation-short-generator | 多agent拆镜 + 角色/场景卡 + 三轴状态 |
| 镜头编排/时间线 | ComfyUI-MiniMaxH3-Director | ComfyUI_MiniMaxH3_Director | 时间线+@refN+retake+save-last-frame |
| 视频生成(对白) | MiniMax-H3(官方 H3-Base FL2VA/Ref2VA) | Phosphene(H3 FL2VA) | 一句prompt出画面+台词+音效 |
| 多镜锁脸 | Phosphene(角色LoRA) | ai-video-pipeline(尾帧链) | face+voice LoRA / 尾帧chaining |
| 长片拼接 | ComfyUI-H3-Motion-Context | (无) | latent-slice + airlock + 32kHz |
| 加速 | ComfyUI-Spectrum-MiniMax-H3 | ComfyUI-MiniMax-H3-Turbo | Chebyshev ridge 跳步 (链式时关!) |
| 小脸精修 | ComfyUI-H3-FaceRefine | — | 逐帧crop→refine→stitch |
| 部署/硬件 | h3lite | — | 硬件→profile→画布→步数 + 一键脚本 |
| 端到端 | Jellyfish | ai-video-pipeline | 全链路(含ffmpeg合成) |

## 2. 全库清单 (按维度)

### A. 核心模型/节点
| 库 | 星 | 维度 | 一句话 |
|---|---|---|---|
| MiniMax-H3-ComfyUI | 128 | 权威文档+节点 | 33B H3 本地 ComfyUI: 架构/提示词/API/FAQ + t2v/i2v/r2v/2k 节点 + VAE + turbo lora |
| comfyui-minimax-h3-audio-T8 | 728 | 音频 | H3 音频节点/加速(T8 block cache) |
| TE-Speed-MiniMaxH3-OSS | 250 | 加速 | 社区加速版 H3 |
| ComfyUI-MiniMaxH3-Easy | 443 | 简化工作流 | 统一多媒质输入+@引用+内联对白块; prompt_guides=官方skills副本 |

### B. 时间线/编排/编辑器
| 库 | 星 | 维度 | 关键机制 |
|---|---|---|---|
| ComfyUI-MiniMaxH3-Director (seesee75) | 211 | 时间线 | 轨道时间线; @refN→<Subject>/<Picture>; speaker ID; 对白冒号规则; Retake Mode; Save Last Frame; 分辨率预设; 17k+5网格 |
| ComfyUI_MiniMaxH3_Director (huangserva) | 677 | 多段导演 | 多段编排 |
| AIMixer-ComfyUI_MiniMaxH3_Director | 521 | 多段导演 | 官方ComfyUI H3 多段 |

### C. 长视频/链式
| 库 | 星 | 维度 | 关键机制 |
|---|---|---|---|
| ComfyUI-H3-Motion-Context | 613 | 链式(核心) | patch ComfyUI 解除首尾帧限制; latent-slice 交接; context22/audio24; airlock; 32kHz; 关Spectrum/Turbo |
| ComfyUI-MiniMax-H3-Turbo | 454 | 加速 | turbo lora (链式时关) |

### D. 一致性/精修
| 库 | 星 | 维度 | 关键机制 |
|---|---|---|---|
| ComfyUI-H3-FaceRefine | 232 | 小脸 | 逐帧人脸检测→crop→H3 refine→stitch 回 |
| Phosphene | 162 | LoRA锁脸+声 | Mac/MLX; LTX-2.5+H3双引擎; face+voice LoRA; 窗口链式; HTTP API可被agent编排 |

### E. 加速
| 库 | 星 | 维度 | 关键机制 |
|---|---|---|---|
| ComfyUI-Spectrum-MiniMax-H3 | 528 | 跳步加速 | Chebyshev ridge 预测post-transformer特征, 跳选定transformer步; 自适应调度; 采样器保护; CPU/VRAM历史 |
| h3lite | 208 | 硬件感知 | 探测硬件→选profile(640x352/4步 W4A8 基线); 32px对齐; 30-50字中文; 音频策略; 一键fastpath |

### F. 提示词/剧本
| 库 | 星 | 维度 | 关键机制 |
|---|---|---|---|
| ComfyUI-MiniMax-H3-Promptor | 138 | 电影级prompt | 自动化生成 H3 规范prompt |
| ComfyUI-H3-Prompt-Builder | — | 剧本→分镜 | 大白话→分镜剧本→逐镜H3提示词 |

### G. 短剧方法论/管线
| 库 | 星 | 维度 | 关键机制 |
|---|---|---|---|
| Jellyfish | 6038 | 端到端 | 12个LLM agent(script_divider/character/scene/costume/prop/consistency_checker/shot_frame_prompt...); 角色/场景/服装/道具卡; 三轴状态(shot.status/video-readiness/runtime); 多provider(openai/volcengine); celery任务 |
| Short-Drama-Concept-Creator | 15 | 方法论 | 7规则+10质检+15字段概念schema; 喜剧公式; 创作者画像反馈闭环 |
| ai-script-hub | 1 | 剧本SaaS | 一句话→分镜表单次LLM; 5黄金法则+5题材模板+3节奏 |
| ai-video-pipeline | 1 | 一人管线 | FLUX→Kling(I2V尾帧链)→TTS→Suno→ffmpeg; 分组并行; $2/条 |
| ai-drama-generation | 0 | 多agent | (下载不稳定, 参考) |

## 3. 关键差异 (为什么选这些组合)

1. **"写什么" vs "怎么生成"**: 官方 skills + SDCC 解决创意/提示词; 官方 H3-Base + Motion-Context + Phosphene 解决生成/拼接/一致性。两者必须配合, 单一库都拼不出完整短剧。
2. **对白**: H3 是唯一"一句 prompt 直接出对白+口型+音效"的路径(ai-video-pipeline 需先 TTS 再对口型, 两步)。短剧对白镜头首选 H3。
3. **一致性三条路**: ① 轻(尾帧链+cutaway, ai-video-pipeline, ~80%) ② 中(Ref2VA 多参考图, 官方) ③ 重(Phosphene face+voice LoRA, 真锁脸跨集)。漫剧/连载选③。
4. **加速的代价**: Spectrum/Turbo 省时间但**伤音频、软画面、误预测钉帧行** → 链式/对白镜头必须关。加速只用在非对白、非链式镜头。
5. **2K 是另一套 API**(H3-Regenerate-2K, 闭源), 本地 base 只有 768px 短边; 别把"2K"当本地默认。
