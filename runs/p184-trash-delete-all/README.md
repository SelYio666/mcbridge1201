# p184 — TrashSlot Shift+Delete (`delete_all`) 真实 UI 路径

日期：2026-10-23。p183 只测了 Delete 对 trash 的 empty；这轮补 **Shift+Delete 跨槽删除同物品**。

## 场景

- dedicated server（端口临时 25566）+ p65 修好的 patched TrashSlot（两端同 jar）；
- 服务端 probe 在 tick 40 直接写玩家背包两个槽：
  - slot 0：5 颗钻石；
  - slot 1：3 颗钻石；
  - （第一次用 `give` 5+3 会被合并成一叠 8，`all=true` 但证明不了跨槽；最终改成直接写槽位。）
- 客户端 inventory 打开后，probe 找到第一个钻石槽 `index=36 x=8 y=142 count=5`，Python 把真实光标
  移到该槽（GUI `(248,247)`，physical `(816,734)`），注入 **Shift+Delete**（扩展 Delete scan 0x53）。

## 结果

```text
DEBUG_KEY key=261 scan=339 mods=1 screen=net.minecraft.class_490
DEBUG_DELETE_CONTAINER slot=36 all=true
... DELETE_TRASH_CLEAR tick=150/180
CLIENT_DIAMONDS count=8   (5+3 两叠)
CLIENT_DIAMONDS count=0
SERVER_DIAMONDS count=8
SERVER_DIAMONDS count=0
```

- `result.json`：`shift_seen=true`、`delete_seen=true`、`server_zero=true`、`client_zero=true`；
- `after.png`：inventory 与 trash 都空；5+3 两叠钻石都被 Shift+Delete 删掉；
- 测试同时把客户端 trash 清空（tick 20/150/180），避免 p183 留下的客户端 trash 钻石干扰截图；
- 无 crash/ClassCast；客户端与服务端一致，没有只删一叠的半状态。

## 根因/修复

- Delete 仍需 p183 的 **`KEYEVENTF_EXTENDEDKEY`**（否则收到 KP_DECIMAL 330）；Shift 用
  `VK_SHIFT` 按下/抬起，游戏日志 `mods=1`；
- `delete_all` 的跨槽行为由服务端 `MessageDeleteFromSlot.handle` 的 same-item 循环执行，客户端
  `DEBUG_DELETE_CONTAINER all=true` 与服务端 8→0 对上了；
- **没有改 TrashSlot/转换器代码**，只是测试 harness + 证据。

## 未验证 / 限制

- 只测 inventory、两个同物品槽、一个客户端；创造模式删除键、多客户端同步仍未测；空 cursor
  右键 undelete 已由 `runs/p185-trash-undelete-right/` 覆盖（取 1 留 4；左键全取见 p63）；
- 测试临时改 dedicated server 的端口/mods；本轮已恢复 `server-port=25565`、原版 trashslot jar，
  客户端恢复为 ImmediatelyFast + Fabric API + p181 probe；
- 不涉及性能。

## 复现

```text
python runs/p184-trash-delete-all/build.py
python runs/p184-trash-delete-all/run.py --timeout 180
```

## 证据

`client.log`、`server.log`、`after.png`、`result.json`、`src/`、`fabric.mod.json`、`trashdelete.mixins.json`。
