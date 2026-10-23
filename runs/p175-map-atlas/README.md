# p175 — ImmediatelyFast 地图 atlas 恢复（真实渲染）

日期：2026-10-23。目标：把 p171 显式 strip、p172 尝试失败的 map atlas 功能真正恢复，并用
**单人世界里实际拿着 filled_map 渲染**的截图 + 日志证明，而不是只证明“能启动”。

## 结果

- Fabric 1.21.1 + Fabric Loader 0.19.5 + Fabric API 0.102.0，补丁 jar
  `ImmediatelyFast-ported.jar`（sha256 `f0f7fa8e…`）；
- 进单人世界 `ColdWorldMap`（`IFMapUser joined the game`），快捷栏 slot 0 为
  `minecraft:filled_map` 且 `minecraft:map_id=1`；
- 地图实际渲染，截图 `world.png`：手持地图显示预先写入的 128×128 棋盘/黄色对角线；
- 日志（`client.log`）：

```text
[STDOUT]: [mcbridge-port] map-atlas create id=0
[STDOUT]: [mcbridge-port] map-atlas assign map=1 packed=0
[STDOUT]: [mcbridge-port] map-atlas texture map=1 packed=0 atlas=0
[STDOUT]: [mcbridge-port] map-atlas bind map=map/1 texture=immediatelyfast:map_atlas/0
```

- 没有 `ClassCastException`、没有 `Mixin apply ... failed`、没有 `Map ... is not in an atlas`，
  也没有生成 crash report（`result.json` 的 `errors=[]`、`crash=null`）。

`map-atlas bind` 行直接说明 `MapTexture` 构造函数里的
`TextureManager.getTextureId("map/" + id, …)` 调用被重定向为
`immediatelyfast:map_atlas/0`，而不是注册 `map/1` 独立纹理；UV 也随
`method_1777` 的重定向指向 atlas 的 `(0,0)` 128×128 tile。截图里图案铺满整张地图（而不是
atlas 左上角一小块），与 UV 重定向一致。

## 1.21.1 实际签名与改动

| 文件 | 1.20.4 | 1.21.1 端口 |
|---|---|---|
| `MixinMapRenderer` | `method_32601(int, class_22)` | `method_32601(class_9209, class_22)`；用 `mapId.comp_2315()` 取 id |
| `MixinMapRenderer_MapTexture` | `method_1777` 的 slice 结束于 `method_1344` | `class_4588.method_1344()` 已移除，slice 结束于 `method_60803(I)` |
| 同上 | `Objects.allocate(NativeImageBackedTexture.class)` 造 dummy | 不再依赖 lenni Reflect；懒创建一个 1×1 `NativeImageBackedTexture`，从不注册/上传/读取/关闭 |
| 同上 | MixinExtras `@Local int id` | 在 `<init>` 的 `super()` **之后**注入捕获 id（1.21.1 的 inner ctor 在 super 前写 outer 字段，`HEAD` 会被 Mixin 判为 before-super，实例 handler 不合法） |
| `MapAtlasTexture` | 1.20.4 纹理 API | Identifier 工厂 `class_2960.method_60655`；`NativeImage` + TextureManager `method_4616/4615` 仍存在 |

编译期还有一个坑：`class_330$class_331` 在 1.21.1 的 class flags 是包可见，`javac` 读到
`CallbackInfoReturnable<class_330.class_331>` 会直接报“private access”。运行时 mod 自带的
access widener 已经把它变 public，所以这里只对**编译 stub** 做 widening
（`tools/widen_stub.py`，只改 access flags / InnerClasses 标志，不改字节码），不修改运行时 jar。

## 规则

`rules/fabric-1.21.1/immediatelyfast-batching-port.json`：

- 删除 `mixinStrips` 中的 `map_atlas_generation.MixinMapRenderer_MapTexture`（p171 的止血）；
- `mixinConfigAdditions` 显式登记 `map_atlas_generation.MixinMapRenderer` 与
  `map_atlas_generation.MixinMapRenderer_MapTexture`；
- `mixinClassReplacements` 新增两个 map mixin 的替换类，并在 `MixinMapRenderer` 的
  `alsoEmbed` 中嵌入 1.21.1 版 `MapAtlasTexture`。

## 审计

```text
python tools/audit_mixins.py --jar .build/ImmediatelyFast-ported.jar
... listed=36 inert=3 problems=3

python tools/audit_mixins.py --jar .build/ImmediatelyFast-ported.jar --allow-inert
... problems=0
```

两个 map mixin 均已从 `INERT` 列表消失；剩余 3 个是 p169 已记录的
`MixinBufferBuilder`、`MixinVertexBuffer`、`MixinFontManager`（与地图无关）。
桥一致性 `problems=0`（18 个 canonical bridge class）。见 `audit.log`、`audit-allow-inert.log`、
`bridge.log`、`build.txt`。

## 复现

```text
# 编译端口类（会自动生成 widening 过的编译 stub）
python tools/build_immediatelyfast_port.py --out .build/if-port-classes

# 打补丁（原版 IF jar -> .build/ImmediatelyFast-ported.jar）
java -cp "java/build/install/mcbridge1201/lib/*" top.mcbridge1201.Main patch \
  --in work/cb/out/popular/immediatelyfast/ImmediatelyFast-Fabric-1.5.5+1.20.4+1.21.1.jar \
  --out .build/ImmediatelyFast-ported.jar \
  --rules rules/fabric-1.21.1/immediatelyfast-batching-port.json \
  --bridge-dir .build/if-port-classes --bridge-dir work/bridges \
  --client-jar work/cb/data/jars/client-1.21.1-intermediary.jar \
  --mappings work/cb/data/mappings/intermediary-1.21.1.tiny \
  --require-hit immediatelyfast/map-renderer-mixin \
  --require-hit immediatelyfast/map-texture-mixin \
  --require-hit immediatelyfast/map-renderer-config \
  --require-hit immediatelyfast/map-texture-config

# 造世界/playerdata/map_1.dat + 装 mods，然后进世界截图
python runs/p175-map-atlas/make_world.py
python runs/p175-map-atlas/run_client.py --timeout 180 --settle 10
```

`make_world.py` 会把服务端世界复制到 `work/launcher-e2e/saves/ColdWorldMap`，写
`data/map_1.dat`（1.21.1 的 SavedData 需要 `{"DataVersion":3955,"data":{...}}` 包装）和
playerdata（hotbar slot 0 的 filled_map + `components:{"minecraft:map_id":1}`，SelectedItemSlot=0，
Pos 用 p139 同一个出生点）；`run_client.py` 用 `--quickPlaySingleplayer ColdWorldMap` 进世界，
等待 `joined` 与 `[mcbridge-port] map-atlas` 标记，再等 10 s 抓窗口。

## 本轮踩过的失败（如实记录）

1. **全新实例停在 Accessibility 引导页**：第一次运行只到“Welcome to Minecraft! … Narrator”，
   Quick Play 等用户点击。修法：`make_world.py` 预置 `options.txt`（`onboardAccessibility:false` 等）。
2. **map_1.dat 放错层级**：1.21.1 的 `SavedDataStorage` 读文件根后取 `nbt.getCompound("data")`，
   直接把 `dimension/xCenter/colors` 放根上会得到 `Invalid map dimension: null`。修法：包一层
   `{"DataVersion":3955,"data":{...}}`。
3. **`@At("HEAD")` 不能用于这个 ctor**：Mixin 报
   `@Inject handler before super() invocation must be static`。修法：改到
   `Object.<init>` 的 `AFTER`。
4. **`@Unique private int immediatelyFast$mapId = -1` 覆盖注入值**：字段初始化器在构造器里
   晚于捕获点执行，导致 redirect 看到 `-1`，日志出现 `Map -1 is not in an atlas`，地图回退
   vanilla（截图仍显示图案，但不是 atlas）。修法：去掉字段初值，捕获点负责写值；最终日志
   变成 `map=1`。

这些失败都在同一轮修掉，最终 `world.png` 与 `result.json` 是最后一次成功运行；失败运行没有
保留日志（会污染证据），但上面的报错文本是本轮实际观察到的。

## 诚实的限制

- p175 只验证了**单人 integrated server + 第一人称手持一张地图**；p177 已补两张地图
  （atlas tile 0/1）与物品展示框同屏渲染（`runs/p177-map-atlas-edge/`）；仍未验证地图动态
  更新/标记、atlas 满 1024 张后的换 atlas；
- 运行器截图后直接 terminate，因此 `method_1771` 的 atlas 清理/`MapTexture.close` 取消路径
  没有被世界正常退出流程覆盖（mixin 已 apply，但没有退出时日志）；
- 地图内容是我们写入的固定图案，只证明渲染/纹理路径，不证明地图数据同步的完整玩法；
- 截图是夜间场景（世界时间未改），地图本身亮度不受影响；
- 没有性能声明；
- 剩余 3 个 inert mixin 仍未处理（与地图无关）；
- `exit_code: 1` 是运行器截图后主动 terminate 进程，不是崩溃；`crash` 为 null，日志无异常。
