# p256 — InteractionResult 三个常量走桥（B03 第四刀）

日期：2026-11-03。p255 用 JVM 实测确认：1.21.4 把 `InteractionResult` 的常量声明成 record 子类型，
所以 1.20.1 的 `GETSTATIC class_1269.field_5811 : Lclass_1269;` 会 `NoSuchFieldError`。
本回合给这三个字段各加一个访问器，把 29 处访问改过去。

## 1. 修法

桥（`InteractionResultBridge1214`）三个方法，每个只是重读目标字段并**宽化回 `class_1269`**：

```java
public static class_1269 field5811() { return class_1269.field_5811; }
```

规则是 `fieldRedirects`：`GETSTATIC class_1269.field_XXXX : Lclass_1269;` →
`INVOKESTATIC bridge.fieldXXXX()Lclass_1269;`。调用点保留它编译时的描述符，桥负责跨过类型变化。

**方法名故意用 intermediary 字段名**：这些常量各自是 SUCCESS / CONSUME / PASS / FAIL 中的哪一个，
本轮**没有重新核实**。给转换起个猜来的名字，就是让桥开始说谎的起点。

## 2. 实测（`tools/run_1214_interaction_bridge.py`，5 项全过）

| 检查 | 期望 | 实测 |
|---|---|---|
| 桥编译 class major | 全 65 | 全 65 |
| 源侧存在旧字段引用 | 是 | 是 |
| 三个字段都被重定向 | 是 | `field-5811` 20 次 / `field-5812` 7 次 / `field-21466` 2 次 |
| **旧字段引用残留（常量池）** | 0 | **0** |
| 桥引用存在 | 是 | 是（11 个 Methodref 条目，跨 8 个类）|

改动的 8 个类里，29 处访问全部改到桥；外层与嵌套 jar 的残留都是 0。

## 3. 这次验证用常量池，不用字符串

p254 踩过坑：对 class 字节做字符串匹配，会把**桥自己的常量池**也算成残留（桥要调用目标成员）。
所以本轮直接解析 class 文件的常量池，按 `Fieldref(owner, name, descriptor)` 三元组计数，
并把 `top/mcbridge1201/bridge/` 排除在"调用方"之外。

另一件小事：常量池是**按类去重**的，29 次调用只产生 11 个 `Methodref` 条目。
第一版检查拿"条目数 = 调用次数"比较，得到 11 vs 29 的假失败——现在 `result.json` 里
`poolDeduplication` 明写这个区别，调用次数以 patch 日志为准。

## 4. 1.21.4 剩下的三条

9 个 `descriptor-changed` 现在修掉 6 个（3 处绘制 + 3 个常量），剩 3 个：

| 项 | 为什么还没做 |
|---|---|
| `BlockStateProperties.field_12481/12525` | 旧类型 `class_2753`（DirectionProperty）**在 1.21.4 被删除**，新类型 `class_2754<Direction>`。这不是字段重定向能解决的：桥无法声明返回一个不存在的类型，所有提到该类型的局部变量、`CHECKCAST` 都要一起改。需要类型替换通道，或显式降级。 |
| `class_4309.<init>`（`SimpleJsonResourceReloadListener`） | `(Gson, String)` → `(Codec, ResourceKey)` 是**解析机制**的变化，不是签名搬移。桥没法把 Gson 自动变成 Codec——需要知道具体的 JSON schema。真要做只能手写移植。 |

这两项都是"静态可以继续做、但已经不是机械转换"的类别。

## 5. 边界

- **只验证链接**：旧引用消失、新引用存在、桥在 class major 65 上可编译。**没有验证行为**——
  这些常量在 1.21.4 的语义是否与 1.20.1 一致，本轮没有核实。
- 没有启动 1.21.4。
- `BlockStateProperties` 与 `Codec` 构造器未处理（见上）。
