# h3-director-desk · 项目演进文档

> 这里记录项目当前结构、技术实现、决策依据和不可丢失的迭代历史。

- 文档更新时间：`2026-09-01T21:23:39+08:00`
- 当前迭代：`I-0023 · 修正完成任务进度显示 / completed`

## 建议阅读顺序

1. [项目总览脑图](mindmaps/project-overview.md)
2. [架构脑图](mindmaps/architecture.md)
3. [技术实现脑图](mindmaps/technical-implementation.md)
4. [仓库结构脑图](mindmaps/repository-structure.md)
5. [迭代脑图](mindmaps/iterations.md)
6. [仓库事实快照](evidence/repository-snapshot.md)

## 最近迭代

- [I-0023 · 修正完成任务进度显示](iterations/I-0023-修正完成任务进度显示.md) — 2026-09-01 / `completed`
- [I-0022 · 生成任务五阶段进度与默认日志](iterations/I-0022-生成任务五阶段进度与默认日志.md) — 2026-09-01 / `completed`
- [I-0021 · 详细生成日志与视频播放稳定性](iterations/I-0021-详细生成日志与视频播放稳定性.md) — 2026-09-01 / `completed`
- [I-0020 · 稳定 Windows 导演台服务启动](iterations/I-0020-稳定-windows-导演台服务启动.md) — 2026-09-01 / `completed`
- [I-0019 · 修复成片预览分段播放](iterations/I-0019-修复成片预览分段播放.md) — 2026-09-01 / `completed`
- [I-0018 · 工作台一句话自动创作流程](iterations/I-0018-工作台一句话自动创作流程.md) — 2026-09-01 / `completed`
- [I-0017 · 在生成镜头下提供可点击视频预览](iterations/I-0017-在生成镜头下提供可点击视频预览.md) — 2026-09-01 / `completed`
- [I-0016 · 增加整集生成总进度并恢复本地导演台服务](iterations/I-0016-增加整集生成总进度并恢复本地导演台服务.md) — 2026-09-01 / `completed`

## 最近决策

- [ADR-0008 · 生成进度按可观察阶段展示并标注估算](decisions/ADR-0008-生成进度按可观察阶段展示并标注估算.md) — `accepted`
- [ADR-0007 · 生成状态轮询保持视频播放状态](decisions/ADR-0007-生成状态轮询保持视频播放状态.md) — `accepted`
- [ADR-0006 · 工作台自动创作与视频生成分离](decisions/ADR-0006-工作台自动创作与视频生成分离.md) — `accepted`
- [ADR-0005 · 生成任务以 ComfyUI 远端队列为幂等边界](decisions/ADR-0005-生成任务以-comfyui-远端队列为幂等边界.md) — `accepted`
- [ADR-0004 · 以项目为入口并按集隔离工作空间](decisions/ADR-0004-以项目为入口并按集隔离工作空间.md) — `accepted`
- [ADR-0003 · split control and inference hosts](decisions/ADR-0003-split-control-and-inference-hosts.md) — `unknown`
- [ADR-0001 · private complete github baseline](decisions/ADR-0001-private-complete-github-baseline.md) — `unknown`

## 维护规则

- 每个有意义的实现任务创建一个 `Ixxxx` 记录。
- 架构或关键取舍变化时创建 `ADR-xxxx`。
- 完成的迭代记录不静默改写；纠错使用补充说明或新迭代。
- 脑图只负责层级，详细证据写在图下方并链接源码、配置、测试或 ADR。
