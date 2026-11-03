# p262 — p260 悬案的根因：CLI 是旧的，不是规则坏了

日期：2026-11-03。p260 撤回注册上下文规则的理由之一是"`insertBeforeCalls` 根本没命中"。
**那个理由不成立**——规则一直是好的，是跑它的 `patch` 用了旧 jar。

## 1. 根因

`patch` 从 `java/build/install/mcbridge1201/lib/*.jar` 加载引擎。我在 p259 之后只跑了
`gradle test`（用 `build/classes`），**没有重建 `installDist`**，于是：

- 单元测试走新代码，全过；
- CLI 走旧 jar，`insertBeforeCalls` 这个 pass 根本不存在 → 规则被解析、但没人执行它。

症状就是 p260 看到的「规则加载正常、命中数 0、字节码没变」，而我把原因归到了匹配逻辑和嵌套 jar 上。

验证方式很直接：把嵌套 jar 里的 `FabricRegistryEntry.class` 单独打包，用同一条规则 patch——

| 阶段 | 结果 |
|---|---|
| 旧 CLI（p260 当时） | `classes changed=0` |
| **重建 installDist 之后** | `rule probe.supplier-context applied 1 time(s)`，字节码变成 `invokestatic RegistryKeyContext.getWithKey(Supplier, class_2378, class_2960)` |

单类就能复现，与嵌套 jar 无关。

## 2. 顺带修掉两个真 bug

它们是在"重新让它命中"之后才暴露的：

**（一）插入的桥没有登记。**
`applyInsertBeforeCalls` 改了字节码却没调 `recordBridge`，于是 `bridges embedded: []`——
产物会带着一条对 `RegistryKeyContext` 的调用，却不含那个类，运行时 `NoClassDefFoundError`。
两种分支（普通插入 / 替换调用）都补上了登记。

**（二）`used` 没有传进这个 pass。**
补登记时编译失败：`applyInsertBeforeCalls` 的签名里没有 `Set<String> used`。加上参数并从
`patchClass` 传入。

修完之后：`bridges embedded: [top/mcbridge1201/bridge/RegistryKeyContext]`。

## 3. 回归

引擎改了两处，所以把既有证据全部重跑：

| 证据 | 结果 |
|---|---|
| 单测 | **61/61**（新增 `RuleSetLoadTest`：从磁盘加载规则文件，断言 `insertBeforeCalls` 的每个字段都被解析出来）|
| p249 注册键 | PASS |
| p252 第一个桥 | PASS |
| p254 三处绘制 | PASS |
| p256 InteractionResult | PASS |
| p257 字段规则 | PASS |

`p243` / `p245` / `p246` 那三个是主仓库时代的证据，本工作区缺少它们要的 `work/` 资源，
重跑会写成 FAIL。**那不是回归，是环境缺失**，已 `git checkout` 还原，不让假结果进仓库。

## 4. 教训（写在最显眼处）

**改了引擎，先 `installDist`，再跑证据。**
`gradle test` 与 CLI 是两份产物：前者用 `build/classes`，后者用 `build/install`。
这一次是"测试全绿、CLI 行为不变"，比"测试红了"更难发现——因为所有证据脚本都"正常地"给出旧结果。

## 5. p260 撤回归还需不需要

p260 撤回规则有两条理由：supplier 规则不命中（**已推翻**）、与 `registrationKeys` 在同一处冲突
（**仍然成立**）。所以规则可以重新评估，但**冲突必须先解决**：`constructorRedirects` 无条件改写
`new Item.Settings()`，会让同方法内的 `registrationKeys` 失去目标。

本轮没有再把它放回 profile——没解决冲突就放回去，等于重演 p260 的错误。

## 6. 边界

- 端到端仍未验证：没有在完整 ironchests 上跑通"包装器注册 + 上下文注入 + 键生效"。
- `RegistryKeyContext` 的 ThreadLocal 生命周期仍然没有测试覆盖。
- 没有启动 1.21.4。
