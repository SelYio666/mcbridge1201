# p183 — TrashSlot 真实 UI empty-trash 键（p65 的“未测试”闭合）

日期：2026-10-23。p65 只验证了 provider 层的 `emptyTrashSlot`；这轮用 dedicated server + 真实鼠标/键盘
注入跑通了 **GUI 的 Delete 键 → provider → 服务端** 整条路径，并找到 p65 Delete 尝试失败的真实原因。

## 场景

- dedicated server：`fabric-1.21.1-server-trashslot`（端口临时 25566），TrashSlot 使用 p65 修好的
  `trashslot-client-empty.jar`（Balm reply bridge）；客户端同样安装它；
- 测试 probe `trashkey`：server tick 40 给服务端 trash 放 5 颗钻石；client tick 60 给客户端 trash
  放 5 颗钻石，tick 80 打开 `InventoryScreen`，tick 100 打印几何：
  ```text
  KEY_SCREEN left=232 top=97 trashX=152 trashY=165 scale=2.0 trash=5 minecraft:diamond
  ```
- 真实输入：`SetCursorPos` 到 trash 槽中心（GUI `(392,270)`，physical `(1104,780)`），发送 **Delete**。

## 结果

```text
DEBUG_KEY key=261 scan=339 mods=0 screen=net.minecraft.class_490
DEBUG_RUN key=261 scan=339 mods=0 type=KEYSYM screen=net.minecraft.class_490
DEBUG_EMPTY_PROVIDER trash=5 minecraft:diamond
DEBUG_RUN_RETURN=true
SERVER_TRASH empty=true count=0      (2 s 后服务端 tick)
```

- `result.json`：`key_seen=true`、`run_seen=true`、`provider_seen=true`、`server_empty=true`；
- `after.png`：inventory 打开，右下角 trash 图标里已没有钻石；
- 没有 crash/ClassCast；客户端和服务端 trash 都清空（p65 的 reply bridge 继续生效）。

## 根因：p65 的 Delete 注入其实不是 Delete

p65 的“Delete / Ctrl+Delete / Shift+Delete 都没反应”不是 TrashSlot 的 key mapping 坏了，而是
`keybd_event(VK_DELETE, 0, 0, 0)` 少了 **`KEYEVENTF_EXTENDEDKEY`**：Delete 是扩展键，未带扩展标志时
游戏收到的是 **KP_DECIMAL (GLFW 330)**，而 TrashSlot 的 `keyBindDelete` 默认是 **DELETE (GLFW 261)**，
于是 `runKeyBindings` 直接返回 false。加上扩展标志后，`runKeyBindings` 命中：

```text
DEBUG_KEY key=261 ...  (而不是 330)
DEBUG_RUN ... DEBUG_EMPTY_PROVIDER ... DEBUG_RUN_RETURN=true
```

修复只在本轮测试脚本 `run.py`（`extended = 0x0001` / `0x53` scan），**没有改 TrashSlot 或转换器代码**。

## 未验证 / 限制

- 只测 inventory 一个界面、一个 5-diamond trash、一个客户端；
- Shift+Delete（delete_all）已由 `runs/p184-trash-delete-all/` 覆盖：两叠 5+3 钻石跨槽删除，
  `all=true`，服务端 8→0；空 cursor 右键 undelete 已由 `runs/p185-trash-undelete-right/` 覆盖
  （取 1 留 4；左键全取见 p63）；创造模式删除键仍未测；
- 未测多客户端同步/重进（TrashSlot 登录会重置 trash，p65 已记录）；
- 测试会临时改 dedicated server 的端口和 mods（25566 + patched trashslot + trashkey）；本轮已恢复
  服务端 `server-port=25565` 和原版 `trashslot-15.1.5+1.21.1.jar`，客户端 mods 恢复为
  ImmediatelyFast + Fabric API + p181 probe；复现时请使用副本或手动恢复；
- 不涉及性能。

## 复现

```text
python runs/p183-trash-key/build.py
python runs/p183-trash-key/run.py --timeout 180
```

`build.py` 编译 probe/mixin 到 `work/tmp/trashkey.jar`（不入库）；`run.py` 启动 dedicated server
（临时 25566）、安装 patched TrashSlot 并注入 Delete，日志/截图写在 `runs/p183-trash-key/`。

## 证据

`client.log`、`server.log`、`after.png`、`result.json`、`src/`、`fabric.mod.json`、`trashkey.mixins.json`。
