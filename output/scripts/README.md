# H3 短剧管线 · 脚本

可执行 Python 包（纯标准库，无第三方依赖；ffmpeg 作为可选子命令）。
把「标准分镜表」编译成 H3 规范提示词、跑 6 条自检、规划硬件 profile、装配成片、调用 provider（无 key 时 dry-run 打印 payload）。

## 运行
```powershell
cd output/scripts
python -m h3_short_drama <cmd> ...
```

## 命令
| 命令 | 作用 |
|---|---|
| `concept --idea "..." [--genre G] [--feeling F] [--execute]` | 一句话点子 → 15 字段概念（LLM dry-run 安全） |
| `storyboard --idea "..." [--aspect 9:16] [--duration 45] [--out P.json] [--execute]` | 点子 → 标准分镜表 JSON（3-6 镜，含 6 列 + 逐秒指令 + 对白 + 参考绑定） |
| `lock --shots P.json [--base-seed N] [--out L.json]` | **抽卡定卡**：把"随机人物"锁成"固定角色"——每镜升 I2VA + first_frame=该镜主角角色卡 + 逐角色固定 seed + `fully_preserved` 参考 + 校验无 T2VA |
| `advance --shots P.json` | **推进剧情**：打印剧情推进脊（每镜 建立→推进→交接→钩子→下一镜开场）+ 校验因果链/气闸/结尾钩子 |
| `check --shots P.json` | 跑 6 条分镜表自检（钩子密度/≤15s/≤3角色/空间继承/逐秒覆盖/跨镜连续） |
| `prompts --shots P.json [--out DIR]` | 每镜编译成 H3 提示词（3段/Ref2VA 6段，speaker ID，`<d>`对白，retention） |
| `plan --vram N --aspect 9:16 --seconds S [--quality fast] [--face]` | 硬件感知 profile（画布/帧网格/步数/cache/offload/turbo） |
| `assemble --clips a.mp4 b.mp4 ... --out F [--bgm B] [--sub S.srt] [--execute]` | ffmpeg 装配（normalize+xfade+BGM duck+字幕；32kHz 安全；已用真 clip 验证） |
| `run --shots P.json` | 全流程 dry-run（check + prompts + provider specs） |

> 端到端闭环：`storyboard`(LLM 生成分镜表) → `lock`(抽卡定卡) → `check`(自检) → `prompts`(H3 提示词) → 生成 clip → `assemble`(成片)。

## 抽卡定卡（lock，核心）
随机人物来自 3 个杠杆：**纯文生 T2VA(无参考) / 随机 seed / 参考图没锁**。`lock` 一次锁住：
- 每角色镜头 **I2VA**（first_frame = 该镜主角角色卡）；
- **逐角色固定 seed**（同角色全片同 seed = 定卡）；
- **`fully_preserved` 参考**绑定（跨镜身份）；
- 校验：任何角色镜若是 T2VA / I2VA 无 first_frame / Ref2VA 无参考 → FAIL。
配合：尾帧链（上镜尾帧→下镜首帧）+ 中远景小脸 FaceRefine + 连载 Phosphene LoRA。

## 示例
```powershell
python -m h3_short_drama check --shots h3_short_drama/examples/sample_project.json
python -m h3_short_drama prompts --shots h3_short_drama/examples/sample_project.json
python -m h3_short_drama plan --vram 8 --aspect 9:16 --seconds 5 --quality fast
python -m h3_short_drama run --shots h3_short_drama/examples/sample_project.json
```

## 环境变量（provider，可选；缺省走 dry-run）
- `OPENAI_API_KEY` → OpenAI Videos
- `VOLC_API_KEY` → 火山方舟（三帧同传）
- `MINIMAX_API_KEY` → MiniMax Context-IR / Regenerate-2K

## 数据 schema（examples/sample_project.json）
`Project{ title, aspect, duration_s, dialogue_mode, dialogue_language, visual_style,
  characters[], scenes[], shots[] }`
`Shot{ shot_id, duration_s, continuity_handoff, fixed_landmarks[], char_positions{},
  lighting_baseline, hook_type, shot_description, per_second[{rng,action,camera,spatial,audio,handoff}],
  dialogue[{text,speaker_id,tone,time_range,is_diegetic}], sfx[], mode, video_model, resolution_tier,
  aspect, references[{label,kind,char,retention,retention_note,path,description}],
  first_frame, last_frame, negative, continuity_type, airlock_s }`

## 关键安全规则（内置）
- 画布 32 对齐；输出帧 17k+5；音频 32kHz（装配不硬编 48k）；对白/链式镜头建议关 Turbo/Spectrum。
- 对白冒号规则：diegetic 行 → `<label> (Sx) says, <d>[Lang] text</d>`；旁白 → narration(mouth closed)。
- speaker ID 按全时间线说话顺序分配（S1,S2...），不进 retention_analysis。
