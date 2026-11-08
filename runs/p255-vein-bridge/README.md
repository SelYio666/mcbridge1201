# p255 — VeinMiner 收尾：实现剩余两条建议 + 无客户端的运行时验证

日期：2026-11-08。p251 的 VeinMiner 建议里还有两条没实现（hurtAndBreak /
broadcastBreakEvent——挖矿时工具耐久与破坏广播路径）。本轮把两条都实现并通过
**探针 mod 做了真实运行时验证**（不需要客户端），顺带修掉 suggester 的一个真缺陷。

## suggester 缺陷修复（tools/suggest_rules.py）

`broadcastBreakEvent` 声明在 LivingEntity 上，而 VeinMiner 的常量池里 owner 写的是
Player——ACC_STATIC 探测按 owner 查不到，旧逻辑退回"无接收者"的 bridgeDesc，但这是
**实例调用**（接收者还在栈上）。修复：owner 查不到时用名字+描述符回退找声明类再探测。
修复后草稿 bridgeDesc = `(Lnet/minecraft/class_1309;Lnet/minecraft/class_1304;)V`（带
LivingEntity 接收者），并注明"declared on class_1309, called through class_1657"。

## 两个桥（方法体均从两侧字节码转录，注释里写明依据）

- `ItemStackHurtAndBreakLegacy`：1.20.1 `hurtAndBreak(int, LivingEntity, Consumer)` →
  1.21.1 `(int, ServerLevel, @Nullable ServerPlayer, Consumer)`。1.21.1 四参的 player
  可空（反汇编证实 `ifnull 20`），非玩家实体传 null 正好对应 1.20.1 的非玩家路径；
  附魔减伤（Unbreaking）已从 hurt() 移进四参本体，行为保留。**关键语义变化**：1.20.1 的
  Consumer 收 LivingEntity，1.21.1 收破坏的 Item——桥把 consumer 重绑为
  `item -> oldConsumer.accept(entity)`。
- `LivingEntityBroadcastBreakEvent`：1.20.1 `broadcastBreakEvent(EquipmentSlot)` →
  1.21.1 `onEquippedItemBroken(Item, EquipmentSlot)`。两者本体相同（都是
  `broadcastEntityEvent(this, slotEventId)`，1.21.1 的 Item 参数根本没被读——反汇编
  证实），桥用槽内当前物品填充。

规则 `rules/fabric-1.21.1/veinminer-damage.json`（2 条 callSiteAdaptation），patch 命中
各 1 次，桥嵌入补丁 jar。

## 运行时验证（无客户端）

探针 mod（`probes/p255-vein-bridge/`，构建脚本 `tools/build_vein_probe.py`）注册
`/mcbridge-probe`：RCON 先 `forceload add 0 0`，召唤一只 NoAI 僵尸、主手钻石镐，
探针从 `getAllEntities` 找到它，对活体实体直接调两个桥并断言（`logs/probe-pass-run.log`）：

```text
PROBE_HURT     before=0 after=100 maxDamage=1561 count=1 consumerCalls=0
PROBE_BREAK    countBefore=1 countAfter=0 consumerCalls=1 consumerGotEntity=true
PROBE_BROADCAST ok
PROBE_RESULT   pass=true
```

- 伤害 0→100、未坏不触发 consumer（1.20.1 语义：consumer 只在物品**实际破坏**时触发）；
- 超限时 count 1→0、1.20.1 形状的 consumer 收到的是**僵尸实体**（不是 1.21.1 的 Item）——
  重绑语义成立；
- 广播桥走 1.21.1 onEquippedItemBroken 无异常。
- 桥类从补丁后的 VeinMiner jar 里加载（探针与 VeinMiner 同装），验证的就是 patch 产物。

回归：同一实例（VeinMiner 补丁件 + p251 的 silk 链 + FLK + 探针）`Done (4.620s)`，
`veinminer` → `Veinminer Version: 2.0.7 (fabric) / Game Version: 1.21.1`
（`logs/veinminer-regression.log`）。

## 调试记录（3 次失败都如实保留在 work/tmp）

1. 前两次 `no-zombie`：召唤点 (0,-59,0)/(0,80,0) 不在已加载区块，实体被丢弃——原版
   `data get entity @e[type=zombie]` 也找不到，确认是区块问题而非代码问题；`forceload
   add 0 0` 后解决。
2. 一次 `fail=no-held-item`：上一轮探针已把残留僵尸的镐打坏（世界未重置）；探针改为只选
   主手非空僵尸，并重置世界。
3. 探针断言 bug：曾在"未破坏"分支断言 consumer 必须触发——与 1.20.1 语义不符，修正为 0；
   pass 表达式还在破坏后误查了破坏前的数量，一并修正。

## 边界（如实）

- hurtAndBreak 的 **ServerPlayer 分支**（耐久同步 + ITEM_DURABILITY_CHANGED 判据）由
  1.21.1 原版代码执行，但没有真实客户端玩家观测过；
- 真实挖矿玩法（客户端破块触发 VeinMiner 的 damageItem）仍未验证——需要客户端驱动，
  与 p251 边界一致；
- 探针验证覆盖 null-ServerPlayer 路径 + 1.20.1 consumer 契约 + 广播桥。

## 复现

```text
py -3.12 tools/build_bridges.py --profile targets/fabric-1.21.1.json
mcbridge1201 patch --in work/cb/out/popular/veinminer/Veinminer-2.0.7+1.21.1.jar --out work/tmp/Veinminer-patched.jar \
  --rules rules/fabric-1.21.1/veinminer-damage.json --bridge-dir work/targets/fabric-1.21.1/bridges \
  --client-jar work/target/client-1.21.1.jar --mappings work/target/intermediary-1.21.1-v2.jar --lib <dfu>
py -3.12 tools/build_vein_probe.py --stub work/cb/data/jars/client-1.21.1-intermediary.jar \
  --lib work/target/fabric-loader-0.19.5.jar \
  --lib work/instances/fabric-1.21.1-server/.fabric/processedMods/fabric-command-api-v2-*.jar \
  --lib work/instances/fabric-1.21.1-server/.fabric/processedMods/fabric-api-base-*.jar \
  --lib work/instances/fabric-1.21.1-server/libraries/com/mojang/brigadier/1.3.10/brigadier-1.3.10.jar \
  --lib work/instances/fabric-1.21.1-server/libraries/org/slf4j/slf4j-api/2.0.9/slf4j-api-2.0.9.jar \
  --bridge-classes work/targets/fabric-1.21.1/bridges --out work/shim/mcbridge-vein-probe-1.0.0.jar
python tools/run_server.py --instance work/instances/vein-probe-server --log <log> \
  --command "forceload add 0 0" \
  --command "summon minecraft:zombie 0 80 0 {HandItems:[{id:\"minecraft:diamond_pickaxe\",count:1},{}],NoAI:1b,PersistenceRequired:1b}" \
  --command "mcbridge-probe" --command stop
```
