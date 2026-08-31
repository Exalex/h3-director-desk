# h3-director-desk · 项目演进文档

> 这里记录项目当前结构、技术实现、决策依据和不可丢失的迭代历史。

- 文档更新时间：`2026-09-01T00:52:36+08:00`
- 当前迭代：`I-0011 · 修复浏览器旧 ComfyUI 地址覆盖 / completed`

## 建议阅读顺序

1. [项目总览脑图](mindmaps/project-overview.md)
2. [架构脑图](mindmaps/architecture.md)
3. [技术实现脑图](mindmaps/technical-implementation.md)
4. [仓库结构脑图](mindmaps/repository-structure.md)
5. [迭代脑图](mindmaps/iterations.md)
6. [仓库事实快照](evidence/repository-snapshot.md)

## 最近迭代

- [I-0011 · 修复浏览器旧 ComfyUI 地址覆盖](iterations/I-0011-修复浏览器旧-comfyui-地址覆盖.md) — 2026-09-01 / `completed`
- [I-0010 · 恢复新版工作台启动入口](iterations/I-0010-恢复新版工作台启动入口.md) — 2026-09-01 / `completed`
- [I-0009 · 重做项目级工作台与集数导航](iterations/I-0009-重做项目级工作台与集数导航.md) — 2026-08-31 / `completed`
- [I-0008 · 修正项目切换列表筛选](iterations/I-0008-修正项目切换列表筛选.md) — 2026-08-31 / `completed`
- [I-0007 · 接入本机项目切换数据](iterations/I-0007-接入本机项目切换数据.md) — 2026-08-31 / `completed`
- [I-0006 · 部署 5800H 导演台控制 spark1 ComfyUI](iterations/I-0006-部署-5800h-导演台控制-spark1-comfyui.md) — 2026-08-31 / `in-progress`
- [I-0005 · 完成 10 秒 H3 真实生成测试](iterations/I-0005-完成-10-秒-h3-真实生成测试.md) — 2026-08-31 / `completed`
- [I-0004 · 验证 spark1 导演台到 spark2 ComfyUI/H3 链路](iterations/I-0004-验证-spark1-导演台到-spark2-comfyui-h3-链路.md) — 2026-08-31 / `completed`

## 最近决策

- [ADR-0004 · 以项目为入口并按集隔离工作空间](decisions/ADR-0004-以项目为入口并按集隔离工作空间.md) — `accepted`
- [ADR-0003 · split control and inference hosts](decisions/ADR-0003-split-control-and-inference-hosts.md) — `unknown`
- [ADR-0001 · private complete github baseline](decisions/ADR-0001-private-complete-github-baseline.md) — `unknown`

## 维护规则

- 每个有意义的实现任务创建一个 `Ixxxx` 记录。
- 架构或关键取舍变化时创建 `ADR-xxxx`。
- 完成的迭代记录不静默改写；纠错使用补充说明或新迭代。
- 脑图只负责层级，详细证据写在图下方并链接源码、配置、测试或 ADR。
