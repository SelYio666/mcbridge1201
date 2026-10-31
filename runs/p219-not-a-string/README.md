# p219 — `Not a string` 溯源尝试：证据、排除项、下一步

日期：2026-10-31。目标：p213 记录的那条 `[Server thread/ERROR]: Not a string` 到底谁抛的。

## 结论（先写）

**没有查出来，但把范围收窄了，并确认它不是阻塞项**：玩家能正常加入、世界能进、玩法正常；
这条只是玩家加入瞬间服务端线程的一行 `LOGGER.error(String)`，没有堆栈。
要真正定源需要 JVM 级插桩（agent 在 `GsonHelper.getAsString` 抛错处打印栈），本轮没做。

## 已核实的证据

1. **不是 1.20.4 独有**。grep 全部 `runs/`：

   | 运行 | 版本 | 模组 | 有该行 |
   |---|---|---|---|
   | p134 / p149 / p150 / p151 / p166 / p167 / p168 / p170 / p171 / p173 | 1.21.1 | ImmediatelyFast 端口（+ Fabric API） | 有 |
   | p213（PCL2 离线启动 1.20.4） | 1.20.4 | 无（`versions/1.20.4/mods` 不存在） | 有 |
   | p214（PCL2 离线启动 1.21.1） | 1.21.1 | 无 | **没有** |

   所以既不能归因到“1.20.4”，也不能归因到“转换后的模组”。

2. **存档 JSON 本身合法**（1.20.4 的 `新的世界`）：
   - `advancements/00000000-0000-3006-….json`：`criteria` 的值都是字符串时间戳
     （`"2026-10-30 20:33:14 +0800"`），`done` 是布尔，`DataVersion: 3700`；
   - `stats/….json`：`minecraft:custom` 下全是整数；
   - `data/` 只有 `raids.dat`、`random_sequences.dat`（1.21.1 世界），**没有** `map_*.dat`；
   - `datapacks/` 为空；`versions/1.20.4/mods` 与全局 `mods/` 都不存在。
   因此“存档里的某个 JSON 字段类型写错”这条假设，在**当前样本**上不成立。

3. **出现位置固定**：p134 的日志里它紧跟在
   `Changing simulation distance to 12` 之后、`IFUser[local:…] logged in` 之前，
   即 `PlayerList.placeNewPlayer` 读玩家数据的窗口内；随后 `Loaded 16 advancements`、进游戏一切正常。

4. 它已经是 p213 `verify_launch.py` 的**允许名单**（同时有一条“它仍然被点名”的检查，没有悄悄过滤）；
   p214 则把“**没有**这条”做成了断言。

## 排除项（做过但没成立）

- **存档数据类型错**：见上，advancements/stats 都合法，无 datapack、无地图数据；
- **1.20.4 特有**：1.21.1 的多次运行同样出现；
- **转换模组特有**：1.20.4 那次根本没装模组。

## 下一步（要做就做实的）

1. 写一个 `-javaagent`（ASM 在 `GsonHelper`/`class_3511` 的 `getAsString` 的
   `JsonSyntaxException("Not a string")` 抛出点插 `new Exception().printStackTrace()`），
   或用 Arthas `watch` 在同一位置打印栈；
2. 用 PCL 的离线 UUID（`00000000-0000-3006-998f-555b73d6dcef`）复现，保证读的是同一份玩家数据
   （本仓库 `mclaunch.offline_uuid` 用的是标准 v3，和 PCL 不同，直接换启动器会绕开该文件）；
3. 定位后决定：若是 mod 配置解析，就修；若是原版行为，就在 README 标注为已知日志。

## 影响

非阻塞：加入成功、世界可进、玩法正常；不应为了消掉一行日志去动核心逻辑。

## JFR 复现尝试（2026-10-31）

做法：把 1.20.4 装进 `work/launcher-e2e`，复制 p213 那个“新的世界”，用 PCL 同款离线 UUID
（`00000000-0000-3006-998f-555b73d6dcef`）、`--quickPlaySingleplayer` 首次进入，并加
`-XX:StartFlightRecording=filename=...,settings=profile,dumponexit=true`；进服后用
`jcmd <pid> JFR.stop filename=...` 收尾。

- **JFR 方法本身可用**：录制文件生成成功，`jfr print --events jdk.JavaExceptionThrow` 可用；
- **这条日志没复现**：第一次（保留玩家数据）与第二次（清空 `advancements`/`stats`/`playerdata`）
  都正常 `logged in` / `joined the game`，日志里没有 `Not a string`；
- 因此它**不随世界/玩家数据稳定出现**，更可能依赖 PCL 自己的启动上下文（它安装的版本目录、选项、
  时序）或当次偶发；下一步是在 PCL 里带同样的 JVM 参数启动后抓 JFR。

可复用脚本：`jfr_repro.py`（参数：`--root --version --world --jfr`）。

## 用 PCL 自己的启动命令复现（2026-10-31）

`PCL\LatestLaunch.bat` 保存着 PCL 上次启动的完整 java 命令（本质是模板：末尾的
`--clientId ${clientid} --xuid ${auth_xuid}` 由 PCL 运行时替换，`cd /D` 到
`versions\1.20.4`）。本轮直接取这条命令：

- 在 `java.exe` 后插入 `-XX:StartFlightRecording=filename=...,settings=profile,dumponexit=true`；
- 末尾追加 `--quickPlaySingleplayer 新的世界`；
- 以 `versions\1.20.4` 为 cwd 运行，等 `joined the game` 后用 `jcmd JFR.stop` 收尾。

结果：**仍然没有 `Not a string`**（`logged in`/`joined the game` 正常，只有离线必然的 401 两条）。
因此这条日志既不复现于我们的启动器、也不复现于 PCL 同款命令；更像 p213 那次
**首次创建世界/首次加入**时的一次性事件，而不是稳定路径。

若之后再遇到：同样的 JFR 参数 + `jfr print --events jdk.JavaExceptionThrow --stack-depth 30` 即可拿栈。
