# p203 — 两个客户端在同一服务端 tick 删自己的垃圾桶

日期：2026-10-28
结论：p192 留下的 "concurrent same-tick trash operations from two clients" 关了。**两个玩家的 trash 写入落在同一个服务端 tick（819），线程是 Server thread，相差 4 ms**，各自的数值互不影响。

## 结果

```text
P203_FIRE role=A action=delete epochMs=1793197755075 driftMs=0 tick=537
P203_FIRE role=B action=take   epochMs=1793197755075 driftMs=0 tick=197

P203_S2C thread=Server thread tick=819 wall=...505078 message=…MessageDeleteFromSlot
P203_SET side=SERVER thread=Server thread tick=819 wall=...505082 seeding=false user=GridUser stack=empty
P203_S2C thread=Server thread tick=819 wall=...505083 message=…MessageTrashSlotClick
P203_SET side=SERVER thread=Server thread tick=819 wall=...505086 seeding=false user=TrashB stack=minecraft:diamondx3

P203_SERVER tick=920 user=GridUser trash=empty
P203_SERVER tick=920 user=TrashB   trash=minecraft:diamondx3
```

`result.json`：14 项判据全 `true`，其中 `same_server_tick=true`、`packet_and_write_same_tick=true`、`wall_delta_ms=4`、`writes_on_server_thread=true`。

## 一、为什么把"并发"定义在服务端

"同时操作"这句话在客户端是说不清的：两个客户端各自每 50 ms 走一 tick，**间隔 2 ms 可能跨 tick，间隔 40 ms 也可能同 tick**。所以判据只能放在有权威 tick 计数器的那一侧——专用服务端：

- 探针在每个服务端 tick 结束时 `ticks++`；
- `TrashHelper.setTrashItem`（玩家持久化 NBT 的唯一写入口）在 `HEAD` 被打时间戳，打出 `side / thread / tick / wall / seeding / user / stack`；
- 两个不同 `user` 的写入带**同一个 tick 号**，才是"并发"。

种子写入也被打上了戳（`seeding=true`），所以它不会被误当成玩家操作——下面那两条 `seeding=true` 的 `diamondx5/diamondx4` 就是探针自己下的种。

顺带把 p65 的登录重置也变成了可见事实：每次加入都有一条 `seeding=false stack=empty` 的写入（tick 278 / 620），早于任何玩家操作。

## 二、怎么让两个客户端真的挤进同一个 tick

不是"差不多同时点"：

1. 两个客户端都 `P203_READY` 之后，harness 才把**同一个开火时刻**（`now + 3000 ms`）写进文件；
2. 客户端每 tick 读一次文件，进入目标前 60 ms 就在客户端线程上**自旋**到点；
3. 到点立刻走 p191/p192 的真实回调路径开火。

于是两边 `P203_FIRE` 的 `epochMs` 完全相同、`driftMs=0`；`P203_SET` 的 wall 差 4 ms，`P203_S2C`（Balm 接收器被调用的那一刻）差 5 ms。

两种操作故意不一样，串台就没法蒙混：

| 玩家 | 手上 | 操作 | 服务端写入 |
|---|---|---|---|
| GridUser (A) | trash 5 钻 | Delete 清空 | `empty` |
| TrashB (B) | trash 4 钻 | 右键取 1 | `minecraft:diamondx3` |

如果谁的包跑到对方身上，A 会变成 4 或 3、B 会变成 empty——都不是现在这个结果。客户端侧另外读出 B 的鼠标上确实握着 1 颗（`carried=minecraft:diamondx1`），A 的 UI 是 empty。

## 三、三次返工，都记下来

1. **第一次：一个包都没拦到。** 探针先混入 `ServerPlayNetworkHandler.onCustomPayload`（`class_3244.method_52392`），带 `mixin.debug` 跑过一次，确认 `Mixing PacketMixin … into class_3244` **确实生效**；但正式跑里连一行 `P203_PKT` 都没有，而服务端 trash 明明变了。也就是说 Balm 桥的 serverbound 消息在本环境里不走这条派发路径。与其猜，把戳挪到**状态写入点**——那才是这条断言真正关心的地方。
2. **第二次：拦到了，但分析器取错了写点。** 拿到 `P203_SET` 之后，第一版分析取"每个玩家的第一条写入"，取到的其实是**登录重置**那两条 `empty`（tick 315 / 671，相隔 17 s），于是 `same_server_tick=false`。改成以开火时刻开窗（`[fire-500, fire+5000]`），并把窗口之前的写入单独列成 `mutations_before_fire`，才是对的。
3. **截图没拍成**：`_grab_window` 需要 Pillow，本机没装（`screenshot skipped`）。这条断言是服务端陈述，两个客户端的 UI 状态是从日志里读的 `P203_TRASH`（含 `carried`），不是看图看出来的。

## 四、和 p190/p192 的关系

- p190：两客户端，A 排水、B 不动 → 隔离；
- p192：三客户端，B 主动排水 + A 重进重置 → 隔离 + 上游登录语义；
- p203：两客户端，**同一 tick** 各自操作 → 隔离在并发下依然成立，且写入都发生在 Server thread 上。

`P203_S2C` 顺带把两条消息的真实身份记下来了：Delete 走 `MessageDeleteFromSlot`，右键走 `MessageTrashSlotClick`（都不是 `MessageTrashSlotContent`，后者是 S2C 方向，p64）。

## 未覆盖（如实）

- **四个及以上客户端**；
- 同一玩家同一 tick 的两次操作（同一连接内是串行的，没有可测的并发）；
- 真实网络：两个客户端都在本机回环，延迟 <1 ms。跨机器时"同 tick"取决于到达时刻，这套判据仍然可用，但没有测；
- 非 Windows、非 60 Hz 显示器下的开火对齐精度。

## 复现

```text
python runs/p203-trash-concurrent/build.py
python runs/p203-trash-concurrent/run.py --timeout 420
```

专用服务器（25566、survival、`online-mode=false`）由 harness 启停，两个客户端用同一个 `launcher-e2e` 实例先后启动（`--quickPlayMultiplayer`），测试结束进程全部回收，`server.properties` 原样备份在 `server.properties.before`。

## 证据

| 文件 | 内容 |
|---|---|
| `server.log` | `P203_JOIN` / `P203_SEED` / `P203_SET` / `P203_S2C` / `P203_SERVER` 全量 |
| `client-a.log`、`client-b.log` | 开火时刻、漂移、各自 UI 的 trash 与手上物品 |
| `result.json` | 14 项判据 + 窗口内外的写入 + 服务端尾部 |
| `repeat/round1-*.log`、`repeat/round1-result.json` | 第一轮（分析器还没修）的原始日志：两次写入同在 **tick 905**，可作为独立复现 |
| `probes/p203-trash-concurrent/` | 探针源码（`ConcurrentProbe`、`ClientProbe`、`PacketMixin`、`TrashHelperMixin`、`BalmBridgeMixin`、两个鼠标 accessor） |

无新 release（v0.5.6，只加探针）。
