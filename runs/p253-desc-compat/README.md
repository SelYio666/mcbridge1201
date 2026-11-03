# p253 — 把"描述符变化"分成真断裂与误报（B03 待办修正）

> **更正（2026-11-03，`runs/p255`）**：本文件里判成 `compatible` 的 3 条是**错的**。
> JVM 解析字段/方法按 name + descriptor 精确匹配（JVMS 5.4.3.2/5.4.3.3），子类型不够。
> 实测旧描述符会抛 `NoSuchFieldError` / `NoSuchMethodError`。修正后 9 条全部需要处理。


日期：2026-11-03。p250 把 ironchests 的 21 项 1.21.4 断裂分成
类删除 6 / 描述符变化 9 / 成员删除 6。本回合回到那 9 个，发现**其中 3 个根本不用改**。

## 1. 为什么要再分一次

静态分析器报 `descMismatch` 的条件是"目标里这个成员存在、但描述符不同"。这个判据不等于
"真的坏"：**如果新类型是旧类型的子类型，JVM 会接受它在旧类型的位置**——字节码验证看的是
"能不能赋值"，不是"描述符字节相等"。

1.21.4 恰好同时有这两种情况，而且靠得很近：

| 字段 | 旧类型 | 新类型 | 关系 |
|---|---|---|---|
| `class_1269.field_21466/5811/5812`（InteractionResult 的 SUCCESS/FAIL/…） | `class_1269` | `class_1269$class_9860` / `$class_9859` | **record implements class_1269** → 子类型 |
| `class_2741.field_12481/12525`（BlockStateProperties 的 FACING 等） | `class_2753`（DirectionProperty） | `class_2754<Direction>`（EnumProperty） | `class_2753` **本身被删** → 真断裂 |

## 2. 结果

`tools/check_desc_compat.py`：对每条取目标里的实际类型，沿 stub 的继承图做广度优先搜索，
判断新类型是不是旧类型的子类型。

```powershell
python tools\check_desc_compat.py
```

| 判定 | 数量 | 说明 |
|---|---:|---|
| `compatible` | **3** | 子类型宽化，JVM 接受，**不需要任何规则** |
| `broken` | **2** | `DirectionProperty` 被删，字段变成 `EnumProperty<Direction>` |
| `method-changed` | **4** | 方法签名移动：`class_332.method_25290/25302`（多一个 `Function` 参数）、`class_2769.method_11898`（返回 `List<T>`）、`class_4309.<init>`（换成 `Codec` 重载） |
| `unknown` | 0 | 构造器名 `<init>` 在 javap 里显示为类名，已单独处理 |

所以 p250 说的"9 个都要 `callSiteAdaptations`/`signatureAdaptations`"是**偏多的**：
真正要动手的是 **2 个字段 + 4 个方法 = 6 个**。

## 3. 对下一步的意义

- **`class_332.method_25290`/`method_25302` 与 p252 已修的 `method_48587` 是同一模式**：
  1.21.4 的 blit 多了 `Function<Identifier, RenderType>` 首参、`u`/`v` 前移。
  p252 的桥已经把「参数顺序 + `guiTextured` 解析器 + `-1` 染色」写清楚了，
  剩下这两条是**同一套桥的另外两个入口**，不是新问题。
- **`BlockStateProperties` 的两个字段**是真麻烦：类型被删了，任何"引用 `class_2753`"的地方
  （字段读取、局部变量类型、`CHECKCAST`）都要一起处理。它属于"类删除的连带"，
  不该用字段重定向草草了事。
- `InteractionResult` 那三个字段**确认不用改**，可以把它从待办里划掉。

## 4. 边界

- **只比描述符**。`compatible` 的含义是"JVM 接受这个值放在旧类型的位置"，**不是**
  "周边逻辑正确"。如果某个字段换了类型且含义也变了（比如枚举改成了 record），
  这里仍会判成 compatible——那是行为问题，静态分析看不出来。
- **成员整体消失**不在这里重判（那是 p250 的 `member-removed`，6 条）。
- 继承检查只走 stub 自己的类头，不解析 JDK 类型；对本项目涉及的 MC 类型没有影响。
- **没有转换、没有规则、没有游戏**。本回合只是把待办列表改准确。
