# p251 — 1.21.4 编译闭包与桥编译探测（B03 基础设施）

日期：2026-11-03。后续每一条需要桥的 1.21.4 规则（例如 `GuiGraphics.method_25290` 多了一个
`Function<Identifier, RenderType>` 参数）都要先能编译。本回合把这块基础设施补齐，
并量化「1.21.1 的桥源码能不能直接用于 1.21.4」。

没有转换、没有写规则、没有启动游戏。

## 1. 闭包

```powershell
python tools\fetch_target_libs.py      # 59 个 MC 库 jar，61.6 MB
python tools\expand_bundle_libs.py     # 47 个 fabric-api 模块 jar
```

| 组成 | 数量 | 来源 |
|---|---:|---|
| MC 库（classpath，不含 natives） | 59 | piston-meta 的 version json，逐项校验 sha1 |
| fabric-api 模块（从 bundle 的 `META-INF/jars/` 展开） | 47 | `fabric-api-0.119.4+1.21.4.jar` |
| **合计** | **106** | 64.1 MB，全部带 sha256 |

`manifests/target-fabric-1.21.4-libs.lock.json` 记录 `classpath` 顺序与每个 jar 的哈希；
`targets/fabric-1.21.4.json` 的 `indices.libClosure` 只引用这一份锁文件（一个引用 + 一个哈希），
而不是把 106 条路径塞进目标身份里。`build_bridges.py --profile` 会展开它，并在哈希不符时拒绝编译。

被排除的 54 项（natives、非 windows 规则）记在锁文件的 `skipped` 里——native jar 是启动游戏用的，
不是 javac 的 classpath。

## 2. 桥编译探测

用现有的 1.21.1 桥源码去编 1.21.4，看差在哪：

| 阶段 | 编译错误 |
|---|---:|
| 只有 59 个 MC 库 | 45 |
| 补上 47 个 fabric-api 模块 | **23** |

错误性质（粗略分类，不是逐条判定）：

- **主体是第三方 mod API 缺失**：`BalmClientInitializeBridge`、`BalmInitializeBridge`、
  `BalmNetworkingBridge` 引用 `net.blay09.mods.balm.*`。Balm 不在 MC 闭包里——
  需要该 mod 的 **1.21.4 版本**才谈得上编译。
- **少数是真实 API 差异**：`StatusEffectInstanceBridge` 用
  `class_7923.field_41174.method_10223(class_2960...)`，1.21.4 的返回类型变成
  `Optional<class_68...>`，直接赋值不兼容。

所以「桥是目标资产」这句话在 1.21.4 上再次成立，而且多了一层：**依赖第三方 mod API 的桥，
还依赖那个 mod 的目标版本**。这条以前没有写下来。

## 3. 这对下一步意味着什么

- `callSiteAdaptations` 通道现在是**可用**的（classpath 完整、`build_bridges --profile` 能跑），
  所以 p250 归类出的 9 个 `descriptor-changed` 具备实施条件。
- 但「一次性把 34 个桥源全部迁移到 1.21.4」不是好起点：23 个错误里有 14 个是 Balm（3 个文件），
  先把它们从探测集里拿掉才能得到干净的迁移清单：14 个 Balm 错误 vs 9 个真实差异（分布见 result.json 的 errorsByFile）。
- `GuiGraphics.method_25290/25302` 需要桥里提供一个 `Function<Identifier, RenderType>`；
  这是语义决定（用哪个 RenderType），不是机械改写——**必须人来做**，然后用规则把它固定下来。

## 4. 边界

- **没有编译成功任何一个桥**：23 个错误仍在（0 个 class 产出）。本回合交付的是闭包与错误量化，不是可用的桥。
- **没有转换任何 jar**，没有规则，没有游戏。
- 错误分类是**按文件名与首行信息粗分**（Balm / 其它），没有逐条断言；`result.json` 里给的是
  错误行数与样例，不是精确分类。
- 闭包本身不含 Balm 等第三方 mod API，这是设计：它们是**模组依赖**，不是游戏库。
- `work/` 下的 jar 不入库；干净机器需要跑这两个脚本重新拉取（脚本幂等、带重试、校验哈希）。
