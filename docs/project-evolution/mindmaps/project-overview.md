# 项目总览脑图

```mermaid
mindmap
  root((H3 Director Desk))
    项目目标
      H3短剧生产工作台
      结构化输入到成片
    用户与参与者
      编导与制片人
      本地开发者
      ComfyUI与LLM服务
    核心能力
      项目优先工作台
      项目内集数切换
      集级素材隔离
      五步制作计划
      分镜六规则门禁
      H3提示词编译
      异步生成与QC
      生成任务状态回显
      时间戳阶段日志
      ComfyUI队列与下载事件
      轮询期间稳定视频预览
      ComfyUI远端队列去重
      镜头级进度与后台日志
      本集总进度汇总
      镜头完成后直接视频预览
      工作台一句话自动创作
      自动资产规划与提示词编译
      尾帧链与成片装配
    系统边界
      仓库内源码与项目资产
      外部模型与推理服务
      ffmpeg运行时
    当前阶段
      5800H本地导演台可运行
      项目与集数层级已接入
      Qwen规划任务可观测
      ComfyUI作为外部H3推理服务
      生成任务支持重开窗口后恢复状态
```

## 项目事实

| 项目 | 内容 | 证据 |
|---|---|---|
| 目标 | 将短剧创作到视频装配组织成可执行闭环 | [`README.md`](../../README.md)、[`director/README.md`](../../director/README.md) |
| 主要用户 | 编导/制片人和需要复用 H3 管线的开发者 | 导演台界面与 CLI 入口 |
| 核心能力 | 项目/集数工作台、分镜门禁、Prompt 编译、生成、QC、装配、任务状态回显与去重 | [`director/assets/app.js`](../../director/assets/app.js)、[`director/serve.py`](../../director/serve.py) |
| 非目标 | 不包含模型权重、ComfyUI 本体和自动化部署平台 | 运行环境说明与外部依赖 |

## 阅读提示

先阅读本页和 [`docs/PROJECT_ANALYSIS.md`](../../PROJECT_ANALYSIS.md)，再查看架构图和技术实现图。仓库事实以源码、配置和已执行命令为准。
