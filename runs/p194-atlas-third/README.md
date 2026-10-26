# p194 — 第三个 atlas（2048+）+ 跨 atlas 同帧

日期：2026-10-26
对象：转换后的 ImmediatelyFast map atlas（`work/launcher-e2e` + `.build/ImmediatelyFast-ported.jar`）
结论：第三个 atlas 创建/编码/上传/清理全部通过，跨 atlas 同帧 draw + 像素校验通过，`run_client.py` exit 0。

## 结果

`result.json`：

```json
{
  "joined": true,
  "logs_ok": true,
  "exit_seen": true,
  "required_maps": [1, 1025, 2049],
  "required_maps_ok": true,
  "map_world_rendered": true,
  "errors": [],
  "crash": null,
  "exit_code": 1
}
```

关键日志（`client.log`）：

```text
[p194-probe] assigned 2050 map ids (reusing map 1's MapState) mapping1024=7967 mapping2048=73503 mapping2049=131072 mapping2050=131328 atlasOf2049=2 atlasOf2050=2
map-atlas create id=2                                  <- 恰好一次（2048 满后溢出创建第三个 atlas）
map-atlas assign map=2049 packed=131072               <- atlas 2 第一格（2<<16）
map-atlas texture map=2049 packed=131072 atlas=2
map-atlas bind map=map/2049 texture=immediatelyfast:map_atlas/2
map-atlas assign map=2050 packed=131328               <- atlas 2（tile 0,1）
[p194-probe] drew maps 1/1025/2049 through MapRenderer.draw (atlas 0/1/2, one HUD frame)
[p194-probe] atlas1-pixel-check mismatches=0 (0,0)ok (64,64)ok (127,127)ok (32,96)ok
[p194-probe] atlas2-pixel-check mismatches=0 (0,0)ok (64,64)ok (127,127)ok (32,96)ok
map-atlas clear atlases=3                             <- 正常退出，三个 atlas 都清理
```

- `mapping1024=7967` = atlas 0 最后一格（31<<8|31）；`mapping2048=73503` = atlas 1 最后一格；`mapping2049=131072` / `2050=131328` = atlas 2 前两格；
- `create id=2` 只出现一次；`clear atlases=3` 说明三个 4096² atlas 都走关闭/清理；
- 跨 atlas 同帧：在**同一个 HUD frame** 里对 map 1（atlas 0）、map 1025（atlas 1）、map 2049（atlas 2）调用公共 `MapRenderer.method_1773`，三个 bind 都出现；
- 像素级验证：atlas 1 和 atlas 2 的 NativeImage 各采 4 点，与 MapState 颜色（`class_3620.method_38480`）完全一致（`method_4315` 读 int 颜色）；
- `exit_code: 1` 是客户端进程的退出码（正常 stop 时如此），runner 自身 exit 0 且 `exit_seen`/`clear atlases=3` 为 true；`errors=[]`、`crash=null`。

## 场景/方法

- 世界 `ColdWorldAtlasThird`：复用 p175/p181 的 world builder（map_1.dat unlocked + Fabric API + ported ImmediatelyFast），p194 probe 放入 mods；数据包只保留空间/计分板（不再需要 `item replace`）。
- probe：等 map 1 的真实 MapState 到达后，用公共 update 路径 `MapRenderer.method_1769(mapId, state1)` 连续分配 **2050 个 id（1..2050）**，全部复用 map 1 的 MapState：
  - 1..1024 → atlas 0；1025..2048 → atlas 1；2049/2050 → atlas 2；
- HUD：第一帧 `method_1773` 画 map 1/1025/2049（同一个 `DrawContext` consumers），触发 atlas 0/1/2 的 bind + 上传；第二帧读回 atlas 1/2 的 NativeImage 做像素校验；
- 60 s 后探针请求正常客户端 stop（p181 模式），runner 校验 `map-atlas clear atlases=3`。
- 截图 `world.png`：手持 map 1（atlas 0）正常渲染；HUD 的跨 atlas 四边形落在 HUD 原点附近（与 p188 一样，几何位置不是重点，bind/像素/日志才是证据）。

## 边界（如实）

- **真实服务端** 1024+ 张地图端到端未测：本轮 1025/2049 是客户端用 map 1 的真实 MapState 合成的 map id；真实服务端下发 1024+ 个 map state 的场景没有覆盖。
- 跨 atlas 的**视觉**正确性只到“同一 HUD frame 三个 bind + 两张 atlas 的像素一致”；没有做“三个 atlas 地图并排出现在同一屏、肉眼可读”的截图（HUD 四边形在原点，见上）。
- 3 个 4096² atlas 的 NativeImage 约 192 MB；客户端 2G 下通过，但这是内存压力边界，不宣称更高数量。
- 27 格/多组 shulker 不相关；p194 无 mod 代码改动，仍沿用 v0.5.6。

## 复现

```text
python runs/p194-atlas-third/build_probe.py
python runs/p194-atlas-third/make_world.py
python runs/p194-atlas-third/run_client.py --timeout 300
```

## 证据

`runs/p194-atlas-third/`（`result.json`、`client.log`、`latest.log`、`world.png`、`build_probe.py`、`make_world.py`、`run_client.py`、README）+ `probes/p194-atlas-third/`（probe + accessor + fabric.mod.json）。

## 后续

- p195：v0.5.6 portable 干净/离线验证 + one-click panel 真实点击 E2E。
- v0.5.7 视 p194/p195 结果与用户确认；p188 的第三个 atlas/跨 atlas 边界在本轮关闭（真实服务端 1024+ 仍开放）。
