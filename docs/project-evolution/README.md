# h3-director-desk · 项目演进文档

> 这里记录项目当前结构、技术实现、决策依据和不可丢失的迭代历史。

- 文档更新时间：`2026-09-01T08:10:24+08:00`
- 当前迭代：`I-0015 · 补充 H3 生成进度与后台日志可视化 / completed`

## 建议阅读顺序

1. [项目总览脑图](mindmaps/project-overview.md)
2. [架构脑图](mindmaps/architecture.md)
3. [技术实现脑图](mindmaps/technical-implementation.md)
4. [仓库结构脑图](mindmaps/repository-structure.md)
5. [迭代脑图](mindmaps/iterations.md)
6. [仓库事实快照](evidence/repository-snapshot.md)

## 最近迭代

- [I-0015 · 补充 H3 生成进度与后台日志可视化](iterations/I-0015-补充-h3-生成进度与后台日志可视化.md) — 2026-09-01 / `completed`
- [I-0014 · 修复 H3 生成提交状态与远端队列去重](iterations/I-0014-修复-h3-生成提交状态与远端队列去重.md) — 2026-09-01 / `completed`
- [I-0013 · 补齐生成视频回显并完成真实单镜验证](iterations/I-0013-补齐生成视频回显并完成真实单镜验证.md) — 2026-09-01 / `completed`
- [I-0012 · 验证 H3 生成并修复任务列表监控](iterations/I-0012-验证-h3-生成并修复任务列表监控.md) — 2026-09-01 / `completed`
- [I-0011 · 修复浏览器旧 ComfyUI 地址覆盖](iterations/I-0011-修复浏览器旧-comfyui-地址覆盖.md) — 2026-09-01 / `completed`
- [I-0010 · 恢复新版工作台启动入口](iterations/I-0010-恢复新版工作台启动入口.md) — 2026-09-01 / `completed`
- [I-0009 · 重做项目级工作台与集数导航](iterations/I-0009-重做项目级工作台与集数导航.md) — 2026-08-31 / `completed`
- [I-0008 · 修正项目切换列表筛选](iterations/I-0008-修正项目切换列表筛选.md) — 2026-08-31 / `completed`

## 最近决策

- [ADR-0005 · 生成任务以 ComfyUI 远端队列为幂等边界](decisions/ADR-0005-生成任务以-comfyui-远端队列为幂等边界.md) — `accepted`
- [ADR-0004 · 以项目为入口并按集隔离工作空间](decisions/ADR-0004-以项目为入口并按集隔离工作空间.md) — `accepted`
- [ADR-0003 · split control and inference hosts](decisions/ADR-0003-split-control-and-inference-hosts.md) — `unknown`
- [ADR-0001 · private complete github baseline](decisions/ADR-0001-private-complete-github-baseline.md) — `unknown`

## 维护规则

- 每个有意义的实现任务创建一个 `Ixxxx` 记录。
- 架构或关键取舍变化时创建 `ADR-xxxx`。
- 完成的迭代记录不静默改写；纠错使用补充说明或新迭代。
- 脑图只负责层级，详细证据写在图下方并链接源码、配置、测试或 ADR。
