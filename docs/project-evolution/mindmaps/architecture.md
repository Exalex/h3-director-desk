# 架构脑图

```mermaid
mindmap
  root((H3 Director Desk 架构))
    入口与参与者
      浏览器导演台
      CLI管线
      编导与制片人
    系统分层
      交互层
        index.html
        app.js
        项目库与集数导航
        中央项目画布
        右侧五步制作计划
        一句话自动创作入口
        工作流进度与最新日志
        时间戳生成事件
        稳定视频预览节点
        五阶段进度与ETA
      编排层
        serve.py
        后台任务注册表
      领域管线层
        data.py
        shot_table.py
        prompt.py
        series.py
        assemble.py
      资产层
        projects
        gen
        libraries
    外部集成
      ComfyUI
      ComfyUI /queue 任务观测
      可选加速服务
      可选LLM
      ffmpeg
    主执行流
      项目manifest
      集episode JSON
      集内素材与outputs
      六规则检查
      Prompt编译
      单镜或串联生成
      任务去重与状态轮询
      进度与日志观测
      ComfyUI事件回调
      队列状态探测
      Qwen规划
      资产清单写入
      每镜提示词编译
      QC与装配
    部署与运行边界
      本地Windows Web服务
      Windows watchdog 启动器
      Linux spark1部署
      ComfyUI独立运行
      模型权重外置
      5800H控制机与GPU推理机分离
```

## 组件职责与依赖

| 组件 | 职责 | 上游 | 下游 | 代码证据 |
|---|---|---|---|---|
| Director Desk | 组织 10 个阶段，提供项目编辑、任务和媒体预览 | 浏览器 | `serve.py` API | [`director/assets/app.js`](../../director/assets/app.js)、[`director/assets/panels.js`](../../director/assets/panels.js) |
| HTTP 编排层 | 静态文件、JSON API、后台长任务、生成任务去重 | 前端/CLI | 领域管线、文件系统、ComfyUI 队列 | [`director/serve.py`](../../director/serve.py) 的 `Handler`、`new_task`、`remote_generations` |
| H3 领域管线 | 校验分镜、编译提示词、生成和装配 | 项目 JSON | ComfyUI、ffmpeg、输出目录 | [`output/scripts/h3_short_drama/`](../../output/scripts/h3_short_drama/) |
| 项目资产 | 按项目/集保存 Bible、角色卡、场景卡、镜头和媒体 | 用户/管线 | JSON、图片、视频 | [`projects/`](../../projects/)、[`gen/`](../../gen/) |

## 主流程

1. 浏览器访问 `director/serve.py`，从 `projects/*/project.json` 构建项目库。
2. 选择项目中的 `episodes/*/episode.json`，工作台只加载当前集的 JSON 与素材。
3. 工作台创意输入进入后台 `chat_workflow`：Qwen 生成项目 JSON，随后写入资产清单、编译 prompts 并执行六规则检查。
4. 当前集也可单独进入 `check`、`prompts`、`plan` 等纯计算阶段。
5. 生成、串联、装配和自动创作作为后台任务执行，返回 task id。
6. 生成提交前同时核对导演台任务表和 ComfyUI `/queue`；前端轮询任务并定时刷新远端队列。
7. 结果落盘到当前集的 `outputs/`，再由 QC 和媒体接口读取。

## 架构约束

- JSON 是项目事实源；导演台任务状态保存在内存任务表中，远端 ComfyUI 队列作为生成去重和重启恢复的补充事实源。
- 有首帧/I2V 的镜头优先使用 ComfyUI；可选加速服务主要承担纯 T2V。
- 生成服务、模型权重、ffmpeg 和外部 LLM 不属于仓库内部部署内容。
- 自动创作只提交文本给 Qwen；资产图和视频生成仍是显式的后续操作。
- Windows 本地服务通过独立启动脚本监护 Python 进程；页面访问失败首先检查 8088 服务生命周期。
- 生成任务日志由 `task_append` 统一追加时间戳；ComfyUI 的排队、状态、瞬时轮询失败、下载和完成事件通过回调回传到导演台。
- 生成弹窗的状态轮询只更新任务文字和进度；当视频 URL 未变化时保留原有 `<video>` 节点，避免播放进度被重置。
- 生成进度按“准备、排队、GPU 生成、下载、完成”五个可观察阶段呈现；ComfyUI 不提供节点级百分比时，页面显示阶段估算并将剩余时间标为估算值。
