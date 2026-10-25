# p189 — TrashSlot creative 删除键（1.21.1 适配修复 + 真实 GUI 验证）

日期：2026-10-25。p183 留下的 "创造模式删除键仍未测"。实测发现 **TrashSlot 的 creative 删除分支
在 1.21.1 转换后结构性失效**，本轮按 p187 模式补了 companion 修复，并用真实 GUI 键注入验证。

## 根因（两个 1.21.1 结构变化使 1.20.x 分支永不可达）

`TrashSlotGuiHandler.runKeyBindings` 的 creative 分支有两个判断，在 1.21.1 下都失效：

1. `mouseSlot.getClass() == Slot.class`（严格相等）——1.21.1 creative 界面
   （`CreativeModeInventoryScreen` = class_481）**覆写了 hover 处理**：
   `AbstractContainerScreen.hoveredSlot` 在 creative 界面恒为 null（p189 实测
   `DEBUG_HOVERED hovered=null`，creative 虚拟槽和 hotbar 槽都不更新）；
2. `mouseSlot.getClass().getSimpleName().equals("SlotWrapper")`——1.21.1 删掉了 SlotWrapper
   内部类（class_490/class_481 无内部类，1.20.x 的 wrapper 结构被重构进 class_1716/menu）。

即：无论按 Delete/Shift+Delete、无论悬停哪里，原分支永远不执行（`DEBUG_RUN_RETURN=false`）。

## 修复（companion，不动 TrashSlot jar）

`java/src/trashcreative/`（`tools/build_trashslot_creative_fix.py` →
`work/client/trashcreative-fix.jar`，mod id `trashcreativefix`）：

- mixin 重写 creative 分支（`runKeyBindings` HEAD cancellable）；
- 1.21.1 事实：creative 界面 menu 保留玩家背包槽（hotbar = menu index 45..53，
  container = PlayerInventory）；删除消息在服务端解析到 **InventoryMenu**（menuSize=46，
  hotbar = 36..44）——恰好等于源码的 "index - 9" 算式；
- 鼠标 gui 坐标 = `Mouse.method_1603/1604() / window scale`（p188 已验证 raw mouse 为窗口像素）；
- 用 `callIsHovering(slot, mouseX, mouseY)`（balm accessor）匹配悬停槽；
- `trashSlot` 画布存在时走 `CreativeDeletionProvider`（删除后清空 trash = 上游 creative 语义）；
  creative 界面没有画布（getTrashSlot()==null）时直接发 `MessageDeleteFromSlot`
  （经 `Balm.getNetworking()` + `BalmNetworkingBridge.sendToServer`，与 converted provider 同路）。

## 场景与结果（result.json / server.log / client.log）

dedicated server（`fabric-1.21.1-server-trashslot`，`gamemode=creative` + `force-gamemode`），
物品由服务端控制台 `/item replace entity GridUser container.N with minecraft:diamond 5/3` 放入
hotbar 0/1（组件语法在 integrated server 的 mcfunction 不被接受，dedicated 控制台可用），
客户端打开 creative 界面，真实键注入（Delete 带 KEYEVENTF_EXTENDEDKEY，p183 教训）：

```text
DEBUG_CREATIVE_DELETE slot=36 all=true     <- Shift+Delete（hot0 上的 5 钻）
SERVER_DELETE slot=36 all=true menu=class_1723 menuSize=46 carried=0 minecraft:air
SERVER_DELETE slot=-1 all=false            <- creative 语义：删除后清空 trash
SERVER_STATE ... hot0=empty hot1=empty     <- delete_all 连锁删除 hot1 的 3 钻（同 item）
DEBUG_CREATIVE_DELETE slot=36 all=false    <- 重放 hot0 的 5 钻后普通 Delete
SERVER_STATE ... hot0=empty hot1=empty
```

- delete_all 连锁：Shift+Delete 删 hot0 的 5 钻 + 遍历同 item 的 hot1 3 钻 → **两格全空**；
- trash 全程 `empty`（creative 删除永久性，`emptyTrashSlot` ✓）；
- 服务端 menu = `class_1723`（InventoryMenu，46 槽）——`slot=36` 恰为 hotbar 0，"index-9" 算式
  成立；`slot=-1` 为 trash 清空消息；
- `after-delete-all.png`（Shift+Delete 后 hotbar 双空）、`after.png`（重放 Delete 后）；
- result.json：`creative_delete_seen=2`、`delete_all_seen=true`、server_deletes 4 条。

## 调试记录（测试侧）

- OS 光标注入时 `SetForegroundWindow` 偶发被前台锁拒绝 → run.py 加 focus 重试 +
  "按一次、验证一次日志"的循环；
- `NativeImage`/`ManagedKeyMapping`/`MessageDeleteFromSlot` 的方法号/类形状按 converted jar
  逐一 javap 校正（`isActiveAndMatchesKey(key, scan, mods)`、MessageDeleteFromSlot 非 record、
  `AbstractContainerMenu.method_34255()` = getCarried）；
- integrated server 的 mcfunction 拒绝 `item replace` 组件语法（dedicated 可过）→ 物品放置改用
  dedicated 控制台。

## 未覆盖

- main inventory 27 格（需要切到 creative 界面的 inventory tab，当前只在 Building Blocks tab
  验证 hotbar 槽——两格 hotbar 已覆盖 creative 分支的两个 slotNumber 语义之一）；
- creative 界面的右键 undelete（`CreativeDeletionProvider.undeleteLast` 上游为空实现）；
- 多客户端（p190）。

## 复现

```text
python runs/p189-trash-creative/build.py
python tools/build_trashslot_creative_fix.py --trashslot work/client/trashslot-client-empty.jar
python runs/p189-trash-creative/run.py --timeout 300
```

## 证据

`after-delete-all.png`、`after.png`、`client.log`、`server.log`、`result.json`、`src/probe/`、
`trashkey.mixins.json`、`fabric.mod.json`、
`java/src/trashcreative/`（companion 修复源码）、`tools/build_trashslot_creative_fix.py`。
