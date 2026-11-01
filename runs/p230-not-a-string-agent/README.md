# p230 — `Not a string` 结案：单人加入时 level.dat 的空 `Player` 模板

日期：2026-11-01。类型：**原版 1.20.4 的无害日志**，不是转换/启动器/模组问题。

## 结论

`[Server thread/ERROR]: Not a string` 来自原版单人（集成服务器）加入世界时的这段代码：

```text
PlayerList.placeNewPlayer                     (aqv.a, SourceFile:158)
  -> loadPlayerData(ServerPlayer)             (aqv.a(ane))
     -> worldData.getPlayerData()             (egs.y)      // level.dat 的 Data.Player
  -> new Dynamic(NbtOps, playerTag.get("Dimension"))
  -> DimensionType.CODEC.parse(...)           (dmq.a)
  -> DataResult.resultOrPartial(LOGGER::error)
  -> Optional.orElse(overworld default)
```

`level.dat` 里的 `Player` 是一个**空模板**（`{}`，没有 `Dimension` 字段）。`NbtOps` 解析缺失字段时
返回错误消息 `Not a string`，`resultOrPartial` 把它原样打到日志；随后代码回退到主世界默认维度。
**玩家数据本身在 `playerdata/<uuid>.dat`，不受影响；加入、进世界、玩法都正常。**

## 证据

### 1. 抓到的真实栈（Java agent，原始行见 `stack.txt`）

```text
java.lang.Exception: TRACE Not a string
  at org.apache.logging.slf4j.Log4jLogger.error(Log4jLogger.java)
  at com.mojang.serialization.DataResult.lambda$resultOrPartial$3(DataResult.java:86)
  at com.mojang.serialization.DataResult.resultOrPartial(DataResult.java:83)
  at aqv.a(SourceFile:158)          -> net.minecraft.server.players.PlayerList
  at aoa.a(SourceFile:128)          -> ServerConfigurationPacketListenerImpl
  at yy.a / xh.a / aia.run          -> 配置完成包 -> PacketUtils -> TickTask
  at net.minecraft.server.MinecraftServer.b/d
```

### 2. 官方映射（client_mappings 1.20.4）

| 混淆 | 命名 |
|---|---|
| aqv | `net.minecraft.server.players.PlayerList` |
| aoa | `net.minecraft.server.network.ServerConfigurationPacketListenerImpl` |
| dmq | `net.minecraft.world.level.dimension.DimensionType` |
| tb | `net.minecraft.nbt.NbtOps`（`getStringValue` 的错误消息就在这里） |

### 3. NBT 实测（`nbt_probe.py`）

| level.dat | `Player` | `Dimension` | 该行 |
|---|---|---|---|
| 1.20.4 全新世界（服务端生成） | 存在，`{}` 空模板 | **缺失** | **有** |
| 1.20.4 玩过多次的世界 | 完整玩家数据 | `String "minecraft:overworld"` | 首次创建时有过，之后不再 |
| 1.21.1 世界 | **不存在 Player** | — | 没有（p214 一致） |

### 4. 不是“一次性”

对同一个 `level.dat` 仍为空模板的世界再进一次，**仍然会出现**（`rejoin.py`：`not_a_string = True`）。
一旦世界保存出完整 `Player.Dimension`（字符串），后续就不再打。

## 影响与处理

- **无功能影响**：加入成功、维度回退到主世界、存档正常；不需要为它改核心逻辑；
- 可选消音：把 `level.dat` 的 `Player.Dimension` 写成字符串，或删掉空的 `Player` 模板；
  本仓库**不改玩家存档**，只记录；
- `p213`/`p214` 里把它列进“允许名单”是正确的，但当时的“来源未知”现在可以销案。

## 复现与工具

- `runs/p229-fresh-world-jfr/probe.py`：服务端生成新世界 + quickplay + JFR；
- `runs/p230-not-a-string-agent/rejoin.py`：直接重进已有世界，确认会重复出现；
- `TraceAgent.java`：ASM agent，仅拦截 `Log4jLogger.error(String)` 且参数等于
  `Not a string`，打印一次栈。构建（产物不入库，仓库保持 0 jar）：

```text
javac -cp <asm.jar> -d build runs/p230-not-a-string-agent/TraceAgent.java
jar cfm trace-agent.jar manifest.mf -C build .
java -javaagent:trace-agent.jar ...
```
