# 新增 6 个模组：1.20.1 → Fabric 1.21.1 独立测试

测试日期：2026-10-19。结论：六个原始模组均完成转换和现有通用规则 patch，但 **5 个出现明确兼容性阻断，1 个只通过启动范围验证，没有新增“功能完整兼容”的样本**。这组结果说明项目现有三个样本的成功尚不能推广到其他模组；这些新模组需要新增适配规则。

## 实测矩阵

| 原始 1.20.1 模组 | 客户端实测 | 服务端/功能实测 | 结论 |
|---|---|---|---|
| AppleSkin 2.5.2 | 初始化崩溃：缺失 `ClientPlayNetworking$PlayChannelHandler` | 未到达 HUD / 食物提示测试 | 不兼容 |
| Mod Menu 7.2.2 | 主菜单初始化/绘制崩溃：访问 `TitleScreen.field_32271` 私有字段 | 模组列表尚未打开 | 不兼容 |
| Clumps 12.0.0.4 | 到主菜单并运行 120 tick | 服务端世界启动；不同面值经验球未合并，正向对照成功 | 核心功能失败 |
| FallingTree 4.3.4 | 初始化崩溃：缺失旧客户端网络处理器 | 空服能启动，但玩家加入触发旧 `ServerPlayNetworking.send` 后服务端崩溃 | 不兼容；砍树测试被入服崩溃阻断 |
| FerriteCore 6.0.1 | 到主菜单并运行 120 tick | 服务端世界启动并完成 200 tick 和实体命令；正常保存停服 | 仅启动范围通过；有降级，未验证节省内存效果 |
| ShulkerBoxTooltip 4.0.4 | 到主菜单；换用原生 Cloth Config 后也能启动 | 初始化实际预览 provider 后读取潜影盒，旧 NBT tombstone 抛错 | 预览内容读取契约失败 |

这里的“到主菜单”由客户端生命周期和 120 tick 探针确认；不代表 GUI 交互或联机通过。服务端启动由真实 `Done` 输出确认，并继续运行命令，未把命令回显当成断言。

## 版本、样本与流程

- 测试代码：本地提交 `89419f50f271993de15da44eb9760d9dff84afe5`，内容树 `a165ff60204327834e85418ca416960794f3ad75`。用户所报远端对应提交为 `3a46e84…`；本次使用匹配该内容树的隔离副本，没有 reset 原仓库。
- 目标：Minecraft 1.21.1、Fabric Loader 0.19.5、Fabric API 0.102.0+1.21.1、Zulu Java 21.0.12.1、Windows。
- 引擎：CenturyBridge `cf4ebeba2eaaa49d3746162cc2c10b670d681aec`，七段转换。使用仓库明确提供的 `MixinCheck.java` 编译 stub；没有把这个空实现算成 mixin 检查通过。
- 六个下载文件均经 Modrinth 公布的 SHA-512 校验。版本 ID、下载地址、SHA-256/512、最终转换件 SHA-256 见 `mod-expansion-results.json` 和证据包 `metadata/`。
- 每个样本均从原始 jar 重新转换，然后运行仓库现有 `rules/fabric-1.21.1/container.json`。没有新增模组专用桥，也没有手动删掉功能以强行启动。原生 Fabric API 作为目标平台依赖。
- 每个模组使用隔离 `mods/`；原有 IronChests / TrashSlot / Lithium 未加入。服务端仅监听 `127.0.0.1`，离线身份只用于本机测试。
- 更新后的 Java 项目 `test installDist` 成功：22 个单元测试，0 失败、0 错误。

转换和 patch 的进程退出码全部是 0。引擎同时明确报告了 `partial` / `degraded`、tombstone 和移除的 mixin，因此不能把这个退出码理解成“已兼容”。现有通用规则主要命中了 Identifier 构造器，并未解决本次网络、NBT 数据组件和经验球 mixin 问题。

## 可直接复现的关键失败

### 1. Clumps：启动成功，核心经验球合并已丢失

转换报告为 `ok_degraded`，明确移除了 `MixinExperienceOrb [load-bearing! may be unstable]`。原始 mixin 定义了 `IClumpedOrb` 实现以及不同面值经验球的合并逻辑；转换后的启用配置不再包含这个 mixin。

在相同 1.21.1 运行时中，固定加载区块，冻结 tick，在同一点生成两颗静止、无重力、面值分别为 3 和 7 的经验球，推进 200 tick 后查询所有带测试 tag 的经验球 Value：

| 对照 | 实际输出 | 是否合并 |
|---|---|---|
| 无 Clumps，仅原生 Fabric API | `3s`、`7s` | 否 |
| 从 1.20.1 转换的 Clumps 12.0.0.4 | `3s`、`7s` | 否 |
| 原生 1.21.1 Clumps 19.0.0.1，仅作正向对照 | `10s` | 是 |

正向对照来自 Modrinth `3ene3W1l`，经过 SHA-512 校验。它没有充当转换件。这是功能缺失，不是刷经验或总量丢失的结论。

证据：`runtime/control-server-patched/`、`runtime/clumps-server-patched/`、`runtime/clumps-native-positive-server-native-control/` 中的 `commands.txt` 和 `console.log`；`converted/clumps/report.md`；`jar-inspection/clumps.json`。

### 2. AppleSkin / FallingTree：需要新的 Fabric 网络桥

客户端分别在 `squeek.appleskin.network.ClientSyncHandler.init` 和 `fr.rakambda.fallingtree.fabric.client.network.FabricClientPacketHandler.registerClient` 抛出：

```text
NoClassDefFoundError: net/fabricmc/fabric/api/client/networking/v1/ClientPlayNetworking$PlayChannelHandler
```

FallingTree 服务端单独启动看起来正常，但让不带 FallingTree 的原生 Fabric 测试客户端连接后，在其玩家加入监听器中抛出：

```text
NoSuchMethodError: void ServerPlayNetworking.send(ServerPlayerEntity, Identifier, PacketByteBuf)
at FallingTree FabricServerPacketHandler.onPlayerConnected:30
```

测试客户端已经在服务端登录，失败发生在 FallingTree 的网络回调内；砍树 fixture 尚未执行。不能把此结果写成“树木砍伐失败”或“服务端兼容”。

这次 Minecraft 自己记录 crash report 后以 **0** 退出；这与之前 runner 吞非零退出码的问题不同。测试必须同时检查崩溃日志和功能断言。

证据：`runtime/appleskin-client-patched/crash-reports/`、`runtime/fallingtree-client-patched/crash-reports/`、`runtime/fallingtree-tree-contract/server/console.log` 及 crash report。

### 3. Mod Menu：主菜单字段访问权限变化

在 `ModMenuEventHandler.shiftButtons:115` 触发：

```text
IllegalAccessError: ModMenuEventHandler tried to access private field net.minecraft.class_442.field_32271
```

这是实际被执行的 Mod Menu 代码；不是把未被选用的旧内嵌 Fabric API 当成运行故障。需要重新适配主菜单布局访问方式或访问权限，再测试模组列表和配置入口。

证据：`runtime/modmenu-client-patched/crash-reports/`。

### 4. ShulkerBoxTooltip：进入菜单不代表能读取内容

先创建一个使用原生 1.21.1 `CONTAINER` 数据组件、装有 5 颗钻石的潜影盒 ItemStack，原生读取确认 `nativeContainerCount=5`。显式加载模组 provider 注册，再调用它自己的实际预览接口：

```text
SHULKER_PROVIDER class=...ShulkerBoxPreviewProvider
UnsupportedOperationException: CenturyBridge tombstone:
net.minecraft.class_1799.method_7941 no longer exists in 1.21.1
at BlockEntityPreviewProvider.getInventory:103
```

这是客户端运行时的 **provider 读取契约测试**，没有声称完成物理按键、真实悬停或预览绘制。需要将旧 ItemStack NBT/BlockEntityTag 路径桥接到 1.21.1 数据组件。

第一次探索探针在 provider 注册前调用，返回 null；该次结论标为不确定，没有据此判不兼容。最终依据是 `provider-initialized` 重新测试产生的明确异常。额外用 Cloth Config 15.0.140+fabric 替代被选中的旧内嵌版本，启动也通过；最终读取失败栈位于模组自己的 provider 和 tombstone。

证据：`runtime/shulkerboxtooltip-client-provider-initialized/console.log`；`contracts/ShulkerContractProbe/ShulkerContractProbe.java`。

### 5. FerriteCore：只确认启动，有明确降级

专用服务器生成并加载世界、执行实体命令和 200 tick、保存停服均正常；客户端主菜单 120 tick 存活。转换器移除了 `FastMapStateHolderMixin` 和 `ModelResourceLocationMixin`，前者被标记 load-bearing，另有一个未解决 tombstone。因此不能宣称原有全部优化保留，也不能用这次启动测试证明节省内存。

证据：`converted/ferrite-core/report.md`、`runtime/ferrite-core-server-patched/`、`runtime/ferrite-core-client-patched/`。

## 新发现的分析器误判

FallingTree 的同一个 jar 同时含 `fabric.mod.json`、有效 Fabric main/client 入口和 `META-INF/mods.toml`。分析器因优先选择 TOML，将其标记 `loader=forge` / `wrong_loader`，尽管 Fabric Loader 实际选用 Fabric 入口并启动了服务端。

定位：`java/src/main/java/top/mcbridge1201/scan/ArtifactScanner.java:116` 附近。建议表示“支持多个 loader”，并按测试目标选择有效元数据；跨 loader 闲置类引用应与目标入口的实际依赖分开。其真正存在的网络 API 不兼容仍需报告，不能被“装错 loader”掩盖。

证据：`fallingtree-loader-evidence.json`、`static-original.json` 和实际服务端启动/入服日志。

## 复现材料与范围

证据包包含样本来源和哈希、转换与 patch 日志、静态结果、原始/转换 mixin 配置、逐次启动参数、控制台及崩溃报告、测试脚本和探针源码、单元测试 XML。`SHA256SUMS.txt` 覆盖包内材料。原始/转换模组与 Minecraft jar 均未打包。

现有本机环境的复现顺序：`expand_fetch.py` → `expand_convert.py` → `expand_patch.py` → `expand_runtime.py server` / `client`；随后 `expand_dependencies.py`、`expand_followups.py server` / `client`、`build_expansion_contracts.py`。经验球命令可直接从 `commands.txt` 重放；FallingTree 入服复现使用 `expand_tree_contract.py`。潜影盒契约通过在独立客户端同时安装转换件、Fabric API 和自编译 `ShulkerContractProbe` 重放。脚本放在 `work/` 时使用同目录资源路径；换机器需配置 JDK、游戏缓存、目标依赖与上游引擎源码路径。逐次完整 JVM 命令在各实例 `launch.json`。

无模组对照客户端和服务器都通过。缓存中缺少部分图片/声音资源，正常对照同样出现这些警告；本报告只将明确模组异常、进程状态和契约断言用于兼容性结论。成功客户端在确认结果后由测试工具终止，清理产生的退出码 1 不算启动失败。

本次没有长时间运行、内存收益比较、完整 GUI 手工验收或新增六模组混装测试，也没有为这些新模组写修复规则。原仓库未修改、未推送 GitHub。
