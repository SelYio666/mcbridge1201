# p119 — EntityCulling 1.21.1：被剥离的 mixin 移植并真进世界

日期：2026-10-22。目标 B 的第一块：不再靠“删掉 load-bearing mixin”冒充通过，而是把
EntityCulling 被 CenturyBridge 剥离的 `EntityRendererMixin` **移植到 1.21.1 并重新启用**，
然后在客户端里验证 culling 功能真的在运行。

## 根因（三个，不是一个）

1. **shadow 签名变化**：原 mixin 里的 `@Shadow method_3926` 是 1.20.4 的 5 参
   `(Entity, Component, PoseStack, MultiBufferSource, int)`；1.20.5+ 变成 6 参
   `(..., int, float delta)`。影子方法找不到 → CenturyBridge 把它标成 load-bearing 并剥离。
2. **config 也被改了**：转换后的 `entityculling.mixins.json` 的 `client` 列表不再包含
   `EntityRendererMixin`，只替换 class 文件是不够的，必须把名字加回配置。
3. **bundled transition 库**：`TRansition-1.0.26...jar` 里 `GeneralUtil.getResourceLocation`
   仍在 `new Identifier(String)` / `new Identifier(String,String)`；1.21.1 里这两个构造器
   已私有/移除 → 客户端在 `EntityCullingModBase.clientTick` 崩溃（第一次实测就是栽在这）。

## 改动

### 1. 规则引擎新增 `mixinConfigAdditions`

- `RuleSet`：新规则类型（`config` + `mixinClass` + capability/risk/evidence）并参与解析；
- `JarPatcher`：在类替换之后把 mixin 简单名追加回 `client`（没有 `client` 时用 `mixins`），
  已存在则不重复；
- `Main`：合并多规则文件时补上这个列表（此前漏掉，导致规则“看起来加载了但没生效”）；
- 新增 Java 测试 `MixinConfigAdditionTest`（追加 + 幂等两条），Java 测试 **25/25**。

### 2. EntityCulling mixin 移植

`java/src/compat/java/dev/tr7zw/entityculling/mixin/EntityRendererMixin.java`

- 保持与原 mixin 相同的包/类名（否则 jar 里 class 的内部名与 config 不符，JVM 报 wrong name）；
- `@Mixin(class_897.class)`，`@Shadow method_3921` 不变，
  `@Shadow method_3926(..., int, float)` 改为 6 参并把 `delta` 透传；
- 仍然实现 `EntityRendererInter`，`entityCullingIgnoresCulling/GetCullingBox` 保持原语义。

编译（`-proc:none` 避免 sponge-mixin 注解处理器找 ASM）：

```text
javac -proc:none --release 21 \
  -cp client-1.21.1-intermediary.jar;entityculling-converted.jar;sponge-mixin-0.8.7.jar \
  -d work/compat/entityculling/classes EntityRendererMixin.java
```

### 3. Identifier 构造器

同一个 bundled transition 里 1 参/2 参构造器都改走现成的
`top/mcbridge1201/bridge/IdentifierBridge.of(String[,String])`（constructorRedirects 两条）。

### 4. 规则文件

`rules/fabric-1.21.1/entityculling-mixin-port.json`：
`mixinClassReplacements` + `mixinConfigAdditions` + 两条 `constructorRedirects`，
每条都带 capability / risk / evidence。

打补丁：

```text
mcbridge1201 patch --in <converted.jar> --out entityculling-ported.jar \
  --rules rules/fabric-1.21.1/entityculling-mixin-port.json \
  --bridge-dir work/compat/entityculling/classes
```

实测输出：4 条规则全部命中（config 1、port 1、identifier 1 参 2 次、2 参 2 次），
`audit_mixins`：`listed=10 inert=0 problems=0`。

## 运行证据

环境：Fabric Loader 0.19.5 + Fabric API 0.102.0 + 移植后的 EntityCulling，Java 21；
世界是仓库内 1.21.1 服务端世界副本（`saves/ColdWorld`），`--quickPlaySingleplayer` 进入。

- 客户端日志：`CullingUser joined the game`，无 `Mixin apply failed` / `NoSuchMethodError`；
- `config/entityculling.json`：`skipEntityCulling:false`、`skipBlockEntityCulling:false`、
  `tickCulling:true`（生成即默认启用）；
- F3 截图 `world-f3.png` 里 EntityCulling 自己的调试行：

  ```text
  [Culling] Rendered Block Entities: 0 Skipped: 0
  [Culling] Rendered Entities: 3 Skipped: 1
  ```

  “Skipped: 1” 是 culling 逻辑真正执行并跳过实体的直接证据，不是“能启动”。
- 无 F3 截图 `world.png`：正常游戏画面。

F3 是脚本用 `keybd_event(VK_F3)` 在窗口置前后按下的，不依赖手动操作。

## 清理

- 测试实例的 `mods/`（两个 jar）、`saves/ColdWorld`、临时 `options.txt` 与解包出的 nested jar
  在证据拷出后删除；`work/` 本身在 D 盘 junction 上。

## 限制（如实）

- 只验证 EntityCulling 1.11.3（1.20.1 → 1.21.1），且只进世界观察了一会儿，没有长时间 soak、
  没有性能对比（不能宣称“帧数提升”）；
- F3 显示 `Skipped: 1` 说明 culling 在工作，但不等于所有场景/所有实体类型都正确；
- ImmediatelyFast 仍未解决：它的 `@Overwrite method_22992` 涉及
  `BufferAllocator → ByteBufferBuilder` 的整段语义变化，不是改描述符能糊过去的；
- Sodium/Iris 没碰。
