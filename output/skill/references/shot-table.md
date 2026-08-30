# 标准分镜表 + 自检门（shot-table）

## 六列（严格此顺序）
表名 `标准镜头信息表` / `standard-shot-table`。

| 列 | 内容 |
|---|---|
| 1 Shot ID & Duration | 镜号+时长 `S03 / 6s`（≤15s） |
| 2 Continuity Handoff | 如何从上镜结尾图/道具位/视线/姿态/声音桥/情绪延续 + 如何布景下镜开场（跨镜脊柱） |
| 3 Reference Anchors（空间+身份） | 4 子字段全必填：Fixed Landmarks（场景卡具名地标+屏幕相对位置）/ Character Positions(camera view)（每角色屏幕位置+朝向+初始姿态）/ Exited Character Status（上镜在·本镜不在者的画外位置+原因）/ Lighting Baseline（继承 key/fill/rim + 逐镜修饰）+ 身份绑定（精确角色卡名+场景卡名） |
| 4 Hook Type | 受控词表：visual-joke / reversal / suspense / tender / chase / reveal / callback / expression-beat |
| 5 Shot Description（逐秒指令） | 景别/运镜/荷兰角/表演/SFX/负面 + 视频模型生成注 + **Per-Second Directives**（0-1s/1-2s/… 子秒 2.0-2.5s）；**每秒覆盖 5 要素**：①动作/姿态/表情 ②运镜 ③空间位置 ④音频 cue ⑤到下一秒/镜 handoff |
| 6 Audio & Dialogue Track | 时序完整音频脚本：Narration / Dialogue(台词+说话人+语气+时间) / SFX(时序锚定) / Performance Note(旁白时 narrator-mouth-closed: true) |

## 全表规则
- 每镜用 Continuity Handoff 继承上镜图像态、布景下镜。
- 逐秒指令要能直接生成分镜面板，避免"continues moving"这类无身体/机位/道具的模糊。
- 景别交替特写/大特写；荷兰角用于追逐/失衡/意外/滑稽。
- 对白语言仅用户明确要才用；含对白镜头，说话每秒记录嘴开/闭（画外旁白默认闭，画面对白默认开）。
- 离镜角色至少在 Exited Character Status 跟踪 1 镜，连续 2 镜画外后丢弃。

## 自检门（六条，强制；任一不过回 STEP5）
1. **钩子密度**：每镜有 Hook Type；每连续 3 镜至少 1 个 reveal/reversal/callback；首镜+尾镜各带强钩子。
2. **单镜时长**：无镜 >15s（超了拆）。
3. **单镜角色数**：无镜 >3 个重要角色（有画面动作或对白者）。
4. **空间锚继承**：同内景 ≥2 镜，下镜 Fixed Landmarks + Lighting Baseline 须匹配上镜或含显式连续性注。
5. **逐秒覆盖**：0s 到镜时长每秒都有 Per-Second Directives，每条含 5 要素，子秒不留空洞。
6. **跨镜连续**：逐行读 Continuity Handoff 成连续链；无镜起始态与上镜结尾矛盾；翻转视线/角色位置/道具态/光线须显式标注（如 `HARD CUT — time skip: 2h`）。

全过 → 打 `shot-table self-check: passed`。

## 门（choice-card）
- 表批准 → 跑自检（推荐）/ 调连续性 / 让动画更夸张 / 调特写节奏 / 调荷兰角
- 自检过 → 批准进分镜脚本（推荐）/ 看自检细节 / 修失败项 / 重跑自检
- 失败 → 不进 STEP6，回 STEP5 列失败行，修好且自检过才再显示批准卡。

## 分镜表行 → 管线输入 schema（可脚本化）
```python
{
  "shot_id": "S03", "duration_s": 6,
  "continuity": {"type": "hard_cut|latent_pin|motion_ref", "handoff": "...", "airlock_s": 2.0},
  "anchors": {"fixed_landmarks": [...], "char_positions": {...}, "exited": [...], "lighting": "..."},
  "hook_type": "reversal",
  "per_second": {"0-1s": {"action":"...","camera":"push","spatial":"...","audio":"...","handoff":"..."}, ...},
  "audio_track": {"narration": "...", "dialogue": [{"text":"...","speaker":"S1","tone":"...","time":"0-2s"}], "sfx": [...]},
  "video_model": "H3", "resolution": "768P",
  "first_frame": "S03_first.png", "last_frame": "S03_last.png",   # FL2VA
  "refs": [{"label":"<Subject 1>","kind":"person","retention":"fully_preserved","image":"char_A.png"}]
}
```
