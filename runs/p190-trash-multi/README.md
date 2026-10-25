# p190 — TrashSlot 多客户端：trash 按玩家隔离（双客户端 + dedicated server）

日期：2026-10-25。p183–p185 留下的 "多客户端同步未测"。两个真实客户端（同一台机器、同一个
launcher 实例目录先后启动）加入同一 dedicated server，验证 **trash 是每玩家独立的**：A 的
移入/取回/清空不影响 B，服务端两份 trash 互不串数据。

## 场景

- dedicated server `fabric-1.21.1-server-trashslot`（端口 25566、`online-mode=false`、survival），
  patched TrashSlot 两端 + p190 probe；
- 服务端 probe（`MULTI_SEED`）：两个玩家都加入后，GridUser 的服务端 trash 放 **5 钻**，
  TrashB 放 **3 钻**；之后每 2 s 打印两人的服务端 trash（`MULTI_SERVER user=... trash=...`）；
- 客户端 A=GridUser 先加入、客户端 B=TrashB 后加入（同 launcher 实例、先后两个进程）；
  两个客户端的 probe 各自打开 inventory 并把**本地 trash UI** seed 成 5 钻（`MULTI_CLIENT_SEED`；
  服务端不会主动推 trash 内容，clientbound 更新是 reply 语义——p64 已记录）；
- 真实 GUI 注入（A 窗口 focus + 光标定位到 trash 槽中心，几何来自 probe 的
  `TRASH_CLIENT ... left= top= trashX= trashY= scale=` 行）：
  1. **右键** trash（p185 语义：取 1 留 4）；
  2. **Delete**（扩展键标志，p183 语义：清空）。

## 结果（result.json / server.log / client-a.log / client-b.log / after.png）

```text
MULTI_SEED first=diamondx5 second=diamondx3
MULTI_SERVER user=GridUser trash=minecraft:diamondx5    <- A 初始
MULTI_SERVER user=TrashB  trash=minecraft:diamondx3     <- B 初始
MULTI_SERVER user=GridUser trash=minecraft:diamondx4    <- A 右键取 1
MULTI_SERVER user=GridUser trash=empty                  <- A Delete 清空
MULTI_SERVER user=TrashB  trash=minecraft:diamondx3     <- B 全程不变
```

- `result.json`：`a_took_one=true`（5→4）、`a_emptied=true`（→empty）、
  `b_server_constant_diamondx3=true`（B 的服务端 trash 全程 diamondx3）、
  `b_client_constant_diamondx3=true`（键名沿用早期命名；实际断言 = B 的客户端 UI 全程停留在
  自己 seed 的 `trash=minecraft:diamondx5`，即 A 的操作对 B 的显示零影响）；
- 隔离语义：服务端 `TrashHelper` 按玩家存取（A 的 click/delete 消息只作用于 A 的 trash；
  `MessageDeleteFromSlot.handle` 的 `Balm.networking().reply` 只回发送者——B 不收到 A 的更新，
  与 p64 观察一致）；
- `after.png`：A 的 inventory（trash 已清空）；无 crash/异常。

## 调试记录（测试侧）

- 一次 patch 的锚点字符串不匹配且 `.replace` 无断言静默失败，导致 seed 块没进源码、
  探针 jar 里没有 `MULTI_CLIENT_SEED`——教训：探针改动后要验证编译产物包含新 marker；
- 日志里物品带 namespace（`trash=minecraft:diamondx5`），gate 匹配串最初写成裸 id 没命中；
- 双客户端同抢一个实例目录：上一个客户端进程没退干净时 mods 目录文件被锁
  （`PermissionError`），run 前需要确保旧 java 进程退出（harness 的 finally 会 terminate，
  但被取消的运行会留下孤儿进程）。

## 未覆盖

- B 主动操作自己的 trash（对称方向）；A/B 互相看对方 trash 的 UI（TrashSlot 本就不显示他人
  trash，无此语义）；
- 重进后 trash 保持（TrashSlot 登录重置是上游行为，p65 已记录）；
- 三个及以上客户端；创意模式下的多客户端。

## 复现

```text
python runs/p190-trash-multi/build.py
python runs/p190-trash-multi/run.py --timeout 300
```

## 证据

`after.png`、`client-a.log`、`client-b.log`、`server.log`、`result.json`、`src/probe/`、
`fabric.mod.json`、`build.py`、`run.py`。测试后 server（25565 + 原版 trashslot jar）与
client（ImmediatelyFast + Fabric API + p181 probe）已恢复。
