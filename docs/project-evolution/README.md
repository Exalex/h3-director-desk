# h3-director-desk · 项目演进文档

> 这里记录项目当前结构、技术实现、决策依据和不可丢失的迭代历史。

- 文档更新时间：`2026-08-31T11:58:28+08:00`
- 当前迭代：`I-0003 · 明确控制机与 H3 推理机分离架构 / completed`

## 建议阅读顺序

1. [项目总览脑图](mindmaps/project-overview.md)
2. [架构脑图](mindmaps/architecture.md)
3. [技术实现脑图](mindmaps/technical-implementation.md)
4. [仓库结构脑图](mindmaps/repository-structure.md)
5. [迭代脑图](mindmaps/iterations.md)
6. [仓库事实快照](evidence/repository-snapshot.md)

## 最近迭代

- [I-0003 · 明确控制机与 H3 推理机分离架构](iterations/I-0003-明确控制机与-h3-推理机分离架构.md) — 2026-08-31 / `completed`
- [I-0002 · 克隆并完成 Windows 本地部署](iterations/I-0002-克隆并完成-windows-本地部署.md) — 2026-08-31 / `completed`
- [I-0001 · 项目架构文档与 GitHub 基线](iterations/I-0001-项目架构文档与-github-基线.md) — 2026-08-28 / `completed`

## 最近决策

- [ADR-0003 · split control and inference hosts](decisions/ADR-0003-split-control-and-inference-hosts.md) — `unknown`
- [ADR-0001 · private complete github baseline](decisions/ADR-0001-private-complete-github-baseline.md) — `unknown`

## 维护规则

- 每个有意义的实现任务创建一个 `Ixxxx` 记录。
- 架构或关键取舍变化时创建 `ADR-xxxx`。
- 完成的迭代记录不静默改写；纠错使用补充说明或新迭代。
- 脑图只负责层级，详细证据写在图下方并链接源码、配置、测试或 ADR。
