# 转换规则

每条规则绑定精确的 `(owner, name, descriptor)` 与目标版本，必须有 id、能力声明、风险和证据。不做“按名字猜”的匹配。

## 应用方式

```powershell
mcbridge1201 patch --in <converted.jar> --out <patched.jar> \
  --rules rules/fabric-1.21.1/container.json \
  --client-jar work/target/client-1.21.1.jar \
  --mappings work/target/intermediary-1.21.1-v2.jar \
  --lib <datafixerupper.jar>
```

- 递归处理嵌套 jar（JiJ）。
- `--client-jar/--mappings/--lib` 可选；提供时额外做 **常量池种类修正**：1.20.5 之后部分类型（如 `com.mojang.serialization.DataResult`）从 class 变成 interface，旧字节码的 `Methodref` 必须改成 `InterfaceMethodref`，方法句柄（`MethodHandle` 常量/indy 参数）同样要改。
- 输出确定性：entry 时间戳固定为 0；修补会使签名失效，因此删除 `META-INF/*.SF|RSA|DSA|EC`。

## 字段重定向 schema

```json
{
  "schemaVersion": "0.1-draft",
  "target": "fabric-1.21.1",
  "fieldRedirects": [
    {
      "id": "itempredicate.any.static-field",
      "sourceOwner": "net/minecraft/class_2073",
      "sourceName": "field_9640",
      "sourceDesc": "Lnet/minecraft/class_2073;",
      "bridgeClass": "top/mcbridge1201/bridge/ItemPredicateAny",
      "bridgeMethod": "any",
      "bridgeDesc": "()Lnet/minecraft/class_2073;",
      "capability": "item.predicate.any",
      "risk": "low",
      "evidence": "为什么这个替换在语义上成立，以及触发它的真实崩溃"
    }
  ]
}
```

桥类由 `BridgeGenerator` 用 ASM 生成并嵌入输出 jar，因此规则不依赖额外安装的桥 mod。

## 调用点签名适配 schema

当目标方法的**参数/描述符**发生变化（不是改名）时，用 `callSiteAdaptations` 把旧调用重定向到
一个 javac 编译的桥方法。匹配是精确的 `(owner, name, oldDesc[, opcode])`，不做通配：

```json
{
  "callSiteAdaptations": [
    {
      "id": "walknodeevaluator.checkneighbourblocks.view-to-context",
      "sourceOwner": "net/minecraft/class_14",
      "sourceName": "method_59",
      "sourceDesc": "(Lnet/minecraft/class_1922;Lnet/minecraft/class_2338$class_2339;Lnet/minecraft/class_7;)Lnet/minecraft/class_7;",
      "sourceOpcode": 184,
      "targetOwner": "net/minecraft/class_14",
      "targetName": "method_59",
      "targetDesc": "(Lnet/minecraft/class_9316;IIILnet/minecraft/class_7;)Lnet/minecraft/class_7;",
      "bridgeClass": "top/mcbridge1201/bridge/WalkNodeEvaluatorCheckNeighbourBlocks",
      "bridgeMethod": "checkNeighbourBlocks",
      "bridgeDesc": "(Lnet/minecraft/class_1922;Lnet/minecraft/class_2338$class_2339;Lnet/minecraft/class_7;)Lnet/minecraft/class_7;",
      "capability": "pathfinding.neighbour_block_scan",
      "risk": "medium",
      "evidence": "触发它的真实 NoSuchMethodError + 旧/新签名 + 语义依据"
    }
  ]
}
```

- `bridgeDesc` 必须与旧栈形状一致；`JarPatcher` 把命中调用改成 `INVOKESTATIC`，直接调用和
  `MethodHandle` 都会处理。
- 桥写成 Java 源码放在 `java/src/bridge/java/...`，用
  `python tools/build_bridges.py --stub <client-1.21.1-intermediary.jar> --lib <gson> --lib <dfu> --out work/bridges`
  编译；`patch --bridge-dir work/bridges` 会把用到的编译产物嵌入输出 jar。
  `tools/inject_bridges.py` 可独立替换/补齐桥类（输出确定性时间戳）。
- 规则引用的桥如果既不是 `BridgeGenerator` 内建、也没有通过 `--bridge-dir` 提供，`patch` 会**硬失败**，
  不会产出悬空调用。
- 当前边界：外部桥只嵌入顶层 jar；嵌套 jar（JiJ）内的调用点尚未覆盖。

## Mixin 目标描述符适配 schema

当 `@Inject` 的目标方法描述符变化（构造器增删参数），用 `mixinCallbackAdaptations` 迁移
Mixin 回调，而不是删 mixin：

```json
{
  "mixinCallbackAdaptations": [
    {
      "id": "lithium.poi.serializing-storage-ctor-callback",
      "mixinClass": "me/jellysquid/mods/lithium/mixin/ai/poi/SerializingRegionBasedStorageMixin",
      "callbackMethod": "init",
      "oldCallbackDesc": "(Ljava/nio/file/Path;...;CallbackInfo;)V",
      "newCallbackDesc": "(Lnet/minecraft/class_9172;...;CallbackInfo;)V",
      "replace": true,
      "refmap": "mixins.lithium.refmap.json",
      "refmapKey": "<init>",
      "refmapValue": "Lnet/minecraft/class_4180;<init>(...new...)V",
      "capability": "mixin.inject.target_descriptor",
      "risk": "medium",
      "evidence": "触发它的真实 InvalidInjectionException + 旧/新目标签名"
    }
  ]
}
```

- `append` 模式（默认）：`insertSlot` + `addedParamDescs/Names`，在 `CallbackInfo` 前插入新参数，
  平移 `VarInsn/IincInsn/LocalVariableTable`，补 `MethodParameters`，并可把 `@Inject.method` 从
  `oldTargetDescriptor` 改写成 `newTargetDescriptor`。
- `replace` 模式：`replace: true`，用 `newCallbackDesc` 替换捕获参数；回调体必须不读取旧参数
  （规则 evidence 里要写明这一点），`maxLocals` 按新描述符重算，旧调试元数据清掉。
- `refmap`：如果原 mixin 用 `<init>` 等短名并依赖 refmap，必须同时把 refmap 的
  `mappings.<mixinClass>.<key>` 改到新描述符，否则 Mixin 会继续用旧签名匹配而失败。
- 这不是 `mixinStrips`：不改 mixin 列表、不删注入；如果目标 API 形状变化超出描述符迁移，
  必须停下来做真正的移植或显式降级，不能把 strip 当通过。

## Mixin 实现类替换 schema

当 mixin 的方法体依赖的 API **形状**整体变化（不是描述符能迁移的），用
`mixinClassReplacements` 保留原 mixin 类名与注解，替换成针对目标版本重新编译的实现：

```json
{
  "mixinClassReplacements": [
    {
      "id": "lithium.serverchunkmanager.chunkresult-port",
      "targetClass": "me/jellysquid/mods/lithium/mixin/world/chunk_access/ServerChunkManagerMixin",
      "replacementClass": "me/jellysquid/mods/lithium/mixin/world/chunk_access/ServerChunkManagerMixin",
      "alsoEmbed": ["top/mcbridge1201/bridge/ChunkAccessPump"],
      "capability": "chunk.access.chunkresult",
      "risk": "medium",
      "evidence": "触发它的真实 ClassCastException/InvalidInjectionException + 为什么不能只改描述符"
    }
  ]
}
```

- 替换类必须编译到同样的内部类名，保留 `@Mixin`/`@Overwrite`，这样 mixin 配置无需改。
- 源码放在 `java/src/mixin/java/...`，用 `tools/build_mixins.py --stub <server-intermediary.jar>
  --lib <sponge-mixin> --lib work/bridges --out work/mixins` 编译（`-proc:none`）；helper 类由
  `build_bridges.py` 编译。`patch --bridge-dir work/bridges --bridge-dir work/mixins` 统一嵌入。
- 这不是 `mixinStrips`：mixin 仍在、注入仍在；如果替换导致优化退化（例如放弃缓存），必须在
  规则的 risk/evidence、`runs/*/README.md` 和兼容档案里写明，不能当作无损替换。

## 现有规则

| id | 目标 | 语义依据 | 状态 |
|---|---|---|---|
| `itempredicate.any.static-field` | `ItemPredicate.ANY` → 空谓词 | 1.20.1 的 ANY 匹配所有物品；1.21.1 的空 `ItemPredicate` 同样匹配所有 | 已应用，ironchests 入口点因此通过 |
| `codec.dispatch.mapcodec-shape` | `Codec.dispatch` 第二参数返回 MapCodec | 1.20.5 引入 MapCodec；桥用 `MapCodec.assumeMapUnsafe` 包装 | 已应用 2 处；ironchests 数据加载/容器契约通过，但 `assumeMapUnsafe` 在部分路径仍可能 NPE（未完全消除，见 baseline §8） |
| `itempredicate.fromjson.static` | `ItemPredicate.fromJson` 的 tombstone 调用（MethodHandle） | 1.21.1 用 registry-aware `ItemPredicate.CODEC` + `RegistryOps` 重建（Java 源码桥） | 已应用 1 处；p9 起启动日志不再出现 fallback 告警 |
| `identifier.ctor.to-factory` | `new Identifier(ns,path)` → 公开工厂 | 1.21.1 私有化构造器 | 已应用 13 处；剩余用 access widener |
| `blockentity.nbt.{read,write}.lookup` | 1 参 NBT 覆写 → 2 参（带 `WrapperLookup`），并给 `ContainerHelper` 调用补参 | 1.20.5 起 BlockEntity NBT 带注册表视图 | **已应用，容器持久化通过** |
| `walknodeevaluator.checkneighbourblocks.view-to-context` | `WalkNodeEvaluator.checkNeighbourBlocks(BlockGetter, MutableBlockPos, PathType)` → 1.21.1 的 `(PathfindingContext, int, int, int, PathType)` | 1.20.1 旧方法体逐条移植；旧调用点可传任意 `BlockGetter`（含 `SingleBlockBlockView`），无法安全构造 `PathfindingContext` | **已应用 2 处；lithium 启动不再抛 `NoSuchMethodError`（推进到下一失败）** |
| `lithium.explosionmixin.ctor-callback` | `Explosion` 构造器从 10 参变为 13 参（追加 2×ParticleOptions + Holder<SoundEvent>） | 回调体只读 shadow 字段；append 3 个未使用参数槽，语义不变 | **已应用 1 处；该注入通过（样本仍卡在 chunk access）** |
| `lithium.poi.serializing-storage-ctor-callback` | `SectionStorage` 构造器改为 `(SimpleRegionStorage, Function, Function, RegistryAccess, ChunkIOErrorReporter, LevelHeightAccessor)` | 回调体只用 `this`；replace 捕获参数并重写 refmap `<init>` 映射 | **已应用 1 处 + refmap 1 处；该注入通过（样本仍卡在 chunk access）** |
| `lithium.serverchunkmanager.chunkresult-port` | `ServerChunkManagerMixin` 的 chunk access 实现 | 1.20.1 的 `ChunkHolderExtended`/`method_17236`/`Either` 在 1.21.1 变为 `ChunkResult`/`GenerationChunkHolder`；整体替换实现，调用 `method_14134` + `ChunkAccessPump` | **已应用 1 处；lithium 到达专用服务端 Done（优化减少）** |
| `trashslot.{itemstack,packet}.*` + `trashslot.balm.initialize-context` | trashslot 的 4 个 ItemStack/NBT tombstone + 旧 Balm 初始化调用 | 1.20.5 组件化；NBT 桥 + `Balm.initialize(String, LoadContext, Runnable)` 调用点桥 | **prepared；Balm 初始化桥已推进，但 Balm 网络 API 仍阻断，未 boot 验证** |
| `constant-kind-fix(-handle)` | class→interface 的常量池种类 | 1.20.5 的 DFU 接口化 | 已应用 123 + 3 处 |

`signatureAdaptations` 会迁移方法描述符、平移局部变量槽、给指定调用补参数，并用 `COMPUTE_FRAMES` 重算帧；这是“签名变化”类损伤的通用处理形态，而不是单点改名。

## 显式降级：mixinStrips

`mixinStrips` 从 mixin 配置里移除注入目标已消失的类（例如 lithium 的 `entity.collisions.movement.EntityMixin`）。每条 strip 必须带 `id`、`config`、`classes`、`reason`，并且：

- 只允许用于**可选优化/装饰性功能**；核心逻辑（存档、掉落、同步）不得靠 strip 过关；
- 产物、报告和兼容档案必须标注 `degraded`；
- 降级档案放在单独文件（如 `lithium-degraded.json`），不混进通用规则。

规则匹配还支持 `MethodHandle`（lambda 实现）——CenturyBridge 的 tombstone 经常以句柄形式出现，不是直接 `invokestatic`。
