# H3 短剧生成 · 流程图 (FLOWCHART)

> 用 mermaid。可粘贴到任何 mermaid 渲染器。

## 1. 端到端 SOP（一集短剧）

```mermaid
flowchart TD
    A[STEP0 输入<br/>一句话点子] --> A1{选 画幅}
    A --> A2{选 单集时长}
    A1 --> B[STEP1 项目简报<br/>What-if/情感前提/风险]
    A2 --> B
    B --> G1{门:方向确认}
    G1 -->|继续| C[STEP2 故事大纲<br/>8-beat因果脊/情感锚点]
    G1 -->|改| B
    C --> G2{门:红线检查<br/>主角主动/巧合不解决/结尾复用锚点}
    G2 -->|过| D[STEP3 角色卡<br/>多视角+表情+do-not-change特征]
    G2 -->|改| C
    D --> G3{门:锁定角色}
    G3 -->|锁| E[STEP4 场景卡<br/>纯环境+连续性地标]
    G3 -->|重生成| D
    E --> G4{门:锁定场景}
    G4 -->|锁| F[STEP5 标准分镜表<br/>六列+逐秒指令]
    G4 -->|重生成| E
    F --> G5{门:5.5自检六条<br/>钩子密度/≤15s/≤3角色/空间继承/逐秒/跨镜连续}
    G5 -->|过| H[STEP6 分镜脚本<br/>每镜一节文本版]
    G5 -->|失败| F
    H --> G6{门:分镜确认+选模式}
    G6 -->|过| I[STEP7 逐镜生成<br/>模型卡/分辨率卡]
    G6 -->|改| H
    I --> G7{门:逐镜clip通过<br/>一致性/QC}
    G7 -->|过| J[STEP8 长片拼接+BGM<br/>§6链式 + §8装配]
    G7 -->|漂移| I7[§10回退阶梯]
    I7 --> I
    J --> K[STEP9 终审 QC<br/>§9清单]
    K --> L([最终交付])
```

## 2. 单镜数据流（分镜行 → H3 提示词 → 生成）

```mermaid
flowchart LR
    ROW[分镜表一行<br/>S03/6s] --> P[提示词编译器]
    CARD[角色卡<br/>一致性锚点①] --> P
    SCEN[场景卡<br/>一致性锚点②] --> P
    PRE[上镜结尾状态<br/>Continuity Handoff] --> P
    P -->|Refs OFF=fl2va| T2V[H3 TextToVideo<br/>integrated_multimodal_description<br/>overall_soundscape<br/>non_diegetic_music]
    P -->|Refs ON=ref2va| R2V[H3 ReferenceToVideo<br/>subject_definitions<br/>summary/retention_analysis<br/>detailed_description<br/>+音效+音乐]
    T2V --> VAE[VAEDecode 视频 + VAEDecodeAudio]
    R2V --> VAE
    VAE --> CLIP[clip.mp4 + 音频]
    CLIP --> QC{QC<br/>口型/一致性/无文字}
    QC -->|过| NEXT[存末帧→下镜首帧<br/>或 Save/Load Latent]
    QC -->|失败| RETRY[强化prompt引用<br/>Reference Anchors 重试]
    RETRY --> P
```

## 3. 长片链式拼接（latent 钉接，Motion-Context 内幕）

```mermaid
sequenceDiagram
    participant A as Clip A 采样
    participant SL as Save Latent
    participant MC as Motion Context 节点
    participant B as Clip B 采样
    participant TR as Trim
    A->>SL: 上段 AV latent (clip_00001)
    SL-->>MC: context_latent (尾22帧切片, bit-identical)
    MC->>MC: 钉成 0..21 never-denoised cond 行<br/>音频尾24帧 末端对齐接点(timeline语义)
    MC->>B: 强化 conditioning + trim_frames=22
    B->>TR: 解码 视频+音频
    TR->>TR: 裁前22帧 + match_tail(消±8.3ms累积)
    TR->>SL: clip_00002 (供下一镜续拍)
    Note over MC: 关 Turbo/Spectrum; 32kHz 拼接
```

## 4. 一致性双路线（不串戏）

```mermaid
flowchart TD
    START{需要跨镜锁脸?} -->|轻/零成本| L1[角色参考肖像 FLUX]
    L1 --> L2[角色镜头走 I2VA]
    L2 --> L3[尾帧链: 每镜从上镜末帧开始]
    L3 --> L4[cutaway 空镜藏漂移]
    L4 --> R(~80%一致 / 0训练成本)
    START -->|中/官方| M1[多参考图 ≤9 Ref2VA]
    M1 --> M2[retention 词汇表<br/>fully/partially/attribute/weak]
    M2 --> M3[Subject N 绑定图+角色<br/>首现全描述 后现短名]
    M3 --> R2(跨镜身份保持)
    START -->|重/漫剧连载| H1[Phosphene 角色LoRA]
    H1 --> H2[37张图 本地Gemma打标<br/>只写变化不写身份]
    H2 --> H3[face LoRA rank32/5000步<br/>+ voice LoRA]
    H3 --> H4[bundle.json 跨集复用<br/>prompt含trigger word]
    H4 --> R3(真锁脸跨集)
```

## 5. 回退阶梯（单镜失败/漂移）

```mermaid
flowchart TD
    F[clip 失败/漂移] --> R1[重试1: 强化prompt<br/>引用Reference Anchors]
    R1 -->|仍失败| R2[重试2: 缩镜≤6s<br/>被删秒拆相邻新行+重跑5.5]
    R2 -->|仍失败| R3[重试3: 该镜切另一模型<br/>H3↔Seedance]
    R3 -->|仍失败| R4{问用户}
    R4 -->|a| A1[只这镜切另一模型]
    R4 -->|b| A2[放宽需求<br/>删道具/简化动作/降钩子]
    R4 -->|c| A3[跳过+标placeholder]
    R4 -->|d| A4[手动供参考视频]
    D[clip 漂移偏离锚点] --> D1[强化prompt引用<br/>精确Reference Anchors重渲染]
    D1 -->|持续漂移| D2[该镜切另一模型混用<br/>不静默混进装配]
```

## 7. 人脸精修（FaceRefine，治 H3 小脸）

```mermaid
flowchart TD
    SRC[源 clip] --> TC[H3 Face Track+Crop<br/>crop_factor 2.5 / canvas 768<br/>smooth 21+51 gaussian<br/>identity_track 按身份选主体]
    TC -->|crops| INJ[H3 Inject Video Latent<br/>img2img: 真帧→视频流 latent<br/>音频流不动]
    TC -->|transform| PF
    TC -->|canvas_w/h| REF[MiniMaxH3ReferenceToVideo<br/>refs + 原 prompt]
    REF -->|av_latent| INJ
    VOC[分离人声] --> AL[MiniMaxH3NativeAudioLock<br/>音频流编码+noise_mask 视频1/音频0<br/>口型由此塑造]
    INJ --> AL
    TC -->|transform| PF[H3 Per-Frame Denoise<br/>小脸强(合成)/大脸轻(保留)<br/>strength 1.0/0.35 face_px 30/120]
    PF --> SAMP[SamplerCustomAdvanced<br/>BasicScheduler, 低denoise, 不用SplitSigmas]
    SAMP --> VAE[VAEDecode]
    VAE -->|refined_crops| ST[H3 Face Stitch Back<br/>只贴脸区+colour_match 1.0<br/>feather rect24/SAM4-8]
    SRC -->|base=原帧| ST
    OAO[原音频] --> SAVE[保存 final]
    ST --> SAVE
    NOTE[成本=canvas²×帧<br/>多人: 逐人串联 run1→run2 base]
```

## 8. 一致性检查（Jellyfish 全局字典法，纯 prompt 最稳）

```mermaid
flowchart LR
    SCRIPT[剧本] --> DIV[ScriptDivider<br/>→shots index]
    DIV --> EXTRACT[ElementExtractor<br/>全局实体字典<br/>characters/scenes/props/costumes]
    EXTRACT --> VAL{全集校验<br/>shots引用的name<br/>必须字典字面一致}
    VAL -->|缺失| ADD[补齐字典条目<br/>name完全一致]
    ADD --> VAL
    VAL -->|过| CAND[候选表<br/>pending→linked/ignored]
    CAND --> CONFIRM[人工确认]
    CONFIRM --> READY[shot.status=ready]
    READY --> GEN[生成: 已确认实体上下文<br/>作强输入 原样保留]
```
