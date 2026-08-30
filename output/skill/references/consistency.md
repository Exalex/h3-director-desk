# 一致性 / 不串戏（consistency）

## 轻量（零成本，~80%，2 天上手）
1. 角色参考肖像（FLUX/图生图）→ **角色镜头走 I2VA**（非 T2VA）。
2. **尾帧链**：每镜从上镜末帧开始（extract_last_frame → 下一镜参考图）。
3. **cutaway 藏漂移**：键盘/空镜/屏幕特写插在主镜之间，隐藏不可避免的漂移。
- 负面提示词：`morphing, flickering, distorted face, extra fingers, blurry, low quality, watermark, text overlay`

## 中量（官方 Ref2VA）
- 多参考图（≤9）+ **retention 词汇表**（`fully_preserved`/`partially_preserved`/`attribute_transfer`/`weak_reference`，逐字输出不重写）。
- `<Subject N>` 绑定图与角色；**首现全描述，后现短名**（`@refN` 替换 + seen 去重）。
- kind 说明句：`the shape, colour and markings of <Picture 2> are retained`。
- 图像 "used as"：frame anchor（默认）/ storyboard / defines a subject（不给 `<Picture N>`，在 `<Subject N>` 行内引用，且不再当关键帧）。

## 重量（Phosphene LoRA，漫剧/连载，真锁脸+锁声）
- 15-50 张图/角色（推荐 ~37）；本地 Gemma 3 12B 4-bit 打标，配方：
  > **只描述变化的部分**：姿态/构图/服装/场景/光线/机位/情绪。**不描述**面部/发色/年龄/族裔（LoRA 从像素吸收身份）。不写 trigger word 进描述。
- face LoRA：rank32/alpha32/5000 步/lr1e-4/576px（步数随 epochs×图数缩放：50图→5000步）；flow matching（shifted_logit_normal）；target to_q/k/v/out；**权重级融合**（lora_A×lora_B 乘加进基模型再量化，非运行时 adapter，换 LoRA 需重建管线）。
- voice LoRA：face 训完链式第二子进程，4s 切片配图像 latent，rank16/250 步。
- 产物：face `<trigger>_v2.safetensors` + voice `<trigger>.audio.safetensors` → `bundle.json`（名字/代词/face 强度/voice 强度/预览图），跨集复用；渲染 prompt **必含 trigger word**。
- 引擎分工：**H3 出对白镜头**（一句 prompt 出画面+台词+音效），**LTX-2.5+角色LoRA 出多镜锁脸叙事**；H3 单 LoRA 槽位（Turbo/用户二选一）。
- 坑：mlx==0.31.1 锁版（0.31.2 音频衰减 22dB）；H3 渲染前杀 LTX helper（40GiB 峰值）；Q4+character 服务端拒审。

## 通用（Jellyfish 强约束，纯 prompt 最稳）
**name-based 全局实体字典 + 精确字符串引用 + 全集校验**：
- 先输出全局字典（characters/scenes/props/costumes），再输出 shots；shots 引用的 name 必须与字典**完全一致**（全角/半角/空格/标点原样）。
- 禁止同义名/括号变体/临时称呼漂移；群体角色（"女子(群)"/"群众"）必须建同名条目；难以判定同一角色时宁拆两条不同 name 也不凭空换名。
- 输出前**全集校验**：shots 出现的所有名字都能在对应字典找到，缺失必须补齐（描述可最小化，name 必须一致）。
- 生成侧再锁：镜头帧提示词把**已确认实体上下文**（character/scene/prop/costume_context，角色含绑定演员形象+默认服装）作强输入，模板要求"已确认实体名原样保留，不得翻译/改名/替换同义词"。

## 资产分析范式（把弱描述升级成可生成描述）
"issues + 保守补全 optimized_description + 禁用模糊词 + 后置模糊句清洗"：
- 缺失维度（年龄/性别/外貌/服装/气质/标志特征/背景动机）保守补全，**不改变原文原意**。
- 禁用词：信息不详/未知/不明确/假设/比如/可以设想/类似/通常/可能/大概。
- 代码层兜底：发现 optimized_description 混入模糊句按句号切句剔除。
