# p251 — 损伤→规则推荐器（compat 方向 A）

日期：2026-11-08。新增 `tools/suggest_rules.py`：把 analyzer 的逐符号损伤
（`missingMember` / `descMismatch`）通过 1.20.1↔1.21.1 映射链（Fabric intermediary
↔ obfuscated ↔ Mojang official，两侧 `intermediary-<ver>-v2.jar` + `client-<ver>-mappings.txt`）
联接成**带身份映射依据**的规则草稿，输出可直接放进 `rules/fabric-1.21.1/` 的
schema 合法文件（`fieldRedirect` / `methodRedirect` / `callSiteAdaptation` /
`signatureAdaptation` 条目，每条带 id、来源、置信度、evidence），并且**先对照现有
29 份规则做冲突检查，会撞键的候选直接丢弃并说明**。

## 工具行为（每条建议都验过映射身份）

- `descMismatch`：analyzer 的 note 给出目标侧 owner+desc；两侧都解到 Mojang 名后，
  身份一致才给 high；Mojang 名跨版本不同（改名/搬家）给 medium。实例方法调用会在
  bridgeDesc 前补接收者参数（从 1.20.1 intermediary stub 读 ACC_STATIC 判定），
  静态调用直接用旧描述符——这是 callSiteAdaptation 桥是 INVOKESTATIC 的硬约束。
- `missingMember`：同一 intermediary id 在 1.21.1 搬家 → methodRedirect 转发桥（high）；
  id 消失但 Mojang 名还在 → 按 Mojang 名+描述符找新 id（同 desc=high / 异=medium）；
  两侧都找不到（如 NBT→组件）→ **拒绝给机械规则**，落成 note（"needs a semantic port"）。
- 冲突检查覆盖 fieldRedirect/methodRedirect/callSiteAdaptation/constructorRedirect/
  signatureAdaptation/mixinCallback/methodRename 的匹配键，**含 signatureAdaptation 的
  callRewrites 子条目**，opcode 0（通配）与钉死 opcode 视为重叠。

## 验收 1：在已通过模组上跑，建议不矛盾（证据 suggestions/）

| 模组 | 草稿 | 丢弃冲突 | 说明 |
|---|---|---|---|
| ironchests | 16 | **4** | 丢的 4 条（load/saveAdditional/loadAllItems/saveAllItems）正是 `container.json` 两条 signatureAdaptation 的 callRewrites 已覆盖的调用点 |
| trashslot | 1 | 0 | `save.retarget` 指向 trashslot.json 未覆盖的调用点，无重叠 |
| lithium | 7 | **1** | `checkneighbourblocks.callsite` 与 `lithium.json` 的同键规则撞（含 opcode 184 通配重叠修正后正确丢弃） |

剩余草稿都指向这些模组**残留但未被规则覆盖**的调用点，不与任何现有规则冲突。

## 验收 2：失败样本 → 挑 1 条建议 → 失败变通过

样本：**VeinMiner 2.0.7（Fabric 1.20.1）+ 其正确依赖 silk 1.10.1**（p111 当时配的是
silk-all 1.10.7——那是新 MC 线的构建，构造器形状都对不上，先换成 1.10.1 才能触到
真正的转换损伤）。

链条：silk 1.10.1 CenturyBridge 转换（ok_degraded_partial）→ 嵌套 jar 元数据
`minecraft: 1.20.x` 手工 bump 到 1.21.1（p111 对 EntityCulling 嵌套库的同一做法，
转换器只改顶层）→ 装入 1.21.1 专用服务器。

- **before**（`logs/before-crash-worldload.log`）：世界加载即崩——
  `NoSuchMethodError: net.minecraft.class_26.method_17924(Function,Supplier,String)`，
  出自 silk-persistence 的 ServerWorldMixin（嵌套 jar）注入 ServerLevel.<init> 的路径。
- **suggester 输出**：`computeifabsent.callsite`，置信度 **high**，evidence 写明
  1.20.1 `DimensionDataStorage.computeIfAbsent(Function,Supplier,String)` →
  1.21.1 `(SavedData$Factory,String)`；bridgeDesc 自动带接收者参数（实例方法）。
- **人工实现**：桥 `java/src/bridge/.../DimensionDataStorageComputeIfAbsent.java`——
  旧 (loadFn, supplier, name) 重建为 `SavedData.Factory(supplier, (tag,lookup)->loadFn(tag),
  DataFixTypes.LEVEL)`。DataFixTypes 槽取 `field_19212` 是照抄 **silk 官方 1.21 构建**
  的 `CompoundSavedData$Companion.createFactory` 字节码（javap 记录在案）。
- **规则**：`rules/fabric-1.21.1/silk-persistence.json`（callSiteAdaptation）；
  `patch` 报告 `applied 1 time(s)`，桥嵌入使用它的嵌套 jar（silk-persistence）。
- **after**（`logs/after-boot-commands.log`）：`Done (1.157s)`；
  `veinminer` → `Veinminer Version: 2.0.7 (fabric) / Game Version: 1.21.1`；
  `veinminer toggle` → `Veinminer functions disabled`；正常 stop、三维度存档。

## 边界（如实）

- VeinMiner 的**挖矿功能路径**（hurtAndBreak / broadcastBreakEvent 两条建议）未验证：
  触发需要真实客户端挖方块，本轮没有客户端驱动；这两条仍是草稿。
- silk 转换剥离了 7 个 mixin、有 6 个 L2 方法和 7 个 tombstone 残留
  （见 suggestions/sugg-silk 的草稿与 note）；本轮只把服务器启动与命令路径修通，
  **不声称 silk 功能完整**。
- suggester 不分析模组自身/第三方库内部的变化（analyzer 只索引 MC+API 类）：
  VeinMiner↔silk 的构造器错配是靠运行日志发现的，不是 suggester 输出。
- `signatureAdaptation` 草稿只在「纯尾部追加参数」形状时生成（静态分析看不出
  mod 是否覆写，targetClass 要人工填）。

## 复现

```text
# 建议（任一 plan）
py -3.12 tools/suggest_rules.py --plan runs/p251-suggest-rules/plan-silk.json --out runs/p251-suggest-rules/suggestions/silk
# silk 链条
java -cp <CenturyBridge classes>;asm;gson top.dext.centurybridge.Main convert work/cb/data/segments 1.20.1 1.21.1 work/cb/out/popular/silk work/tmp/silk-1.10.1.jar
py -3.12 - <<...  # 嵌套 fabric.mod.json minecraft -> 1.21.1（脚本见 result.json 步骤）
python tools/build_bridges.py --profile targets/fabric-1.21.1.json
mcbridge1201 patch --in <converted> --out <patched> --rules rules/fabric-1.21.1/silk-persistence.json --bridge-dir work/targets/fabric-1.21.1/bridges --client-jar work/target/client-1.21.1.jar --mappings work/target/intermediary-1.21.1-v2.jar --lib <dfu>
python tools/run_server.py --instance work/instances/veinminer-server --log <log> --command "veinminer" --command "veinminer toggle" --command stop
```

jars 不入库（红线 0 jar）；链条各步的 sha256 记在 result.json。
