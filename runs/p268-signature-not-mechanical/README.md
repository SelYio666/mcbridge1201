# p268 — 那条"描述符变化"不是规则能处理的：参数是重排，不是追加

日期：2026-11-04。p267 把 `method_9559` / `method_26226` 从 "removed" 修正为 "descriptor-changed"，
并写了「属于 `callSiteAdaptations` / `signatureAdaptations` 的领域，规则能处理」。
**后半句要撤回**：细看调用点之后，这条需要人工移植。

## 1. 调用点的真实形态

`method_9559` 在 ironchests 里只有一处，出现在 `GenericChestBlock`：

```
public class_2680 method_9559(class_2680, class_2350, class_2680, class_1936, class_2338, class_2338)
  ...
  46: invokespecial class_2237.method_9559(6 个参数)   // 调父类实现
  49: areturn
```

也就是说：**ironchests 覆写了父类的 `method_9559`，并在其中 `invokespecial` 调父类版本**。

到 1.21.4 变成两处同时坏：

1. 覆写方法不再覆写任何东西（父类没有这个方法了）；
2. `invokespecial` 指向一个不存在的签名 → `NoSuchMethodError`。

（`method_26226` 在 ironchests 里**没有调用点**，是 p250 从索引差异推出来的，不是实际使用。）

## 2. 两版签名不是"追加参数"

| | 参数序列 |
|---|---|
| 1.20.1 | `(BlockState, Direction, BlockState, LevelAccessor?, BlockPos, BlockPos)` |
| 1.21.4 | `(BlockState, class_4538, class_10225, BlockPos, Direction, BlockPos, BlockState, class_5819)` |

`Direction`（`class_2350`）从**第 2 位挪到第 5 位**，`class_1936` 消失，新增 3 个类型。
这不是"末尾多两个参数"，而是**参数重排 + 语义重组**。

`signatureAdaptations` / `callSiteAdaptations` 能表达的是"改名 / 换描述符"，
**表达不了"第 2 个参数现在要放到第 5 位"**——那需要知道每个参数在新签名里对应什么，
也就是要读 1.21.4 的实现。

## 3. 结论（对 p267 的修正）

| 条目 | p267 说 | 现在 |
|---|---|---|
| `method_9559` | 规则能处理 | **需人工移植**（覆写 + super 调用 + 参数重排）|
| `method_26226` | 规则能处理 | **无调用点**，暂不影响 |

所以 1.21.4 剩余待办里，**规则能处理的已经全部处理完**——没有"最后一刀"了。

## 4. 为什么这个结论值得单独写一篇

因为写一条"看起来能跑"的规则很容易：把 6 参改成 8 参、顺手补两个 `aload`，
patch 会命中、字节码甚至能验证通过（只要类型凑巧兼容），**但语义是错的**。
真正的验证要等 1.21.4 跑起来——而这正是离线环境做不到的。

宁可在这里停下，把"做不到"写清楚，也不产出一个会在游戏里悄悄出错的东西。

## 5. 边界

- 没有实现任何规则或桥。
- 没有解析 1.21.4 那个 8 参方法的语义（需要读实现，超出当前环境）。
- 覆写是否真的"不再覆写"未在 1.21.4 运行时确认，但 1.21.4 的 `class_4970` 只有 8 参版本
  这一点是 javap 实证。
