# p177 — 地图 atlas 边界：两张地图 + 物品展示框

日期：2026-10-23。p175 只验证了单人第一人称手持一张地图。本轮补两个共享同一 atlas 的
实际渲染路径：

1. 两张不同的地图（map id 1、2）同时存在，分别落到 atlas 的 tile 0 和 tile 1；
2. 物品展示框里的地图（非手持路径）也走 `MapRenderer.method_1773 → method_1777`。

## 场景

- 世界 `ColdWorldMapEdge`（p175 世界构建器复制后改造）；
- 玩家 `IFMapUser`，快捷栏 slot 0 = `filled_map`(map_id=1)，slot 1 = `filled_map`(map_id=2)，
  选中 slot 0；
- `data/map_1.dat` / `data/map_2.dat` 写入两套固定图案：
  - map 1：红/白/绿/蓝棋盘 + 黄色对角线（与 p175 相同）；
  - map 2：青/紫竖条纹 + 白色十字 + 洋红中心；
- 数据包 `p177-mapframe` 的 `load` 函数在出生点前方放置支撑石并 summon 物品展示框：
  `(17,67,73)`，`Facing:2b`（朝北，正对 yaw 0 的玩家），框内为 `filled_map` map_id=2。
  地图 2 同时在玩家背包 slot 1，确保服务端通过背包 tick 把 map 2 状态同步给客户端。

## 结果

日志（`client.log` / `latest.log`）：

```text
[STDOUT]: [mcbridge-port] map-atlas create id=0
[STDOUT]: [mcbridge-port] map-atlas assign map=1 packed=0
[STDOUT]: [mcbridge-port] map-atlas texture map=1 packed=0 atlas=0
[STDOUT]: [mcbridge-port] map-atlas bind map=map/1 texture=immediatelyfast:map_atlas/0
[STDOUT]: [mcbridge-port] map-atlas assign map=2 packed=256
[STDOUT]: [mcbridge-port] map-atlas texture map=2 packed=256 atlas=0
[STDOUT]: [mcbridge-port] map-atlas bind map=map/2 texture=immediatelyfast:map_atlas/0
```

`packed=0` → atlas tile `(0,0)`；`packed=256` = `1 << 8` → atlas tile `(128,0)`。两张地图都
绑定到同一个 `immediatelyfast:map_atlas/0`，tile 不同；UV 重定向按各自的 `packedLocation` 计算。

截图 `world.png` 同时显示：

- 底部手持地图（map 1，棋盘/黄对角线）；
- 中央物品展示框里的地图（map 2，青紫条纹/白十字/洋红中心）。

两者图案完整、没有串 tile，也没有 `Map ... is not in an atlas` 警告、没有
`ClassCastException`、没有 Mixin apply 失败、没有 crash report。`result.json`：
`required_maps_ok=true`、`errors=[]`、`crash=null`。

## 代码改动

**没有生产代码改动**。为了复用 p175 的 runner，`runs/p175-map-atlas/run_client.py` 增加：

- `--run-dir`：证据输出目录；
- `--require-map <id>`（可重复）：等待 `map-atlas bind map=map/<id>` 标记。

p177 的 `run_client.py` 只是用这些选项跑 `ColdWorldMapEdge`。

## 复现

```text
python runs/p177-map-atlas-edge/make_world.py
python runs/p177-map-atlas-edge/run_client.py --timeout 180
```

## 仍未验证

- 地图**动态更新**（服务端改 colors 后客户端刷新）和地图标记；
- atlas 满 1024 张后的换 atlas；
- 世界正常退出时的 `method_1771` atlas 清理 / `MapTexture.close` 取消路径（运行器截图后
  terminate）；本轮只覆盖“多 tile + 展示框”；
- 多个展示框/旋转角度/不同面朝向未测。
