# p259 — 插入式规则类型（`insertBeforeCalls`）

日期：2026-11-03。p258 定位了 ResourcefulLib 的注入点，但要落地需要一个引擎里还不存在的
能力：**在被匹配的调用之前插一条桥调用**。现有规则类型都是"替换一处已有引用"，
`registrationKeys` 是在 settings 构造**之后**插入、且要求同方法内有 register 调用。

本回合只做这座底座，**没有任何规则使用它**。

## 1. 规则形状

```jsonc
{
  "id": "...",
  "matchOwner": "java/util/function/Supplier",   // 匹配的调用
  "matchName": "get",
  "matchDesc": "()Ljava/lang/Object;",
  "matchOpcode": 185,                            // invokeinterface
  "loadLocal": 1,                                // 插入前压入的局部变量槽
  "loadKind": "aload",
  "bridgeClass": "...", "bridgeMethod": "set", "bridgeDesc": "(Ljava/lang/String;)V"
}
```

落地成 `ALOAD 1; INVOKESTATIC bridge.set(Ljava/lang/String;)V`，插在 `Supplier.get()` **之前**。

## 2. 两个必须成立的性质

**栈中性**：插入发生时，被匹配调用的参数已经在栈上（这里就是 supplier）。
`ALOAD slot` 压入的正是桥消费的那一个，所以净变化 0——不能把调用方的栈搞乱。
测试里直接断言了"桥调用前一条指令是 `ALOAD 1`"。

**两遍匹配**：先收集命中，再统一插入。边走边插会把刚插入的 `INVOKESTATIC` 喂回同一个遍历，
规则条目重叠时会重复触发。这个坑在写的时候就避开了，测试用"一个方法两个命中点"钉住
（期望 2 次，不能是 0 或 4 次）。

## 3. 单元测试（4 个用例，全过）

| 用例 | 断言 |
|---|---|
| 插入位置 | 桥调用在 `Supplier.get()` 之前 |
| 参数来源 | 桥调用前一条是 `ALOAD 1`（声明的局部变量） |
| 两处命中 | 2 次插入、2 条原调用都还在（不重复、不吞掉） |
| 缺槽位 | `loadLocal = -1` 时**不触发**（否则会发出 `ALOAD -1` 这种非法指令）|

全套单测 **60/60**（原 56 + 新 4）。

## 4. 它解锁了什么、还没解锁什么

解锁：ResourcefulLib 那条路径的**第一半**——在 `FabricRegistryEntry.of` 里、
`Supplier.get()` 之前把 registry id 存进上下文。

**还缺**（这也是为什么本回合不算"修好注册键"）：

- 上下文桥本身（ThreadLocal + settings 工厂），以及它的生命周期处理；
- lambda 侧把 `new Item.Settings()` 重定向到桥的规则（那里没有 register 调用，现有规则匹配不到）；
- **规则包里没有任何一条使用这个类型**——仓库现状仍是 5 条规则，ironchests 的注册路径仍然未修。

## 5. 边界

- 只是引擎能力 + 单元测试，**没有对真实模组跑过**。
- 没有验证 `loadKind = "iload"`（int 参数）的形态，测试只覆盖 `aload`。
- 插入只支持"一个局部变量 + 一个无返回值桥调用"这一种形状，不是通用指令插入器。
