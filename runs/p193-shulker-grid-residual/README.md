# p193 — Shulker grid 残余：多物品 / FULL / 真实 hover / 服务端 box

日期：2026-10-26
对象：转换后的 ShulkerBoxTooltip（`work/client/shulker-patched2.jar` + `mcbridgepreview` companion）
结论：p187 留下的四个残余全部通过，`run.py` exit 0。

## 结果

`result.json`：

```json
{
  "client_multi_items2": true,
  "full_render": true,
  "server_multi_items2": true,
  "real_hover_path": true
}
```

- 客户端多物品：shulker box 里 3 diamond + 2 emerald，tooltip 网格两个 slot 都画出图标和数量。
- FULL 类型：`P193_FULL_REQUEST` 之后 `GRID_DRAWITEMS type=FULL`；`after-full.png` 是完整 27 格网格。
- 真实 hover：FULL 之前已有 `DRAWTOOLTIP lines=3 data=PreviewTooltipData`，走的是真实 `Screen`/tooltip 管线（输入注入方式见下）。
- 服务端 box：dedicated server `/item replace GridUser container.10` 放入 2 diamond + 4 emerald，服务端回显 `Replaced a slot`、`data get` 显示 2+4；客户端 `P193_SERVER_AIM` 后 `GRID_DRAWITEMS first=minecraft:emeraldx4`，`after-server.png` 显示同一条 tooltip。

## 证据文件

| 文件 | 内容 |
|---|---|
| `result.json` | 四个断言的最终值 |
| `client.log` | `P193_CLIENT_BOX`、`P193_CLIENT_AIM`、`P193_FULL_REQUEST`、`P193_SERVER_AIM`、`P193_BOX_SLOT listPos=10`、`GRID_DRAWITEMS`/`GRID_DRAWITEM` |
| `server.log` | `Replaced a slot on GridUser with [Shulker Box]` + `data get` 的 2 diamond/4 emerald |
| `after-full.png` | FULL 预览：3 diamond + 2 emerald |
| `after-server.png` | 服务端 box 的 compact 预览：2 diamond + 4 emerald |
| `after-compact.png` | 服务端 box 的 compact 预览（第二次截图） |
| `ShulkerResidualProbe.java` + `src/probe/mixin/*` | 客户端探针：client box、真实 hover、FULL、server phase |
| `run.py` / `build.py` | 启服/启客户端、发 server box、截图、断言 |

关键日志：

```text
P193_CLIENT_BOX slot=9 diamondx3+emeraldx2
GRID_DRAWITEMS ... type=COMPACT items=2 first=minecraft:diamondx3
P193_FULL_REQUEST tick=...
GRID_DRAWITEMS ... type=FULL items=2 first=minecraft:diamondx3
DRAWTOOLTIP lines=3 data=...PreviewTooltipData   (FULL 之前，真实 hover)
Replaced a slot on GridUser with [Shulker Box]
data get ... {count: 4, id: "minecraft:emerald"} ...
P193_SERVER_AIM tick=...
GRID_DRAWITEMS ... type=COMPACT items=2 first=minecraft:emeraldx4
```

## 方法

- **输入**：沿用 p191 的确定性方案——探针直接写 `Mouse` raw 坐标（`@Accessor`），并在 GLFW 回调边界合成 `Keyboard.onKey` / `Mouse.onMouseButton`，让真实 `Screen`/tooltip 代码路径照常触发；OS 级光标注入在这台机器上不可靠，本探针不依赖它。
- **客户端 box**：tick 60 在 slot 9 写入 3 diamond + 2 emerald 的 `ContainerComponent`，打开 creative inventory、切 inventory tab，aim 到 slot 9。
- **FULL**：在 `clientAimTick + 80` 触发 preview key（342），`preview.alwaysOn=true` 由 harness 写入 `config/shulkerboxtooltip.json5`；日志 `type=FULL`。
- **Phase B**：FULL 窗口后真实 ESC 关屏，再打开 `class_490` survival inventory；等待 server box。
- **Server box**：`run.py` 在 `P193_SURVIVAL_SCREEN` 后通过 dedicated server stdin 执行 `item replace entity GridUser container.10 with minecraft:shulker_box[minecraft:container=[{slot:0,item:{id:"minecraft:diamond",count:2}},{slot:1,item:{id:"minecraft:emerald",count:4}}]]`；客户端 `P193_SERVER_AIM` 后 tooltip 走 server 栈。
- **断言**：`client_multi_items2` 取 FULL 前 client 段；`full_render` 取 `type=FULL`；`server_multi_items2` 取 `P193_SERVER_AIM` 之后的 `GRID_DRAWITEMS first=minecraft:emeraldx4`；`real_hover_path` 取 FULL 之前的 `DRAWTOOLTIP data=...PreviewTooltipData`。

## 本轮修掉的半成品

zcode 额度中断时留下的 p193 source/run 是中间态：

- `ShulkerResidualProbe.java` 的 screen guard 被拆坏（`if (client.field_1755 == null` 缺闭合、`|| ...` 悬空），lambda 多了一个 `}`，导致 `findSlot/hasServerBox` 掉到类外；已恢复为 phase B 之后统一 guard。
- `build.py` 的 sponge-mixin 路径写死 `D:\我的世界\.minecraft\libraries`，本机不存在；改为 `work/launcher-e2e/libraries/.../sponge-mixin-0.17.4+mixin.0.8.7.jar`。
- `run.py` 的 `server_multi`/`real_hover` 检查字符串与日志格式不匹配（`emeraldx4` vs `emerald count=4`；`GRID_DRAWITEMS` 里没有 `data=`）；已按阶段拆分并改成实际 marker。
- `run.py` 的 server box 门槛从“等 `P193_SURVIVAL_SCREEN`”改为“该 marker 出现后发”，与新版 phase B 对齐。

## 边界（如实记录）

- 真实 hover 是 **GLFW 回调级注入**，不是 OS 级鼠标；它与真实输入走同一 `Screen`/tooltip 代码路径，但操作系统光标层未验证。
  - **2026-10-28 更正（p202）**：这一条后来做到了——探针不写鼠标字段，由外部进程移动真实光标，`focusedSlot` 变成槽位 10 时 `keysSent=false`（`runs/p202-hover-nbt/`）。同处也纠正了"OS 级光标注入在这台机器上不可靠"：真正的原因是游戏窗口没在最上层，不是注入机制（控制组只做指针 warp 也能悬停，见 `runs/p202-hover-nbt/repeat/run3-control-warp.log`）。
- FULL 依赖 `preview.alwaysOn=true` + preview key（342）；默认按键/其他配置未逐一验证。
- 服务端 box 只验证了 dedicated server 的 `/item replace container.10`；integrated server 的 mcfunction 组件语法问题见 p188，未在这里重复。
- 27 格全满/多组不同物品的网格、preview key 的按键重绑定、真实 OS 鼠标 hover 未测。
- 本轮**没有修改** ShulkerBoxTooltip companion 或 mod 代码；p187 的 companion 1.1.0 不变，p193 是验证轮。无新 release（保持 v0.5.6）。

## 后续

- p194：map atlas 第三个 atlas（2048+）/跨 atlas 同屏/真实服务端 1024+ 张地图。
- p195：v0.5.6 portable 干净/离线验证 + one-click panel 真实点击 E2E。
- v0.5.7 视 p194/p195 结果与用户确认。
