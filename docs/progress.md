# 进度交接

最后更新：2026-10-18 20:50（Asia/Shanghai）。下一轮从这里继续，不必重读方案全文。

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
| 早期阻塞日志 | `runs/p0-server-baseline/` |
| 证据 hash 清单 | `runs/SHA256SUMS.txt` |

## 未解决（按优先级）

1. **lithium 的 `ExplosionMixin` 注入目标变化**：1.21.1 的 `Explosion` 构造器改为接收 `Holder`/注册表项，旧 `@Inject` 描述符不存在。这是当前 lithium 启动的下一道墙；需要改注入点或用规则显式降级，不得删除核心逻辑 mixin。
2. **调用点适配的覆盖面**：目前只验证了顶层 jar 的直接调用/句柄；嵌套 jar（JiJ）内的调用点尚未覆盖，需要把桥嵌入到对应嵌套 jar 或改用可见性更好的桥部署方式。
3. **`Codec.dispatch` 的可靠适配**：ironchests 契约虽已通过，但 `assumeMapUnsafe` 在部分路径仍可能 `Optional.of(null)`；应改成真正的 `MapCodec` 构造/显式诊断。
4. **CenturyBridge 桥 jar 未构建**：`core/shims/1.21.1` 未编译，`build.sh` 四道门禁未跑（`MixinCheck` 缺失）。
5. **玩家侧 / 多人**：GUI、右键交互、渲染、两个客户端同步仍 pending；服务端只做了命令契约。
6. **Forge 成员级分析缺失**：需 `mcp_config` joined.tsrg（SRG）+ 1.21.1 Mojang 映射 + NeoForge 1.21.1 索引。
7. **Mixin 注入点级分析**：只看目标类是否存在，未看 ordinal/slice/局部变量；`ExplosionMixin` 正是这类问题。
8. **BytecodeVerify** 未编译运行，转换件未做数据流校验。
9. **重映射器的覆盖面**：目前只验证了服务端 jar；客户端 jar、带资源的 jar、模块化 jar 未验证；输出未做签名清理以外的规范化（entry 时间固定）。

## 下一步精确命令

```powershell
# A. 复现调用点适配（lithium）
$env:JAVA_HOME='C:\Users\27682\Documents\新建文件夹\.toolchain\jdk'
cd java; gradle --no-daemon installDist; cd ..
python tools/build_bridges.py --stub work/cb/data/jars/client-1.21.1-intermediary.jar `
  --lib work/lib/gson-2.11.0.jar `
  --lib work/instances/fabric-1.21.1-server/libraries/com/mojang/datafixerupper/8.0.16/datafixerupper-8.0.16.jar `
  --out work/bridges
java\build\install\mcbridge1201\bin\mcbridge1201.bat patch `
  --in work/cb/out/lithium/lithium-fabric-mc1.20.1-0.11.4+1.21.1.jar `
  --out work/cb/out/lithium/lithium-patched-callsite.jar `
  --rules rules/fabric-1.21.1/lithium-degraded.json `
  --rules rules/fabric-1.21.1/lithium.json --bridge-dir work/bridges
python tools/run_server.py --instance work/instances/fabric-1.21.1-server-lithium `
  --log runs/p10-lithium-signature/server-callsite.log --timeout 240

# B. 下一个阻断：lithium ExplosionMixin 的 @Inject 目标（1.21.1 Explosion 构造器）
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
