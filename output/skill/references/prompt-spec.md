# H3 提示词规范（prompt-spec）

## 图片对齐指令（有图才写；I2VA/FL2VA/L2VA 的第一行，后空一行）
- **I2VA**：`For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced.`
- **FL2VA**：`How the reference pictures align with the target video — Picture 1 (from Shot 1) aligns with the 0.00-second mark of the target video; Picture 2 (from Shot N) aligns with the S.SS-second mark of the target video.`
- **L2VA**：`How the reference pictures align with the target video — <Picture 1> (from [Shot N]) aligns with the S.SS-second mark of the target video.`

## 运镜公式：类型 + 幅度 + 速度
类型（Zoom/Push/Pull/Pan/Truck/Tilt/Pedestal/Arc/Tracking/Static/Shake/POV/Roll）+ 幅度（`with small amplitude`/`with large amplitude`）+ 速度（`at slow speed`/`at fast speed`）。写成自然句，不堆标签：`The camera pushes in with small amplitude at slow speed toward the folded letter in her hands.`

## 口型规则（lip-sync）
**台词长短要和镜头长短对齐**（口型问题大多出在这）；3 秒镜头别说一大段话。跨 shot 台词写"接着上个 shot 继续说"（J-cut/L-cut）。

## Shot 与时间戳
`[Shot 1]` 不带时间戳；后续 `[Shot N] At MM:SS.mmm`，时间严格递增且在时长内。普通切镜用 `the camera cuts to / the shot transitions to`；仅用户明确要才用 cross-dissolve/fade/wipe。切镜要带来新信息；仅距离/角度微调优先用运镜而非切镜。

## 输出规则（全局）
- 重写部分用英文；**对白/歌词/可见场景文字保留原语言**。
- 每镜按 构图/主体/环境/动作/运镜/声音/参考内容出现的确切点 描述。
- 避免剧情梗概、未解析的参考标签、与请求时长不匹配的时间线。
- 总时长严格匹配请求（4-15s）。
- 参考标签全程一致（`<Picture 1>`/`<Video 1>`/`<Audio 1>`）。
- 优先具体视听细节，拒绝"cinematic/beautiful"这类抽象词。

## 5 模式锚点（严格）
| 输入 | 模式 | 规则 |
|---|---|---|
| 纯文字 | T2VA | 从开场态建完整音画时间线 |
| 首帧图 | I2VA | `<Picture 1>` 锚 0.00，保留身份+构图，向前（它是真实首帧非灵感） |
| 首+尾图 | FL2VA | 描述两态间**连续物理路径**（单镜更可靠；别写两张静态图） |
| 尾帧图 | L2VA | 推断早先态，收敛到尾帧（尾帧属最后镜非 Shot1） |
| 图/视频/音频参考 | Ref2VA | 先定义参考角色+retention，再写时间线 |

## Base 三段（T2VA/I2VA/FL2VA/L2VA）
```
integrated_multimodal_description:
[Shot 1] Cinematic, medium wide, pushing in slowly. <角色/服装/动作/环境/光线/时间标记>
[Shot 2] At 00:04.500, the camera cuts to ...
overall_soundscape: <现场音/物理音/音频动态(渐强/骤静)>
non_diegetic_music: <配器/节奏情绪/动态>   # 空写 N/A
```

## Ref2VA 六段（顺序固定）
```
subject_definitions:
<Subject 1> is [ref图描述].
<Video 1> is the source video for the editing task.
<Audio 1> is [音频描述].
summary: [任务类型] 目标视频 [发生什么]
retention_analysis:
<Subject 1>: fully_preserved - [保留什么]
detailed_description: [完整场景, 对白用 <d> 标签]
overall_soundscape: [音频]
non_diegetic_music: [音乐]
```

## 标签
`<Subject N>` 可复用人/物/环境/风格/动作/姿态；`<Picture N>` 具体图/关键帧；`<Video N>` 源视频/续写源/时序；`<Audio N>` 拷贝/参考音频。同资产可多角色但独立编号。仅"真·帧/分镜锚"才给 `<Picture N>`；只用于定义主体的图**不**给 `<Picture N>`（在 `<Subject N>` 行内引用）。

## retention 词汇（逐字输出，永不改写）
- 视觉：`fully_preserved` / `partially_preserved` / `attribute_transfer` / `weak_reference`
- 音频：`fully_copy` / `partially_copy` / `reference` / `weak_reference`
- 示例：`<Subject 2> (appears in [Shot 1],[Shot 2]): fully_preserved - the Samoyed's thick white fur, pointed ears, dark nose, curved tail are retained.`
- 音色可作 reference（不拷波形）；BGM 可 partially_copy 垫在新台词下。

## 对白（一等目标）
- 官方：`<d>[Chinese] 台词</d>`；跨cut/截断用 `<scenetrans>`（跨cut两端都加）/ `<cutoff>`（结尾被截断）。
- 稳定 speaker ID + 精确文本；说话顺序跨全时间线分配 `(S1)(S2)`，同一人保持同 ID，**不写进 retention_analysis**；多人同说用 `(S1,S2)`；不发声角色不编号；首现给足身份（角色类型/年龄/性别/画内外/音色/语速/口音）。
- **画外音**：`says in an off-screen voiceover: <d>...</d>`，后必须写嘴巴不动（`lips remain completely closed`）。
- **冒号=对白，引号≠对白**：
  - `@ref1 says "hello"` → 旁白（无 speaker ID 无 `<d>`）
  - `@ref1 says: hello` → `<Subject 1> (S1) says, <d>[English] hello</d>`
- 台词留在写的位置（不甩镜尾）；`</d>` 闭合后直接续字不加句点。
- 短对白测试 7 要素：谁说话面向哪 / 嗓音质感语速语言 / 精确词+顺序 / 轮间停顿反应 / 说话后嘴身反应 / 房间底噪 / 音乐是否现场音。

## 电影化写法
- 先立身份/服装/位置/环境/光/初态，再写运动。
- 每个动作给可见状态变化+后果。
- 焦点变化：同时说谁出谁进。
- 说话结束：写嘴/颌回到非说话态（助音画时序）。
- 音随因：门先关再锁咔哒；引擎先蓄能再震感/撞击。
- 音乐写配器/节奏/织体/动态，别只写"情绪化电影配乐"。

## 8 项提交前清单
1 模式+参考锚对  2 每主体一稳定身份  3 首尾帧规则匹配模式  4 每 cut 加信息或用动机化运镜  5 对白精确有序绑稳定 speaker  6 现场音/环境音/非现场音乐分离  7 retention+音频角色显式  8 时长/FPS/分辨率/硬件兼容。**结果要目视+听验证，不从 prompt 推断。**

## H3 前缀（逐镜渲染时，分镜表→视频模型）
- H3（默认）：强调 packaging/设计语言/motion clarity/双声道音意图，per-second 指令近乎原样送。加：`Pixar-inspired 3D cartoon rendering, C4D + Octane look, stylized Q-version proportions, warm SSS skin, strong character design language, clean motion`（按题材调）。
- Seedance（回退）：强调电影机位/弹性 squash-and-stretch/anticipation/follow-through/布光戏剧性/镜头焦段。
