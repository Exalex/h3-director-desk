# 项目总览脑图

```mermaid
mindmap
  root((aiDirector))
    项目目标
      H3短剧生产工作台
      结构化输入到成片
    用户与参与者
      编导与制片人
      本地开发者
      ComfyUI与LLM服务
    核心能力
      十阶段导演台
      分镜六规则门禁
      H3提示词编译
      异步生成与QC
      尾帧链与成片装配
    系统边界
      仓库内源码与项目资产
      外部模型与推理服务
      ffmpeg运行时
    当前阶段
      文档与GitHub基线
      Odyssey示例已验证
```

## 项目事实

| 项目 | 内容 | 证据 |
|---|---|---|
| 目标 | 将短剧创作到视频装配组织成可执行闭环 | [`README.md`](../../README.md)、[`director/README.md`](../../director/README.md) |
| 主要用户 | 编导/制片人和需要复用 H3 管线的开发者 | 导演台界面与 CLI 入口 |
| 核心能力 | 项目 JSON、分镜门禁、Prompt 编译、生成、QC、装配 | [`director/serve.py`](../../director/serve.py)、`output/scripts/h3_short_drama/` |
| 非目标 | 不包含模型权重、ComfyUI 本体和自动化部署平台 | 运行环境说明与外部依赖 |

## 阅读提示

先阅读本页和 [`docs/PROJECT_ANALYSIS.md`](../../PROJECT_ANALYSIS.md)，再查看架构图和技术实现图。仓库事实以源码、配置和已执行命令为准。
