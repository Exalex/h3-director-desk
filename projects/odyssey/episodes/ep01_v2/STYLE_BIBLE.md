# 奥德赛 · 全局视觉与世界观圣经（Style Bible）

> 本系列所有分镜、角色卡、场景卡、提示词一律服从本文件。改这里 = 重生成下游全部，改前先警告。
> 剧集节奏：每集 ~10s（3-5 镜，单镜 2-3s 剪辑目标；H3 生成按 5s 留量、后期裁剪）。

## 1. 历史背景（硬约束）
- **迈锡尼文明时期（Mycenaean Greece，约公元前 1200 年）**，青铜时代晚期的黑暗质感。
- 建筑：巨石垒砌（cyclopean masonry）、粗木柱、土坯与石墙；**禁止古典时期元素**（雅典卫城式大理石柱廊、科林斯柱头、华丽神庙）。
- 器物：粗糙青铜器皿（goblet/kettle/toorc）、陶罐、木案、油灯；织物：粗布麻衣（undyed wool/linen）、兽皮；武器：青铜剑/矛。
- 社会：宫殿（palace）经济，王权衰落，求婚者霸占厅堂。

## 2. 电影参考
- 《特洛伊》(Troy, 2004) 的粗粝质感
- 《斯巴达300勇士》的暗黑与油画感
- 《北欧人》(The Northman) 的原始野性与低饱和冷色

## 3. 摄影风格关键词（写进每镜 prompt 的 Style 行）
- Cinematic lighting / chiaroscuro（明暗对比）
- shot on 35mm lens
- Gritty realism（粗粝写实）
- Volumetric smoke（体积烟雾/光柱）
- 暗调大地色低饱和调色、film grain、8k highly detailed

**全局 Style 行（ep 级复用，直接作为 project.visual_style）：**
```
Mycenaean Greece 1200 BC: cyclopean masonry, rough timber pillars, crude bronze vessels, coarse undyed linen and animal hides; gritty realism, cinematic epic, chiaroscuro cinematic lighting, shot on 35mm lens, volumetric smoke, dark earthy low-saturation palette, film grain; reference: Troy (2004) texture, 300 dark oil-painting mood, The Northman primal rawness; no classical marble, no ornate temple architecture
```

## 3.5 ⚡ 当前系列风格 v2（2026-08-19 起，覆盖 §3 电影摄影风）
> §3 的写实电影风保留为历史参考（v1 EP01 已用）。**v2 起全系列 = 写实漫画风**。
- 核心词：**Realistic graphic novel style, dark fantasy comic, heavy ink shadows, crosshatching, detailed line work, deep black shadows, high contrast cinematic lighting (chiaroscuro), gritty comic book art, muted dark palette**
- 历史背景约束不变（§1 迈锡尼 1200BC，禁古典大理石）——时代不变，只换渲染风格。
- 全局 Style 行（v2，project.visual_style 直接用）：
```
Realistic graphic novel style, dark fantasy comic: heavy ink shadows, crosshatching, detailed line work, deep black shadows, high contrast cinematic lighting, chiaroscuro, gritty comic book art, muted dark palette; Mycenaean Greece 1200 BC setting: cyclopean masonry, rough timber pillars, crude bronze vessels, coarse undyed linen and animal hides; 8k highly detailed
```
- 角色卡必须与风格同源（v2 卡 = 漫画风肖像，见 cards_v2.json）；风格再变 = 全卡重做。

## 3.6 ⚡ EP04 风格 override（2026-08-19：女仙岛集 = 实拍真人风）
> 用户指令（EP04）："要用真人画风，不要有一点动画的感觉"——该集整体切回**实拍电影质感**（§3 系），
> 漫画/插画措辞（graphic novel / ink / comic / panel / crosshatch）一律不得进 EP04 任何 prompt。
- 全局 Style 行（EP04 专用，project.visual_style 直接用）：
```
Cinematic photorealistic live-action film still: hyperrealistic skin texture, visible scar detail, volumetric storm light and sea spray, natural motion blur, muted desaturated teal-and-amber cinematic palette, subtle film grain; ancient Mediterranean island c.1200 BC: basalt cliffs, primitive grotto, bronze-age tools; absolutely no illustration, no comic ink lines, no crosshatching, no panel borders; 8k highly detailed
```
- **风格是按集切换的**：每个 ep 的 visual_style + 该集角色卡必须同风格。跨风格出镜 = 卡重做。
  EP04 新角色卡（实拍风）= gen/odyssey_ep04/card_*.png；若后续漫画风集要出奥德修斯，需重做漫画风卡。
- EP04 镜头 prompt 前置实拍锚点（T2V 防漂移规则 §7.6 的实拍版）：
  `Live-action cinematic film still: photorealistic, no comic style, no ink lines, no panel borders.`

## 4. 角色圣经（身份锁：卡片 + 固定 seed，跨集不变）
| 角色 | 定位 | 视觉锚点（do-not-change） | 卡片文件（当前 v2 漫画风） | 固定 seed |
|---|---|---|---|---|
| Telemachus 忒勒玛科斯 | 主角，奥德修斯之子，~19岁 | 瘦削、短乱深褐发、锐利下颌、深色粗羊毛短衣、左腕细铜臂环 | gen/odyssey_ep01_v2/card_Telemachus.png | 70001 |
| Penelope 佩涅罗珀 | 王后，~34岁 | 椭圆脸、深发、**素色面纱覆头**、高挑沉静、素色灰白亚麻长袍、素铜颈环 | gen/odyssey_ep01_v2/card_Penelope.png | 70002 |
| Antinous 安提诺斯（求婚者首领） | 反派，~32岁 | **肌肉发达、满脸横肉**、油亮浓黑须、后梳黑发、残忍狂笑、厚重青铜颈环+大戒指、扎染红衣罩毛皮 | gen/odyssey_ep01_v2/card_Antinous.png | 70003 |
| Odysseus 奥德修斯 | 主角，~45岁（漂泊20年后） | 枯槁战疤脸、浓密蓬乱深褐须、深陷疲惫深色眼、日晒古铜皮、赤膊旧疤、粗麻破布 | gen/odyssey_ep04/card_Odysseus.png（实拍风） | 70004 |
| Calypso 卡吕普索（女仙） | 仙女，不老 | 金色长卷发、莹润摄魂眼、半透明金色金纱袍、发间微光花 | gen/odyssey_ep04/card_Calypso.png（实拍风） | 70005 |
| Hermes 赫尔墨斯（神使） | 神使，~25岁 | 短金卷发+小型银翼盔、翼凉鞋、双蛇银杖、蓝白金边短袍 | gen/odyssey_ep04/card_Hermes.png（实拍风） | 70006 |

> 卡片文件 = **该角色在当前系列风格下的卡**（v2 漫画卡见上表；EP04 实拍卡为独立一套）。
> v1 写实风卡片存档于 gen/odyssey_ep01/（仅对照/回退用，勿再进 v2+ 镜头）。
> 风格切换时：seed 不变，卡按新风格重做。

规则：
- 任何出现该角色的镜头 = **I2VA**，first_frame = 该角色卡片（硬切入），`fully_preserved` 参考绑定。
- 同角色全片同 seed（上表），禁止随机重抽。
- 群演（求婚者众人）不锁脸，只做氛围；如需锁某配角 → 先立卡再出镜。

## 5. 场景圣经
### 迈锡尼大厅（Mycenaean Megaron）— 本系列主场景
- 巨厅：巨石垒墙、粗木柱、中央火塘、兽皮铺地、烟雾缭绕、夜晚。
- 固定地标（跨镜继承）：`central-hearth: center` / `wooden-pillars: left & right edges` / `stone-wall: background` / `animal-skins: floor`
- 光基线：火塘主光（暖橙）+ 体积烟 + 深阴影；月光镜（如 S04）= 冷月光主光 + 下方火光辉映。
- 场景卡：projects/odyssey/assets/megaron.png（从 EP01 S01 抽帧，生成后补）

## 6. 音频圣经（H3 原生音画同步，逐镜 diegetic SFX）
- 每镜 sfx 写进 shot.sfx（H3 会随画面生成）：火噼啪、兽骨碰撞、铜杯叮当、烤肉滋滋、狂笑、闷喘、夜风、低频 drone。
- **不逐镜 BGM**；BGM 在剪辑软件里统一铺（粗犷古希腊里拉琴 Lyre 拨弦 + 男声合唱低吟），对白/关键 SFX 处 duck。
- 每集结尾 2 秒：切沉重环境音（低频 drone + 远处火光 + 风），史诗感收尾。

## 7. 系列一致性铁律（几百个分镜不跑偏的 5 条）
1. 角色镜必 I2VA 锁卡 + 定 seed；尾帧链只用于同主体延续镜头，不同角色之间一律硬切。
2. 同场景连续镜继承地标 + 光基线（分镜表 check 规则 4 自动校验）。
3. 每镜逐秒指令 5 要素无空洞（check 规则 5 自动校验）。
4. 风格漂移 → 先改 Style 行重跑，不许单镜私改。
5. 小脸糊 → FaceRefine 逐帧救；跨集漂移 → 卡片重抽后全下游重生成（先警告）。
6. **T2V 镜头防风格漂移**（EP01 v2 实证：无卡 T2V 宽景易漂成"亮色数字插画"）：
   凡 T2V 镜头，shot_description 开头必须前置强化风格锚点——
   `Dark comic ink illustration: heavy ink shadows, crosshatched shading, deep black shadows, muted desaturated dark palette, no vibrant colors, no clean digital look.`
   全局 Style 行只算底线，不够。

## 8. 技术基线（EP01 实证）
- 服务器：http://192.168.3.153:8188（ComfyUI 0.31.0 / GB10 130GB / minimax_h3_fl2va_pruned_fp8_scaled）
- 画布 480×832（9:16 竖屏短剧），24fps，帧数 17k+5（5s=124f），20 steps，cfg=1.0 euler
- 生成 5s → 剪辑裁剪到 edit_target_s（3/2/3/2）→ concat 硬切 → 10s 整集
- 角色卡 = H3 肖像 T2V 124f → 抽 2.4s 帧（中间帧最稳）
