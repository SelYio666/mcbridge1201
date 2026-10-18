# 交接摘要（一页）


更新（2026-10-18 23:42）：**三样本 + CodecDispatch probe 通过**。all-three 实例加载 P37 probe，`Done (5.425s)`、`CODEC_DISPATCH_PROBE_OK`；安全 Codec 包装在三样本同服时仍正常。证据 `runs/p43-all-three-codec/`。
更新（2026-10-18 23:55）：**三样本同服 chunk 压力通过**。all-three 实例 225 chunks、远角方块 save/restart 断言全 true，两进程 exit 0；证据 `runs/p42-all-three-chunk/`。
更新（2026-10-18 23:50）：**三样本同服通过**。lithium + ironchests(P26) + trashslot(P29)/Balm 21 同实例 `Done (4.632s)`；容器契约两次重启 5/5。证据 `runs/p41-all-three/`。
更新（2026-10-18 23:45）：**证据总校验扩展**。`tools/verify_evidence.py` 增加 P35/P36 at-target 计数和 lithium profile 检查；全部 checks true，exit 0。证据 `runs/p40-verify-extended/`。
更新（2026-10-18 23:40）：**证据总校验工具**。`tools/verify_evidence.py` 检查 18 个测试、P14/P24/P26/P27/P33/P37/P38 证据及“无 tracked jar”；`passed=true`，exit 0。证据 `runs/p39-verify-evidence/`。
更新（2026-10-18 23:35）：**P29 client bridge 的 BytecodeVerify**。`trashslot-client-aw.jar` 顶层 47 classes / 0 failures，覆盖 `BalmNetworkingBridge`/`$Payload`/`$Client`；客户端分支仍未执行。证据 `runs/p38-client-bv/`。
更新（2026-10-18 23:30）：**CodecDispatch 语义 probe 通过**。`RecordCodecBuilder` 的 `Box(int a)` 经 `CodecDispatch.dispatch` encode 为 `{"a":1,"type":"k"}`、decode 回 `Box(1)`，日志 `CODEC_DISPATCH_PROBE_OK`；服务端 `Done (4.847s)`、exit 0。直接验证 P26 安全 MapCodec 包装。证据 `runs/p37-codec-probe/`。
更新（2026-10-18 23:25）：**at-target 补丁前后对照**。转换件 `214 injections / 86 at-targets / 3 unresolved`，补丁件 `209 / 84 / 0`；P11/P13 清掉已知构造器，at-target 解析保持一致。证据 `runs/p36-patched-at/`。
更新（2026-10-18 23:20）：**refmap `@At` 目标解析**。`atRawTarget` 也走 refmap，lithium 的 `mixinAtTargets` 从 0 提升到 **86**，unresolved 仍 3（已知构造器），没有新增 false positive；测试 18/18。证据 `runs/p35-at-refmap/`。
更新（2026-10-18 23:15）：**`@At` 目标提取（保守）**。scanner 解析 `@Inject` 等的 `@At(value,target)`，analyzer 对 intermediary 的 INVOKE/FIELD 目标做存在性检查；转换后 lithium `mixinInjections=214`、`mixinAtTargets=0`（Yarn/refmap 跳过）、3 个已知构造器 unresolved；测试 18/18。证据 `runs/p34-at-targets/`。
更新（2026-10-18 23:10）：**trashslot 三个包 codec 全部往返通过**。`MessageTrashSlotClick`/`MessageTrashSlotContent` 的空栈与 5 钻石、`MessageDeleteFromSlot(3,true)` 均通过（`TRASHSLOT_ALL_CODEC_OK`）；服务端 `Done (4.993s)`、exit 0。仍不含客户端投递/GUI。证据 `runs/p33-all-packets/`。
更新（2026-10-18 23:05）：**trashslot packet codec 往返通过**。服务器内 probe 对空栈与 5 钻石执行 `MessageTrashSlotClick.encode/decode`，断言 empty/count/item 全部通过（`TRASHSLOT_CODEC_OK`）；服务端 `Done (5.025s)`、exit 0。仍不含客户端网络投递。证据 `runs/p32-trashslot-codec/`。
更新（2026-10-18 23:00）：**CodecDispatch 选择回归测试**。验证 `--bridge-dir` 提供的 javac `CodecDispatch` 优先于 generated fallback，且不嵌入 `CodecDispatch$Adapter`；测试 18/18。证据 `runs/p31-codec-selection/`。
更新（2026-10-18 22:55）：**lithium / trashslot 兼容档案**。新增两份 `booted_within_scope` profile 与 `profiles/README.md` 索引；lithium 记录 boot/225-chunk/combined，trashslot 记录原生 Balm 21 与 boot/网络；客户端/玩法仍 pending。证据 `profiles/`。
更新（2026-10-18 22:50）：**trashslot clientbound receiver 已接入**。`BalmNetworkingBridge$Client` 在客户端用 `ClientPlayNetworking.registerGlobalReceiver` 调用旧 `BiConsumer<Player,T>`；服务端反射跳过，仍 `Done (4.894s)`。客户端分支未执行，不能宣称客户端通过；证据 `runs/p29-client-receiver/`。
更新（2026-10-18 22:45）：**P26 安全 Codec 构建的 BytecodeVerify**。顶层 73 classes / 0 failures，nested ResourcefulLib 142 classes / 0 failures，exit 0；运行侧由 P26/P27 契约覆盖。证据 `runs/p28-codec-verify/`。
更新（2026-10-18 22:40）：**安全 CodecDispatch 联合回归**。lithium + P26 `ironchests-safe-aw.jar` 同实例，两进程容器契约 5/5、两次 `Done`、exit 0；P26 未破坏 P14 共存路径。证据 `runs/p27-combined-safe-codec/`。
更新（2026-10-18 22:35）：**Codec.dispatch 安全 MapCodec 适配**。活跃路径改用 javac `CodecDispatch`，用 `MapCodec.of(MapEncoder, MapDecoder)` 真正包装旧 `Codec`，不再依赖 `assumeMapUnsafe`；ironchests 容器契约 5/5，测试 17/17。证据 `runs/p26-codec-safe/`。
更新（2026-10-18 22:30）：**Codec.dispatch 空结果保护**。`CodecDispatch$Guard` 把 `assumeMapUnsafe` 的 null-success 变成 `DataResult.error`；重新补丁 ironchests 后容器契约 5/5 通过，测试 17/17。证据 `runs/p25-codec-guard/`。
更新（2026-10-18 22:25）：**chunk 压力测试工具化**。新增 `tools/run_chunk_stress.py`，两进程 force-load 225 chunks、远角方块、save/restart、`execute if block` 断言；本次 `chunksMarked=225`、`STRESS_OK_A/B`、`passed=true`，exit 0。证据 `runs/p24-chunk-stress-tool/`。
更新（2026-10-18 22:20）：**lithium chunk-access 压力测试通过**。224 个 forceload chunk（`[-7,-7]` 到 `[7,7]`），远角钻石/绿宝石块 save/restart 后均被 `execute if block` 读回（`STRESS_OK_A/B`），两次 `Done`、exit 0。证据 `runs/p23-chunk-stress/`。
更新（2026-10-18 22:15）：**注入目标静态检查交叉验证**。同一 1.21.1 索引下：转换后 lithium `214/3`（3 个 unresolved 正是 P11/P13 的构造器阻断），补丁后 lithium `209/0`；Balm `43/0`，ironchests/trashslot 顶层无 mixin。证据 `runs/p22-cross-analyze/`。
更新（2026-10-18 22:10）：**refmap 注入目标解析**。读取 mixin config 的 refmap，把命名目标映射到 `Lowner;method(desc)`（含构造器），`Analyzer` 静态复现 lithium 的 3 个已知构造器变化：`class_4180`(POI)、`class_3610`(FluidState)、`class_1927`(Explosion)。测试 16/16；证据 `runs/p21-refmap/`。
更新（2026-10-18 22:05）：**Mixin 注入目标提取 + 保守校验**。`ArtifactScanner` 解析 `@Inject`/`@Redirect` 等的 `method` 目标，`Analyzer` 新增 `mixinInjections`/`mixinInjectionsUnresolved`；只校验 intermediary 名称+描述符，命名/refmap/构造器跳过。测试 15/15；转换后 lithium 实跑 214 个注入目标、0 unresolved；证据 `runs/p20-mixin-inject/`。
更新（2026-10-18 21:55）：**BytecodeVerify 已跑**。对 ironchests/lithium/trashslot 三个补丁 jar 顶层类验证 650 classes / 0 failures；对 ironchests nested ResourcefulLib 验证 141 classes / 0 failures。仅栈深度校验；证据 `runs/p19-bytecode-verify/`。
更新（2026-10-18 21:52）：**嵌套 jar 的桥改为按 jar 嵌入**。`JarPatcher` 为每层 jar 记录 `used` 集合并把生成的/javac 桥嵌入使用它的那个 jar；新增 synthetic nested jar 测试，ironchests 重补丁只在 nested ResourcefulLib jar 多出 `IdentifierFactory`，容器契约 5/5 仍通过。测试 13/13；证据 `runs/p18-nested-bridges/`。
更新（2026-10-18 21:50）：**trashslot 到达专用服务端 `Done`**。原生 Balm 21.0.66 + `Balm.initialize` call-site 桥 + 旧 Balm 网络注册 → Fabric `PacketType`/`StreamCodec` 载荷桥 + 4 个 ItemStack/NBT 桥，`Done (4.655s)`，世界加载/保存。仍是 BOOTED，客户端 GUI/网络包往返未验证；证据 `runs/p17-balm-net/`。
更新（2026-10-18 21:45）：**Balm 初始化调用点桥已推进 trashslot，但卡在 Balm 网络 API**。`Balm.initialize(String,Runnable)` → `initialize(String, EmptyLoadContext, Runnable)` 的 call-site 桥生效，旧的初始化 `NoSuchMethodError` 消失；下一失败是 `BalmNetworking.registerServerboundPacket(Identifier, Class, BiConsumer, Function, BiConsumer)`，Balm 21 已改为 `PacketType`/`StreamCodec` 载荷注册。仍未 boot，规则保持 prepared/unverified；证据 `runs/p16-balm/`。
更新（2026-10-18 21:40）：**第三个样本 trashslot 受阻于 Balm/Fabric networking**。trashslot 自身 4 个 ItemStack/NBT tombstone 已写桥并 patch，但依赖 Balm：转换 Balm 7.3.44 后卡在 Fabric API 移除的 `ServerPlayNetworking$PlayChannelHandler`，原生 Balm 21.0.66 又缺 `Balm.initialize(String,Runnable)`。未 boot；规则标记 prepared/unverified，证据 `runs/p15-trashslot/`。
更新（2026-10-18 21:35）：**lithium + ironchests 联合容器契约通过**。同一 Fabric 1.21.1 专用服务端实例加载两份转换件，两进程放置/插入/NBT/重启读回 5 钻石全部通过；P13 chunk access 移植没有破坏容器持久化，两样本可共存。证据 `runs/p14-lithium-ironchests/`，说明 `docs/baseline.md` §7.20。仍不含 lithium 自身玩法/客户端。
更新（2026-10-18 21:25）：**lithium 到达专用服务端 `Done`**。`ServerChunkManagerMixin` 的 chunk access 实现移植到 1.21.1 `ChunkResult`/`GenerationChunkHolder` API（保留 mixin 类与 `@Overwrite`，不是 strip），启动 `Done (4.772s)`，世界加载/保存，命令 chunk 探针通过。规则 `mixinClassReplacements`，证据 `runs/p13-chunk-port/`，说明 `docs/baseline.md` §7.19。仍只是 BOOTED，不是玩法/客户端兼容。
更新（2026-10-18 21:05）：**Mixin 目标描述符适配已实现**。lithium 的 `ExplosionMixin` 与 POI `SerializingRegionBasedStorageMixin` 两处 `@Inject` 目标签名迁移成功，服务端推进到 chunk access 的 `ChunkHolderExtended` cast；下一阻断是 1.21.1 chunk API 形状 + CenturyBridge tombstone，不是描述符。规则 `rules/fabric-1.21.1/lithium.json`，证据 `runs/p11-lithium-explosion/`，说明 `docs/baseline.md` §7.18。
更新（2026-10-18 20:50）：**调用点签名适配已实现并用 lithium 的 `class_14.method_59` 验收**。补丁后 `NoSuchMethodError` 消失，启动推进到下一失败（`world.explosions.ExplosionMixin` 的注入目标变化）。规则 `rules/fabric-1.21.1/lithium.json`，证据 `runs/p10-lithium-signature/`，说明 `docs/baseline.md` §7.17。
更新（2026-10-18 20:20）：`ItemPredicate.fromJson` 的降级已消除——改用反射读取 BuiltInRegistries 并通过 RegistryOps 解析 codec，启动日志不再出现 falling back，兼容档案已升为 `passed_within_scope`（服务端范围）。
日期：2026-10-18。给下一个接手者：先读这页，再按需展开 `docs/baseline.md`。

## 现在能做什么

在 `work/instances/fabric-1.21.1-server`（Fabric 1.21.1 + Fabric API 0.102.0）里：

- 归档的 `ironchests 5.0.2`（1.20.1 原始 jar）经过 CenturyBridge 转换 + 本项目规则补丁后，**随服务端启动并加载世界**（`Done (1.2s)`，42 个模组）。
- **容器契约通过**（服务端命令范围）：放置 `ironchests:iron_chest` → 插入 5 钻石 → NBT 出现 `Items` → 进程重启 → 读回 `count=5`。一键：

```powershell
$env:JAVA_HOME='C:\Users\27682\Documents\新建文件夹\.toolchain\jdk'
python tools/run_contract.py --instance work/instances/fabric-1.21.1-server --out runs/contract
```

## 关键机制（都已实现并实测）

| 机制 | 位置 | 作用 |
|---|---|---|
| body-preserving 重映射 | `java/.../remap/JarRemapper.java` | 解决本机 Fabric remap 被 zipfs 只读阻塞；方法/字段/lambda 名称传播 |
| 规则引擎 | `java/.../rules/` | 字段/方法/句柄重定向、构造器重定向、常量池种类修正、**调用点签名适配**（javac 桥）、覆写签名适配、**Mixin 目标描述符适配**（append/replace + refmap）、**Mixin 实现类替换**（API 形状变化）、**mixin 降级** |
| 规则包 | `rules/fabric-1.21.1/container.json`、`lithium.json` | ironchests 7 条 + lithium 调用点/2 条 Mixin 目标规则，全部有触发证据 |
| 降级档案 | `rules/fabric-1.21.1/lithium-degraded.json` | mixin 剥离，显式记录 |
| 契约脚本 | `tools/run_contract.py` | 两进程重启 + 断言 + verdict.json |
| 报表 | `tools/build_reports.py` | 生成兼容档案 + 支持矩阵 |

## 当前最高证据阶段

`CONTRACT_PASSED`（**仅限**专用服务端 + 命令 API + 单进程重启）。ironchests 兼容档案状态 `passed_within_scope`；lithium 到达专用服务端 `BOOTED`（`Done (4.772s)`），lithium+ironchests 联合容器契约通过；trashslot 也到达专用服务端 `BOOTED`（`Done (4.655s)`，原生 Balm 21 + 载荷桥），但无 lithium/trashslot 自身玩法或客户端契约，lithium 仍有 2 条显式 mixinStrip。

## 未解决（按优先级）

1. **lithium 仅到 BOOTED**：专用服务端 `Done`、世界加载/保存、命令 chunk 探针通过；lithium+ironchests 联合容器契约也通过（§7.20），但没有 lithium 自身玩法、客户端 GUI/渲染或多人同步。2 条显式 `mixinStrips` 仍在，chunk 优化也减少了（旧多入口缓存/off-thread 快路径未重写）。
2. **`mixinClassReplacements` 的覆盖面/优化**：chunk access 已用实现类替换打通；还需验证该模式在更多 API 形状变化上的可维护性，并决定是否重写被放弃的优化。
3. **调用点适配的覆盖面**：已覆盖顶层 jar 的直接调用和 `MethodHandle`；P18 已把桥按 jar 嵌入嵌套 jar（synthetic + ironchests JiJ 回归），可继续覆盖更多样本/多层嵌套/更多句柄形状。
4. **Mixin 目标描述符适配的覆盖面**：已处理 Explosion 与 POI storage；仍需覆盖更多 `@Inject`/`@Redirect`/`@ModifyConstant` 目标变化。
5. **第三个样本 trashslot 仅到 BOOTED**：原生 Balm 21 + 初始化/网络载荷桥 + 4 个 NBT 桥已让专用服务端 `Done`；但无客户端连接，clientbound receiver 未安装，包 encode/decode 与 ItemStack NBT 桥未被玩家动作触发，客户端 GUI/玩法未验证。
6. **客户端侧**：GUI 打开、右键交互、渲染、两个客户端同步。本机无显示验证，需要客户端实例。
7. **Forge 成员级分析**：目前只有命名空间级；需要 tsrg(SRG) + Mojang 映射的联合索引。
8. **`BytecodeVerify`**：已对三个顶层补丁 jar + 一个 nested jar 运行（0 failures，§7.23）；其他 nested jar/客户端路径未覆盖，且仅栈深度校验。
9. **Mixin 注入点级分析**：已提取 `@Inject`/`@Redirect` 的 `method` 目标，支持 refmap 和构造器，并静态复现 lithium 的 3 个已知构造器变化；ordinal/slice/局部变量和非 refmap 命名目标仍未解析。

> 已完成（不要再当未解决）：`ItemPredicate.fromJson` 的 registry-aware 构造（2026-10-18 20:20，profile `passed_within_scope`）；lithium 的 `class_14.method_59` 调用点签名适配（20:50，§7.17）；lithium `ExplosionMixin` + POI storage 的 Mixin 目标描述符适配（21:05，§7.18）；lithium chunk access 的 1.21.1 实现类移植与 `BOOTED`（21:25，§7.19）；lithium+ironchests 联合容器契约（21:35，§7.20）。

## 复现路径（从零）

```powershell
python tools/fetch_target_env.py     # 1.21.1 client jar / mappings / Fabric API / loader
python tools/fetch_corpus.py         # 10 份样本（校验 sha512）
cd java; gradle --no-daemon installDist; cd ..
python tools/setup_server.py --instance work/instances/fabric-1.21.1-server
python tools/remap_server.py --instance work/instances/fabric-1.21.1-server --loader 0.19.5 `
  --mappings work/cb/data/mappings/intermediary-1.21.1.tiny
python tools/run_server.py --instance work/instances/fabric-1.21.1-server --log runs/boot.log
```

转换 ironchests 需要 CenturyBridge 引擎（`work/upstream/src/...`，编译脚本见 `docs/baseline.md` §6），然后：

```powershell
mcbridge1201 patch --in <converted.jar> --out patched.jar --rules rules/fabric-1.21.1/container.json `
  --client-jar work/target/client-1.21.1.jar --mappings work/target/intermediary-1.21.1-v2.jar `
  --lib <datafixerupper.jar>
python tools/inject_aw.py --jar patched.jar --out final.jar --aw rules/fabric-1.21.1/mcbridge.accesswidener
```

lithium 调用点 + Mixin 目标 + chunk access 移植（完整命令和日志见 `runs/p10-lithium-signature/README.md`、`runs/p11-lithium-explosion/README.md`、`runs/p13-chunk-port/README.md`）：

```powershell
python tools/build_bridges.py --stub work/cb/data/jars/client-1.21.1-intermediary.jar `
  --lib work/lib/gson-2.11.0.jar --lib <datafixerupper.jar> --out work/bridges
python tools/build_mixins.py --stub work/remap/server-intermediary.jar `
  --lib <sponge-mixin.jar> --lib work/bridges --out work/mixins
mcbridge1201 patch --in <lithium converted.jar> --out lithium-patched.jar `
  --rules rules/fabric-1.21.1/lithium-degraded.json `
  --rules rules/fabric-1.21.1/lithium.json `
  --bridge-dir work/bridges --bridge-dir work/mixins
```

## 不要做的事

- 不要把 `fromJson` 的全匹配回退当作兼容成功；如果未来重新出现，档案里必须保持 `degraded`。
- 不要用 mixin 剥离掩盖核心逻辑（存档/掉落/同步）。
- 不要分发游戏 jar、模组 jar 或转换件；只分发工具、规则与哈希清单。
- 不要把静态 `ANALYZED` 或 `blocked_static` 写成“可运行”。
