# p258 — ResourcefulLib 注册路径的注入点探针（B03 可行性）

日期：2026-11-03。p248 发现 ironchests 的注册藏在嵌套 jar 的 ResourcefulLib 包装器里，
`registrationKeys` 规则（要求 register 调用与 settings 构造在**同一方法**）因此用不上。
本回合只回答一个问题：**这条路径上有没有可用的注入点**。没有 patch 任何东西。

## 1. 注册链路（javap 实证）

```
IronChestsFabric  → ResourcefulRegistries.create(Registry, "ironchests")
                  → FabricResourcefulRegistry.register(name, supplier)
                  → entries.add(FabricRegistryEntry.of(registry, new Identifier(modid, name), supplier))
                  → FabricRegistryEntry.of:  supplier.get()  →  Registry.register(...)
```

四个事实，四项检查全过：

| 事实 | 证据 |
|---|---|
| 包装器的 `register()` **只收集条目**，不注册 | `RegistryEntries.add` 出现，`method_10230` 不出现 |
| `init()` 是空方法 | 方法体只有 `return` |
| `FabricRegistryEntry.of` 是**唯一**同时调用 supplier 并注册的地方 | `Supplier.get` @8 → `method_10230` @13 |
| id 在 supplier 求值**之前**就可用 | `aload_1`（局部变量 1 = Identifier）@4 与 @6，早于 @8 |

## 2. 注入点

```text
 4: aload_1                    // the Identifier local        ← 在这里可用
 6: aload_1
 7: aload_2                    // the Supplier
 8: invokeinterface Supplier.get    ← settings 在这里被构造
13: invokestatic class_2378.method_10230   // 注册
```

所以：**在 `Supplier.get()` 之前用 `aload_1` 把 id 存进一个上下文（ThreadLocal），
mod 的 lambda 在构造 `Item.Settings` 时就能读到它并注入 key。**

这是这条路唯一可行的注入点——`register()` 太早（还没有 id 之外的信息，且不注册），
`init()` 是空的，注册本身在 factory 里。

## 3. 要落地还缺三件东西

| 缺什么 | 为什么不能复用现有的 |
|---|---|
| **插入调用**的规则类型 | 现有 `registrationKeys` 是在 settings 构造后插入，且要求同方法内有 register 调用；这里要插在**另一个类的某个调用之前** |
| 上下文桥（pending id + settings 工厂） | 没有它，lambda 里的 `new Settings()` 拿不到 id |
| **lambda 侧**的 settings 重定向规则 | mod 的 `new Item.Settings()` 在合成方法里，周围没有 register 调用，现有规则匹配不到 |

风险（写下来以免以后当作"顺手就能做"）：

- **ThreadLocal 生命周期**：嵌套注册或异常会让 pending id 泄漏，下一次注册拿到错的 id——
  这是**数据损坏级**的风险，必须在 bridge 里成对 set/clear，并且 clear 要放在 finally 语义里。
- **第三方库字节码改写**：要给 ResourcefulLib 的类打补丁，意味着转换产物的正确性依赖
  某个第三方库的具体版本；该库升级就要重做。
- **只能覆盖走这条包装器的模组**：直接调 `Registry.register` 的模组不走这里（那由 p249 的
  规则覆盖）。

## 4. 结论

**注入点存在且位置精确**（`FabricEntry.of` 的 `Supplier.get` 之前，局部变量 1）。
但落地需要一个新的规则类型 + 一个上下文桥 + 对第三方库的改写，且带一个数据损坏级的生命周期风险。

本轮**没有实现**，也没有宣称注册键在真实模组上可修——ironchests 的注册路径仍然是
"已知缺口"，只是现在缺口的位置、形状和代价都写清楚了。

## 5. 边界

- 探针用 `javap` 读字节码，没有运行任何东西。
- 只看了 ResourcefulLib 2.0.6（随 ironchests 打包的那一份）；别的版本可能不同。
- 没有验证 lambda 侧的 `new Item.Settings()` 具体形态（那是实现阶段第一步）。
