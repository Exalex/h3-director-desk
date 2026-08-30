# 部署 / 硬件感知（deployment）

## 平台路由
| 平台 | 状态 | 引导 |
|---|---|---|
| Windows + NVIDIA CUDA | 主，已验证 | ComfyUI/H3 Lite fast path |
| macOS Apple Silicon | 社区备选 | MLX/Phosphene（双引擎 LTX-2.5 + H3；可训 LoRA） |
| macOS Intel | 不推荐 | 走云端 API |
| Linux + NVIDIA | 未验证 | 显式实验选择 |

## 三条路（显存不足走云端）
- 本地 Windows+NVIDIA：ComfyUI + H3 节点
- 本地 Mac：Phosphene(MLX)，`uvx mmh3turbo` 或 bundle
- 显存 <6GB：走云端 API（OpenAI/火山/MiniMax）

## 3 档 profile（h3lite）
| profile | 画布 | 帧 | 步数 | Cache | 适用 |
|---|---|---|---|---|---|
| Fast | 640×352 | 124 | 4 | Block Cache | 8GB 基线/成功率 |
| Balanced | 640×352 | 124 | 6 | 关 | 8GB |
| Quality | 640×352 | 124 | 8 | 关 | 8GB |
| 中/高显存 | 864×480(0.4MP 16:9) | — | 6-8 | 关 | 16GB |

- 画布 **32 像素对齐**（VAE 16px + DiT 2px patch）；0.4MP 16:9 → 864×480；9:16 → 480×864(Fast)/768×1344(Native)。
- 显存 ~8GB→Set A(W4A8 INT4 文本编码器 4B)；16GB→Set B(FP8)。
- 瓶颈 = offload/CPU带宽/首编译（非 GPU 计算）。

## 模型文件
fl2va/ref2va pruned_fp8_scaled(21GB) + qwen3vl_32b 文本编码器(15GB) + video_vae_fp16(4.9GB→fp32~10GB) + audio_vae_fp32(0.6GB)；bf16 66GB 最高质；int8_convrot 34GB。
VAE：H3-VisualVAE(f16t4d24) + H3-AudioVAE（双 VAE 独立）。

## 中文提示词诀窍
- 避免超短名词式（1-2 token 易被 seed 主导）；用 **30-50 字**或结构化细节（主体特征/场景/构图/光线/运动）。
- 先便宜画布验证，再提档。

## 音频策略
- "无对白"≠静音：保留环境音；仅"完全静音"才移除音频流。
- 本地默认：有对白→双声道(对白+环境)；无对白→环境音；完全静音→移除流。

## 零推理优化约束（质量门/QA 原则）
硬件检查/QA 不得：加采样步 / 加生成模型 / 跑第二次视频推理。只可重排/复用已生成数据。

## 人脸质量路由
- 要可识别/说话人脸 → 别用低显存 W4A8 640×352 当最终。
- 单镜说话：I2VA 清晰首帧。
- 跨镜身份：Ref2VA 参考。
- 先检首/中/尾帧人脸一致性（身份漂移/模糊/换脸）。

## 诊断顺序（生成失败）
1 页面文件/RAM 2 缺模型/节点 3 错文件夹 4 CUDA/PyTorch 5 OOM/offload 6 flow/audio 图 7 提示词/参考对齐。
VAE flat grey = NaN → 启动 `--fp32-vae`。

## 快速命令
```powershell
# 复跑（一条命令；别再逐个 doctor/plan/preflight/generate/status）
python scripts/h3_fastpath.py --comfyui <路径> --prompt-text "<改写提示词>" --resolution 640x352 --video-seconds 5 --json
# 模式：--mode i2va --first-frame <png>   /   fl2va --first-frame <首> --last-frame <尾>   /   l2va --last-frame <尾>
```
