# p232 — 同一玩家同 tick 两次垃圾桶操作（p203 遗留边界）

日期：2026-11-01。**结论：同一玩家的两个操作在同 tick 内都落、按注入顺序落、且落在同一个
服务端 tick（1755），第二个操作没有被合并或丢弃**；三个旁观客户端全程零影响。判据 21/21。

## 场景（完全复用 p231 的设施）

- 与 [p231](../p231-quad-latency/README.md) 相同：专用服务器（25566，offline）+ 4 个客户端 ×
  4 个独立 gameDir + 每条连接经 `latency_proxy.py`（双向各延 50 ms）；
- 唯一区别在探针动作（`probes/p232-same-player-two-ops/`，jar `work/tmp/p232twoops.jar`）：
  - **A（GridUser）`action=double`**：同一 client tick 内先注入右键（trash 5→4，光标拿 1），
    紧接着注入 Delete（trash 4→empty，光标保持 1）——两条 serverbound 消息同一毫秒发出；
  - **B/C/D `action=none`**：旁观见证人，探针打一行 `P232_STANDBY` 后永不开火；
- 种子不变：A=5、B=4、C=3、D=2（服务端写）。

## 结果（result.json 21/21 true）

```text
P232_JOIN ×4 → P232_SEED tick=1530 GridUser=5 TrashB=4 TrashC=3 TrashD=2
P232_FIRE role=A action=double epochMs=1793524195173 driftMs=0 tick=1215
P232_SET side=SERVER thread=Server thread tick=1755 wall=…5249 user=GridUser stack=minecraft:diamondx4   <- take
P232_SET side=SERVER thread=Server thread tick=1755 wall=…5250 user=GridUser stack=empty                 <- delete
one_way = 76 / 77 ms（两条写各自相对开火 epoch；注入 50 ms 单向 + tick 对齐）
```

- **两条写入都在 tick 1755，wall 相差 1 ms，顺序与注入一致**（先 take 后 delete）——
  同一玩家在同一 tick 的第二个操作既没有被合并、也没有被丢弃，也没有落到下一个 tick；
- 值互为指纹：take 后是 x4（5−1）、delete 后是 empty；若顺序颠倒或只落一个，
  `first_write_is_take` / `second_write_is_delete` / `actor_has_exactly_two_writes` 会红；
- **三个见证人**：`P232_STANDBY` ×3，窗口内零写入，服务端 trash 最终 x4/x3/x2 不变，
  客户端 UI（自己的种子值 + `carried=empty`）不变——A 的两个包没有串到任何人；
- A 客户端最终 `trash=empty carried=diamondx1`（take 的那颗在光标上，Delete 只清 trash）；
- 代理 4 条连接各有 ≥200 KB 真实游戏流量；`p232-gamedir-{a..d}` 四个路径互不相同。

## 口径与边界（如实）

- **动作是 GLFW 回调边界合成输入**（p191/p192/p231 约定），不是 OS 级键鼠；
  OS 级 SendInput 需要目标窗口确证在前台并记录句柄，用户在用电脑时不做（本轮未做）。
- "同 tick"这里是单连接上两条消息背靠背到达的自然结果（wall 相差 1 ms），不是对任意
  间隔的保证；间隔拉大到接近一个 tick 的情形不在本轮范围内。
- 判据里 `both_writes_same_server_tick` 是严格断言（本轮成立）；若未来在别的负载下出现跨
  tick，应如实记录 tick 而不是放宽判据（p231 的处理先例）。
- 每客户端独立 assets / resourcepacks 仍未测（p231 的 junction 只读共享形态未变）。

## 真跨机：blocked（无第二台机器），不冒充

按第二轮交接要求如实记录：**真跨机延迟本轮未做，因为没有第二台机器**；p231/p232 的 50 ms
延迟是本机用户态代理注入的合成延迟，不能代替真实 NIC/WiFi/路由路径。就绪方案（拿到机器即可跑）：

1. 服务端留本机（`runs/p232-same-player-two-ops/run.py` 的 server 部分即可，或直接手工起
   `fabric-1.21.1-server-trashslot` 实例，端口放行）；
2. 远程机装一个 1.21.1 Fabric 客户端（同 loader/API 版本），装 balm + trashslot 转换件 +
   p232 探针 jar，`--quickPlayMultiplayer <本机LAN IP>:25566` 直连（不走代理）；
3. 沿用 p232 的探针与判据：seed → 同 epoch 开火 → `P232_SET` 的 tick/wall 与 `P232_FIRE` 的
   epochMs 相减，得到**真实网络路径**的"开火→服务端写点"延迟；RTT 用代理位置换成
   客户端 ping 值或服务端 keepalive 观测，报告里写清两机连接方式（LAN/WiFi/路由）。

## 复现

```text
py -3.12 runs/p232-same-player-two-ops/build.py
py -3.12 runs/p232-same-player-two-ops/run.py --timeout 900
```

## 证据

`result.json`、`server.log`、`client-{a..d}.log`（首行含各自 gameDir 的完整 java 命令）、
`proxy.log`（listening/traffic/close）、`after-twoops.png`、`run.py`、`latency_proxy.py`、
`build.py`、探针源码 `probes/p232-same-player-two-ops/`。
测试后环境已恢复：服务端 mods 与 server.properties 从备份还原（`work/tmp/p232-mod-backup/`、
`runs/p232-same-player-two-ops/server.properties.before`）。
