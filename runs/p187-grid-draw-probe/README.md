# p187 — ShulkerBoxTooltip 网格 item icon 恢复 + 桥接组件读损坏修复

日期：2026-10-24。接手 p186 的两个遗留缺口：网格里 item icon 不画、真实服务端 item 仍是
`!minecraft:container`。本轮找到 **两个真实根因** 并修复，服务端同步的 shulker 预览也一并恢复。

## 根因

### 根因 1：`method_57379(type, null)` 是 `ItemStack.set()`，不是 getOrDefault

桥接和 companion 里所有"读组件"的代码都写成了
`stack.method_57379(class_9334.field_49622, null)`。该方法实际是
`ItemStack.set(DataComponentType, T)`（返回旧值）——传 `null` 等于**把 CONTAINER 组件清空**：

- `ShulkerBoxNbtBridge.legacyBlockEntityTag`：mod 自己的 provider 走 legacy NBT 读路径时，
  第一次"读"就把真实背包栈（包括服务端同步来的）的 container 组件清空——
  **这就是 p110/p186 "真实服务端 item 仍是 !minecraft:container" 的根因**；
- `AppleSkinFoodBridge.foodComponent`：对临时栈恰好"能用"（set(null) 返回默认值），
  纯属侥幸；
- companion 的 `ComponentPreviewProvider`：读一次就毁掉 client-side 栈的 container
  （p187 探针实测：同一栈对象第一次读 nonAir=1，之后全为 0）。

正确读法：`stack.method_57353().method_57829(type)`（`getComponents().get(type)`）。
四处全部修正（两处 bridge + companion + p187 probe）。

### 根因 2：转换后的 mod 没有任何 mixin 提供 `PreviewTooltipData`

`shulkerboxtooltip-*-mixins.json` 里只剩 4+1 个 mixin——**ItemStackMixin（含 fabric 变体）
在转换时被整体剥掉**（其 1.20.4 目标方法已死）。所以 vanilla 的
`ItemStack.getTooltipData()` 永远返回 empty：没有人把 `PreviewTooltipData` 递给 tooltip 渲染，
p186 里"出现的框"其实只是 vanilla 加高的 tooltip 背景（mod 的 renderer 因
`PreviewType.NO_PREVIEW` 提前 return，从未画过东西）。

修复（companion `sbtpreview` 1.1.0）：

1. `PreviewTooltipDataMixin` 重新注入 `method_32347`（现在没有竞争者）：
   CONTAINER 组件非空时构造 `PreviewTooltipData(provider, context)`；
2. `ComponentPreviewProvider`（component-first，委托 mod 原 provider 兜底 legacy 路径）
   由 `CompanionInit` 在首个 client tick 注册进 mod 的 `PreviewProviderRegistry`
   （registry 默认 locked、优先级需严格大于原 provider，注册一次覆盖 17 个 shulker 物品）；
   文本路径（`modifyStackTooltip` → `Diamond ×5`）与数据路径因此一致；
3. mod 默认 `preview.alwaysOn=false`（需要按住预览键），harness 写入
   `config/shulkerboxtooltip.json5` 强制 `alwaysOn: true`。

## 结果（result.json / client.log / grid.png）

```text
GRID_HUD frame=1 source=client nonAir=1
GRID_SERVERBOX slot=3 nonAir=1                      ← 服务端同步的 shulker
GRID_HUD frame=101 source=server nonAir=1           ← HUD 源切到服务端栈
GRID_DRAWITEMS call=1 type=COMPACT items=1 first=minecraft:diamondx5 empty=false
GRID_DRAWITEM call=1 stack=minecraft:diamond count=5 empty=false
```

`grid.png`：tooltip 网格槽内 **diamond 图标 + ×5 计数**正常画出，下方 `Diamond ×5`；
热键栏 slot 3 是服务端 `/item replace` 放入的真实 shulker。

## 测法（与 p186 的差异）

鼠标 hover 注入不可靠（窗口遮挡/焦点会吞掉 OS 光标移动，p187 多次复现），
harness 改为 **HUD 驱动**：探针在 `HudRenderCallback` 里对目标栈调用真实管线
`getTooltip → getTooltipData → DrawContext.method_51437 → PreviewTooltipComponent →
BasePreviewRenderer`，与真实 hover 完全同一条代码路径，只是由探针而不是鼠标触发。
服务端物品通过服务器控制台 `/item replace entity GridUser container.3 with
minecraft:shulker_box[minecraft:container=[{slot:0,item:{id:"minecraft:diamond",count:5}}]]`
注入（1.21.1 的 container 组件条目要 `slot`+`item` 嵌套）。

## 仍未覆盖

- `PreviewType.FULL`（isFullPreviewAvailable=true 时 3x9 全网格）只验证了 COMPACT；
- 只测 1 个 client-side 栈 + 1 个服务端栈（5 颗钻石）；多物品/多槽/合并策略未测；
- 鼠标 hover 的真实 GUI 路径未回归（harness 层面的注入不稳定，非转换缺陷）；
- 预览键（KeyboardMixin）交互路径未测。

## 复现

```text
python runs/p187-grid-draw-probe/build.py
python runs/p187-grid-draw-probe/run.py --timeout 240
```

`build.py` 编译 probe（entrypoint + 3 个 tracer mixin）；`run.py` 起
`fabric-1.21.1-server-trashslot`，客户端装 converted Shulker + companion + probe，
HUD 渲染 + 服务端 `/item replace` + 截图。测试后 server/client 已恢复。

## 证据

`grid.png`、`client.log`、`server.log`、`result.json`、`src/probe/`、
`java/src/shulkerpreview/`（companion 1.1.0）、
`java/src/bridge/java/top/mcbridge1201/bridge/ShulkerBoxNbtBridge.java`、
`java/src/bridge/java/top/mcbridge1201/bridge/AppleSkinFoodBridge.java`。
