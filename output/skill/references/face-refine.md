# 人脸精修（face-refine）— H3 小脸问题解法

> 来源：ComfyUI-H3-FaceRefine (Carasibana)。解决 H3 的固有小脸问题。

## 核心问题
**H3 在头部占画面比例小时渲染差**——这是"头在画面里多大"的性质，不是输出分辨率的问题，720p 及以上也照样烂。所以提分辨率没用，要**重生成脸**。

## 解法（Impact-Pack FaceDetailer 适配到视频，逐帧）
```
source clip → H3 Face Track+Crop → crops → H3 Inject Video Latent(img2img)
   │                                  transform ─┐
   │                 MiniMaxH3ReferenceToVideo(refs) ─→ NativeAudioLock(vocals)
   │                                                          │
   └── transform ──→ H3 Per-Frame Denoise ←───────────────────┘
                                → SamplerCustomAdvanced → VAEDecode
                                → H3 Face Stitch Back(base=原帧) → 原音频 → 保存
```

## 关键节点参数（诀窍）
**H3 Face Track + Crop**
- `crop_factor 2.5`（2.0-3.0 有效区）：脸占裁剪 ~40%，接缝落在头发/背景。
- `canvas 768` = H3 原生短边 = 最好脸（512 的 2.25× 成本）。
- `smooth_window 21`（~0.9s，裁剪中心）；`size_smooth_window 51`（**更大**，尺寸抖动让裁剪"呼吸"→shimmer）。
- `smooth_method gaussian`（抗抖动最好）。
- `identity_reference + identity_track`：按**身份**而非大小选主体；身份嵌入只在两个候选相似或框重叠时才查，连续性扛住侧脸/遮挡。
- `report` 看 `magnification < 1.0x` = 裁剪被降采样 = 真细节丢弃 → 提画布或跳过全程近景的 clip。
- **多人**：每人跑一遍（各自 identity_reference + refs），串联（run1 拼好 → run2 的 base_images），复合累加。

**H3 Inject Video Latent (img2img)**
- 把真实帧编码进 H3 **联合 AV latent 的视频流**，音频流不动——这是**缺失的 img2img 路径**（H3 原生节点永远建 zeros latent，参考是每步重注入的 conditioning，不是起点）。没有它就没有 video-to-video。
- strength 由下游 `BasicScheduler` 的 `denoise` 定，**不用 SplitSigmas**。

**H3 Per-Frame Denoise**
- 沿时间轴按**实测脸大小**变 denoise：小脸→强 pass（合成细节），大脸→轻 pass（保留已有细节）。
- `strength_small_face 1.0` / `strength_large_face 0.35`；`face_px_small 30` / `face_px_large 120`；`gamma` 调曲线；`smooth_frames 9`（突变 denoise 会纹理 pop）。
- base denoise 与这些乘子**一起调**；绕过本节点要把 base 降很多，否则大脸被重写。

**H3 Face Stitch Back**
- warp 回原 float 框 + colour-match + feather + composite；单次 `grid_sample` 不二次量化。
- **只 composite 脸区**（宽裁剪是给采样器当 context，不贴）：贴整张裁剪盖 ~88% canvas vs 脸框 16%。
- `feather ~24`（rect 掩码）/ `4-8`（SAM）；`colour_match 1.0`（裁剪和帧走了独立 pass，不 match 脸会偏亮像贴上去的）；`blend <1.0` 回调过锐。
- `undetected_frames fade_out`（**所有帧都过 H3** → 时间一致；这只控制贴不贴）。

## 关键 诀窍（最易翻车）
1. **H3 denoise 值不能从 SDXL 直接搬**：H3 是 flow matching + 大 sigma shift。`sigma = shift*t/(1+(shift-1)*t)`。shift=12 时 denoise 0.25（普通 FaceDetailer 值）→ 有效 sigma 0.800 → **重写整帧**。H3 需要低得多的 denoise。
   | denoise | 有效 sigma(shift12) |
   |---|---|
   | 0.02 | 0.197 |
   | 0.05 | 0.387 |
   | 0.15 | ~0.66 |
   | 0.25 | 0.800 |
2. **steps 与 denoise 独立**：BasicScheduler 建 steps/denoise 长的全范围 schedule，保留最低 steps+1 个 sigma → 4 步 + turbo LoRA 又快又轻。**别用 SplitSigmas**（4 步 schedule 在 shift12 下最后一个 split 点已是 sigma 0.800）。
3. **推 denoise 太高** → 头相对身体漂移（内容问题，任何 mask 遮不住）。
4. **帧数必须在 17k+5 网格**（5,22,39…175,226,362）；H3 生成的 clip 天然满足。
5. **成本 = canvas² × 帧数**；auto 画布只看脸大小，长 clip 可能选超 VRAM 的画布 → 从系统内存流式载权重（慢一个数量级，不是干净报错）。
6. **SAM vs rect 掩码**：rect 常常赢（接缝在头发/背景，不显眼；SAM 贴脸太紧，漂移全落在轮廓上，侧脸鼻子最明显）。先试 rect。
7. **mask 输入，别 mask 输出**：从源裁剪算 mask（对齐 FaceDetailer），生成不回喂 mask（否则模型把脸往内挪，mask 贴新轮廓，原脸从边缘戳出）。
8. **onnxruntime**：别把 onnxruntime-gpu 和 onnxruntime 同时装（CPU 包遮蔽 GPU，CUDAExecutionProvider 消失，身份匹配静默跑 CPU）。

## 口型（lipsync）
H3 是**联合音画模型**。`MiniMaxH3NativeAudioLock` 把真实音频编码进 AV latent 音频流，`noise_mask` 视频=1/音频=0 → 只有视频 denoise，视频分支 cross-attend 到固定音频 = 塑造嘴型。喂**分离人声** track 更干净；**原音频**另外进 save 节点（两条音频路径别混）。

## 一句话决策
- 近景大脸：直接 I2VA/Ref2VA 通常够。
- 中远景小脸：跑 FaceRefine（逐帧重生成脸）；成本 canvas²×帧。
- 多人镜头：逐人串联。
