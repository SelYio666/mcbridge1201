# p185 — TrashSlot 空 cursor 右键 undelete（1 个进 cursor，trash 留 4）

日期：2026-10-23。p63 只测了左键取回**全部 5 个**；这轮补右键 `undeleteLast(..., right=true)` 的
拆分语义。

## 场景

- dedicated server（端口临时 25566）+ p65 修好的 patched TrashSlot（两端同 jar）；
- probe 给服务端/客户端 trash 各放 5 颗钻石；客户端 inventory 打开，trash 槽 `x=152,y=165`，
  screen `left=232 top=97 scale=2.0`；
- 真实输入：
  1. 先 `focus_window`，**然后**重新 `ClientToScreen` + 重新算物理坐标（之前先算原点、
     `ShowWindow(SW_RESTORE)` 之后窗口位置变了，右键落点漂成 `368,323`）；
  2. 在 GUI 外 `(20,20)` 做一次中性左键，吃掉 window activation；
  3. 光标移到 trash 中心 `(392,270)`，右键。

## 结果

```text
DEBUG_CLICK button=0 x=10.0 y=10.0 hovering=false carried=0 trash=5 ...   (中性左键)
DEBUG_CLICK button=1 x=392.0 y=270.0 hovering=true carried=0 trash=5 ...  (右键)
DEBUG_PROVIDER_UNDELETE trash=5 minecraft:diamond right=true
RIGHT_STATE carried=1 trash=4
SERVER_TRASH empty=false count=5 -> count=4
```

- `result.json`：`right_seen` / `carried_one` / `client_trash_4` / `server_trash_4` 全 true；
- `after.png`：cursor 在左上角带着 1 颗钻石，trash 图标剩 4 颗；与 p63 左键“全取 5、trash 0”
  形成对照；
- 无 crash/ClassCast；客户端/服务端一致。

## 踩到的坑（测试 harness，不是 mod 问题）

- 第一次右键成了“激活窗口”的一次性点击，屏幕上没有任何 `DEBUG_CLICK`；加中性左键后解决；
- `origin` 在 `focus_window` 之前算，`ShowWindow(9)` 恢复窗口后原点变化，右键事件落到
  `368,323`、`hovering=false`；改为 focus 后重算 origin，右键回到 `392,270`；
- Balm 的 `ScreenEvent` **确实分发了右键**（`button=1`），没有改 TrashSlot/转换器代码。

## 未验证 / 限制

- 只测一个客户端、一次右键；左键全取是 p63，跨槽删除是 p184；
- 创造模式删除键、多客户端同步、其他界面/其他物品未测；
- 测试临时改 dedicated server 的端口/mods；本轮已恢复 `server-port=25565` 和原版 trashslot jar，
  客户端恢复为 ImmediatelyFast + Fabric API + p181 probe；
- 不涉及性能。

## 复现

```text
python runs/p185-trash-undelete-right/build.py
python runs/p185-trash-undelete-right/run.py --timeout 180
```

## 证据

`client.log`、`server.log`、`after.png`、`result.json`、`src/`、`fabric.mod.json`、`trashright.mixins.json`。
