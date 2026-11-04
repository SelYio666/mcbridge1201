# p250 — 21 项 1.21.4 断裂的可执行分类（B03 规则候选）

> **更正（2026-11-04，`runs/p267`）**：本文 `member-removed` 的 6 条里只有 **4 条是真删**。
> `method_9559` 与 `method_26226` 在 1.21.4 里仍然存在，只是描述符变了——本文记录的是
> **调用点 owner**，而它们声明在父类 `class_4970` 上，查询没有爬继承链。


日期：2026-11-03。B01（`runs/p247`）量出「真实样本在 1.21.4 上比 1.21.1 多 21 个断裂」，
但一个数字不是工作项。本回合把每一条变成**可执行条目**：Mojang 名 + 类别 + 建议的规则类型。

只做分类：没有转换任何 jar、没有写规则、没有启动游戏。

## 1. 方法

```powershell
python tools\classify_1214_breaks.py
```

对 p247 的每个 `newIn1214` 条目：

1. 用 **1.21.1 的官方映射**把 `class_XXXX` 还原成 Mojang 名（"class_1269" 不可执行，
   "InteractionResult" 才可以）；
2. 在 **1.21.4 的 stub** 里查所属类是否存在（zip 条目）、成员名是否还出现在该类常量池里；
3. 分类：`class-removed` / `member-removed` / `descriptor-changed`；
4. 附上建议的规则类型（**建议，不是已具备的能力**）。

## 2. 结果

21 条全部拿到了 Mojang 名：**类删除 6、描述符变化 9、成员删除 6**。

| 类别 | 例子（Mojang 名） | 建议规则 |
|---|---|---|
| 类删除（6） | `MetadataSectionSerializer`、`ItemProperties`、`ClampedItemPropertyFunction`、`DirectionProperty` | 需要手写桥或显式降级——**规则造不出一个类** |
| 描述符变化（9） | `InteractionResult` 的三个字段、`BlockStateProperties` 两个字段、`GuiGraphics.method_25290/25302`、`SimpleJsonResourceReloadListener.<init>` | `callSiteAdaptations` / `signatureAdaptations` |
| 成员删除（6） | `RenderShape.field_11456`、`InteractionResult.method_29236`、`LevelAccessor.method_39281`、`BaseEntityBlock.method_9559`、`BlockState.method_26226`、`Sheets.method_24076` | `methodRedirects` / `fieldRedirects` 到桥，或显式降级 |

## 3. 与官方变化清单的交叉验证

分类结果和 p247 里的官方清单对得上，这提高了"分类没跑偏"的可信度：

| 实测条目 | 官方哪条解释它 |
|---|---|
| `MetadataSectionSerializer` 整个类消失 | 1.21.4「Resource Metadata files now use Codec serializers」 |
| `ItemProperties` / `ClampedItemPropertyFunction` 消失 | 1.21.4「Item Models 改为 `assets/<ns>/items` 定义文件，`ItemColors` 及相关 API 移除」 |
| `InteractionResult` 的字段与方法变化 | 1.21.2「ActionResult / ItemActionResult / TypedActionResult 合并」 |
| `BlockStateProperties` 两个字段类型变化 | 由 `DirectionProperty` 消失引起（见下） |
| `GuiGraphics` 两个方法描述符变化 | 未在 1.21.4 博客显式列出，属于渲染重构的连带 |

### 官方清单没有覆盖的一条

`DirectionProperty`（1.21.1 = `class_2753`）在 1.21.4 里**连 Mojang 映射都没有**——
不是换了 intermediary 名，是类本身没了（`EnumProperty` 还在）。1.21.4 的 Fabric 博客
没有提这件事。

所以：**官方变化清单不是完整清单，实测是必要的**。这条已经作为专项写进分类结果，
不并进"已知原因"里蒙混。

## 4. 一个顺带确认的事实

intermediary 名在版本之间大体稳定（`BooleanProperty` 在两个版本都是 `class_2746`），
所以跨版本转换**主要不是改名问题**，但一旦某个类被删除，它引用的字段/方法会跟着
进 `member-removed`——分类器把这两种情况分开了，不会把"类删除"误报成"成员删除"。

## 5. 边界

- **判据是常量池子串**：「成员存在」只表示这个名字在该类的常量池里出现过，
  不表示"这个描述符的调用能解析"。分类器把 `descriptor-changed` 单独拎出来，正是因为
  这一层信息它看不到。
- **没有转换**：一条都没修，规则一条没写。
- **没有游戏**：分类是静态事实，不是"修好了"。
- 只分类了 ironchests 一个输入（fixture 在 1.21.4 上没有新增断裂，0 条）。
- 建议的规则类型是**下一步的工作项建议**，不是已有能力。已有能力目前只有 p249 的
  `registrationKeys` 一条。
