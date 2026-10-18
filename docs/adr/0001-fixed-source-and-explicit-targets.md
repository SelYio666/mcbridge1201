---
status: accepted
date: 2026-10-18
---

# 固定 1.20.1 来源，逐个声明目标环境

来源只固定 Minecraft 1.20.1，不同时接入所有历史来源；目标按游戏版本、加载器和运行侧逐项声明，以便将维护工作集中在用户关心的存量模组。Fabric 和 Forge 是不同来源路线，不能因为来源游戏版本相同而共享同一兼容承诺。旧于 1.20.1 的目标和未验证的未来版本暂不进入首期支持矩阵；长期目标保留扩展空间。

这是交接方案的默认实施建议，用户尚未指定加载器和首批模组。P0 必须同时调查 Fabric 与 Forge 样本，不能把一个 Fabric 样例当作 Forge 产品需求已解决。

## P0 证据（2026-10-18）

- 来源固定 1.20.1、首个目标 Fabric 1.21.1、Forge 同步取样：见 `docs/baseline.md` §3–§5。
- 复用 CenturyBridge 作为首个引擎：见 `docs/engine-selection.md`；Retromod 保留为第二候选。
- 转换采用离线 `convert` + 独立实例：见 `docs/baseline.md` §6.3。

