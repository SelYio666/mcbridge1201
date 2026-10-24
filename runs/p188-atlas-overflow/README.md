# p188 — 地图 atlas 1024 溢出路径（第二个 atlas）

日期：2026-10-25。p181 留下 "Atlas overflow (1024 maps) is still untested"。本轮补上：填满
atlas 0 的 1024 张地图后再分配，验证溢出创建第二个 atlas、packed 编码、跨 atlas 的 GL 上传、
以及正常退出的双 atlas 清理。**实现零改动**——本轮是纯验证轮（溢出路径本来就是对的）。

## 场景（全部客户端内驱动，无数据包命令）

- 世界 `ColdWorldAtlasOverflow`（复用 p181 的世界构建：map_1.dat unlocked + Fabric API +
  ported ImmediatelyFast + p188 probe）；
- 探针 `p188probe`：等服务端发来 map 1 的真实 MapState 后，用公共 update 路径
  `MapRenderer.method_1769(mapId, state1)` 连续分配 **1026 个 map id（1..1026）**，全部复用
  map 1 的 MapState——前 1024 个填满 atlas 0，id 1025/1026 溢出；
- 之后在 `HudRenderCallback` 里对 map 1025 调用公共的 `MapRenderer.method_1773`
  （真实 draw 路径），触发 atlas 1 的 bind + 上传；
- 60 s 后探针发起正常客户端 stop（p181 模式）。

## 结果（result.json / client.log）

```text
[p188-probe] assigned 1026 map ids mapping1024=7967 mapping1025=65536 mapping1026=65792
             atlasOf1025=1 atlasOf1026=1
map-atlas create id=1                                  <- 恰好一次（1024 满后溢出创建）
map-atlas assign map=1024 packed=7967                  <- atlas 0 最后一格（31<<8|31）
map-atlas assign map=1025 packed=65536                 <- atlas 1 第一格（tile 0,0）
map-atlas assign map=1026 packed=65792                 <- atlas 1（tile 0,1）
map-atlas bind map=map/1025 texture=immediatelyfast:map_atlas/1
[p188-probe] drew map 1025 through MapRenderer.draw (atlas 1)
[p188-probe] atlas1-pixel-check mismatches=0 (0,0)ok (64,64)ok (127,127)ok (32,96)ok
map-atlas clear atlases=2                              <- 正常退出，两个 atlas 都清理
```

- `atlas1-pixel-check`：draw 后读回 atlas 1 的 NativeImage（`method_4315`），4 个采样点的
  颜色与 MapState 颜色（`class_3620.method_38480` 变换后）完全一致——溢出 atlas 的上传在
  **像素级**证实（update marker 有节流 `<=3 || %1000`，此图的上传计数 >3 不打印，所以用
  像素证明）；
- `result.json`：`joined/required_maps_ok/logs_ok/exit_seen/map_world_rendered` 全 true、
  `errors=[]`、`crash=null`；markers 共 3084 行（1026 次分配的 assign/texture/bind）；
- `world.png`：手持 map 1（atlas 0）正常渲染（p175 路径未回归）。

## 过程中的两个测试侧坑（记录，不是实现缺陷）

- integrated server 的 mcfunction 里 `item replace ... filled_map[minecraft:map_id=N]` 报
  "Incorrect argument at position 59"（dedicated server 同语法可通过），渲染验证因此改为客户端
  内的 `MapRenderer.draw` 直调；
- `NativeImage` 的像素读取是 `method_4315(x,y)`（int 颜色）；`method_4311(x,y)` 返回 byte
  （亮度），第一次用错导致全 -1。

## 未覆盖

- 第三个 atlas（2048 张以上）未测（代码路径与第二个完全一致：`getNextMapLocation()` 全满 →
  `new MapAtlasTexture(size)`）；1025 张 = 2×4096×4096 NativeImage ≈ 128 MB，更多张的内存
  压力未评估；
- 跨 atlas 的**视觉**正确性（同屏画 atlas 0 与 atlas 1 的地图）未截图验证——像素检查 +
  bind marker 已覆盖绑定与上传，UV 数学（`drawAtlasTexture`）与 atlas 0 相同代码路径；
- 真实服务端下发 1024+ 张已探索地图（`/give` 循环）的端到端场景。

## 复现

```text
python runs/p188-atlas-overflow/build_probe.py
python runs/p188-atlas-overflow/make_world.py
python runs/p188-atlas-overflow/run_client.py --timeout 240
```

## 证据

`world.png`、`client.log`、`latest.log`、`result.json`、
`probes/p188-atlas-overflow/`（探针 + accessor mixin + fabric.mod.json）。
