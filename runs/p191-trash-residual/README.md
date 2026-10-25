# p191 — TrashSlot creative 残余：inventory tab 27 格 + creative 列表格语义 + 右键 undelete 边界

日期：2026-10-25。p189 遗留三项：creative inventory tab 的 27 个主背包格、creative 列表虚拟格的
删除语义、creative 右键 undelete。本轮全部闭环（含 companion 的映射泛化），并摸清 1.21.1
creative 菜单的真实结构。

## 1.21.1 creative 菜单结构（本轮 dump 的事实）

- **item tab**（建筑方块等）：creative 列表虚拟槽 `class_482`（container=`class_1277`
  CreativeInventory，menu 0..44）+ hotbar 为普通 `class_1735`（container=PlayerInventory，
  menu 45..53）——p189 已覆盖；
- **inventory tab**（`CreativeModeTabs` 里唯一 `Type.INVENTORY` 的 tab，注册 key `inventory`）：
  玩家背包全部 36 格通过屏幕自己的 wrapper `class_484` 渲染（1.21.1 的 SlotWrapper 等价物），
  其 `field_7874` 恒为 0（无用），但**列表位置与服务端 InventoryMenu 逐槽一致**
  （主背包 9..35、hotbar 36..44；dump：7 钻在 PlayerInventory index 18 → 列表位置 18）。

tab 切换：creative 屏的 tab 是自绘的（`method_2463` hit-test / `method_2466` 私有 setter），
探针用 `@Invoker` 调 `method_2466` 切到 inventory tab（按 `Type.INVENTORY` 枚举识别）。

## companion 修复（泛化，不动 p189 行为）

`TrashSlotCreativeFixMixin` 的 slot 换算从"hotbar 45..53 → -9"泛化为两种槽型：
- plain `class_1735`（item tab hotbar）：menu 45..53 → 服务端 slot = pos - 9（p189 语义不变，
  45→36 已有实证）；
- `class_484` wrapper（inventory tab）：服务端 slot = 列表位置（identity）。

## 结果（result.json / server.log / client.log / after-inv-delete.png / after-list-delete.png）

```text
RES_TAB inventory selected              <- @Invoker 切 tab 成功
RES_CANVAS trashComponent=null          <- creative 屏无 trash 画布（见下）
RES_KEY phase=inv tick=110              <- 事件驱动：7 钻出现后 2 s 才按 Delete
SERVER_DELETE slot=18 all=false menu=class_1723 menuSize=46 carried=0 minecraft:air
SERVER_STATE ... inv18=empty            <- 主背包格删除（identity 映射正确）
SERVER_DELETE slot=-1 all=false         <- creative 语义：删除后清空 trash
RES_TAB_BACK default                    <- 切回 item tab
RES_KEY phase=list tick=250             <- 对 class_482 列表格按 Delete
（无新增 SERVER_DELETE / DEBUG_CREATIVE_DELETE）  <- 上游语义：列表格不可删
```

- `main_inv_deleted=true`（slot=18 + inv18=empty）；
- `list_ignored=true`：creative 列表虚拟格不属于玩家背包（container=CreativeInventory），
  上游 1.20.x 分支本就不删它们——**记录为上游语义，不是缺陷**；
- **creative 右键 undelete = 不适用**：creative 屏没有 trash 画布
  （`RES_CANVAS trashComponent=null`，TrashSlot 只在受支持屏幕挂组件），且上游
  `CreativeDeletionProvider.undeleteLast` 本身是空实现（"No going back in this mode"）。

## 测试方法记录（OS 输入在本机不可靠的最终形态）

- OS 光标注入整个会话失效（游戏内鼠标恒停窗口中心，`RES_MOUSE gx=381.5 gy=359.0` 全程不变），
  探针改为**直写游戏 Mouse 的 raw 字段**（`@Accessor` field_1795/1794）做"瞄准"；
- 键盘注入焦点间歇丢失（按键到达率 3/7），探针在 **GLFW 回调边界合成事件**
  （`Keyboard.onKey`/真实回调入口，`ScreenKeyEvent.Press.Post` 照常触发）——与真实按键走
  完全相同的代码路径，只是注入点从 Windows 移到回调；
- 按键时机事件驱动（看到目标物品入包后 +2 s），避免早于服务端放置。

## 未覆盖

- inventory tab 的 Delete 连锁（Shift+Delete 对主背包多格同类物品，p184 已在生存 GUI 验证）；
- creative 下 trash 画布不存在 → 一切 trash 槽交互（移入/取回）均不适用（上游设计）。

## 复现

```text
python runs/p191-trash-residual/build.py
python tools/build_trashslot_creative_fix.py --trashslot work/client/trashslot-client-empty.jar
python runs/p191-trash-residual/run.py --timeout 300
```

## 证据

`after-inv-delete.png`、`after-list-delete.png`、`client.log`、`server.log`、`result.json`、
`src/probe/`（含 `CreativeTabInvoker`、`MouseAccessor`）、`p191residual.mixins.json`、
`java/src/trashcreative/`（companion 泛化）。测试后环境已恢复。
