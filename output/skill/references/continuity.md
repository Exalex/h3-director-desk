# 长片链式拼接（continuity）

H3 单镜 4-15s；长片 = 多个 in-range 窗口拼接。

## 路线 A：首尾帧法（简单，适合分镜切换）
- 每镜 `Save Last Frame` → 下一镜 `first_frame`（FL2VA 硬件锁首尾）。
- 每镜 prompt 前后缀**硬锁**（PE 增强后仍重套，旧包裹自动剥离防堆叠）：
  > "完全保持首尾帧。视频第一帧必须与给定首帧画面一致，最后一帧必须与给定尾帧画面一致；首尾帧是硬锁定关键帧，不是软参考，禁止改动首尾画面、主体外观与机位。"
- 镜头串联：shots 共享关键帧（shot1 end = shot2 start；shot2 end = shot3 start）。

## 路线 B：latent 钉接（运动级无缝，同机位长镜头）
- 上段 **sampler 输出 AV latent 尾 22 帧**（音频 24 帧）直接切片（bit-identical，无 decode/resize/encode）→ 钉成下段 0..N-1 never-denoised cond 行 → 采样 → Trim 裁前 22 帧 + match_tail。
- 参数：`context_length=22`（可选 5/22/39/56，必 latent step 整数，`start%5==0` 相位断言）；`audio_context_length=24`（=1s，3 的倍数落 40Hz 网格）。
- 上段 latent 跨 run 走磁盘（Save/Load Latent，`clip_00002.safetensors`；clip_index 固定槽=重拍覆盖自身 reject，retry-safe）。
- 音频：尾 24 帧切片，**末端对齐接点向回延伸**（timeline 语义）→ 模型"续播"而非"cover band 模仿"（互相关 0.45→0.95+，tick 消失）。
- 常量：ENCODE_MODE=video / ANCHOR_MODE=head / AUDIO_MODE=timeline / CROP=disabled（分辨率变直接拒绝）。

## 拼接 prompt 纪律（4 条）
1. 模型把矛盾渲染成**并集**（钉帧非建议）→ 切镜指令写时间序而非并列。
2. **气闸(airlock)**：换调度时，下镜开头 ~2s 保持上镜结尾取景、无对白，再切。
3. 给 hold 一点事做（呼吸/重心/眼神）→ 空 hold 渲染成 freeze。
4. head 模式交付比采样短 22 帧(0.92s) → 时间码对采样版写。

## 硬约束
- **关 Turbo/Spectrum**（对白/链式镜头；伤音频/软画面/误预测 pinned 行）。
- **32kHz 陷阱**：H3 输出 32kHz 非 48；拼接脚本必须读采样率，硬编 48000 静默毁长片尾。
- 分辨率中途不能变（latent 不能 resize）；接缝验收：cross-correlation + 电平/room-tone + 采样率 + freeze。
- 质量沿链衰减主要在音频（复印机效应，高频先丢）；重启链选自然音乐过渡处。
- 接缝验收四件套（可脚本化）：seam_probe（延续/模仿/漂移 + lag ms）、level_step（电平/room-tone + 采样率）、freeze_detect（画面静止）。

## 运动向量延续（双轨）
- 同机位/同动作：latent 钉接（bit-identical 无 seam）。
- 换机位保运镜/节奏：参考视频轨 `<Video k>`（ref2va，单段 2-15s 总 ≤15s 短边 ≤768 省显存），retention 声明（"its camera work, not its pixels"）。
- 分镜表每镜标 continuity 类型：`hard_cut` / `latent_pin` / `motion_ref`。
