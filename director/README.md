# 🎬 导演台 Director Desk — H3 短剧全流程控制台

把一条 H3 短剧制作项目（剧本 → 分镜 → 角色卡 → 分解 → 自检 → 生成 → 质检 → 成片）
封装成本地 Web 导演台。**用编导/制片人的视角**组织成 10 个可控制环节，
每个环节都可在浏览器里执行、预览、调参。纯 stdlib，零第三方依赖，稳定跑通。

## 启动

```bash
python director/serve.py --port 8088                 # 默认 ComfyUI: 192.168.3.153:8188
# 或指定 ComfyUI:  python director/serve.py --port 8088 --comfy http://127.0.0.1:8188
```
打开浏览器 → http://127.0.0.1:8088/

Windows 双击 `start_director.bat` 亦可。

## 界面结构（项目入口 + 集数工作台）

- **左栏 · 项目库**：项目是最主要入口；展开项目后显示它自己的集数列表。项目或集数切换后，中央画布、右侧计划、资产引用和生成目录全部绑定到新的工作空间。
- **中栏 · 项目画布**：展示当前集的简案、资产参考和分镜卡片，点击分镜可选中镜头。
- **右栏 · 制作计划**：按「制作简案 → 资产 → 分镜图 → 视频生成 → 后期合成」推进，状态来自当前集的真实 JSON、素材和产物扫描。

## 新建项目（三种方式）

点左栏底部「＋ 新建项目」，填入项目名后三选一：

1. **① 空白模板（手填）**：生成一集带齐全字段的空白分镜（N 个占位镜头），在各环节手动填写，配"自检"给待办引导。不依赖任何 key，立即可用。
2. **② 用示例导入**：复制奥德赛 ep01 的 4 镜结构作为起步，改角色/场景即可。
3. **③ AI 自动生成**：输入一句话点子 → 后端调用 OpenAI 兼容 LLM 自动生成整集分镜 JSON。需要配置环境变量 `OPENAI_API_KEY`（或 `DEEPSEEK_API_KEY`，可选 `OPENAI_BASE_URL`/`LLM_MODEL`）；未配置时前端会清晰提示，不崩。

## 💬 对话式迭代（核心工作流：你不用填字段，只提意见）

左栏顶部「💬 对话式迭代」按钮打开一个聊天窗。这是全自动的"导演×编剧"轮换：

- **第 1 轮**：把语料 / 背景 / 风格粘进输入框发送 → AI 基于它生成一集短剧的完整分镜骨架（含逐秒指令）。
- **之后每一轮**：直接在对话框里说"哪里有问题"（如 *第3镜太慢，把反派改阴郁些*、*加一镜打脸*）→ AI 自动改好并保存，导演台各环节实时刷新。
- 你只需要**指出问题**，AI 负责改；一轮一轮迭代到满意。
- 后端接口 `POST /api/chat/iter`（mode=iterate，基于当前项目 JSON + 反馈 → 返回改后完整 JSON 落盘）。需 LLM key（同 AI 生成），无 key 时友好提示不崩。

## ⚡ 加速服务（spark2 :8123，可选第二种生成后端）

现有 ComfyUI 流程**完全不变**，额外提供一台局域网加速推理服务：

- `http://192.168.100.11:8123`：常驻模型、Sol-Attn + FirstBlockCache + VAE 批处理加速（约 2.3×），返回 URL 直出下载（带音轨）。
- **生成环节**新增「生成后端」下拉：`ComfyUI（原）` / `加速服务 8123`；部署环节新增加速服务在线状态面板。
- **如何选择（编导视角）**：加速服务是**纯文生图（T2V）**，没有图像/首帧输入参数。所以——
  - 纯 T2V 镜头（如第一镜建场景）在加速模式下使用加速服务，提速明显；
  - **带角色卡首帧的 I2V 镜头会自动回退到 ComfyUI**，以保住"角色身份锁定"（不会因改后端而丢一致性）。
- 加速服务离线时：生成下拉自动禁用/不可选，页面明确提示，ComfyUI 流程不受影响。
- 配置：后端环境变量 `ACCEL_BASE`（默认 `http://192.168.100.11:8123`）。
- 长任务契约：`POST /generate` → `{ok,video:"/videos/h3_x.mp4",seconds}` → 下载 `/videos/<f>`；`/health` 健康检查。

## 可视化编辑（不碰 JSON 也能做）

- **① 设定 Bible**：直接在面板填剧名/画幅/时长/对白/概念/感受/视觉风格，点「💾 保存设定」。
- **② 分镜表**：每镜点「✎ 编辑」打开表单——改画面描述/时长/剪辑秒/mode/钩子/seed/首帧/跨镜衔接/对白/SFX，并逐秒增删改 5 要素（动作/机位/空间/声音/衔接）；「＋ 新增镜头」「删除本镜」。
- 所有编辑即时落盘到 `projects/<name>/episodes/<episode>/episode.json`；每一集自己的 `assets/`、
  `references/`、`prompts/` 和 `outputs/` 与其他集数、项目隔离。
- 后端增量接口：`POST /api/stage/patch`（field=shots|characters|scenes|meta 局部替换）、`POST /api/stage/save_project`（整项目保存）。
- **中栏 · 导演工作区**：当前环节的控制面板（执行按钮 + 参数 + 实时结果）。
- **右栏 · 导演监视器**：常驻的成品预览 + 角色卡 / 场景卡 / 分镜 / 后台任务 四个监视页签。

## 10 个环节

| # | 环节 | 前端控制 |
|---|------|----------|
| 01 | 设定 Bible | 项目概念 / 感受 / 视觉风格 / 制作流程总览 |
| 02 | 分镜表 Board | 逐镜卡片：景别、方式、时长、角色、逐秒 5 要素指令、对白、SFX |
| 03 | 自检 Check | 一键跑 6 条分镜硬规则门禁（PASS/FAIL 红绿灯） |
| 04 | 角色卡 Cards | 定卡缩略图 + do_not_change 身份锁定规则 |
| 05 | 场景卡 Scene | 场景空间锚点 + 地标/光线 |
| 06 | 提示词 Prompts | 逐镜编译 H3 规范提示词（含逐秒块/对白/音景），可落盘 |
| 07 | 部署 ComfyUI | 服务在线/显存/GPU 状态 + 时长规划 |
| 08 | 生成 Generate | 逐镜或整集提交 ComfyUI 长任务，实时轮询进度，参数可控（宽/高/steps/seed/首帧） |
| 09 | 质检 QC | 列出成片抽帧 QC 资产 |
| 10 | 成片 Assemble | 按 edit_target 裁剪 → 硬切 concat → 可选 BGM → 成片播放 |

## 后端 API（serve.py）

| 端点 | 作用 |
|------|------|
| `GET /api/director?path=` | 导演台总览：项目摘要 + Comfy 在线状态 |
| `GET /api/projects` `GET /api/project?path=` | 列项目 / 读项目 JSON |
| `GET /api/stage/check` | 6 规则自检 |
| `GET /api/stage/prompts[&out=]` | 编译提示词（可落盘） |
| `GET /api/stage/plan` | 显存/时长规划 |
| `GET /api/hardware` | ComfyUI 状态探测 |
| `GET /api/files?path=` | 列出目录媒体资产 |
| `GET /api/stage/qc` | 质检帧列表 |
| `POST /api/stage/generate` | 提交单镜生成（长任务；`backend=comfy|accel` 选生成后端，accel 下 I2V 镜头自动回退 Comfy） |
| `POST /api/stage/series` | 提交整集尾帧链生成（长任务） |
| `POST /api/stage/assemble` | 装配成片（hardcut 硬切 / xfade 转场 + BGM） |
| `POST /api/project/new` | 新建项目（template=blank/example，建独立目录+写 project.json） |
| `POST /api/project/ai_storyboard` | 用 LLM 从点子生成整集分镜（需 key） |
| `POST /api/chat/iter` | 对话式逐轮迭代（反馈 → AI 改 → 落盘；需 LLM key） |
| `POST /api/stage/save_project` | 保存/覆盖项目 JSON |
| `GET /api/task/<id>` `GET /api/tasks` | 后台长任务状态 / 列表 |
| `GET /api/media?path=` | 代理读取图片/视频（含 Range 支持，可拖进度条） |

长任务一律后台线程 + task id + 前端轮询，绝不在 HTTP 请求里同步阻塞；
ComfyUI 生成需要目标服务器在线（130GB 显存 GB10 实测通过）。

## 目录

```
director/
  serve.py            # 后端：纯 stdlib HTTP + 管线封装
  index.html          # 前端壳
  assets/
    style.css         # 浅色项目画布与三栏工作台
    app.js            # 项目/集数状态、工作台渲染、任务轮询
    panels.js         # 旧版流程面板（保留作兼容参考）
docs/h3_pipeline_api_contract.md   # 管线 API 契约（subagent 产出）
start_director.bat    # 一键启动
```

## 验证状态

- ✅ 全 API 端点 200（含 director/projects/project/check/prompts/hardware/files/qc/media/tasks）
- ✅ 静态三件套伺服正常
- ✅ **装配真实跑通**：4 段 trim 硬切 concat → EP01_desk_pilot.mp4（10.08s / 480×832 / h264 / aac 32k / 1.5MB）
- ✅ **生成真实链路**：S02 I2V（Antinous 卡 → first_frame 上传 → 480×832×124f seed 70003）已提交到 ComfyUI 后台轮询完成

## 参考项目借鉴

- **Jellyfish**（端到端短剧平台）：状态驱动的单 CTA 导航、三层状态分离、三栏导演工作台、全局异步任务中心。
- **ComfyUI-MiniMaxH3-Director**：时间轴分镜表、subject/retention 引用管理。
- 管线数据模型与生成参数完全复用 `output/scripts/h3_short_drama` 已验证的 H3 打法定稿。
