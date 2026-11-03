# p257 — 被删除类型的字段：用共同父类做桥（附一个帧重算的真 bug）

日期：2026-11-03。`BlockStateProperties` 的两个方向属性在 1.21.4 里**类型被删**：
1.20.1 是 `DirectionProperty`（`class_2753`），1.21.4 是 `EnumProperty<Direction>`（`class_2754`），
而 `class_2753` 整个类没了。这不是字段重定向能直接解决的——桥不能声明一个不存在的返回类型。

## 1. 修法：返回共同父类

桥返回 `Property`（`class_2769`），它是两者的共同父类：

```java
public static class_2769 field12481() { return class_2741.field_12481; }  // 1.21.4 里是 class_2754
```

**这个做法成立与否取决于"调用点怎么用"**，所以先扫描再动手：样本里 5 处对 `class_2753` 的引用是
4 个 `getstatic` + 1 个常量池里的类名，消费方式只有 `BlockState#has(Property)` 和
`Property#equals`——两者都吃父类型。没有任何 `DirectionProperty` 专有调用，也没有 `CHECKCAST`。

如果真有专有调用，这个桥就不够，那是真移植而不是重定向。规则 evidence 里写明了这个前提。

## 2. 顺手抓到一个真 bug（不是本轮引入的）

第一版跑完，指令都改对了，但产物里**还留着 `class_2753`**：

```
19: areturn
StackMapTable:
  frame_type = 66 /* same_locals_1_stack_item */
    stack = [ class net/minecraft/class_2753 ]   ← 已经删除的类型还在帧里
```

根因在 `JarPatcher`：`fieldRedirects` 分支把 `GETSTATIC` 换成 `INVOKESTATIC` 后只设了
`changed`，**没设 `framesAffected`**。于是 `ClassWriter(0)` 原样保留旧 `StackMapTable`，
而字段重定向恰恰会改变栈上的类型（桥可以返回父类型）。

后果是运行时验证失败——指令全对、帧里指着一个不存在的类，比"某条调用没改"更难查。
修法是那个分支补上 `framesAffected = true`，让帧重算。改完 52 个既有单测全过。

**这个 bug 只在"桥返回的类型与原字段类型不同"时暴露**，而 1.21.1 的字段重定向恰好都保持原类型，
所以一直没被发现。

## 3. 实测（`tools/run_1214_field_rules.py`，7 项全过）

同时覆盖两组字段规则（`interaction-result` 与 `blockstate-properties`）：

| 检查 | 期望 | 实测 |
|---|---|---|
| 桥编译 class major | 全 65 | 全 65 |
| 源侧有旧字段引用 | 是 | 是 |
| 源侧引用被删类型 | 是 | 是 |
| 两组规则都命中 | 是 | 是 |
| **旧字段引用残留** | 0 | **0** |
| **被删类型残留（含帧）** | 0 | **0** |
| 桥引用存在 | 是 | 是 |

验证用新抽出的 `tools/classpool.py` 解析常量池，同时数 **`Fieldref`** 和 **`CONSTANT_Class`**：
只查指令抓不到帧里的类名——这正是第 2 节那个 bug 的形态。

## 4. 1.21.4 进度

9 个 `descriptor-changed`：**8 个已修**（3 绘制 + 3 常量 + 2 方向属性）。

只剩 `class_4309.<init>`（`(Gson, String)` → `(Codec, ResourceKey)`）：那是**解析机制**变化，
不是类型或签名搬移。桥没法把 Gson 自动变成 Codec，需要知道具体 JSON schema，只能手写移植。

## 5. 边界

- **只验证链接**：旧引用与被删类型都清零、桥在 major 65 上可编译。**没有验证行为**——
  `Property` 的宽化在语义上安全吗？本轮只证明了"消费点只要父类型"，没证明"这些字段在 1.21.4
  的语义与 1.20.1 一致"。
- 没有启动 1.21.4。
- 帧重算用 `SafeClassWriter`，其 `getCommonSuperClass` 固定返回 `Object`（游戏类不在 classpath）。
  对"删类型后宽化"够用，但对需要精确公共父类的场景可能过于保守——这是既有取舍，本轮没改。
