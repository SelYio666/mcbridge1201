# 已知限制

本文件记录“这套工具/这轮证据不能说明什么”。任何对外表述都必须带着这些限定。

## 1. 证据阶段

- 目前最高阶段：**`CONTRACT_PASSED`（范围受限）**——专用服务端 + 命令 API 下，转换后的 ironchests 完成“放置 → 插入 → NBT 写入 → 进程重启 → 读回”。
- 客户端 `WORLD_LOADED`（玩家进入世界、GUI、渲染）**未验证**。
- `SET_PASSED` 与多人同步：pending。
- `BOOTED` 使用的游戏 jar 由本项目 ASM 重映射器生成（Loader 本体未改），因为原版 remap 被沙箱 `Files.isWritable` 阻塞。这不是 stock 路径，复现时必须写明。
- 静态 `CLEAN_STATIC` 只表示“在索引覆盖的命名空间里没有发现缺类/缺成员”，不表示能加载，更不表示玩法正确。

## 2. 静态分析器

- 只判断**符号存在性/描述符一致性**。方法体语义、数据流、事件阶段、线程约束都不判断。
- 继承解析依赖目标索引里的真实类文件；遇到未索引的非 `java/lang/Object` 祖先时记 `UNKNOWN`，会低估损伤。
- Mixin 只解析 `@Mixin` 的 `value`/`targets` 类是否存在；`@Inject` 的 method/ordinal/slice/local capture **未分析**。
- Forge 样本只做到命名空间级：`net/minecraftforge.*` 在 Fabric/NeoForge 目标下的类级消失、SRG 引用的数量，没有成员级映射。
- 反射字符串、动态生成字节码、Kotlin/Scala 元数据中的引用不在覆盖范围。
- 嵌套 jar（JiJ）只扫描一层；多层嵌套未递归。

## 3. CenturyBridge 使用

- 固定提交 `cf4ebeba...` 的 `core/src` **缺少** `MixinCheck.java`；本地补的是 no-op 空实现。任何与 `mixin-check` 相关的门禁结论都不成立。
- `convert` 的 `ok_partial` 是上游自己的判定；本项目未独立验证它的语义。
- 28 个 tombstone 意味着“调用到就抛错”，不是“已桥接”。ironchests 的容器玩法在没有桥 jar 时必然失败。
- **实测确认（首次、未打规则补丁时）**：转换件在 1.21.1 服务端被 Loader 接受后，入口点即抛 `NoSuchFieldError: ItemPredicate.ANY`（`class_2073.field_9640`）。这说明 `ok_partial` 不代表能初始化。
- 规则补丁后，同一转换件已到达 `Done` 并通过容器契约（放置/插入/NBT/重启读回，见 `docs/baseline.md` §7.14）；`ItemPredicate.fromJson` 已改为 registry-aware 桥（p9），不再回退全匹配。**这不改变客户端/GUI/多人仍未验证的边界。**
- 桥 jar（`core/shims/1.21.1`）未构建；`build.sh` 的四道门禁一步都没跑。
- 转换件的 jar 签名已被上游清理；不得声称它仍由原作者签名。

## 3.1 自研重映射器

- 只为解决本机 zipfs 只读阻塞而写；它不是 TinyRemapper 的等价替代：没有 `--propagatePrivate`、冲突检测、record/模块化细节的完整处理。
- 目前只在 **1.21.1 服务端 jar** 上验证（6148 类，能启动到 Done）；客户端 jar、带资源 jar、多版本 jar 未验证。
- 名称传播规则是工程近似：static/private 不传播、字段仅在 owner 未声明时向上找；遇到多接口同签名冲突时取第一个命中，没有冲突失败机制。
- 输出 entry 时间戳固定为 0，便于复现；未做 jar 签名清理以外的规范化。

## 4. 环境

- 本会话的 Java 进程无法在本会话工作区外写入，工作区内 `Files.isWritable` 恒 false；这直接导致 Fabric Loader 拒绝 remap。不是代码缺陷，但复现时必须换环境。
- `%TEMP%` 不可写；所有 JVM 命令需要 `-Djava.io.tmpdir`。
- 没有 JDK 17；1.20.1 来源 fixture 尚未编译（如要做，用 JDK 21 `--release 17` 或另装 JDK 17）。
- 没有可用图形会话的验证；客户端标题画面/渲染/截图全部未做。

## 5. 样本与许可

- 10 份样本只为工程取样，不是统计代表性结论；数量与类型受 Modrinth 可得性影响。
- 多份样本是 All-Rights-Reserved 或 NC-SA；它们的 jar 与转换件**只在本地**，不得随工具分发。
- `ironchests` 的 CenturyBridge 作者案例只复现到“转换成功”，作者报告的客户端玩法链未复现。
- 没有验证 Fabric API 版本替换、重复 mod id、依赖冲突求解。

## 6. 结论表述

合格的表述：

> 在 2026-10-18 的 Windows 11 + Zulu 21 环境中，对 `ironchests-5.0.2-fabric.jar`（SHA-256 `6a0706...de6`）执行静态分析，得到 1 个消失类、20 个消失成员、19 个描述符变化、12 个 Fabric API 缺失，且 52 条损伤全部能在 1.20.1 索引中复现；CenturyBridge `convert` 产出 `ok_partial` 转换件，其中 28 个调用点被替换为惰性抛错的 tombstone。经本项目规则补丁（含 NBT 签名适配、access widener、registry-aware `fromJson`）后，该转换件在 Fabric 1.21.1 **专用服务端**到达 `Done`，并通过“放置 → 插入 → NBT → 进程重启 → 读回”的容器契约；客户端 GUI/渲染、玩家交互与多人同步**未验证**。lithium 的 `class_14.method_59` 调用点签名已用 javac 桥适配，`ExplosionMixin` 与 POI storage 的 Mixin 目标描述符也已迁移；启动推进到 chunk access 的 `ChunkHolderExtended` cast（chunk API 形状 + CenturyBridge tombstone），仍未通过。

不合格的表述：

> 支持 ironchests、支持 1.21.1、CenturyBridge 已验证兼容。
