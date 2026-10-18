# 已知限制

本文件记录“这套工具/这轮证据不能说明什么”。任何对外表述都必须带着这些限定。

## 1. 证据阶段

- 目前最高阶段：**`TRANSFORMED`**（CenturyBridge 产出 ironchests 转换件）与 **`ANALYZED`**（10 份样本）。
- `BOOTED`、`WORLD_LOADED`、`CONTRACT_PASSED`、`SET_PASSED`：**全部 pending**。本轮没有成功启动任何 Minecraft 进程。
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
- 桥 jar（`core/shims/1.21.1`）未构建；`build.sh` 的四道门禁一步都没跑。
- 转换件的 jar 签名已被上游清理；不得声称它仍由原作者签名。

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

> 在 2026-10-18 的 Windows 11 + Zulu 21 环境中，对 `ironchests-5.0.2-fabric.jar`（SHA-256 `6a0706...de6`）执行静态分析，得到 1 个消失类、15 个消失成员、19 个描述符变化、12 个 Fabric API 缺失，且 47 条损伤全部能在 1.20.1 索引中复现；CenturyBridge `convert` 产出 `ok_partial` 转换件，其中 28 个调用点被替换为惰性抛错的 tombstone。**未启动游戏，未验证玩法。**

不合格的表述：

> 支持 ironchests、支持 1.21.1、CenturyBridge 已验证兼容。
