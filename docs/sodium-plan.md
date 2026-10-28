# Sodium 1.20.1 → 1.21.1 可迁移性评估（方案，不是移植）

日期：2026-10-28　结论：**当前范围内不可行，且不是“加规则就能过去”的那一类不可行。**
范围：只做调研与方案，**没有**转换成功、**没有**启动游戏、**不宣称**支持 Sodium、不提交任何游戏/模组 jar。

本文件回答三个问题：13 个缺失类各是什么、15 + 16 个成员级问题怎么分类、最小可行验证路径长什么样。
所有数字都能用 `runs/p199-sodium-plan/resolve.py` 从仓库内的映射数据复算，不引用外部说法。

## 一、结论先行

1. **阻塞点在渲染内核，不在 API 细节。** Sodium 0.5.13 是围绕 1.20.1 的即时模式顶点管线写的：它的
   `SodiumBufferBuilder` 直接 `extends BufferBuilder`（`BufferBuilder#begin`、`#end`、`#defaultColor`
   都是它继承来的方法），自己的 3 个 mixin 也注入在 `BufferBuilder` 上。1.21.1 把这条管线换成了
   `ByteBufferBuilder` + `MeshData`，`BufferBuilder` 的 `begin/end` 整体消失、`DefaultedVertexConsumer`
   类被删除、`DefaultVertexFormat.ELEMENT_*` 六个字段全部消失。这些不是名字变了，是**被删掉的模型**。
2. **44 条里有 6 条根本不是 Sodium 的问题。** 它们来自 Sodium 的 `META-INF/jars/` 里内嵌的 1.20.1 版
   Fabric API 模块（block-view、resource-loader）。真机上 1.21.1 的 API 模块会按版本胜出，所以这 6 条
   大概率不会阻塞——但**本轮没有验证**，只按“来源”标出来，不计入 Sodium 自身工作量。
3. **剩下 38 条里：纯规则可解的 7 条，写适配层能解的 7 条，必须动渲染内核的 23 条，另有 1 条连不上映射。**
   前 14 条可以做，也值得做（能让静态分析从 `blocked_static` 收敛）；后 23 条不是规则问题。

## 二、方法与证据

`mcbridge1201 analyze`（p158）给的是**引用级**损伤：13 个解析不到的类、15 个解析不到的成员、16 个
描述符对不上。它只说“这里对不上”，不说“这里变成了什么”。本轮补的是后者：

- 输入：`runs/p158-sodium-probe/plan.json`（p158 原始矩阵）、
  `work/target/intermediary-1.20.1-v2.jar` 与 `intermediary-1.21.1-v2.jar`（obf ↔ intermediary）、
  `work/target/client-1.20.1-mappings.txt` 与 `client-1.21.1-mappings.txt`（obf ↔ Mojang 官方名）。
- 方法：把 intermediary 描述符里的 obf 类名改写成官方名，与 Mojang 映射按
  `(obf 类, obf 成员, 官方描述符)` 三元组连接。这样 `a`/`b` 这种重载的 obf 名不会张冠李戴。
  构造器在 intermediary 里不出现（两个命名空间同名，无需映射），单独从 Mojang 侧按描述符比对。
- 判定：`removed`（1.21.1 里没有这个名字）/ `re-signed`（同名但描述符变了）/ `re-ID`（同名同签名，
  只是 intermediary id 变了，纯规则可解）/ `moved`（换宿主类）/ `unresolved`（连不上映射，**列出来
  不隐藏**，共 3 条）。
- 复算：`python runs/p199-sodium-plan/resolve.py`（表格）、`--json`（机器可读）。原始输出见
  `runs/p199-sodium-plan/resolve-table.log` 与 `resolve.json`。

判定只覆盖“这个名字在 1.21.1 还在不在、签名变没变”，**不**覆盖“行为是否等价”。行为等价要等运行时。

## 三、13 个缺失类逐条

| 1.20.1 符号 | 结论 | 1.21.1 现状 | 来源 |
|---|---|---|---|
| `com.mojang.blaze3d.vertex.DefaultedVertexConsumer` | 类已删除 | 无同名类 | Sodium |
| `com.mojang.blaze3d.vertex.DefaultedVertexConsumer#<init>` | 类已删除 | 无构造器可比 | Sodium |
| `com.mojang.blaze3d.vertex.DefaultedVertexConsumer#putBulkData` | 签名变化 | 参数从 `PoseStack$Pose` 起算，形参表整体改变 | Sodium |
| `com.mojang.blaze3d.vertex.DefaultedVertexConsumer#putBulkData`（重载） | 签名变化 | 同上 | Sodium |
| `com.mojang.blaze3d.vertex.BufferBuilder$RenderedBuffer` | 类已删除 | 无同名类（改由 `MeshData` 承担） | Sodium |
| `com.mojang.blaze3d.vertex.BufferBuilder#format` | 改 id（同签名） | 签名不变，仅 id 变 | Sodium |
| `net.minecraft.client.renderer.texture.SpriteContents#originalImage` | 改 id（同签名） | 签名不变，仅 id 变 | Sodium |
| `net.minecraft.util.CubicSampler#gaussianSampleVec3` | 改 id（同签名） | 签名不变，仅 id 变 | Sodium |
| `net.minecraft.client.player.LocalPlayer#blockPosition` | 改 id（同签名） | 继承自 `EntityAccess`，本身未变 | Sodium |
| `net.minecraft.client.renderer.LevelRenderer#globalBlockEntities` | 改 id（同签名） | 签名不变，仅 id 变 | Sodium |
| `net.minecraft.client.multiplayer.ClientChunkCache$Storage#replace` | 改 id（同签名） | 签名不变，仅 id 变 | Sodium |
| `net.minecraft.client.model.geom.ModelPart$Cube#polygons` | 改 id（同签名） | 签名不变，仅 id 变 | Sodium |
| `net.minecraft.world.level.storage.loot.LootDataManager` | 类已删除 | 内嵌 Fabric API 的引用，非 Sodium 代码 | Fabric API（内嵌） |

**读法**：7 条是纯 id 变化（规则能修），2 条是同名签名变化，3 条是真删除且都在 `DefaultedVertexConsumer`
一族，1 条不是 Sodium 的。

## 四、15 个缺失成员

| 1.20.1 符号 | 结论 | 1.21.1 现状 | 来源 |
|---|---|---|---|
| `com.mojang.blaze3d.vertex.BufferBuilder#begin` | 成员消失 | 1.21.1 无此方法 | Sodium |
| `com.mojang.blaze3d.vertex.BufferBuilder#end` | 成员消失 | 1.21.1 无此方法，返回值类型 `RenderedBuffer` 也已删除 | Sodium |
| `com.mojang.blaze3d.vertex.BufferBuilder#defaultColor` | 成员消失 | 声明处 `VertexConsumer` 里已无此成员 | Sodium |
| `com.mojang.blaze3d.vertex.BufferBuilder#unsetDefaultColor` | 成员消失 | 同上 | Sodium |
| `com.mojang.blaze3d.vertex.Tesselator#getBuilder` | 成员消失 | 1.21.1 无此方法 | Sodium |
| `com.mojang.blaze3d.vertex.Tesselator#end` | 成员消失 | 1.21.1 无此方法 | Sodium |
| `com.mojang.blaze3d.vertex.DefaultVertexFormat#ELEMENT_POSITION` | 成员消失 | 字段已删除 | Sodium |
| `… #ELEMENT_COLOR` | 成员消失 | 字段已删除 | Sodium |
| `… #ELEMENT_UV0` | 成员消失 | 字段已删除 | Sodium |
| `… #ELEMENT_UV1` | 成员消失 | 字段已删除 | Sodium |
| `… #ELEMENT_UV2` | 成员消失 | 字段已删除 | Sodium |
| `… #ELEMENT_NORMAL` | 成员消失 | 字段已删除 | Sodium |
| `… #ELEMENT_PADDING` | 成员消失 | 字段已删除 | Sodium |
| `net.minecraft.world.level.block.entity.BlockEntity#getRenderData` | 未能解析 | Fabric API 接口注入的方法，vanilla 映射里没有 | Sodium 侧调用 |
| `net.minecraft.server.packs.repository.Pack$ResourcesSupplier#open` | 未能解析 | Fabric API 接口方法 | Fabric API（内嵌） |

**读法**：13 条是真删除，且 13 条全部落在即时模式顶点管线（`BufferBuilder` / `Tesselator` /
`DefaultVertexFormat`）上。这一桶里**没有**一条是“规则能补”的。

## 五、16 个描述符不匹配

| 1.20.1 符号 | 结论 | 1.21.1 现状 | 来源 |
|---|---|---|---|
| `net.minecraft.resources.ResourceLocation#<init>` | 签名变化 | `(String)` → `(String, String)` | Sodium |
| `net.minecraft.client.renderer.texture.TextureAtlasSprite#getU` | 签名变化 | `(D)` → `(F)` | Sodium |
| `net.minecraft.client.renderer.texture.TextureAtlasSprite#getV` | 签名变化 | `(D)` → `(F)` | Sodium |
| `com.mojang.blaze3d.vertex.VertexFormat#getElements` | 签名变化 | `ImmutableList` → `List` | Sodium |
| `com.mojang.blaze3d.vertex.VertexBuffer#upload` | 签名变化 | 参数由 `RenderedBuffer` 改为 1.21.1 的网格类型 | Sodium |
| `com.mojang.blaze3d.vertex.SheetedDecalTextureGenerator#<init>` | 签名变化 | `(VertexConsumer, Matrix4f, Matrix3f, float)` → 走 `PoseStack$Pose` | Sodium |
| `net.minecraft.client.gui.screens.Screen#renderBackground` | 签名变化 | `(GuiGraphics)` → `(GuiGraphics, int, int, float)` | Sodium |
| `net.minecraft.world.effect.MobEffects#FIRE_RESISTANCE` | 签名变化 | `MobEffect` → `Holder<MobEffect>` | Sodium |
| `net.minecraft.client.player.LocalPlayer#hasEffect` | 签名变化 | `MobEffect` → `Holder<MobEffect>` | Sodium |
| `net.minecraft.client.player.LocalPlayer#getEffect` | 签名变化 | 同上，返回值也变 | Sodium |
| `net.minecraft.client.renderer.FogRenderer$MobEffectFogFunction#getMobEffect` | 签名变化 | 返回 `Holder` | Sodium |
| `net.minecraft.client.gui.screens.VideoSettingsScreen#<init>` | 构造器消失 | 该类在 1.21.1 无构造器（设置界面重组） | Sodium |
| `net.minecraft.server.packs.repository.Pack#readMetaAndCreate` | 签名变化 | 形参表整体改变 | Fabric API（内嵌） |
| `net.minecraft.nbt.NbtIo#readCompressed` | 签名变化 | `File` → `Path` + `NbtAccounter` | Fabric API（内嵌） |
| `net.minecraft.nbt.NbtIo#writeCompressed` | 签名变化 | `File` → `Path` | Fabric API（内嵌） |
| `net.minecraft.nbt.ListTag#add` | 未能解析 | 继承自集合基类，1.20.1 侧也不在本类声明 | Fabric API（内嵌） |

**读法**：11 条是 Sodium 侧的真签名变化。其中 `ResourceLocation(String)`、`getU/getV(D→F)`、
`MobEffect→Holder`、`renderBackground` 加参，都有明确的 1.21.1 对应写法，属于适配层工作量；
`VertexBuffer#upload`、`SheetedDecalTextureGenerator#<init>`、`getElements` 依赖新的网格模型，属于内核工作量。

## 六、汇总与工作量

| 分组 | 条数 | 性质 | 判断 |
|---|---|---|---|
| 纯 id 变化（`re-ID`） | 7 | Sodium 侧，签名不变 | 规则可解，半天级 |
| 签名变化、有明确对应写法 | 7 | `ResourceLocation(String)`、`getU/getV`、`MobEffect` 改 `Holder`（3 处）、`renderBackground` | 适配层，1–2 天级 |
| 签名变化、依赖新网格模型 | 6 | `VertexBuffer#upload`、`DecalGenerator`、`VertexFormat#getElements`、`putBulkData` ×2 | 内核工作量 |
| 成员/类被删除 | 17 | `DefaultedVertexConsumer`、`RenderedBuffer`、`BufferBuilder.begin/end`、`Tesselator` 全删、`ELEMENT_*` 全删 | **重写**，不可规则化 |
| 连不上映射（已单列） | 1 | `BlockEntity#getRenderData`，Fabric API 注入的方法 | 不猜，按未解析记 |
| 不是 Sodium 的代码 | 6 | 内嵌 1.20.1 Fabric API 模块 | 大概率随 1.21.1 API 消失，未验证 |

- Sodium 自身：38 条 = 7 + 7 + 6 + 17 + 1（`unresolved`）。另有 2 条纯 Fabric API 的 `unresolved` 已在第四节/第五节单列。
- 粗略量级：前两类 14 条，按本项目以往的规则/适配节奏是“数天”；后两类 23 条落在渲染内核上，
  不是“数天”的量级——按 1.21.1 的 `ByteBufferBuilder` + `MeshData` 重做即时模式路径，工作量与
  **移植/重写一个 Sodium 相当**，这也是 p158 当初判 `blocked_static` 的原因。
- 这个排序有实际含义：先做 14 条不会让 Sodium 跑起来，只会让静态分析变干净。**不要**把它当成
  “进展百分比”。

## 七、最小可行验证路径（按代价从低到高，逐级可否证）

每一步都能独立失败、独立出结论，不需要一路做到世界渲染才算数：

1. **规则层收敛（不启动游戏，现在就能做）**：把 7 条 `re-ID` + 7 条有明确对应写法的签名变化写进
   `rules/fabric-1.21.1/sodium-*.json`，重跑 `mcbridge1201 analyze`，看
   `missingClass/missingMember/descMismatch` 三个计数是否只下降可规则化的部分。
   验收：计数变化与上表逐条对得上；没有靠“静默跳过”换来的下降。
2. **refmap / 注入可行性（不启动游戏）**：`inject_bridges` + `tools/audit_mixins.py`，
   看 103 个 mixin 类、104 个注入点在 1.21.1 索引里能落地多少。p158 记录的 2 个未解析注入
   （`class_6850.method_39969`、`class_3288.method_45275`）都属于 Fabric API 的注入点，
   预期随 1.21.1 API 消失；**这也要逐条验证，不许默认成立**。
   验收：注入点解析率、未解析清单及原因。
3. **能不能启动到主菜单（第一个运行时里程碑）**：如果第 1、2 步之后 `BufferBuilder` 一族的调用
   还在（必然还在），就要先有一个“能加载但渲染路径未启用”的形态，否则 `NoSuchMethodError` 会在
   类加载/首次绘制时炸。这一步的意义是**证伪**“只改规则就能启动”，不是证明可用。
4. **进世界 + 区块渲染对比（真正的验收）**：满区块截图对比、FPS、GL 错误日志。到这一步就必须
   已经有可用的 1.21.1 顶点路径，属于第 3 节里“重写”那一类的产物。

**建议**：只做第 1、2 步（成本低、结论硬、能固化成规则与测试）。第 3、4 步要等“是否接受内核重写”
这个决定，**不做决定就不要开第 3 步**——否则会得到一个既不能启动、又没人维护的半移植 jar。

## 八、不做什么（明确写死）

- 不提交游戏 jar、模组 jar、转换产物 jar（门禁 `no_tracked_jars` 仍然生效）。
- 不在文档、README、release note 里写“支持 Sodium”“Sodium 已兼容”“性能提升”。
- 不把静态分析通过当成运行时通过：`ANALYZED` ≠ `VERIFIED` ≠ `BOOTED`。
- 不用“估算的显存/帧数”充当实测。

## 九、复现

```text
python runs/p199-sodium-plan/resolve.py            # 三张表 + 汇总
python runs/p199-sodium-plan/resolve.py --json     # 逐条机器可读
```

依赖（仓库工作集里已有，无需下载）：`work/target/intermediary-{1.20.1,1.21.1}-v2.jar`、
`work/target/client-{1.20.1,1.21.1}-mappings.txt`。

## 十、证据

- `runs/p158-sodium-probe/`：原始静态矩阵（`plan.json`、`analyze.log`、`plan.md`）。
- `runs/p199-sodium-plan/`：本轮的 `resolve.py`、`resolve-table.log`、`resolve.json`、`README.md`。
