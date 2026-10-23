# p181 — 地图 atlas 生命周期：动态更新 + 正常退出清理（并修掉一个真实崩溃）

日期：2026-10-23。p175/p177 只验证了首次上传；p178 的 A/B 运行器截图后直接 terminate。本轮补上：

1. **第二次 atlas 上传**：`locked=0` 的 held map，玩家被数据包移动后服务端发送地图更新；
2. **正常客户端退出**：client probe 调用 `class_310.method_1592`（主循环 stop），走
   `Stopping! → MapRenderer.method_1771 → MapAtlasTexture.close`；
3. 真实退出暴露出一个 **map atlas 崩溃**并已修复。

## 场景

- `ColdWorldMapUpdate`，map_1.dat `locked=0`，玩家手持 map 1（slot 0）；
- 数据包 `p181-map-update` 每 20 tick 把玩家在 `z=70.5` / `z=78.5` 之间传送，并挖空前方 box；
- 测试用 client probe `p181probe`：客户端初始化 30 s 后调用 `class_310.method_1592`
  （主循环 stop，不是 in-frame `disconnect`）；这是正常的客户端关闭路径。

## 结果

```text
map-atlas create id=0
map-atlas assign map=1 packed=0
map-atlas texture map=1 packed=0 atlas=0
map-atlas bind map=map/1 texture=immediatelyfast:map_atlas/0
map-atlas update count=1 map=1        <- 首次上传
map-atlas update count=2 map=1        <- 玩家移动后的第二次上传
[p181-probe] requesting client stop
Stopping!
map-atlas keep-dummy map=1            <- MapTexture.close 被取消（不要关 dummy）
map-atlas close id=0                  <- atlas texture close + unregister
map-atlas clear atlases=1             <- MapRenderer.method_1771 清理
```

- `result.json`：`exit_seen=true`、`exit_code=0`、`crash=null`、`errors=[]`；
- 截图 `world.png`：held map 已从初始棋盘图案更新成地形（蓝色水域/地形），左下角只剩一小块
  棋盘 —— 第二次 atlas 上传真实发生；
- 最终 jar `ImmediatelyFast-ported.jar` sha256 `7141abdc…84f1`；审计 `listed=37 inert=2`，
  桥一致性 `problems=0`。

## 修掉的真实崩溃

第一次用 **in-frame 的 `client.execute(() -> method_18096(null, false))`** 触发退出，日志出现：

```text
map-atlas keep-dummy map=1
map-atlas close id=0
map-atlas clear atlases=1
...
java.lang.IllegalStateException: Image is not allocated.
  at class_1011.method_4305
  at MixinMapRenderer_MapTexture.updateAtlasTexture
  at class_331.method_1776 -> method_1777
```

原因：atlas 已 close，但同一帧里还有排队的地图渲染，`updateAtlasTexture` 继续往已释放的
`NativeImage` 写入。修复：

- `MapAtlasTexture` 增加 `closed` 标志 + `isClosed()`，`close()` 幂等；
- `MixinMapRenderer_MapTexture.updateAtlasTexture` 在 `ci.cancel()` 后先检查
  `atlasTexture.isClosed()`，命中则打印 `map-atlas skip-closed` 并直接返回，不碰已释放图像。

修复后同一路径不再崩；crash report 保留为 `crash-before-fix-map.txt`。

> 第一次尝试还顺带触发了一个 **HUD batching NPE**（`crash-midframe-hud.txt`）：in-frame
> disconnect 把 `client.world` 置空后，同一帧的 HUD 渲染仍继续。它来自 probe 的**非正常
> in-frame 调用方式**，不是 map atlas；最终 probe 改为 `method_1592` 主循环 stop，正常退出
> 干净（exit 0、无 crash）。没有为此改动 HUD 代码。

## 已知限制

- 只测了一张 unlocked held map、8 格 teleport；完整探索/多地图/地图标记未测；
- 正常退出通过 probe 的 stop 路径，不是 ESC→Save and Quit 的鼠标点击路径；
- atlas 满 1024 张换 atlas 未测；
- `closed` 守卫只在退出帧场景验证；长时间运行/资源重载未测；
- 无性能声明。

## 复现

```text
python runs/p181-map-atlas-lifecycle/build_probe.py
python runs/p181-map-atlas-lifecycle/make_world.py
python runs/p181-map-atlas-lifecycle/run_client.py
```

`build_probe.py` 把测试 probe 编译到 `work/tmp/p181-probe.jar`（不入库）；`make_world.py` 会把它
和当前 `ImmediatelyFast-ported.jar` 一起装进测试实例 `mods/`。
