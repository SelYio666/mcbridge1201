# p261 — 目标成员校验器：拦住"字节码正确、游戏里炸"

日期：2026-11-03。p260 里发现 `Registry#registryKey` 在 1.21.4 改名（`method_30517` →
`method_46765`），而规则仍写旧名；**所有字节码断言都通过**，因为 `patch` 只生成调用、
不检查被调用者是否存在。本回合补上这道闸。

## 1. 它检查什么

只检查规则里**显式标注为目标侧**的引用，不猜：

| 规则列表 | 检查字段 |
|---|---|
| `registrationKeys` | `setterOwner/Name/Desc`、`keyFactoryOwner/Name/Desc`、`registryKeyOwner/Name/Desc` |
| `callSiteAdaptations` | `targetOwner/targetName/targetDesc` |
| `signatureAdaptations` | `targetClass/methodName/newDesc` |

**不检查** `sourceOwner/sourceName`（那是 1.20.1 的形态，本就不该存在于目标）与
`bridgeClass/bridgeMethod`（那是我们自己编译的类）。

这条边界是刻意的：会猜的检查器会产生误报，而**误报就是把门禁关掉的开始**。

## 2. 精确到什么程度

不只查类存在，还查**声明**：解析目标类文件的 `fields`/`methods` 表，要求
`(name, descriptor)` 成对出现。所以

- `method_30517()` 与 `method_46765()` 的差别会被抓到；
- 同名但描述符不同的重载**不会**被误判为存在。

用的是新增的 `classpool.declarations()`——它读的是**声明表**，不是引用池。

## 3. 实测

```powershell
python tools\check_rule_targets.py                 # 当前规则包
python tools\check_rule_targets.py --rules-dir work/tmp/old-rule   # 负例
```

| 用例 | 结果 |
|---|---|
| 当前 5 个规则文件、3 组目标引用 | **0 missing**，rc 0 |
| 把 `registryKeyName` 改回 `method_30517` | **1 missing**，rc 1 |

负例输出：

```
MISSING member registration-key.json 1214.item-settings.registry-key: net/minecraft/class_2378.method_30517()Lnet/minecraft/class_5321;
        no such member with this exact descriptor
```

也就是说：**p260 那个错误如果当时跑过这个检查，会在 patch 之前被拦下**。

## 4. 为什么没放进自动门禁链

它需要目标 stub（`work/target/client-1.21.4-intermediary.jar`），而 `work/` 不入库。
放进 `release_check.py` 会让干净 checkout 的门禁失败——那是本仓库一直在避免的形态（p242 起
就吃过"manifest 里列了本机产物"的亏）。

所以它是**在有目标环境的机器上跑的检查**，与 `profile-check` 并列，而不是串进默认门禁。

## 5. 边界

- 只覆盖上表三类字段。`fieldRedirects`/`methodRedirects`/`constructorRedirects` 的目标是桥，
  桥由 `build_bridges` 编译保证，不在本检查范围。
- 不检查**资源**（配方、标签、模型）层面的目标引用。
- 不做语义检查：成员存在 ≠ 行为不变。
- 只对 `rules/fabric-1.21.4` 跑过；1.21.1 的规则目标是另一套索引，本回合没接。
