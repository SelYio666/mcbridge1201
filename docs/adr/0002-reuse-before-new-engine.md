---
status: accepted
date: 2026-10-18
---

# 先复现现有实现，再决定上游扩展或另建引擎

Retromod 和 CenturyBridge 已有与目标重叠的 MIT 许可实现，而转换基础设施和规则库的重建成本较高。先记录现有引擎在同一模组样本和目标环境上的行为，优先扩展能够复用的引擎；只有出现可复现的架构缺口、无法隔离的行为降级或工程限制，才选择 fork 或新的核心。独立产品可以先提供测试、报告和兼容档案，无需先重写全部转换器。

MIT 只描述对应仓库授权，不替代第三方依赖、游戏和来源模组的许可。未查到许可证的 Retrofit 不作为代码复制来源。

## P0 证据（2026-10-18）

- 来源固定 1.20.1、首个目标 Fabric 1.21.1、Forge 同步取样：见 `docs/baseline.md` §3–§5。
- 复用 CenturyBridge 作为首个引擎：见 `docs/engine-selection.md`；Retromod 保留为第二候选。
- 转换采用离线 `convert` + 独立实例：见 `docs/baseline.md` §6.3。

