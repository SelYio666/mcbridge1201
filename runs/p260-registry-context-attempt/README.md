# p260 — 尝试接上包装器注册路径：一个真修正、两个阻塞、一次撤回

> **更正（2026-11-03，`runs/p262`）**：本文列的第一个阻塞「supplier 规则根本没命中」**结论作废**——规则是好的，当时跑它的 `patch` 用的是未重建的旧 jar。第二个阻塞（与 `registrationKeys` 在同一处冲突）仍然成立。


日期：2026-11-03。p258 定位了 ResourcefulLib 的注入点，p259 做出了插入式规则类型。本回合试着
把这条路径真正接上，结果是：**修掉了一个真实错误，但没能接通，于是把未验证的部分撤回了**。

## 1. 修掉的真错误：`Registry#registryKey` 在 1.21.4 改名了

| 版本 | 方法名 |
|---|---|
| 1.20.1 | `class_2378.method_30517()` |
| **1.21.4** | **`class_2378.method_46765()`** |

p249 的注册键规则里写的是 `method_30517`——**1.21.4 里不存在这个名字**。

**为什么之前没暴露**：`patch` 只负责生成调用指令，**不检查目标成员是否存在**。
所以 p249 的字节码验证全过，产物却会 `NoSuchMethodError`。

已修正：规则、桥源码、p249 的检测常量三处；重跑后反汇编确认调用是

```
21: invokevirtual class_2378.method_46765:()Lnet/minecraft/class_5321;
```

p249 的五项检查重新全过。

**这是一类会漏的系统性缺口**：规则里引用的每一个"目标侧成员"都该在生成前对目标索引校验存在性。
本轮没做这个校验器（时间不够），已列为下一步。

## 2. 阻塞一：两条注册键规则在同一处竞争

新写的 `registry-key-context` 用 `constructorRedirects` 无条件把 `new Item.Settings()` 换成
`RegistryKeyContext.settings()`；而 p249 的 `registrationKeys` 是在 settings 构造**之后**插入
key 设置。两者在同一处命中：

```
patched mcbfixture-1.0.0.jar (classes changed=1)
  rule 1214.item-settings.registry-context applied 1 time(s)
  rule 1214.item-settings.registry-key     applied 1 time(s)
```

语义上冲突：注入的 key 设置现在作用于工厂的返回值，而工厂自己可能已经加了 key。
**没有一条规则是错的，但它们不能同时开着。**

## 3. 阻塞二：supplier 规则根本没命中

`insertBeforeCalls` 那条规则的匹配目标是嵌套 jar 里 `FabricRegistryEntry.of` 的
`Supplier.get()`。patch 之后检查：

```
FabricRegistryEntry.class | Supplier.get: True | getWithKey: False
```

**没有改写**。规则字段（owner/name/desc/opcode = `java/util/function/Supplier` /
`get` / `()Ljava/lang/Object;` / 185）与 javap 输出一致，插入式规则类型也有单测覆盖，
所以问题在别处——很可能是 patch 对嵌套 jar 里类的规则应用路径，而不是匹配本身。**未查明**。

## 4. 决定：撤回

- 删除 `rules/fabric-1.21.4/registry-key-context.json`；
- `targets/fabric-1.21.4.json` 的 `ruleOrder` 与 `capabilities` 回退到 5 条规则；
- **保留** `RegistryKeyContext.java`（编译通过、设计仍成立），但它**没有任何规则引用**。

理由：留着一条"看起来支持、实际没命中"的规则，比没有更糟——它会让下一次的
"支持矩阵"说谎。

## 5. 本回合的净结果

| 项 | 结果 |
|---|---|
| `method_30517` → `method_46765` | **修正并验证** |
| p249 证据 | 重新全过（字节码用新名）|
| 包装器注册键路径 | **未接通**，原因部分定位 |
| 规则包 | 仍是 5 条（撤回 1 条）|

## 6. 边界

- 撤回的那条规则从未在真实模组上验证过；研究本身（p258/p259 的注入点与规则类型）仍然有效。
- `RegistryKeyContext` 的 ThreadLocal 生命周期设计（try/finally、嵌套恢复）没有被任何测试覆盖，
  因为还没有东西用它。
- "目标成员存在性校验器"是本轮得出的最明确的下一步。
