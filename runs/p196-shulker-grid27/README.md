# p196 — Shulker grid 27 格全满（+ 预览键重绑定边界）

日期：2026-10-26
结论：27 种不同物品的 shulker box 在 FULL 预览下画出 27 个 icon/计数；server box 与真实 tooltip 路径仍然正常。**预览键重绑定当轮未生效**：配置字段写错分类 + F 触发原版交换副手，FULL 仍靠默认 342（右 Shift）；该结论已在 p197 更正（mod 实际会读 `controls.previewKey/fullPreviewKey`）。

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

- client 27 格：`GRID_DRAWITEMS call=1 type=COMPACT items=27 first=minecraft:iron_ingotx3`；FULL 后 `GRID_DRAWITEMS type=FULL items=27`；
- 27 种物品：diamond/emerald/iron_ingot/.../slime_ball（每格 1..3 个），避免同物品被 `ContainerComponent` 合并（第一次 27 个 diamond 被合并成 `diamondx135`，已改掉）；
- server box：仍为 2 钻 + 4 绿宝石，`GRID_DRAWITEMS first=minecraft:emeraldx4`；
- real hover：pre-FULL `DRAWTOOLTIP data=PreviewTooltipData`，p191 的 Mouse-raw + GLFW 回调路径；
- `client.log` / `server.log` / `after-full.png` / `after-server.png` / `after-compact.png`。

## 预览键重绑定（已被 p197 更正）

- 配置写入了 `"previewKey": "key.keyboard.f"`、`alwaysOn=false`；probe 发送 **F(70)** 并把 `InputPollMixin` 改成伪造 70 —— 结果 `GRID_DRAWITEMS` 全空（preview 类型 NO_PREVIEW）。
- 当轮的解释是“mod 用 `InputConstants.isKeyDown(window, 342)` 轮询硬编码右 Shift、不读 config”，**这个解释是错的**（2026-10-26 p197 用 javap + 运行时配置回读更正）：
  - 键码来自 `config.controls.previewKey/fullPreviewKey`（默认 340/342）；
  - p196 把 `previewKey` 写进了 `preview` 分类，Jankson 忽略未知字段，实际生效的是默认值；
  - 构造在创造模式背包里按 F 还会触发原版 `key.swapOffhand`，把悬停物品换走，tooltip 直接消失。
  - 正确做法见 `runs/p197-preview-key/`：写 `controls` 分类、换用无原版绑定的键，COMPACT/FULL/COMPACT/NO_PREVIEW 全部可复现。

## 27 格构造

- `String[] p196Ids` 27 种 `minecraft:` item id；每格 `(i % 3) + 1` 个；
- `ContainerComponent` 用 `method_57493(p196Items)`，`ItemStack` 列表不再合并；
- `GRID_SETRENDER inv=27`、`GRID_DRAWITEMS items=27` 是 27 格的直接证据。

## 边界

- 预览键重绑定当轮未生效（配置字段分类写错 + F 触发原版交换副手）；**已在 p197 更正并验证**（`runs/p197-preview-key/`）。
- 27 格只验证 icon/计数与 FULL 网格；未验证 27 格全部不同 NBT/附魔/自定义名称的渲染差异。
- 无新 release（v0.5.6，p196 无 mod 代码改动）。

## 复现

```text
python runs/p196-shulker-grid27/build.py
python runs/p196-shulker-grid27/run.py --timeout 300
```

## 证据

`runs/p196-shulker-grid27/`（`result.json`、`client.log`、`server.log`、`after-full.png`、`after-server.png`、`after-compact.png`、`build.py`、`run.py`、`fabric.mod.json`、`resources/p196.mixins.json`、`src/`）。
