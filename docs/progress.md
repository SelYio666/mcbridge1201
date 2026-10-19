# 进度交接

最后更新：2026-10-19 08:10（Asia/Shanghai）。下一轮从这里继续，不必重读方案全文。

更新（2026-10-19 08:10）：**TrashSlot 不是普通 handler slot**。probe 取到 `TrashSlotSlot` 坐标 `152,165`、component anchor `231,211`，但 `handler.field_7761.indexOf(trash)=-1`（46 个槽），说明垃圾桶是客户端自定义 component 绘制/拦截，普通 `clickSlot` 无法定位。P56 的点击/拖拽失败由此解释；仍未完成实际转移。证据 `runs/p58-trash-click/`。
更新（2026-10-19 01:25，修正）：**trash 重进为空是 TrashSlot 登录重置**。`setTrashItem` 同会话读回 5 钻石，live `BalmData/TrashSlot` 也是 `{count:5,id:"minecraft:diamond"}`；但 TrashSlot 的 `PlayerLoginEvent` 显式把 trash 设为 `ItemStack.EMPTY`，所以重进为空不能证明 NBT 桥失败。P57 原结论已修正；GUI 拖放仍是独立未解问题。证据 `runs/p57-trash-persist/`。
更新（2026-10-19 01:15）：**真实 ItemStack 进入背包，trash 拖放未成功**。probe 给玩家 5 钻石，背包显示正常；点击/拖拽到 TrashSlot 按钮后物品仍停在光标，trash 未接收，logs 无异常。这是未验证项，不声称通过。证据 `runs/p56-client-item/`。
更新（2026-10-19 01:05）：**背包 + TrashSlot GUI 渲染**。合成 E 键不可靠，改用客户端测试 mod 自动打开 `InventoryScreen`；截图显示原版背包和右下角 TrashSlot 按钮。点击空 trash 按钮不改变界面；物品移入/移出、持久化、容器 GUI、同步仍未验证。证据 `runs/p55-client-gui/`。
更新（2026-10-19 01:00）：**客户端进入世界并渲染**。补 `LithiumVarIntBridge`（`class_8703.method_53015`）后，世界生成通过，客户端加入单人世界、渲染地形/HUD；截图 `runs/p54-client-lithium/world.png`。trash GUI/容器持久化/同步仍未执行。证据 `runs/p54-client-lithium/`。
更新（2026-10-19 00:55）：**世界加入越过 Balm payload**。修正旧 Balm writer 参数顺序 `(packet, buf)` 后，`trash_slot_content` 编码错误消失；客户端进入世界生成，新阻断为 lithium `class_2540.method_10815` tombstone（对应 1.21.1 `VarInt.getByteSize`）。证据 `runs/p53-client-world/`。
更新（2026-10-19 00:50）：**客户端到达主菜单**。PCL Fabric 1.21.1 客户端加载全部五个模组并进入主菜单（截图）；Balm 客户端初始化、ironchests 模型加载桥已补。创建/进入世界时 server 端 `BalmNetworking.sendTo` 的 payload 编码仍失败（`class_9129` vs `MessageTrashSlotContent`），未进入世界/GUI。证据 `runs/p52-client-balm/`。
更新（2026-10-19 00:40）：**ResourcefulLib 客户端网络桥生效**。重写嵌套 RL 2.0.6 的 `FabricClientPacketHelper` 到 1.21.1 Payload API；客户端越过 ironchests **main** 入口点，新阻断为 `ModelLoadingRegistry` 缺失与 `BalmClient.initialize(String,Runnable)` 缺失。证据 `runs/p51-client-bridge/`。
更新（2026-10-19 00:35）：**首次真实客户端运行（PCL）**。已装 1.21.1 Fabric 0.19.5 客户端；五个模组全部加载，ironchests 入口点崩溃：`ClientPlayNetworking$PlayChannelHandler` 缺失（旧 ResourcefulLib 2.0.6 客户端网络 API）。换 ResourcefulLib 3.0.12 会在 `PacketHandler` 处失败。这是新的真实客户端阻断，不是服务端问题。证据 `runs/p50-client/`。
更新（2026-10-19 00:05）：**`@At.ordinal` 提取**。`Injection.atOrdinal` + `mixinAtOrdinals`；lithium 86 at-targets 中 10 个带 ordinal；仅提取，不做匹配指令计数/越界校验；测试 **22/22**。证据 `runs/p49-at-ordinal/`。
更新（2026-10-18 23:59）：**nested jar mixin 展开**。scanner 读取 `META-INF/jars/*.jar` 内的 `.mixins.json`，带 `!/` 前缀；ironchests P26 从 0 mixin/0 injection 变为 **1/1**（unresolved 0），lithium 保持 202/214/86/3；测试 **21/21**。证据 `runs/p48-nested-mixins/`。
更新（2026-10-18 23:58）：**字段 `@At` 解析测试**。`FIELD` target `class_14.field_99:L...;` 的 owner/name/desc/`atTargetField` 全部断言；测试 **20/20**。证据 `runs/p47-field-at/`。
更新（2026-10-18 23:55）：**多 method injection 数组回归测试**。`method_59`+`method_60` 产生两条 Injection 且共享 at-target；测试 **19/19**。证据 `runs/p46-multi-method/`。
更新（2026-10-18 23:50）：**剩余工作边界文档**。新增 `docs/remaining-work.md`：服务端/静态工作已覆盖；客户端 GUI/网络/多人因无 client fixture 未执行；chunk 优化、nested mixin 静态分析、Forge 分析列为非阻塞后续。没有新增“客户端通过”声明。
更新（2026-10-18 23:45）：**三样本 bundle profile**。新增 `profiles/bundle-all-three__fabric-1.21.1.json`，`passed_within_scope`：coexistence + 容器 5/5 + 225-chunk stress + CodecDispatch probe；profiles 索引已更新。证据 `profiles/`。
更新（2026-10-18 23:42）：**三样本 + CodecDispatch probe 通过**。all-three 实例加载 P37 probe，`Done (5.425s)`、`CODEC_DISPATCH_PROBE_OK`；证明安全 Codec 包装在 lithium/trashslot/Balm 同时加载时仍正常。证据 `runs/p43-all-three-codec/`。
更新（2026-10-18 23:55）：**三样本同服 chunk 压力测试通过**。all-three 实例 force-load 225 chunks、远角方块 save/restart 断言全 true，两进程 exit 0；说明 lithium chunk 移植在 ironchests/trashslot/Balm 同时加载时仍正常。证据 `runs/p42-all-three-chunk/`。
更新（2026-10-18 23:50）：**三样本同服通过**。lithium + ironchests(P26) + trashslot(P29)/Balm 21 同实例，`Done (4.632s)`；容器契约两次重启 5/5 通过。证据 `runs/p41-all-three/`。
更新（2026-10-18 23:45）：**证据总校验扩展**。`tools/verify_evidence.py` 增加 P35/P36 at-target 计数和 lithium profile 检查；全部 checks true，exit 0。证据 `runs/p40-verify-extended/`。
更新（2026-10-18 23:40）：**证据总校验工具**。新增 `tools/verify_evidence.py`，一次性检查 18 个测试、P14/P24/P26/P27/P33/P37/P38 证据和“无 tracked jar”；本次 `passed=true`，exit 0。证据 `runs/p39-verify-evidence/`。
更新（2026-10-18 23:35）：**P29 client bridge 的 BytecodeVerify**。`trashslot-client-aw.jar` 顶层 47 classes / 0 failures，覆盖 `BalmNetworkingBridge`/`$Payload`/`$Client`；客户端分支仍未执行。证据 `runs/p38-client-bv/`。
更新（2026-10-18 23:30）：**CodecDispatch 语义 probe 通过**。用 `RecordCodecBuilder` 的 `Box(int a)` 做 `CodecDispatch.dispatch` encode/decode，期望 `{"a":1,"type":"k"}`，日志 `CODEC_DISPATCH_PROBE_OK`；服务端 `Done (4.847s)`、exit 0。直接验证了 P26 安全 MapCodec 包装的编解码语义。证据 `runs/p37-codec-probe/`。
更新（2026-10-18 23:25）：**at-target 补丁前后对照**。转换件 `214 injections / 86 at-targets / 3 unresolved`，补丁件 `209 / 84 / 0`；P11/P13 规则清掉了 3 个已知构造器，at-target 解析保持一致。证据 `runs/p36-patched-at/`。
更新（2026-10-18 23:20）：**refmap `@At` 目标解析**。`atRawTarget` 也走 refmap，lithium 的 `mixinAtTargets` 从 0 提升到 **86**，`mixinInjectionsUnresolved` 仍为 3（已知构造器），没有新增 false positive；测试 18/18。证据 `runs/p35-at-refmap/`。
更新（2026-10-18 23:15）：**`@At` 目标提取（保守）**。scanner 解析 `@Inject` 等的 `@At(value,target)`，analyzer 对 intermediary 的 INVOKE/FIELD 目标做存在性检查；转换后 lithium `mixinInjections=214`、`mixinAtTargets=0`（Yarn/refmap 目标跳过）、3 个已知构造器 unresolved；测试 18/18。证据 `runs/p34-at-targets/`。
更新（2026-10-18 23:10）：**trashslot 三个包 codec 全部往返通过**。`MessageTrashSlotClick`/`MessageTrashSlotContent` 的空栈与 5 钻石、`MessageDeleteFromSlot(3,true)` 均通过，日志 `TRASHSLOT_ALL_CODEC_OK`；服务端 `Done (4.993s)`、exit 0。仍不含客户端投递/GUI。证据 `runs/p33-all-packets/`。
更新（2026-10-18 23:05）：**trashslot packet codec 往返通过**。服务器内 probe 对空栈与 5 钻石分别执行 `MessageTrashSlotClick.encode/decode`，断言 empty/count/item 全部通过，日志 `TRASHSLOT_CODEC_OK`；服务端 `Done (5.025s)`、exit 0。验证了 4 个 ItemStack/NBT 桥和 registry-aware codec，仍不含客户端网络投递。证据 `runs/p32-trashslot-codec/`。
更新（2026-10-18 23:00）：**CodecDispatch 选择逻辑回归测试**。新增 `JarPatcherCodecDispatchTest`，验证 `--bridge-dir` 提供的 javac `CodecDispatch` 优先于 generated fallback，且不嵌入 `CodecDispatch$Adapter`；测试 18/18。证据 `runs/p31-codec-selection/`。
更新（2026-10-18 22:55）：**lithium / trashslot 兼容档案**。新增 `profiles/lithium...json`（`booted_within_scope`，boot + 225-chunk + combined）与 `profiles/trashslot...json`（`booted_within_scope`，原生 Balm 21；客户端/网络未执行），并加 `profiles/README.md` 索引；所有 hash 由脚本从实际文件计算。证据 `profiles/`。
更新（2026-10-18 22:50）：**trashslot clientbound receiver 已接入**。`BalmNetworkingBridge$Client` 在客户端用 `ClientPlayNetworking.registerGlobalReceiver` 调用旧 `BiConsumer<Player,T>`；服务端通过环境反射跳过，专用服务端仍 `Done (4.894s)`。客户端分支未执行，不能宣称客户端通过；证据 `runs/p29-client-receiver/`。
更新（2026-10-18 22:45）：**P26 安全 Codec 构建的 BytecodeVerify**。`ironchests-safe-aw.jar` 顶层 73 classes / 0 failures，nested ResourcefulLib 142 classes / 0 failures，exit 0；运行侧由 P26/P27 契约覆盖。证据 `runs/p28-codec-verify/`。
更新（2026-10-18 22:40）：**P26 安全 CodecDispatch 的联合契约回归**。在 lithium + ironchests 同实例中换用 P26 的 `ironchests-safe-aw.jar`，两进程容器契约 5/5 通过、两次 `Done`、exit 0；说明安全 Codec 适配没有破坏 P14 的共存路径。证据 `runs/p27-combined-safe-codec/`。
更新（2026-10-18 22:35）：**Codec.dispatch 安全 MapCodec 适配**。活跃路径改用 javac `CodecDispatch`，用 `MapCodec.of(MapEncoder, MapDecoder)` 真正包装旧 `Codec`，不再依赖 `assumeMapUnsafe`；重新补丁 ironchests 后容器契约 5/5 通过，测试 17/17。证据 `runs/p26-codec-safe/`。
更新（2026-10-18 22:30）：**Codec.dispatch 空结果保护**。`CodecDispatch$Guard` 把 `assumeMapUnsafe` 的 null-success 变成 `DataResult.error`，避免 `Optional.of(null)` 外泄；重新补丁 ironchests 后容器契约 5/5 通过，测试 17/17。证据 `runs/p25-codec-guard/`。
更新（2026-10-18 22:25）：**chunk 压力测试工具化**。新增 `tools/run_chunk_stress.py`：两进程 force-load 225 chunks、远角方块、save/restart、`execute if block` 断言，输出 `verdict.json`；本次运行 `chunksMarked=225`、`STRESS_OK_A/B`、`passed=true`，exit 0。证据 `runs/p24-chunk-stress-tool/`。
更新（2026-10-18 22:20）：**lithium chunk-access 压力测试通过**。224 个 forceload chunk（`[-7,-7]` 到 `[7,7]`），在远角设置钻石/绿宝石块，save/restart 后 `execute if block` 分别输出 `STRESS_OK_A/B`；两次 `Done`、exit 0。说明 P13 chunk 移植不只在单 chunk 探针上正确。证据 `runs/p23-chunk-stress/`。
更新（2026-10-18 22:15）：**注入目标静态检查交叉验证**。同一 1.21.1 索引下：转换后 lithium `214/3`（3 个 unresolved 正是 P11/P13 的构造器阻断），补丁后 lithium `209/0`；Balm `43/0`，ironchests/trashslot 顶层无 mixin。说明 P21 的检查能在补丁前发现真实阻断、补丁后清零。证据 `runs/p22-cross-analyze/`。
更新（2026-10-18 22:10）：**refmap 注入目标解析**。读取 mixin config 的 refmap，把命名目标映射到 `Lowner;method(desc)`（含构造器），`Analyzer` 现在能静态复现 lithium 的 3 个已知构造器变化：`class_4180`(POI)、`class_3610`(FluidState)、`class_1927`(Explosion)。测试 16/16；证据 `runs/p21-refmap/`。
更新（2026-10-18 22:05）：**Mixin 注入目标提取 + 保守校验**。`ArtifactScanner` 解析 `@Inject`/`@Redirect` 等的 `method` 目标，`Analyzer` 新增 `mixinInjections`/`mixinInjectionsUnresolved`；只校验 intermediary 名称+描述符，命名/refmap/构造器跳过。测试 15/15；转换后 lithium 实跑 `214` 个注入目标、`0` unresolved；证据 `runs/p20-mixin-inject/`。
更新（2026-10-18 21:55）：**BytecodeVerify 已跑**。编译 CenturyBridge 的 `BytecodeVerify.java`，对 ironchests/lithium/trashslot 三个补丁 jar 的顶层类验证：650 classes / 3 jars，0 failures；再对 ironchests 内嵌 ResourcefulLib：141 classes，0 failures。仍只是栈深度校验；证据 `runs/p19-bytecode-verify/`。
更新（2026-10-18 21:53）：**嵌套 jar 的桥改为按 jar 嵌入**。`JarPatcher` 为每层 jar 记录 `used` 集合并把生成的/javac 桥嵌入使用它的那个 jar；新增 synthetic nested jar 测试，ironchests 重补丁只在 nested ResourcefulLib jar 多出 `IdentifierFactory`，容器契约 5/5 仍通过。测试 13/13；证据 `runs/p18-nested-bridges/`。
更新（2026-10-18 21:50）：**trashslot 到达专用服务端 `Done`**。用原生 Balm 21.0.66 + call-site 桥（`Balm.initialize` 加 context；旧 Balm 网络注册 → Fabric `PacketType`/`StreamCodec` 载荷桥）+ 4 个 ItemStack/NBT 桥，`Done (4.655s)`，世界加载/保存。仍是 BOOTED，客户端 GUI/网络包往返未验证；证据 `runs/p17-balm-net/`。
更新（2026-10-18 21:45）：**Balm 初始化调用点桥已推进 trashslot，但卡在 Balm 网络 API**。`Balm.initialize(String,Runnable)` → `initialize(String, EmptyLoadContext, Runnable)` 的 call-site 桥生效，旧的初始化 `NoSuchMethodError` 消失；下一失败是 `BalmNetworking.registerServerboundPacket(Identifier, Class, BiConsumer, Function, BiConsumer)`，Balm 21 已改为 `PacketType`/`StreamCodec` 载荷注册。仍未 boot，规则保持 prepared/unverified；证据 `runs/p16-balm/`。
更新（2026-10-18 21:40）：**第三个样本 trashslot 尝试受阻于 Balm/Fabric networking**。trashslot 自身的 4 个 ItemStack/NBT tombstone 已写桥并 patch，但依赖 Balm：转换 Balm 7.3.44 后卡在 Fabric API 移除的 `ServerPlayNetworking$PlayChannelHandler`，改用原生 Balm 21.0.66 又卡在 `Balm.initialize(String,Runnable)` 被移除。未 boot，未宣称通过；证据 `runs/p15-trashslot/`。
更新（2026-10-18 21:35）：**lithium + ironchests 联合容器契约通过**。同一 Fabric 1.21.1 专用服务端实例加载两份转换件，`run_contract.py` 两进程放置/插入/NBT/重启读回 5 钻石全部通过；说明 P13 chunk access 移植没有破坏容器持久化，且两样本可共存。证据 `runs/p14-lithium-ironchests/`，说明 `docs/baseline.md` §7.20。仍不含 lithium 自身玩法/客户端。
更新（2026-10-18 21:25）：**lithium 到达专用服务端 `Done`**。`ServerChunkManagerMixin` 的 chunk access 实现整体移植到 1.21.1 `ChunkResult`/`GenerationChunkHolder` API（保留 mixin 类与 `@Overwrite`，不是 strip），启动 `Done (4.772s)`，世界加载/保存，`forceload`/`setblock`/`data get` 命令探针通过。规则 `mixinClassReplacements`，证据 `runs/p13-chunk-port/`，说明 `docs/baseline.md` §7.19。仍只是 BOOTED，不是玩法/客户端兼容。
更新（2026-10-18 21:05）：**Mixin 目标描述符适配已实现**：lithium 的 `ExplosionMixin` 与 POI `SerializingRegionBasedStorageMixin` 两处 `@Inject` 目标签名迁移成功，服务端推进到 chunk access 的 `ChunkHolderExtended` cast（下一阻断是 1.21.1 chunk API 形状 + CenturyBridge tombstone，不是描述符）。说明见 `docs/baseline.md` §7.18、`rules/fabric-1.21.1/lithium.json`、`runs/p11-lithium-explosion/`。
更新（2026-10-18 20:50）：**调用点签名适配已实现并用 lithium 的 `class_14.method_59` 验收**。补丁后 `NoSuchMethodError` 消失，启动推进到下一失败（`world.explosions.ExplosionMixin` 的注入目标变化）。规则、桥、命令、退出码与日志见 `docs/baseline.md` §7.17、`rules/fabric-1.21.1/lithium.json`、`runs/p10-lithium-signature/`。

## 本轮做了什么

1. 建立独立研发目录 `mcbridge1201/`（未改动用户已有项目、游戏实例和 `.minecraft`）。
2. 环境核查：JDK 21 / Gradle 9.8.1 / Git / Python 3.12 可用；**无 JDK 17**；PowerShell 与 git 的 HTTPS（schannel）不可用；`%TEMP%` 与工作区 `Files.isWritable` 异常。
3. 锁定上游：Retromod `e693278...`、CenturyBridge `cf4ebeba...`，均 MIT，许可证文本与快照 hash 入 `manifests/upstream.lock.json`。
4. 建立 10 份 1.20.1 样本（5 Fabric + 5 Forge），Modrinth sha512 与自算 sha256 双校验。
5. 实现并运行自研分析器 `mcbridge1201`（Gradle + ASM）：目标/源双索引、继承解析、命名空间区分、mixin 目标存在性、JSON 计划输出、Markdown 矩阵；3 个单元测试。
6. 实测 CenturyBridge：引擎编译（需本地补 `MixinCheck` 空实现）、生成 1.20.1→1.21.1 的 7 节分段、转换 ironchests（`ok_partial`，28 tombstone，55 条未记账引用）。
7. **突破启动阻塞**：新增 body-preserving 重映射器（ASM + ZipOutputStream，绕开 zipfs 只读），修复方法名传播、字段传播、lambda invokedynamic 命名；Fabric 1.21.1 专用服务端到达 `Done (4.803s)` 并正常停止 → **BOOTED**。
8. **转换件首次运行时验证**：ironchests 被 Loader 接受（`Loading 42 mods` 含 ironchests 5.0.2），入口点抛 `NoSuchFieldError: ItemPredicate.ANY`（`class_2073.field_9640`）→ **LOADED，未通过**。
9. 这次崩溃暴露分析器漏报（字段解析把 JDK 接口祖先当未知），修正后 ironchests 确认损伤 47→52，新增的正是该字段 → 静态预测与真实崩溃一致。
10. **第一条转换规则 + 桥**：`rules/fabric-1.21.1/container.json` 把 `ItemPredicate.ANY` 重定向到生成的 `ItemPredicateAny.any()`；`patch` 命令同时做常量池种类修正（class→interface，123 处 + 3 个 method handle），并递归处理 JiJ。ironchests 因此**通过入口点**。
11. **第二、三条规则**：`codec.dispatch.mapcodec-shape`（重定向到生成桥，`MapCodec.assumeMapUnsafe`）与 `itempredicate.fromjson.static`（重建 1.20.1 的 `fromJson`，且调用点是 MethodHandle）。规则引擎现在支持字段/方法/句柄重定向、常量池种类修正、JiJ 递归。
12. **access widener 打通注册**：1.21.1 私有化 `Identifier(String,String)`，逐点改写覆盖 13 处后仍有一处参数由方法调用产生；改为注入 `rules/fabric-1.21.1/mcbridge.accesswidener`（+ `tools/inject_aw.py`），转换件**随服务端到达 Done（1.134s），世界加载完成**。
13. **最小容器契约（无客户端）**：`setblock` 放置 `ironchests:iron_chest` 成功、`item replace` 插入钻石成功；但 `data get block` 没有 `Items`，重启后仍无。对照 vanilla chest 同一命令有 `Items`。
14. **根因已定位**：`GenericChestBlockEntity.method_11007/11014` 仍是 1 参数的旧签名，而 1.21.1 的 `BlockEntity` 已带 `WrapperLookup` 参数，导致方法不再 override，vanilla 保存走基类实现——静默丢物品。
15. **签名适配规则修复持久化**：新增 `signatureAdaptations`（描述符迁移 + 局部槽平移 + 调用补参 + 帧重算），把两个 NBT 覆写迁到 2 参，并给 `super` 与 `ContainerHelper.save/loadAllItems` 补 `WrapperLookup`。
16. **容器契约通过（服务端命令范围）**：放置 `ironchests:iron_chest` → 插入 5 钻石 → NBT 出现 `Items` → 重启进程 → 读回 `Items[0].count = 5`。证据：`runs/p5-contract-nbt-fix/`、`runs/p5-contract-nbt-restart/`。
17. **第二份样本 lithium**：转换 `ok_degraded_partial`、加载成功（131 个配置项）；两次 mixin 注入失败通过显式 `mixinStrips` 降级绕过，随后卡在 `class_14.method_59` 的 `NoSuchMethodError`（签名变化）。
18. **降级机制**：`mixinStrips` 记录 id/配置/类/原因，单独档案 `rules/fabric-1.21.1/lithium-degraded.json`；实例已恢复 ironchests 并重跑契约通过。
19. **降级探针**：`fromJson` 的回退实际被触发（`{"items":["minecraft:dirt"]}` 被 1.21.1 codec 拒绝），确认这是真实的语义弱化；下一步改为 registry-aware 构造。
20. **交付物成型**：`tools/build_reports.py` 从锁文件与证据生成兼容档案（`profiles/ironchests-5.0.2-fabric__fabric-1.21.1.json`；p9 之后状态升为 `passed_within_scope`）与支持矩阵（`docs/support-matrix.md`），字段与证据哈希全部来自实际文件。
20b. 产出 `docs/baseline.md`、`docs/engine-selection.md`、`docs/limitations.md`、`rules/README.md`、生成矩阵、`runs/SHA256SUMS.txt`。

## 2026-10-18 20:50 更新：调用点签名适配

21. **规则引擎新增 `callSiteAdaptations`**：按精确 `(owner, name, oldDesc[, opcode])` 匹配直接调用与 `MethodHandle`，重定向到 `INVOKESTATIC` 桥；桥可以是 javac 源码编译产物，不再只能由 `BridgeGenerator` 生成 ASM。未知桥会硬失败，避免产出悬空调用。
22. **lithium 桥写成 Java 源码**：`WalkNodeEvaluatorCheckNeighbourBlocks`，按 1.20.1 `checkNeighbourBlocks` 的真实字节码逐条移植（3×3×3 邻居、DANGER_OTHER/DANGER_FIRE/WATER_BORDER/DAMAGE_CAUTIOUS、保留 `MutableBlockPos` 副作用）。语义依据来自 body-preserving remap 后的 `javap -c`，不是猜。
23. **工具链打通**：`tools/build_bridges.py` 对 `client-1.21.1-intermediary.jar` 编译（需 gson + datafixerupper 两个 lib）；`patch --bridge-dir` 嵌入；`tools/inject_bridges.py` 可独立替换/补齐（也修了“只替换、不新增”的限制）。
24. **验收结果**：lithium 补丁 `walknodeevaluator.checkneighbourblocks.view-to-context` 命中 **2** 次（`PathNodeCache.getNodeTypeFromNeighbors`、`AbstractBlockStateMixin.init`）；服务端启动不再抛 `NoSuchMethodError`，推进到 `ExplosionMixin` 的 `@Inject` 目标不匹配；`doneSeen=false`，runner exit 11，属“下一失败”而不是通过。回归检查：用 `container.json` 重补 ironchests，输出与既有 `-patched.jar` 逐字节相同（SHA-256 `7d89d452...bc9a1`）。
25. **测试与证据**：新增 `CallSiteAdaptationTest`（精确匹配）与 `JarPatcherCallSiteTest`（合成 jar 端到端 + 缺桥拒绝）；`gradle test` 8/8 通过。日志、哈希、复现命令在 `runs/p10-lithium-signature/README.md`。

## 2026-10-18 21:05 更新：Mixin 目标描述符适配

26. **规则引擎新增 `mixinCallbackAdaptations`**：支持 `append`（在 CallbackInfo 前插新参数、平移局部变量、重写 `@Inject.method`）与 `replace`（替换回调捕获参数、清过期调试元数据、按新描述符算 `maxLocals`）；可选 `refmap` 重写，防止 Mixin 继续用旧 refmap 锁定旧签名。
27. **ExplosionMixin**：1.21.1 `Explosion` 构造器追加 `ParticleOptions, ParticleOptions, Holder<SoundEvent>`；回调体只读 shadow 字段，因此插入 3 个未使用参数槽即可，语义不变。
28. **POI `SerializingRegionBasedStorageMixin`**：`SectionStorage` 构造器从 `Path/DataFixer/...` 变为 `SimpleRegionStorage/RegistryAccess/ChunkIOErrorReporter/...`；回调体只用 `this`，替换捕获参数，并把 refmap 的 `"<init>"` 映射改到新描述符。
29. **结果**：补丁命中 Explosion 1 次、POI 1 次、refmap 1 次；服务端不再有这两处注入失败，走到 `Preparing level "world"`，随后在 `class_3215.getChunkBlocking` 抛 `ClassCastException: class_3193 cannot be cast to ChunkHolderExtended`。`doneSeen=false`，runner exit 11，JVM exit 0；仍不是兼容通过。
30. **下一阻断分析**：CenturyBridge 移除了 `ChunkHolderMixin`（`field_16425` / `class_3193$class_3724` 消失），保留的 `ServerChunkManagerMixin` 仍 cast 到 `ChunkHolderExtended`。直接 re-add 失败（`@Shadow field_16425` 不存在）；本地化 field 的实验越过 cast 但撞上 `class_3898.method_17236` tombstone。两者都记录在 `runs/p11-lithium-explosion/`，**均未采用**，也没有用 mixin strip 掩盖。
31. **测试**：新增 `MixinCallbackAdaptationTest`（append/replace/refmap 合成 jar），`gradle test --rerun-tasks` 11/11 通过。

## 2026-10-18 21:25 更新：chunk access 移植，lithium BOOTED

32. **`mixinClassReplacements`**：新增规则类型，保留原 mixin 类名/`@Overwrite`，用 javac 编译的 1.21.1 实现替换原类，并嵌入 helper 类。
33. **`ServerChunkManagerMixin` 1.21.1 移植**：调用 `ServerChunkManager.method_14134`，用 `ChunkAccessPump` 反射泵私有 chunk 队列，`ChunkResult.method_57130(null)` 取 chunk；移除对 `ChunkHolderExtended`/`method_17236`/`Either` 的依赖。保留 mixin，不是 strip。
34. **工具链**：`tools/build_mixins.py` 对 `work/remap/server-intermediary.jar` + Sponge Mixin lib 编译；`build_bridges.py` 编译 `ChunkAccessPump`；`patch --bridge-dir work/bridges --bridge-dir work/mixins` 统一嵌入。
35. **结果**：lithium 补丁 `chunkresult-port` 1 次；服务端 `Done (4.772s)`，三主世界保存；命令探针 `forceload add 0 0` / `setblock` / `data get` 通过。仍是 BOOTED，不是玩法/客户端兼容。
36. **测试**：新增 `MixinClassReplacementTest`；`gradle test --rerun-tasks` 12/12 通过。

## 2026-10-18 21:35 更新：lithium + ironchests 联合契约

37. **联合实例**：同一 Fabric 1.21.1 专用服务端加载 P13 lithium jar + P5 ironchests AW jar。
38. **契约**：`run_contract.py` 两个真实进程，放置 `ironchests:iron_chest` → 插入 5 钻石 → NBT 出现 `Items` → 重启 → 读回 5；5 个断言全部 true，`passed=true`。
39. **意义**：P13 的 chunk access 移植没有破坏容器 NBT 持久化，两份转换件可以共存；仍只是专用服务端 + 命令 API，不含 GUI/渲染/多人或 lithium 自身玩法。
40. **证据**：`runs/p14-lithium-ironchests/README.md`、`verdict.json`、两步日志。

## 2026-10-18 21:40 更新：第三个样本 trashslot（受阻）

41. **转换**：trashslot 15.1.5 `ok_partial`，4 个 tombstone（ItemStack writeNbt/fromNbt、FriendlyByteBuf write/readItemStack）。
42. **桥与规则**：`TrashSlotNbtBridge` + `rules/fabric-1.21.1/trashslot.json`，用 1.21.1 `ItemStack.CODEC` + `RegistryOps(NbtOps)` 和 `FriendlyByteBuf` NBT 方法；patch 命中 1+1+2+2 次。
43. **依赖阻断**：trashslot 依赖 Balm。转换 Balm 7.3.44 后注入 AW，仍卡在 Fabric API 移除的 `ServerPlayNetworking$PlayChannelHandler`；原生 Balm 21.0.66（1.21.1）又缺少 `Balm.initialize(String,Runnable)`。未 boot。
44. **状态**：trashslot 规则标记为 **prepared / not boot-verified**；不是通过。证据 `runs/p15-trashslot/README.md`。

## 2026-10-18 21:45 更新：Balm 初始化桥（仍有网络阻断）

45. **`BalmInitializeBridge`**：`Balm.initialize(String,Runnable)` → `initialize(String, EmptyLoadContext, Runnable)` 的 call-site 适配；patch 命中 1 次，旧的初始化 `NoSuchMethodError` 消失。
46. **下一失败**：`BalmNetworking.registerServerboundPacket(Identifier, Class, BiConsumer, Function, BiConsumer)`；Balm 21 改为 `PacketType`/`StreamCodec` 载荷注册，不是可简单补 context 的描述符。
47. **状态**：trashslot 仍未 boot；NBT 桥 + Balm 初始化桥 prepared，整体 unverified。证据 `runs/p16-balm/README.md`、`server-balm2.log`。

## 2026-10-18 21:50 更新：trashslot BOOTED

48. **Balm 网络桥**：旧 `BalmNetworking.registerServerboundPacket(Identifier,Class,BiConsumer,Function,BiConsumer)` / `registerClientboundPacket` 重定向到 `BalmNetworkingBridge`；桥把包类包成 `CustomPayload`，用旧 encode/decode 构造 `StreamCodec<RegistryFriendlyByteBuf,T>`，注册 playC2S/playS2C 与 `ServerPlayNetworking` 全局接收器（serverbound 2 次、clientbound 1 次）。
49. **结果**：原生 Balm 21.0.66 + trashslot 补丁 `Done (4.655s)`，世界加载/保存；`doneSeen=true`，runner/JVM exit 0。
50. **范围**：BOOTED，不是客户端/玩法通过；没有客户端连接，clientbound receiver 未安装，包 encode/decode 与 ItemStack NBT 桥未被玩家动作触发。
51. **证据**：`runs/p17-balm-net/README.md`、`verdict.json`、`server-net2.log`、`patch2.log`。

## 2026-10-18 21:53 更新：嵌套 jar 桥按 jar 嵌入

52. **修改**：`JarPatcher.patchEntries` 增加 per-jar `used` 集合；`recordBridge` 同时记入全局报告和当前 jar；`embedUsedBridges` 在每层 jar 结束时嵌入生成的/javac 桥。顶层未使用的桥不再溢出，nested jar 拿到自己的副本。
53. **测试**：新增 `embedsBridgeInsideNestedJarThatUsesIt`（synthetic nested jar）；`gradle test --rerun-tasks` **13/13**，exit 0。
54. **ironchests 回归**：重补丁规则计数与旧结果一致；顶层类/桥完全相同，唯一差异是 nested ResourcefulLib 多出 `IdentifierFactory.class`；整体 hash 变为 `aa589bbb...0430`（AW 前），属预期。新 jar 启动 `Done`，容器契约 5/5（放置/插入/NBT/重启读回 5 钻石）。
55. **证据**：`runs/p18-nested-bridges/README.md`、`contract/verdict.json`、`gradle-test.log`。

## 2026-10-18 21:55 更新：BytecodeVerify

56. **编译**：CenturyBridge `core/tools/BytecodeVerify.java` + ASM 9.7.1/asm-analysis，输出到 `work/tmp/bytecodeverify`。
57. **顶层**：ironchests/lithium/trashslot 三个补丁 jar，**650 classes / 3 jars，0 methods failed**，exit 0。
58. **nested**：ironchests 的 ResourcefulLib jar，**141 classes，0 failures**，exit 0。
59. **边界**：`BasicInterpreter` 只检查栈深度/`max_stack`；其他 nested jar/客户端路径未覆盖。证据 `runs/p19-bytecode-verify/`。

## 2026-10-18 22:05 更新：Mixin 注入目标提取

60. **扫描器**：`ArtifactScanner` 解析 `@Inject`/`@Redirect`/`@ModifyConstant` 等的 `method` 值（单值/数组/owner 前缀），存入 `MixinInfo.injections`。
61. **分析器**：`Analyzer.Result` 新增 `mixinInjections` / `mixinInjectionsUnresolved` / `unresolvedMixinInjections`；只对 `method_*` + 明确描述符查 1.21.1 索引，缺失/描述符不匹配会进入 `blocked_static`。
62. **测试**：新增 `MixinInjectionScanTest` 与 `AnalyzerCoreTest` 的 missing-target 用例；`gradle test --rerun-tasks` **15/15**，exit 0。
63. **实跑**：转换后 lithium `mixins=202`、`mixinInjections=214`、`mixinInjectionsUnresolved=0`；0 是保守策略的结果（Yarn/refmap/构造器跳过），提取路径已被 214 个目标覆盖。
64. **边界**：不是运行时 Mixin 验证；refmap/命名描述符/构造器/ordinal/slice/local capture 仍未解析。证据 `runs/p20-mixin-inject/`。

## 2026-10-18 22:10 更新：refmap 注入目标解析

65. **refmap**：`ArtifactScanner` 读取 mixin config 的 `refmap`，把命名目标映射到 `Lowner;method(desc)`；新增 `Injection.targetOwner/rawTarget`。
66. **构造器**：`Analyzer` 现在校验 `<init>` 精确描述符，不再跳过。
67. **验证**：转换后 lithium `mixinInjections=214`、`mixinInjectionsUnresolved=3`，正好是 `class_4180`(POI)、`class_3610`(FluidState)、`class_1927`(Explosion) 三个已知构造器变化；静态分析独立复现了 P11/P13 的运行时阻断。
68. **测试**：新增 refmap 映射测试；`gradle test --rerun-tasks` **16/16**，exit 0。
69. **边界**：只检查精确描述符；ordinal/slice/local capture、非 refmap 命名目标仍未解析。证据 `runs/p21-refmap/`。

## 2026-10-18 22:15 更新：注入目标交叉验证

70. **转换 vs 补丁**：同一索引下，转换后 lithium `214` 个目标 / `3` unresolved；补丁后 lithium `209` / `0`。3 个 unresolved 正是 P11/P13 的 POI/FluidState/Explosion 构造器变化，补丁后清零。
71. **其他样本**：Balm 转换后 `32` mixins / `43` 目标 / `0` unresolved；ironchests/trashslot 顶层无 mixin（nested 未展开）。
72. **意义**：P21 的检查不是 synthetic-only；它能在补丁前发现真实阻断、补丁后确认清零。
73. **边界**：顶层 mixin、精确描述符；ordinal/slice/local capture 与 nested mixin 未覆盖。证据 `runs/p22-cross-analyze/`。

## 2026-10-18 22:20 更新：lithium chunk 压力测试

74. **场景**：`fabric-1.21.1-server-lithium`，forceload `224` 个 chunk（`[-7,-7]` 到 `[7,7]`），在 `(112,100,112)` 与 `(-112,100,-112)` 设置钻石/绿宝石块，`save-all flush` 后停止。
75. **重启**：新 JVM `forceload add` 显示“No chunks were marked”（force-load 状态持久化），`execute if block` 远角两块均输出 `STRESS_OK_A` / `STRESS_OK_B`；两次 `Done`，exit 0。
76. **意义**：P13 chunk access 移植在更大 chunk 集与保存/重启路径上仍然正确，不只是单 chunk 命令探针。
77. **边界**：专用服务端 + 命令 API；无客户端/玩家/多人；chunk 优化减少仍在。证据 `runs/p23-chunk-stress/`。

## 2026-10-18 22:25 更新：chunk 压力测试工具

78. **工具**：`tools/run_chunk_stress.py` 自动跑两个服务端进程：`forceload remove all` → 225-chunk force-load → 远角 setblock → save → restart → `execute if block` 断言，输出 `verdict.json`。
79. **结果**：`chunksMarked=225`、`STRESS_OK_A/B`、`step1/2 Done + exit 0`，`passed=true`，exit 0。
80. **修复**：第一版工具在 `forceload add` 后立即 `setblock`，因异步 chunk 加载出现 “Could not set the block”；现在 step1 命令间隔 2.5s，并解析实际 “Marked N chunks” 而不是只算期望值。
81. **证据**：`runs/p24-chunk-stress-tool/README.md`、`verdict.json`、`step1.log`、`step2.log`。

## 2026-10-18 22:30 更新：Codec.dispatch 空结果保护

82. **Guard**：`CodecDispatch$Guard` 实现 `MapCodec$ResultFunction`，`apply` 检测 `assumeMapUnsafe` 的 null-success 并返回 `DataResult.error`；`coApply` 原样返回 `RecordBuilder`。
83. **生成/嵌入**：`BridgeGenerator.generate` 随 `CodecDispatch` 生成 `$Guard`；重新补丁 ironchests 后 jar 内包含 `CodecDispatch`/`$Adapter`/`$Guard`，规则计数不变（36 classes）。
84. **验证**：AW 注入后容器契约 5/5，两次 `Done`、exit 0；`gradle test` **17/17**。
85. **边界**：这是保护层，不是 `assumeMapUnsafe` 的完全替代；真正的 `MapCodec` 构造/形状校验仍待做。证据 `runs/p25-codec-guard/`。

## 2026-10-18 22:35 更新：Codec.dispatch 安全 MapCodec 适配

86. **javac 桥**：新增 `CodecDispatch.java`，用 `MapCodec.of(MapEncoder, MapDecoder)` 包装旧 dispatch 返回的 `Codec`；decode 走 `DynamicOps.createMap` + `codec.decode(...).map(Pair::getFirst)`，encode 走 `codec.encodeStart` + 复制 map entries；`MapCodecCodec` 直接 unwrap。
87. **选择逻辑**：`JarPatcher` 在 `--bridge-dir` 提供 `CodecDispatch.class` 时优先用它；其他生成桥仍走 ASM；无 bridge dir 时才回退到 P25 generated guard。
88. **验证**：重新补丁 ironchests，36 classes，`javac bridges: [CodecDispatch]`，jar 内无 `$Guard`；容器契约 5/5，两次 `Done`、exit 0；`gradle test` **17/17**。
89. **边界**：MapCodec wrapper 的 keys/compressor 为空是 dispatch 值的有意设计；契约仍为专用服务端 + 命令 API。证据 `runs/p26-codec-safe/`。

## 2026-10-18 22:40 更新：安全 CodecDispatch 联合回归

90. **场景**：`fabric-1.21.1-server-lithium-ironchests`，lithium chunkport + P26 `ironchests-safe-aw.jar`（javac `CodecDispatch`，无 `$Guard`）。
91. **结果**：两进程 `Done (26.7s/17.0s)`，容器契约 5/5，两次 exit 0。
92. **意义**：P26 的安全 Codec 适配不破坏 P14 已建立的 lithium+ironchests 共存路径。
93. **证据**：`runs/p27-combined-safe-codec/README.md`、`verdict-summary.json`、`verdict.json`。

## 2026-10-18 22:45 更新：安全 Codec 构建的 BytecodeVerify

94. **顶层**：P26 `ironchests-safe-aw.jar`，`73 classes / 1 jar`，0 methods failed，exit 0。
95. **nested**：ResourcefulLib，`142 classes`，0 failures，exit 0。
96. **说明**：覆盖 javac `CodecDispatch`/`$1`/`$2` 与 nested 类；仍只是栈深度校验，运行语义由 P26/P27 契约覆盖。证据 `runs/p28-codec-verify/`。

## 2026-10-18 22:50 更新：clientbound receiver

97. **实现**：`BalmNetworkingBridge$Client` 使用 `ClientPlayNetworking.registerGlobalReceiver`，把 payload 解出后调用旧 `BiConsumer<Class_1657,T>`；`registerClientbound` 通过 `FabricLoader` 环境反射，只在 `CLIENT` 时加载/调用该嵌套类。
98. **服务端**：更新后的 trashslot 补丁启动 `Done (4.894s)`，`doneSeen=true`，exit 0；没有 `ClientPlayNetworking` 类加载错误。
99. **边界**：没有客户端 fixture，client 分支、receiver 注册和 `MessageTrashSlotContent` 实际投递/解码均未执行；不能宣称客户端通过。证据 `runs/p29-client-receiver/`。

## 2026-10-18 22:55 更新：兼容档案

100. **lithium profile**：`profiles/lithium-0.11.4-fabric__fabric-1.21.1.json`，`booted_within_scope`；contracts 含 boot / chunk load / chunk save+restart / combined，pending gameplay/client/multiplayer；记录两条 mixinStrip 与优化减少。
101. **trashslot profile**：`profiles/trashslot-15.1.5-fabric__fabric-1.21.1.json`，`booted_within_scope`；记录原生 Balm 21 依赖、7 条规则、boot/initialize/network；pending client GUI/packet round-trip/player。
102. **索引**：`profiles/README.md` 列三个 profile 与状态词表；所有 source/rule/evidence hash 由脚本按实际文件计算。
103. **证据**：`profiles/`。

## 2026-10-18 23:00 更新：CodecDispatch 选择回归

104. **测试**：`JarPatcherCodecDispatchTest` 构造一个调用 `CodecDispatch.dispatch` 的 synthetic caller，`bridgeClasses` 提供 dummy `CodecDispatch`；断言规则命中、`externalBridges` 含 `CodecDispatch`、输出类是 supplied class、且没有 `CodecDispatch$Adapter`。
105. **意义**：锁住 P26 的 `--bridge-dir` 优先逻辑，防止以后又回退到 generated fallback。
106. **结果**：`gradle test --rerun-tasks` **18/18**，exit 0。证据 `runs/p31-codec-selection/`。

## 2026-10-18 23:05 更新：trashslot packet codec 往返

107. **Probe**：一个 Fabric 测试 mod 在 `SERVER_STARTED` 时调用 `MessageTrashSlotClick.encode/decode`，分别测试空栈与 `new ItemStack(Items.DIAMOND,5)`，断言 empty/count/item。
108. **结果**：日志 `TRASHSLOT_CODEC_OK`，服务端 `Done (5.025s)`、exit 0；覆盖 `TrashSlotNbtBridge.writeItem/readItem`、`FriendlyByteBuf` NBT 和 registry-aware `ItemStack.CODEC`。
109. **边界**：仍没有客户端 `ClientPlayNetworking` 投递、trash GUI 或玩家动作。证据 `runs/p32-trashslot-codec/`。

## 2026-10-18 23:10 更新：三个包全部往返

110. **扩展 probe**：`MessageTrashSlotClick`、`MessageTrashSlotContent`（各空栈 + 5 钻石），以及 `MessageDeleteFromSlot(3,true)`。
111. **结果**：`TRASHSLOT_ALL_CODEC_OK`，服务端 `Done (4.993s)`、exit 0；覆盖三个包的 encode/decode 和双向 ItemStack/NBT 桥。
112. **边界**：仍无客户端 `ClientPlayNetworking` 投递、GUI 或玩家动作。证据 `runs/p33-all-packets/`。

## 2026-10-18 23:15 更新：@At 目标

113. **扫描**：`Injection` 增加 `atValue/atTargetOwner/atTargetName/atTargetDesc/atTargetField`；支持 `@At` 单值/数组；修了多 `method` 数组被合并成一条的问题（injection 数恢复 214）。
114. **校验**：只对 intermediary 的 `@At` INVOKE/FIELD 目标查索引，缺失进 `unresolvedMixinInjections`；`mixinAtTargets` 计数。
115. **实跑**：lithium `mixinInjections=214`、`mixinAtTargets=0`（Yarn/refmap 目标跳过）、3 个已知构造器 unresolved；无新增 false positive。
116. **测试**：synthetic `@At` 提取 + analyzer missing-at-target；18/18。证据 `runs/p34-at-targets/`。

## 2026-10-18 23:20 更新：refmap @At

117. **映射**：`Injection.atRawTarget` 也走 mixin refmap；`applyAtMapped` 解析 `Lowner;method(desc)` / `field:type`。
118. **实跑**：lithium `mixinInjections=214`、`mixinAtTargets=86`、unresolved 仍 3（已知构造器），无新增 false positive。
119. **测试**：refmap 测试同时映射 handler 与 at-target；18/18。证据 `runs/p35-at-refmap/`。

## 2026-10-18 23:25 更新：at-target 补丁前后

120. **对照**：转换件 `214 injections / 86 at-targets / 3 unresolved`；补丁件 `209 / 84 / 0`。
121. **意义**：P11/P13 规则清掉 3 个已知构造器，at-target 解析仍保留 84 个；P35 的检查与真实补丁方向一致。
122. **边界**：静态检查；ordinal/slice/local capture 未解析。证据 `runs/p36-patched-at/`。

## 2026-10-18 23:30 更新：CodecDispatch 语义 probe

123. **Probe**：`record Box(int a)` + `RecordCodecBuilder` 作为 value codec；`CodecDispatch.dispatch(Codec.STRING, v->"k", k->valueCodec)`。
124. **断言**：encode `Box(1)` 得到 `{"a":1,"type":"k"}`；parse 回 `Box(1)`；日志 `CODEC_DISPATCH_PROBE_OK`。
125. **结果**：服务端 `Done (4.847s)`、exit 0；直接验证 P26 安全 MapCodec 包装的编解码语义。证据 `runs/p37-codec-probe/`。
126. **边界**：synthetic record，不是 ironchests ShapeTypes；无客户端。

## 2026-10-18 23:35 更新：client bridge BytecodeVerify

127. **验证**：P29 `trashslot-client-aw.jar`，47 classes / 1 jar，0 methods failed，exit 0。
128. **覆盖**：`BalmNetworkingBridge`、`$Payload`、`$Client` 及 NBT 包桥；仍不证明客户端运行语义。
129. **证据**：`runs/p38-client-bv/README.md`、`verdict.json`、`top-level.log`。

## 2026-10-18 23:40 更新：证据总校验

130. **工具**：`tools/verify_evidence.py` 读取 unit-test XML、P14/P24/P26/P27/P33/P37/P38 verdict，并检查 `git ls-files` 无 `.jar`。
131. **结果**：9 项 checks 全 true，`passed=true`，exit 0；18 个测试、0 failures/errors。
132. **边界**：只校验既有证据一致性，不重新启动服务端/客户端，也不替代真实契约。证据 `runs/p39-verify-evidence/`。

## 2026-10-18 23:45 更新：证据总校验扩展

133. **新增 checks**：P35 `(214,86,3)`、P36 `(209,84,0)`、lithium profile `booted_within_scope`。
134. **结果**：`passed=true`，exit 0；原有 9 项 + 新增 3 项全部 true。
135. **边界**：仍只校验既有证据，不启动服务端/客户端。证据 `runs/p40-verify-extended/`。

## 2026-10-18 23:50 更新：三样本同服

136. **实例**：`fabric-1.21.1-server-all-three`，lithium(P13) + ironchests(P26) + trashslot(P29) + Balm 21 + Fabric API。
137. **结果**：`Done (4.632s)`；容器契约两次重启 5/5，`passed=true`，两次 exit 0。
138. **意义**：三份转换件可以共存，ironchests 持久化未被 lithium/trashslot 干扰。
139. **边界**：专用服务端 + 命令 API；无客户端、trash GUI、lithium 玩法/多人。证据 `runs/p41-all-three/`。

## 2026-10-18 23:55 更新：三样本 chunk 压力

140. **场景**：all-three 实例上运行 `run_chunk_stress.py --radius 7`，225 chunks、远角方块、save/restart。
141. **结果**：`chunksMarked=225`，`STRESS_OK_A/B`，两次 exit 0，`passed=true`。
142. **意义**：lithium chunk 移植在 ironchests/trashslot/Balm 同时加载时仍正常。
143. **证据**：`runs/p42-all-three-chunk/README.md`、`verdict.json`、`step1.log`、`step2.log`。

## 2026-10-18 23:42 更新：三样本 + Codec probe

144. **场景**：P41 all-three 实例加载 `codecdispatchprobe.jar`，执行 P37 record-codec encode/decode。
145. **结果**：`CODEC_DISPATCH_PROBE_OK`，`Done (5.425s)`、exit 0。
146. **意义**：安全 `CodecDispatch` 在 lithium/trashslot/Balm 同时加载时仍正常。
147. **证据**：`runs/p43-all-three-codec/README.md`、`verdict.json`、`server.log`。

## 2026-10-18 23:45 更新：三样本 bundle profile

148. **档案**：`profiles/bundle-all-three__fabric-1.21.1.json`，`passed_within_scope`。
149. **contracts**：boot 4.632s、容器 5/5、225-chunk stress、CodecDispatch probe；client/GUI pending。
150. **证据**：`profiles/README.md`、bundle profile（4 个 evidence hash）。

## 2026-10-18 23:50 更新：剩余工作边界

151. **文档**：`docs/remaining-work.md` 汇总已验证项与阻塞项。
152. **结论**：服务端/静态工作已覆盖；客户端 GUI/网络/多人因无 client fixture 未执行；没有新增“客户端通过”声明。
153. **后续**：chunk 优化、nested mixin 静态分析、Forge 成员分析列为非阻塞。

## 2026-10-18 23:55 更新：多 method 数组回归

154. **测试**：`@Inject(method={"method_59()V","method_60()V"})` + 共享 `@At(method_61)`，断言两条 Injection。
155. **结果**：19/19 通过；钉住 P34 的修复（此前数组被折叠成一条，lithium 214→207）。
156. **证据**：`runs/p46-multi-method/README.md`、`verdict.json`、`gradle-test.log`。

## 2026-10-18 23:58 更新：字段 @At

157. **测试**：`@At(value="FIELD", target="Lnet/minecraft/class_14;field_99:Lnet/minecraft/class_1799;")`。
158. **断言**：owner/name/desc、`atTargetField=true`、`atValue=FIELD`。
159. **结果**：20/20 通过。证据 `runs/p47-field-at/`。

## 2026-10-18 23:59 更新：nested mixin 展开

160. **实现**：`scanNested` 保留嵌套 jar 字节；`readNestedMixinConfigs` 解析其中 `.mixins.json`，configName 带 `!/` 前缀，refmap/injection/at-target 一并解析。
161. **实跑**：ironchests P26 从 0/0/0 变为 1 config/1 class/1 injection（unresolved 0）；lithium 仍 202/214/86/3。
162. **测试**：新增 nested synthetic 测试；21/21。证据 `runs/p48-nested-mixins/`。

## 2026-10-19 00:05 更新：@At ordinal

163. **提取**：`Injection.atOrdinal`；`@At` visitor 读 `ordinal`，多 method 数组共享。
164. **计数**：lithium 86 at-targets 中 10 个带 ordinal；不改变 unresolved 3。
165. **边界**：只提取，不统计目标方法匹配指令，也不判越界；测试 22/22。证据 `runs/p49-at-ordinal/`。

## 2026-10-19 00:35 更新：首次客户端运行

166. **安装**：PCL 的 `D:\我的世界\.minecraft` 下装 1.21.1 base + Fabric 0.19.5 profile；用 PCL 的 Microsoft Java 21 跑 Fabric installer（工作区 JDK TLS 不可用）。
167. **加载**：Fabric API、Balm 21、lithium、ironchests、trashslot 全部出现在 mod 列表，进入 `Initializing game`。
168. **崩溃**：ironchests 入口点 `NoClassDefFoundError: ClientPlayNetworking$PlayChannelHandler`（旧 ResourcefulLib 2.0.6 客户端网络 API）；换 ResourcefulLib 3.0.12 又在 `PacketHandler` 失败。
169. **结论**：这是新的真实客户端阻断，服务端测试覆盖不到。证据 `runs/p50-client/`。

## 2026-10-19 00:40 更新：RL 客户端网络桥

170. **桥**：重写嵌套 RL 2.0.6 `FabricClientPacketHelper`，旧 handler 编解码保留，外层用 1.21.1 `CustomPayload`/`PlayPayloadHandler`。
171. **结果**：客户端越过 ironchests main 入口点，进入 client 入口点；新阻断 `ModelLoadingRegistry` 缺失、`BalmClient.initialize(String,Runnable)` 缺失。
172. **边界**：桥是 work-only 实验，尚未规则化；没有客户端通过声明。证据 `runs/p51-client-bridge/`。

## 2026-10-19 00:50 更新：客户端主菜单

173. **安装**：PCL 1.21.1 Fabric 0.19.5 客户端 + 五模组；Fabric 加载全部模组。
174. **桥**：RL 客户端网络、`BalmClient.initialize`、ironchests `ModelLoadingPlugin`；客户端到达主菜单（`main-menu.png`）。
175. **新阻断**：进入世界时 `BalmNetworking.sendTo` 的 payload 编码 `ClassCastException: class_9129 -> MessageTrashSlotContent`；世界/GUI/同步仍未执行。证据 `runs/p52-client-balm/`。

## 2026-10-19 00:55 更新：世界加入

176. **修复**：旧 Balm writer 是 `BiConsumer<T, FriendlyByteBuf>`（packet 在前），bridge 改为 `writer.accept(value, buf)`。
177. **结果**：`trash_slot_content` 编码错误消失，客户端登录并开始世界生成。
178. **新阻断**：lithium `class_2540.method_10815` tombstone（1.20.1 `getVarIntSize`，1.21.1 移到 `VarInt.getByteSize`）。证据 `runs/p53-client-world/`。

## 2026-10-19 01:00 更新：客户端进入世界

179. **桥**：`LithiumVarIntBridge.getByteSize` → `class_8703.method_53015`；`lithium-varint.json` 命中 2 处。
180. **结果**：世界生成通过，客户端登录并渲染地形/HUD（`world.png`，窗口 `Minecraft* 1.21.1 - Singleplayer`）。
181. **未做**：trash GUI/容器持久化/同步；合成 E 键未打开背包，不声称已测。证据 `runs/p54-client-lithium/`。

## 2026-10-19 01:05 更新：背包/TrashSlot GUI

182. **测试入口**：客户端 probe 在 player 存在后调用 `method_1507(new class_490(player))`，绕开不可靠的合成 E 键。
183. **结果**：截图显示原版背包 + 右下角 TrashSlot 按钮；世界/HUD 背景正常。
184. **边界**：点击空 trash 按钮无可见变化；物品移入/移出、重启持久化、ironchests GUI、同步未测。证据 `runs/p55-client-gui/`。

## 2026-10-19 01:15 更新：真实物品 + trash 拖放

185. **注入**：probe 在 `ServerPlayConnectionEvents.JOIN` 给玩家 5 钻石；背包/快捷栏显示正常。
186. **尝试**：点击钻石再点 trash 按钮、或拖拽到按钮；物品仍停在光标，trash 未接收，日志无异常。
187. **结论**：不能记为通过；需查 TrashSlot GUI slot 的点击路径/坐标/处理器。证据 `runs/p56-client-item/`。

## 2026-10-19 01:25 更新：trash 生命周期（修正）

188. **同会话**：`TrashHelper.setTrashItem` 后立即 `getTrashItem` 读回 5 钻石；live `BalmData/TrashSlot` 为 `{count:5,id:"minecraft:diamond"}`。
189. **重进为空的原因**：`TrashSlot.lambda$initialize$0(PlayerLoginEvent)` 显式 `setTrashItem(player, ItemStack.EMPTY)` 并发送空 content；这是模组自己的登录重置，不是 NBT 桥失败。
190. **结论**：P57 原“持久化缺口”结论撤回；trash 在该版本按登录重置，不能作为持久化契约。GUI 拖放仍是独立未解问题。证据 `runs/p57-trash-persist/`。

## 2026-10-19 08:10 更新：TrashSlot 不是 handler slot

191. **probe**：`TrashSlotSlot` 坐标 `152,165`，component anchor `231,211`，钻石槽 `36`。
192. **关键**：`handler.field_7761.indexOf(trash) = -1`（共 46 个槽），垃圾桶不在普通 slot 列表；它是客户端 component 绘制/拦截。
193. **结论**：普通 `clickSlot` 无法定位垃圾桶，P56 的点击/拖拽失败由此解释；实际转移仍未完成。证据 `runs/p58-trash-click/`。

## 证据在哪里

| 证据 | 路径 |
|---|---|
| 环境探针 | `work/evidence/doctor.json` |
| 样本锁 | `manifests/corpus.json` |
| 上游锁 | `manifests/upstream.lock.json` |
| 目标环境锁 | `manifests/environment.lock.json` |
| 静态分析计划 | `runs/p0-fabric-target/plan.json` |
| 静态矩阵 | `docs/generated/static-matrix-fabric-1.21.1.md` |
| CenturyBridge 编译日志 | `work/evidence/cb-javac.log` |
| CenturyBridge 转换报告 | `work/cb/out/ironchests/report.md`、`full-audit.tsv` |
| 转换件 | `work/cb/out/ironchests/ironchests-5.0.2-fabric+1.21.1.jar` |
| 重映射后的服务端游戏 jar | `work/remap/server-intermediary.jar`（SHA-256 `27d29458...978d`） |
| BOOTED 日志 | `runs/p1-server-baseline/server-baseline.log`（`Done (4.803s)`） |
| 转换件运行时失败日志 | `runs/p1-server-converted-ironchests/server.log` |
| 第一条规则 + 补丁后日志 | `rules/fabric-1.21.1/container.json`、`runs/p2-server-ironchests-rule1/server.log` |
| 第二/三条规则后日志 | `runs/p2-server-ironchests-rule2/server.log` |
| 规则说明 | `rules/README.md` |
| 打补丁后的转换件 | `work/cb/out/ironchests/ironchests-5.0.2-fabric+1.21.1-patched.jar` |
| 调用点规则（lithium） | `rules/fabric-1.21.1/lithium.json` |
| 调用点桥源码 | `java/src/bridge/java/top/mcbridge1201/bridge/WalkNodeEvaluatorCheckNeighbourBlocks.java` |
| 1.20.1 / 1.21.1 `method_59` 方法体 | `runs/p10-lithium-signature/class_14-1.20.1-body.txt`、`class_14-1.21.1-body.txt` |
| 调用点补丁 / 启动 / 哈希 | `runs/p10-lithium-signature/README.md`、`patch-lithium.log`、`server-callsite.log`、`verdict.json` |
| 单元测试 | `runs/p10-lithium-signature/gradle-test.log`（8 tests, 0 failures） |
| Mixin 适配规则 | `rules/fabric-1.21.1/lithium.json`（`mixinCallbackAdaptations`） |
| Mixin 适配补丁 / 启动 / 实验 | `runs/p11-lithium-explosion/README.md`、`patch-lithium3.log`、`server-explosion3.log`、`server-readd.log`、`server-chunkholder-local2.log` |
| Mixin 适配测试 | `runs/p11-lithium-explosion/gradle-test.log`（11 tests, 0 failures） |
| chunk access 分析 | `runs/p12-chunk-access/README.md` |
| chunk access 移植 / BOOTED | `runs/p13-chunk-port/README.md`、`server-chunkport-rule.log`、`server-chunkport-commands.log`、`verdict.json` |
| chunk access 测试 | `runs/p13-chunk-port/gradle-test.log`（12 tests, 0 failures） |
| lithium+ironchests 联合契约 | `runs/p14-lithium-ironchests/README.md`、`verdict.json`、`step1-place-insert.log`、`step2-restart-read.log` |
| trashslot 尝试（受阻） | `runs/p15-trashslot/README.md`、`convert.log`、`convert-balm.log`、`patch.log`、`server-trashslot3.log` |
| Balm 初始化桥（仍受阻） | `runs/p16-balm/README.md`、`patch.log`、`server-balm2.log` |
| trashslot BOOTED | `runs/p17-balm-net/README.md`、`verdict.json`、`server-net2.log` |
| 嵌套 jar 桥 | `runs/p18-nested-bridges/README.md`、`contract/verdict.json`、`gradle-test.log` |
| BytecodeVerify | `runs/p19-bytecode-verify/README.md`、`verdict.json`、`verify.log`、`verify-nested.log` |
| Mixin 注入目标分析 | `runs/p20-mixin-inject/README.md`、`verdict.json`、`gradle-test.log`、`analyze-converted.log` |
| refmap 注入目标 | `runs/p21-refmap/README.md`、`verdict.json`、`lithium-converted.json`、`analyze-converted.log` |
| 注入目标交叉验证 | `runs/p22-cross-analyze/README.md`、`verdict.json`、`lithium-patched.json` |
| lithium chunk 压力测试 | `runs/p23-chunk-stress/README.md`、`verdict.json`、`step1b.log`、`step2.log` |
| chunk 压力测试工具 | `tools/run_chunk_stress.py`、`runs/p24-chunk-stress-tool/README.md`、`verdict.json` |
| Codec dispatch guard | `runs/p25-codec-guard/README.md`、`verdict.json`、`contract/verdict.json` |
| Codec dispatch 安全适配 | `runs/p26-codec-safe/README.md`、`verdict.json`、`contract/verdict.json` |
| 安全 Codec 联合回归 | `runs/p27-combined-safe-codec/README.md`、`verdict-summary.json`、`verdict.json` |
| 安全 Codec BytecodeVerify | `runs/p28-codec-verify/README.md`、`verdict.json`、`top-level.log`、`nested.log` |
| clientbound receiver | `runs/p29-client-receiver/README.md`、`verdict.json`、`server.log` |
| 兼容档案 | `profiles/README.md`、`profiles/lithium-...json`、`profiles/trashslot-...json` |
| CodecDispatch 选择回归 | `runs/p31-codec-selection/README.md`、`verdict.json`、`gradle-test.log` |
| trashslot packet codec | `runs/p32-trashslot-codec/README.md`、`verdict.json`、`server.log` |
| trashslot all packets | `runs/p33-all-packets/README.md`、`verdict.json`、`server.log` |
| @At 目标分析 | `runs/p34-at-targets/README.md`、`verdict.json`、`lithium-converted.json` |
| refmap @At | `runs/p35-at-refmap/README.md`、`verdict.json`、`lithium-converted.json` |
| at-target 补丁前后 | `runs/p36-patched-at/README.md`、`verdict.json`、`lithium-patched.json` |
| CodecDispatch 语义 probe | `runs/p37-codec-probe/README.md`、`verdict.json`、`server.log` |
| client bridge BytecodeVerify | `runs/p38-client-bv/README.md`、`verdict.json`、`top-level.log` |
| 证据总校验 | `tools/verify_evidence.py`、`runs/p39-verify-evidence/README.md`、`verify.log` |
| 证据总校验扩展 | `runs/p40-verify-extended/README.md`、`verify.log` |
| 三样本同服 | `runs/p41-all-three/README.md`、`verdict.json`、`server.log`、`contract/verdict.json` |
| 三样本 chunk 压力 | `runs/p42-all-three-chunk/README.md`、`verdict.json`、`step1.log`、`step2.log` |
| 三样本 Codec probe | `runs/p43-all-three-codec/README.md`、`verdict.json`、`server.log` |
| 三样本 bundle profile | `profiles/bundle-all-three__fabric-1.21.1.json`、`profiles/README.md` |
| 剩余工作边界 | `docs/remaining-work.md` |
| 多 method 数组回归 | `runs/p46-multi-method/README.md`、`verdict.json`、`gradle-test.log` |
| 字段 @At 解析 | `runs/p47-field-at/README.md`、`verdict.json`、`gradle-test.log` |
| nested mixin 展开 | `runs/p48-nested-mixins/README.md`、`verdict.json`、`ironchests.json` |
| @At ordinal | `runs/p49-at-ordinal/README.md`、`verdict.json`、`lithium-converted.json` |
| 首次客户端运行 | `runs/p50-client/README.md`、`client.log`、`crash-report.txt` |
| RL 客户端网络桥 | `runs/p51-client-bridge/README.md`、`FabricClientPacketHelper.java`、`crash-report.txt` |
| 客户端主菜单 | `runs/p52-client-balm/README.md`、`main-menu.png`、`latest.log` |
| 世界加入 | `runs/p53-client-world/README.md`、`crash-report.txt`、`latest.log` |
| 客户端进入世界 | `runs/p54-client-lithium/README.md`、`world.png`、`latest.log` |
| 背包/TrashSlot GUI | `runs/p55-client-gui/README.md`、`inventory-probe.png`、`trash-click.png` |
| 真实物品/trash 拖放 | `runs/p56-client-item/README.md`、`inventory-with-diamonds.png`、`trash-drag.png` |
| trash 持久化 probe | `runs/p57-trash-persist/README.md`、`latest.log`、`pause2.png` |
| TrashSlot handler 定位 | `runs/p58-trash-click/README.md`、`latest.log`、`TrashClickProbe.java` |
| 早期阻塞日志 | `runs/p0-server-baseline/` |
| 证据 hash 清单 | `runs/SHA256SUMS.txt` |

## 未解决（按优先级）

1. **lithium 仅到 BOOTED**：专用服务端 Done、世界加载/保存、命令 chunk 探针通过；没有 lithium 玩法契约、客户端 GUI/渲染或多人同步。两条显式 `mixinStrips` 仍在。
2. **`mixinClassReplacements` 的覆盖面/优化**：chunk access 已用实现类替换打通；被放弃的多入口缓存/off-thread 快路径可以后续重写，并需验证该模式在更多 API 形状变化上的可维护性。
3. **调用点适配的覆盖面**：目前验证了顶层 jar 的直接调用/句柄，以及 P18 的嵌套 jar 桥（synthetic + ironchests JiJ 回归）；还可继续覆盖更多样本、多层嵌套和更多句柄形状。
4. **Mixin 目标描述符适配的覆盖面**：已处理 Explosion 与 POI storage 两处；仍需覆盖更多 `@Inject`/`@Redirect`/`@ModifyConstant` 目标变化，并验证 append/replace 模式在真实注入点上的边界。
5. **`Codec.dispatch` 的可靠适配**：ironchests 契约虽已通过，但 `assumeMapUnsafe` 在部分路径仍可能 `Optional.of(null)`；应改成真正的 `MapCodec` 构造/显式诊断。
6. **CenturyBridge 桥 jar 未构建**：`core/shims/1.21.1` 未编译，`build.sh` 四道门禁未跑（`MixinCheck` 缺失）。
7. **玩家侧 / 多人**：GUI、右键交互、渲染、两个客户端同步仍 pending；服务端只做了命令契约。
8. **第三个样本 trashslot 仅到 BOOTED**：原生 Balm 21 + 初始化/网络桥 + 4 个 NBT 桥已让专用服务端 `Done`；但无客户端连接，clientbound receiver 未安装，包 encode/decode 和 ItemStack NBT 桥未被玩家动作触发，客户端 GUI/玩法仍未验证。
9. **Forge 成员级分析缺失**：需 `mcp_config` joined.tsrg（SRG）+ 1.21.1 Mojang 映射 + NeoForge 1.21.1 索引。
10. **Mixin 注入点级分析**：已提取 `@Inject`/`@Redirect` 的 `method` 目标，支持 refmap 和构造器，并静态复现 lithium 的 3 个已知构造器变化；ordinal/slice/局部变量和非 refmap 命名目标仍未解析。
11. **BytecodeVerify** 已对三个顶层补丁 jar + 一个 nested jar 运行（0 failures）；其他 nested jar/客户端路径未覆盖，且只是栈深度校验，不是完整类型校验。
12. **重映射器的覆盖面**：目前只验证了服务端 jar；客户端 jar、带资源的 jar、模块化 jar 未验证；输出未做签名清理以外的规范化（entry 时间固定）。

## 下一步精确命令

```powershell
# A. 复现 lithium BOOTED（调用点 + 2 处 Mixin 目标 + chunk access 移植）
$env:JAVA_HOME='C:\Users\27682\Documents\新建文件夹\.toolchain\jdk'
cd java; gradle --no-daemon installDist; cd ..
python tools/build_bridges.py --stub work/cb/data/jars/client-1.21.1-intermediary.jar `
  --lib work/lib/gson-2.11.0.jar `
  --lib work/instances/fabric-1.21.1-server/libraries/com/mojang/datafixerupper/8.0.16/datafixerupper-8.0.16.jar `
  --out work/bridges
python tools/build_mixins.py --stub work/remap/server-intermediary.jar `
  --lib work/instances/fabric-1.21.1-server-lithium/libraries/net/fabricmc/sponge-mixin/0.17.4+mixin.0.8.7/sponge-mixin-0.17.4+mixin.0.8.7.jar `
  --lib work/bridges --out work/mixins
java\build\install\mcbridge1201\bin\mcbridge1201.bat patch `
  --in work/cb/out/lithium/lithium-fabric-mc1.20.1-0.11.4+1.21.1.jar `
  --out work/cb/out/lithium/lithium-patched-chunkport.jar `
  --rules rules/fabric-1.21.1/lithium-degraded.json `
  --rules rules/fabric-1.21.1/lithium.json `
  --bridge-dir work/bridges --bridge-dir work/mixins
python tools/run_server.py --instance work/instances/fabric-1.21.1-server-lithium `
  --log runs/p13-chunk-port/server-chunkport-rule.log --timeout 240

# B. 下一步：lithium 玩法/客户端契约（当前只到 BOOTED）
# C. 客户端侧：用 1.21.1 客户端实例测试 GUI/渲染（本机沙箱暂无法启动图形客户端）
# D. Forge 第二套索引（并行可做）
#    下载 de.oceanlabs.mcp:mcp_config:1.20.1:joined.tsrg 与 NeoForge 1.21.1 universal jar，
#    新增 MojangIndex；analyze --target-loader neoforge
```

## 工作方式约定

- 每轮只把实际跑过的阶段写进结论；`pending` 不写成通过。
- 所有实验保留命令、退出码、日志路径；失败也保留。
- 原始 jar、游戏 jar、转换件只在 `work/`，不入库、不外发。
- 上游改动先记 ADR，再动代码；本地绕过（重映射器、stub 补丁）必须在文档中显式标注。
