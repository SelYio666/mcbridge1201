# p229 — 复现 `Not a string`：全新世界 + 首次单人进入（JFR）

日期：2026-11-01。目标：不用点击，用服务端生成一个全新 1.20.4 世界，再让客户端首次进入，
在 JFR 录音下观察 `[Server thread/ERROR]: Not a string`。

## 做法

1. 从 1.20.4 官方 version json 取 `server.jar`（49,150,256 B），生成 `p229world`；
2. 把世界复制进客户端 `saves/p229-world`（每次运行前覆盖，保证“没有玩家数据”）；
3. 客户端 `--quickPlaySingleplayer p229-world` + `-XX:StartFlightRecording`；
4. 等 `joined the game` 后 `jcmd JFR.dump`，再结束进程。

## 结果

- **稳定复现**：4 次运行全部出现该行（`result.json` 为最近一次）；
- 位置固定在 `Changing simulation distance` 与 `logged in` 之间；
- JFR 里**没有**对应的 `jdk.JavaExceptionThrow` 事件 —— 这行不是异常栈，而是
  `DataResult.resultOrPartial(LOGGER::error)` 打出的编解码错误消息。

根因追踪见 `runs/p230-not-a-string-agent/`。
