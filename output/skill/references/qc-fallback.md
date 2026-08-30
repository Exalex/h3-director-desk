# QC 终审 + 回退阶梯（qc-fallback）

## STEP 9 终审 QC 清单
- 角色一致性（对照 consistency.md）
- 场景连续性（对照 Reference Anchors：每个地标是否落在表里说的位置）
- 情感锚点 payoff / 镜头目的清晰
- **对白可懂性**：逐帧 + 音频流 + 可懂性 三级验证（有音频流 ≠ 台词清晰；有嘴动 ≠ 可懂对白）
- Foley/SFX 同步（对照 Audio & Dialogue Track）
- BGM 平衡
- **无分镜 artifacts**：panel 边框/铅笔线/箭头/标签/手写/时序标记/双绑定标签(`[char:…] [scene:…] [shot:…] [dur:…] [hook:…]`)
- 缺失/弱镜头；任何需重生成资产
- 接缝验收（长片）：cross-correlation + 电平/room-tone + 采样率(**32kHz!**) + freeze

## 装配 + BGM（STEP 8 规则）
- 按分镜表顺序拼接；生成**一条连续 BGM** 匹配情绪/节奏/喜剧点/追逐律动/结尾调。
- BGM 在**对白/反应/重要 SFX 下 duck**；保留已有 clip 音频/SFX（除非用户要替换）。
- **不逐镜生成 BGM**；不加字幕/文字除非用户明确要。
- 最终无分镜痕迹。
- 混音参考：BGM volume 0.08-0.10，voice 1.4-1.5，amix；xfade 0.4s 循环。

## 回退阶梯（单镜失败/漂移）
**H3**：
1. 重试：强化 prompt 引用精确 Reference Anchors 块
2. 重试：缩镜 ≤6s，被删秒拆相邻新行，重跑 5.5
3. 重试：该镜切 Seedance 2.0（混用模式=一键非重构）
4. 三次失败后问用户：只这镜切 Seedance / 放宽(删道具/简化动作/降钩子) / 跳过+placeholder / 手动供参考视频

**Seedance**（用户显式选或 H3 已 3 败）：
1. 强化 prompt 引用 Reference Anchors
2. 丢参考图改纯文本
3. 缩镜 ≤6s 拆行
4. 三次失败后问用户：切 H3 / 放宽 / 跳过 / 供参考视频

**漂移**：渲染 clip 偏离批准 Reference Anchors（door-frame 落错边/角色从错边出/光线翻转）→ 强化 prompt 引用精确 Reference Anchors 块重渲染；持续漂移 → 该镜切另一模型混用路径；**不静默把修正/未修正 clip 混进装配**。

## 重生成纪律（最新资产）
任何资产重生成后，下游必须用**最新批准版本**：
- 角色卡改了 → 下游 shot table/分镜/clip/装配/合成全引用新版（按精确角色名）
- 场景卡改了 → 同上（按精确场景名）
- shot table 改了 → 分镜/clip/装配用新版 + 重跑 5.5
- 分镜节改了 → 对应 clip 用该节；抽出独立节点则该节点为真值
- clip 重渲染 → 装配/BGM/合成用新 clip；H3↔Seedance 切换视为 model switch，记录并重查逐镜规则
- BGM 重生成 → 合成用新 BGM
- 不静默混新旧资产；多版本时先按文件名/节点名指明当前版本。

## 门（choice-card 纪律）
每个需确认处用 choice card（不用纯聊天问句）；默认推荐项第一；允许自定义输入；用户说"continue"=选推荐项。
必设门：画幅 / 时长 / 简报 / 大纲 / 角色卡 / 场景卡 / 分镜表(门1) / 自检过(门2, 选分镜模式) / 逐镜分镜 / 视频模型 / 分辨率 / 逐镜 clip / 装配+BGM+合成。
