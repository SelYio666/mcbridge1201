# p255 — 用真 JVM 推翻 p253 的"兼容"判断

日期：2026-11-03。p253 曾经判定 3 个 `InteractionResult` 字段变化是"子类型宽化，兼容，不需要规则"。
**那个判断是错的**，本回合用 JVM 实测把它推翻了。

## 1. 错在哪

p253 的理由是：新类型 `class_1269$class_9860` 实现了旧类型 `class_1269`，所以"JVM 会接受它"。

前半句对，后半句错。**赋值兼容 ≠ 解析成功**：

- JVMS 5.4.3.2（字段解析）：按 **name + descriptor** 匹配，描述符不同就是 `NoSuchFieldError`；
- JVMS 5.4.3.3（方法解析）：同理，`NoSuchMethodError`。

字节码验证器在解析**之后**才看赋值是否合法，所以"子类型能不能塞进去"根本没轮到考虑。

## 2. 实测

`JvmResolutionTest` 用 ASM 生成一个只做单条引用的类，把它和 1.21.4 stub 一起用
`URLClassLoader` 加载，然后调用——不需要启动游戏，只要 stub 作 classpath。

| 用例 | 引用 | 期望 | 实测 |
|---|---|---|---|
| 旧字段描述符 | `GETSTATIC class_1269.field_21466 : Lclass_1269;` | `NoSuchFieldError` | **通过** |
| 目标字段描述符 | `GETSTATIC ... : Lclass_1269$class_9860;` | 可解析 | **通过** |
| 旧方法描述符 | `INVOKEVIRTUAL class_2769.method_11898()Ljava/util/Collection;` | `NoSuchMethodError` | **通过** |
| 目标方法描述符 | `INVOKEVIRTUAL ... ()Ljava/util/List;` | 可解析 | **通过** |

方法那条传 `null` 作 receiver 是故意的：解析发生在前，所以拿到的是链接错误而不是 NPE——
这也顺带证明了"抛的到底是哪一个"。

## 3. 修正后的分类

| 判定 | p253（错） | p255（实测） |
|---|---:|---:|
| 免规则（compatible） | 3 | **0** |
| 字段真断（broken） | 2 | **5** |
| 方法变更（method-changed） | 4 | 4 |

所以 9 个描述符变化**全部要处理**，p250 原来的说法（"9 个都要 `callSiteAdaptations`/
`signatureAdaptations`"）反而是对的。

工具有了实质变化：`newTypeIsSubtype` 仍然记录（它是有用信息），但**不再影响判定**——
描述符不同就是 broken，子类型只是"可能是同类替换"的线索。

## 4. 顺带查清的两条

p253 里那两个 `method-changed` 的调用点其实**不在 ironchests 自己的代码里**，而在嵌套的
ResourcefulLib 中：

- `method_11898`：`resourcefullib-fabric-1.20-2.0.6.jar!` 的 `StateVariant`
- `class_4309.<init>`：同 jar 的 `HighlightHandler`

所以这两条要处理，等于要改**第三方库的嵌套 jar**（patch 的递归改写能做，但语义决策更难：
`class_4309` 的 `(Gson, String)` → `(Codec, ResourceKey)` 是解析方式的变化，不是能机械转换的）。

## 5. 教训

静态分析说"子类型，没关系"是不够的——**链接语义要问 JVM**。而问 JVM 不需要游戏，
只要有目标 stub 和一次 `ClassLoader`，这就是一条在本环境里可用的验证通道。

p253 的 README 保留原样（历史记录），但顶部已加注：它的 `compatible` 判定被本文件推翻。
