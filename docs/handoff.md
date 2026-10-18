# 交接摘要（一页）


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
9. **Mixin 注入点级分析**：只看目标类是否存在，未看 ordinal/slice/局部变量；chunk access 已通过实现类替换解决，但同类问题仍需分析器覆盖。

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
