# p200 — 三张 atlas 并排，逐张地图校验 tile 落点

日期：2026-10-28
对象：转换后的 ImmediatelyFast map atlas（`work/launcher-e2e` + `.build/ImmediatelyFast-ported.jar`）
结论：**2050 个 map id 逐个校验**槽位（不是抽样），三张 4096² atlas 的地图同屏并排出现且尺寸/间距逐像素对上，退出时三个 atlas 全部清理。显存在本机不可观测，只给进程工作集实测 + 192 MiB 的精确账，没有估算冒充。

## 结果

`result.json`：

```json
{
  "joined": true,
  "required_ok": true,
  "exit_seen": true,
  "errors": [],
  "crash": null,
  "exit_code": 1,
  "screenshot": "world.png"
}
```

关键日志（`client.log`，`exit_code: 1` 是客户端正常 stop 的返回码，runner 自身 exit 0）：

```text
[p200-probe] allocated 2050 ids in 193 ms heap-used=481 MiB atlases=3
             atlasOf1=0 atlasOf1024=0 atlasOf1025=1 atlasOf2048=1 atlasOf2049=2 atlasOf2050=2
[p200-probe] atlas0 image 4096x4096 last-pixel-ok=true past-end-throws=true bytes=67108864
[p200-probe] atlas1 image 4096x4096 last-pixel-ok=true past-end-throws=true bytes=67108864
[p200-probe] atlas2 image 4096x4096 last-pixel-ok=true past-end-throws=true bytes=67108864
[p200-probe] atlas images=3 native-bytes=201326592 (192 MiB)
[p200-probe] tile-sweep ids=2050 mapping-mismatch=0 pixel-verified=2050 pixel-mismatch=0
             layout-ids-solid-verified=3 write-ms=436 verify-ms=1
[p200-probe] layout-tiles map1=atlas0@0,0 0xFF0000FF expected 0xFF0000FF
             map1025=atlas1@0,0 0xFF3AD900 expected 0xFF3AD900
             map2049=atlas2@0,0 0xFFFF4040 expected 0xFFFF4040 atlas-count=3
[p200-probe] layout-drawn guiScale=2.0 scale=2 framebuffer=1280x720 gui=640x360
             rects=map1@16,16+256;map1025@288,16+256;map2049@560,16+256
[mcbridge-port] map-atlas clear atlases=3
```

截图校验（`layout-check.json`，由 `verify_layout.py` 生成）：

| 地图 | 所在 atlas | 期望 GUI 位置 | 截图实测 bbox | 尺寸 | 截图色 |
|---|---|---|---|---|---|
| map 1 | atlas 0 | `16,16 +256` | `24,47` | 256×256 | `255,0,0` |
| map 1025 | atlas 1 | `288,16 +256` | `296,47` | 256×256 | `0,217,58` |
| map 2049 | atlas 2 | `560,16 +256` | `568,47` | 256×256 | `64,64,255` |

- 三块都是 **65536 像素**（= 256²，正好等于 128 × guiScale 2），没有边缘渗色；
- 三块在截图里的原点偏移一致：`[8,31] / [8,31] / [8,31]`（窗口边框，抓图含标题栏）；
- 块间距 272 = `136 × 2`，与 probe 记录的 `LAYOUT_STEP` 一致；
- 颜色按本链路的实际打包顺序 `0xAABBGGRR` 解出后与 atlas 里写进去的 int 完全对应。

## 为什么 p194 的像素校验不够

p194 的 2050 个 id 共用同一个 MapState（都复制 map 1 的内容）。atlas 里 1024 格内容一模一样，于是"读回格子像素 == 地图颜色"在**槽位错位时同样成立**：它能证明"格子被写过"，不能证明"这张地图落在它自己的格子上"。

p200 给每个 id 一段只属于它的内容：把 id 的 12 位写进 tile 第 0 行的 12 个像素（最亮/最暗两个调色板色当 1/0），逐 id 走一次性 update+draw，再从 atlas 里**该 id 报告出来的槽位**读回这 12 位。错位、串格、覆盖都会立刻变成 mismatch，而不是看起来正常。

三个展示地图（每张 atlas 的第一格）不参与编码校验，改用纯色验证：它们的 tile 是单一颜色，读三个对角点即可。

## 方法

1. **分配**：等 map 1 的真实 MapState 到达后，用公共更新路径 `MapRenderer.update` 连续创建 id 1..2050，槽位全部由 mod 自己的分配器给出（1..1024 → atlas 0，1025..2048 → atlas 1，2049/2050 → atlas 2）。probe 同时用 `expectedMapping(id)` 复算一遍并逐 id 比对（`mapping-mismatch=0`）。
2. **逐张写入 + 回读**：对每个 id 写入自己的 12 位编码 → `update` → 在 HUD 里 translate 到屏幕外（-100000）画一次，触发该 tile 的上传 → 读回该 id 槽位的 12 个像素。
3. **并排帧**：三张展示地图各持**自己的** MapState（纯色），每帧在固定 GUI 坐标 `8,8 / 144,8 / 280,8` 画一次，稳定到截图为止。
4. **退出**：25 s 后请求正常 stop，验证 `map-atlas clear atlases=3`。

### 为什么要各持 MapState

atlas 上传是"把这个 MapInstance 持有的 MapState 的 16384 字节抄进自己的 tile"。三张图若共用一个 state，每帧最后一次写入的颜色会把另外两格的 tile 一起刷成同一个颜色——第一版就是三块全灰。先试过 `replaceMapData` 中途换 state（probe 内自检 `state-replaced=true`，tile 却仍是旧内容），最终改成**创建时就**给三张图各自的 state，这条弯路记在这里，省下一个人重踩。

## 内存：能测的和不能测的

- **192 MiB 是算出来的，但尺寸不是假定的**：每张图读 `(4095,4095)` 成功、读 `(4096,4096)` 抛异常（`past-end-throws=true`），说明缓冲恰好 4096²，×4 字节 ×3 张 = 201,326,592 字节。
- **进程工作集实测**（100 ms 采样，170–189 个样本）：分配前 1556.0 MB → 分配后 2016.9 MB（**+460.9**），全流程峰值 2247.3 MB。同一场景**重复三次**的步进是 **+460.9 / +548.1 / +486.5 MB**（中位 486.5，峰值 2192.0–2247.3，见 `memory-runs.json`，重复两次的关键日志摘录见 `repeat-runs.log`）——波动范围本身就跨 87 MB，所以只报区间，不拿单点当结论。
- **显存没有测**。这台机器上没有厂商侧工具能读 GPU 私有分配，工作集里也混着堆、驱动和 GL 上传缓冲；任何"约 192 MB 显存"的说法都只是把算术当测量。报告里不写。

## 与 p194 的差别

| 项 | p194 | p200 |
|---|---|---|
| 2050 个 id 的槽位 | 抽查映射值（日志打印 4 个） | 逐 id 复算 + 逐 tile 回读内容 |
| 内容区分度 | 全部相同（同一个 state） | 每 id 唯一 12 位编码 |
| 三张 atlas 同屏 | 只有"同帧三个 bind"，quad 落在 HUD 原点 | 三块并排、位置/尺寸/间距按截图核对 |
| 内存 | 未测（只写"约 192 MB"） | 工作集三次实测 + 精确的 192 MiB 账 |

## 边界（如实）

- **仍没有真实专用服务器**下发 1024+ 张地图的端到端：2050 个 id 是客户端复用 map 1 的 MapState 合成的，不是服务端真的发来 2050 个 `MapItemSavedData`。
- 只用到 2050 格（两个 atlas 满 + atlas 2 的前两格），**没有压到 3072**（三张全满）去看第四张 atlas 的创建。
- 工作集 ≠ 显存；GPU 侧分配未测。
- 颜色打包顺序是 `0xAABBGGRR`（红在低字节）。第一版校验器按 ARGB 解，把红蓝读反，误报"三个色块都不是预期色"；改成按实际顺序解后完全对上，这条弯路保留在 `verify_layout.py` 的注释里。
- 三张展示地图的 tile 被改成纯色，手里那张 map 1 也因此变成纯红——这是探针行为，不是渲染缺陷。

## 复现

```text
python runs/p200-atlas-layout/build_probe.py
python runs/p200-atlas-layout/make_world.py
python runs/p200-atlas-layout/run_client.py --timeout 300
python runs/p200-atlas-layout/verify_layout.py
```

截图校验要 Pillow。本机默认解释器（`~/.workbuddy/binaries/python/.../3.13`）没装 Pillow，`run_client.py` 会打印 `screenshot skipped: Pillow missing` 并让本次运行失败——这是 p194 之后环境变化导致的，用带 Pillow 的解释器跑即可（本次用的是 `AppData/Local/Programs/Python/Python312`）。

## 证据

- `runs/p200-atlas-layout/`：`client.log`、`latest.log`、`result.json`（含 189 个工作集样本与标记点）、`world.png`（整屏）、`layout-crop.png`（三块裁切）、`layout-check.json`、`memory-runs.json`（三次运行）、`repeat-runs.log`（重复两次的关键行摘录，完整日志留在 gitignore 的 `work/tmp`）、`gate-review-fixes.log`、`build_probe.py`、`make_world.py`、`run_client.py`、`verify_layout.py`
- `probes/p200-atlas-layout/`：probe 源码 + `DrawContextConsumersAccessor`（只借 HUD 的 consumers，不改被测代码）

## 后续

- 真实专用服务器 1024+ 张地图：需要起 dedi 服 + 客户端跨 atlas 绑定，本轮未做。
- 3072 格压满 → 第四张 atlas：未做。
