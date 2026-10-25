# p192 — TrashSlot 三客户端：B 主动清空 + A 重进（上游登录重置）

日期：2026-10-25。p190 遗留：B 主动操作方向、第三客户端、重进保持。三项全部闭环。

## 场景

- dedicated server（survival、`online-mode=false`、端口 25566）+ **三个真实客户端**
  （GridUser / TrashB / TrashC，同一实例先后启动；B 带 `-Dp192.actor=true`）；
- 服务端 probe：三人都在线后 seed A=5、B=4、C=3 钻，之后每 2 s 打印三人服务端 trash；
- 三个客户端各自打开 inventory、把本地 trash UI seed 成 4 钻（服务端不主动推，p64）；
- **B（actor）** 等 3 人在线 + seed 落地后，全程走真实 GLFW 回调路径（p191 的最终形态）：
  瞄准（写 Mouse raw 字段）→ 合成右键（取 1，p185 语义）→ 合成 Delete（清空，p183 语义）；
- B 清空后 harness 杀掉 A（服务端 trash 仍是 5 钻）并重启 A。

## 结果（result.json / server.log / client-*.log）

```text
ACTIVE_SEED GridUser=5 TrashB=4 TrashC=3
P192_AIM gx=392.0 gy=270.0            (B)
P192_RIGHT_CLICK trash take-one       (B)
P192_DELETE trash empty               (B)
ACTIVE_SERVER user=TrashB trash=minecraft:diamondx3   <- B 右键取 1（服务端 4→3）
ACTIVE_SERVER user=TrashB trash=empty                 <- B Delete 清空
ACTIVE_SERVER user=TrashC trash=minecraft:diamondx3   <- C 全程不变（服务端）
P192_TRASH ... trash=minecraft:diamondx4              <- C 客户端 UI 全程自己的值
ACTIVE_JOIN name=GridUser total=3      (第二次)         <- A 重进
ACTIVE_SERVER user=GridUser trash=empty                <- 上游 PlayerLoginEvent 重置（p65 语义）
```

- `b_took_one=true`、`b_emptied=true`：B 的主动操作只作用于 B（4→3→empty）；
- `c_constant=true` + `c_client_untouched=true`：C 服务端/客户端全程不受 B 影响；
- `a_had_five=true` + `a_rejoined=true` + `a_reset_after_rejoin=true`：A 断开时服务端 trash
  仍是 5 钻，重进后变 **empty**——这是 TrashSlot 上游 `PlayerLoginEvent.setTrashItem(EMPTY)`
  的登录重置设计（p65 已记录），**按上游语义记录，不是持久化 bug**；
- 无人为广播：`reply` 只回发送者（p64/p190 语义在三客户端下依旧成立）。

## 调试记录

- 第一轮 B 的动作早于服务端 seed（C 加入慢、seed 等三人）——packet 到达时服务端 trash 还是
  空的，全部 no-op。修法：actor 等 `ClientLevel.method_18456().size() >= 3` + 3 s 余量；
- p192 build.py 初版忘了把 `p192.mixins.json` 打进 jar（服务端 mixin 初始化失败）。

## 未覆盖

- C/B 同时操作（并发竞争已由 p79/p80 在 ironchests 验证过同类语义，TrashSlot 未测）；
- 四客户端及以上；A 重进后重新 seed 的再操作循环。

## 复现

```text
python runs/p192-trash-multi-active/build.py
python runs/p192-trash-multi-active/run.py --timeout 420
```

## 证据

`result.json`、`server.log`、`client-griduser.log`、`client-trashb.log`、`client-trashc.log`、
`src/probe/`（含 `MouseAccessor`/`MouseInvoker`）、`fabric.mod.json`、`p192.mixins.json`、
`build.py`、`run.py`。测试后环境已恢复（server 25565 + 原版 trashslot；client
ImmediatelyFast + Fabric API + p181 probe）。
