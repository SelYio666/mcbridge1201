# p231 — 四客户端 × 四独立 gameDir × 50 ms 单向延迟代理：同 tick 四方垃圾桶操作

日期：2026-11-01。关掉交接文档"多客户端 / 跨机器延迟"里**本机可关的部分**。p190/p192/p203 的
双/三客户端全都共用同一个 gameDir（`work/launcher-e2e`）且只在回环上跑过；四客户端与延迟从未测过。
真跨机（第二台机器）仍然开放，本回合不声称。

## 场景

- dedicated server（`fabric-1.21.1-server-trashslot` 实例，端口 25566，`online-mode=false`）
  + `p231quad` 探针：4 用户各 seed 5/4/3/2 钻（服务端写），每个 `TrashHelper.setTrashItem`
  写点都打 tick/wall/user/stack 戳（p203 机制的 4 用户版）；
- **4 个客户端，各自独立 gameDir**（`work/tmp/p231-gamedir-{a..d}`）：`.fabric` / `assets` /
  `libraries` / `versions` 用 NTFS junction 指回 `launcher-e2e`（运行期只读共享），
  mods / saves / logs / options.txt 各自独立；
- 每个客户端经 `latency_proxy.py` 连接：`127.0.0.1:23110 → 127.0.0.1:25566`，
  **双向各延迟 50 ms**（FIFO 保序，TCP 流看到的就是一条慢连接）；
- 四方在文件仲裁的同一 epoch 自旋开火（p203 机制），动作互不相同、互为指纹：
  A 删空 5 → empty；B 取 1（4→3）；C 取 1（3→2）；D 取 1（2→1）；
- 客户端 JVM：`-Xmx768M -XX:+UseSerialGC -XX:TieredStopAtLevel=1`，服务端 `-Xmx512M`
  （原因见"踩坑"，机器空闲内存经常不足 1G）。

## 结果（result.json 15/15 true）

```text
P231_JOIN ×4 → P231_SEED tick=? GridUser=5 TrashB=4 TrashC=3 TrashD=2
P231_FIRE role=A..D（同一 epoch，driftMs≈0）
P231_SET side=SERVER thread=Server thread tick=1715 user=GridUser stack=empty
P231_SET side=SERVER thread=Server thread tick=1715 user=TrashB  stack=minecraft:diamondx3
P231_SET side=SERVER thread=Server thread tick=1715 user=TrashC  stack=minecraft:diamondx2
P231_SET side=SERVER thread=Server thread tick=1715 user=TrashD  stack=minecraft:diamondx1
one_way_ms = 70 / 71 / 70 / 71   （服务端写点 wall − 客户端开火 epochMs）
写点 wall spread = 1 ms；代理 traffic 行 10 条，4 条连接各自 down ≥ 200 KB 真实游戏流量
```

- **四玩家的写入落在同一个服务端 tick（1715），数值互为指纹、互不串台**——任一包走错人，
  对应玩家的 stack 就不是期望值或缺一条写；
- **注入的延迟被实测看到**：70–71 ms ≈ 50 ms 单向注入 + 服务器 tick 对齐；判据 ≥40 ms 且 ≤400 ms；
  回环基线是 p203 的 4 ms，差一个数量级以上；
- 客户端最终 UI 各自正确（A `trash=empty`；B/C/D `trash=x3/x2/x1` 且 `carried=diamondx1`）；
- 4 个 gameDir 路径互不相同，且各自写出了自己的 `logs/latest.log`。

## "同 tick" 的口径（如实）

回环下 p203 已证两玩家同 tick（4 ms 间隔）。在 50 ms 注入延迟 + 本机负载下，**到达落在哪个
tick 是网络抖动，不是逻辑性质**：本回合第 4 次运行实测跨 2 个 tick（2108/2110），第 7 次全同
tick（1715）。判据因此取"四个写点 wall 聚集 ≤250 ms"并把精确 tick 记进 result.json，不把一次
好运写成跨负载的保证。

## 踩坑（7 次运行，前 6 次的问题如实记录）

1. **第 1 次：内存换页卡死。** 4×2G 客户端 + 2G 服务端，机器（15.3G，用户日常应用占用大）
   全体停在 atlas 阶段 8 分钟无进展（各 java 进程 WS ~1G、空闲物理内存 1.8G）→ 全部杀掉。
2. **第 2 次：quickPlay 被无障碍引导屏挡住（真根因，值得记住）。** 降到 1G 仍全体停在
   atlas 后两行。对照 p203 成功日志，缺的正是 `Connecting to`：**全新 gameDir 首次启动会弹
   "无障碍引导"屏，quickPlay 不会在其后连服**。p203 的客户端继承了 launcher-e2e 的
   options.txt（`onboardAccessibility:false`）所以从未见过。修复：每个 gameDir 复制
   options.txt。
3. **第 3 次：链路通，verdict 自伤两处。** 4 join、seed、全同 tick（2043）、one_way 66–73 全部
   出现；但 same-tick 判据写成"去重集合长度 == 4"（应为 ==1），且客户端被硬杀后代理 close 行
   没写全。
4. **第 4 次：tick 真散了**（2108/2110，见上）→ 判据改为 wall 聚集；代理加**周期性 traffic 行**
   （每 200 KB 一条），字节证据不再依赖优雅退出。
5. **第 5 次：14/15**——唯一红是 verdict 笔误（连接计数仍在数 close 行，traffic 行已证明 4 条）。
6. **第 6 次：机器空闲内存只剩 0.8G**，client-b 加入早期冻住 10 分钟直到超时，判据如实报红
   （four_ready=false 全家）。
7. **第 7 次（最终，15/15）**：`-Xmx768M + SerialGC + C1-only`、服务端 512M、启动间隔 15 s、
   timeout 900 → 四客户端全部就位并完成取证。

## 边界（如实）

- **延迟是本机用户态代理注入的合成延迟，不是第二台机器**（the latency is synthetic — a
  userspace proxy on this one machine — not a second machine, and not a real network hop）；
  真实跨机（NIC/WiFi/路由、真实第二台机器的客户端）仍然开放。
- 同 tick 并发已由 p203 在回环下证明（2 玩家）；本回合第 7 次在 50 ms 注入下也观察到 4 玩家
  同 tick（1715），但口径如上，不作为保证重申。
- p203 边界里的"同一玩家同 tick 两次操作"仍未测。
- 客户端动作是 GLFW 回调边界合成输入（p191/p192 约定），不是 OS 级键鼠。
- junction 共享的 4 个目录按运行期只读使用（比 p203 多客户端共用整个 gameDir 已收紧）；
  每客户端独立资源包/资产未测。
- 本机 15.3G 内存下，768M 堆 × 4 客户端 + 512M 服务端是实测能跑完的形态；堆再大在低空闲内存
  时会换页卡死（第 1 次）。

## 复现

```text
py -3.12 runs/p231-quad-latency/build.py
py -3.12 runs/p231-quad-latency/run.py --timeout 900
```

## 证据

`result.json`、`server.log`、`client-{a..d}.log`（首行是完整 java 命令行，含各自 gameDir）、
`proxy.log`（listening/traffic/close 行）、`after-quad.png`（四窗口截图）、`run.py`、
`latency_proxy.py`、`build.py`、探针源码 `probes/p231-quad-latency/`。
测试后环境已恢复：服务端 mods 与 server.properties 从备份还原（`work/tmp/p231-mod-backup/`、
`runs/p231-quad-latency/server.properties.before`）。
