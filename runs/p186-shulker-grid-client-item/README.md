# p186 — ShulkerBoxTooltip 网格预览：client-side component + wrapper + t2/t4 桥（部分恢复）

日期：2026-10-24。p110 卡在“客户端 container 空”；p186 证明 **component 不空**，并绕过 legacy 路径让
grid renderer 真正跑到 tooltip。结果是 **预览网格框 + `Diamond ×5` 出现，但网格里的物品图标还没画出来**，
且使用的是 client-side item；真实服务端 item 仍受 p110 的同步问题限制。本文件如实记录这个“部分恢复”。

## 结果

```text
SBT_ITER raw1=1 raw2=1 head=minecraft:diamondx5 empty=false
SBT_WRAP show=true inv=27 nonAir=1 stack=minecraft:shulker_box
```

- `grid.png`：creative inventory 中悬停 client-side shulker box，ShulkerBoxTooltip 出现
  **预览网格框**，下方显示 `Diamond ×5`；p110 的 `grid-window.png` 当时完全没有网格；
- **网格格子里没有画出 diamond 图标**（框和计数有了，item icon 仍缺）；这是下一个缺口；
- `result.json`：`sbt_seen=true`、`container=true`；
- 无 crash / tombstone / ClassCast。

## 修了什么

1. **p110 的 component 其实有物品**：p186 client-side item 的 `ContainerComponent.method_59714()`
   有 1 个 diamond；p110 看到 0 是 legacy NBT 路径的问题。
2. **companion wrapper**：新增 `mcbridgepreview.ComponentPreviewProvider`，直接用 p110 在 tooltip
   剥离前缓存的 `class_9288` component 生成 27 格 inventory；必须放在 `sbtpreview` mixin 包之外
   （Mixin 不允许引用同包非 mixin 类）。`PreviewTooltipDataMixin` 用 wrapper 构造
   `PreviewTooltipData`，所以 `SBT_WRAP show=true inv=27 nonAir=1` 成立。
3. **grid renderer 的两个 tombstone**：
   - t2 `ItemStack.getNbt()` (`method_7969`) → `ShulkerBoxNbtBridge.legacyNbt`；
   - t4 `ItemStack.setNbt(...)` (`method_7980`) → `setLegacyNbt` no-op；
   - `rules/fabric-1.21.1/shulker-nbt.json` 增加 `shulker.legacy.get-nbt` / `shulker.legacy.set-nbt`；
     重新 patch Shulker jar（`shulker-patched2.jar`）后 grid renderer 不再抛
     `CenturyBridge tombstone`。
4. 测试服：`fabric-1.21.1-server-trashslot`（已加载世界），peaceful/creative、重启前删
   `GridUser` 的死亡 playerdata；客户端补同版本 patched TrashSlot；否则上一轮的 creeper 死亡会
   一直停在 death screen。

## 仍未解决

- **网格里的 item icon 没画出来**：计数/框在，slot 内容不显示；需要看 `PreviewTooltipComponent`
  / `PreviewRenderer` 的 item 绘制路径（可能与 t2/t4 或 1.20.4 item render 桥有关）；
- **真实服务端 item 仍不可用**：p110 的 `/item replace` 栈在客户端仍是 `!minecraft:container`；
  本轮的 client-side item 绕过了这个同步问题，不等于真实 gameplay 恢复；
- 只测一个 client-side shulker box、5 颗钻石、creative inventory、一个客户端；
- 无新 release（部分恢复，不宣称完整 grid）。

## 复现

```text
python runs/p186-shulker-grid-client-item/build.py
python runs/p186-shulker-grid-client-item/run.py --timeout 180
```

`build.py` 编译 client probe；`run.py` 启动 `fabric-1.21.1-server-trashslot`（临时 patched
TrashSlot + peaceful/creative + 删 GridUser playerdata），客户端装 converted Shulker + rebuilt
companion + probe，悬停截图。测试后 server/client 已恢复。

## 证据

`grid.png`、`client.log`、`server.log`、`result.json`、`src/probe/GridProbe.java`、
`java/src/shulkerpreview/java/mcbridgepreview/ComponentPreviewProvider.java`、
`rules/fabric-1.21.1/shulker-nbt.json`。
