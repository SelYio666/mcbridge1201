# p253 — 兼容垫片包（compat 方向 C）

日期：2026-11-08。新增 `compat-shim/`（一个小 Fabric mod 的源码）+ `tools/build_compat_shim.py`：
运行时提供高频被删符号，作为 fieldRedirect 规则的**免规则替代**。本轮先做
`ItemPredicate.ANY`（1.20.1 `class_2073.field_9640`，1.21.1 的 ItemPredicate 变 record 后删除）。

产物 jar 只落 `work/`（红线：仓库 0 jar）。

## 机制（以及为什么踩了三次 Mixin 的墙）

垫片要在 `class_2073` 上**重新加回一个 public static 字段**，名字必须是 `field_9640`，
才能让模组里现存的 `GETSTATIC class_2073.field_9640` 直接解析。Mixin 是运行时唯一的类变换
通道，但本环境的 sponge-mixin 0.17.4 对「mixin 里的非私有静态字段」一律拒绝：

- `@Unique public static` → `InvalidMixinException ... contains non-private static field`（`logs/variant-shim-rejected-by-mixin.log`）；
- 去 `@Unique`、改 `static final` 内联初始化 → 同样拒绝；
- 反汇编 `MixinPreProcessorStandard.validateField` 找到判定：静态字段**只有 private 或
  ACC_SYNTHETIC（0x1000）**两条放行路径（另有带 `@Shadow` 才放行，但 @Shadow 字段必须在
  目标里存在，加不了新字段）。

解法：`tools/build_compat_shim.py` 在 javac 产物上把 `field_9640` 的 access_flags 置上
ACC_SYNTHETIC——JVM 字段解析完全不看 synthetic 标志，GETSTATIC 照常工作；Mixin 校验放行；
字段以 public static 并入目标类，`<clinit>` TAIL 注入用与 fieldRedirect 桥**完全相同的形状**
初始化（`new ItemPredicate(Optional.empty(), MinMaxBounds.Ints.ANY, DataComponentPredicate.EMPTY, Map.of())`）。

## A/B 对照（同一实例、同一补丁件，只差 shim）

补丁件：ironchests 5.0.2 转换件用**去掉了 `itempredicate.any.static-field` 的 container.json**
（`container-noany.json`）patch，其余规则不变——即“该字段规则不再存在”。

| 组 | mods | 结果 | 日志 |
|---|---|---|---|
| 对照 | fabric-api + ironchests-noany | **启动即崩**：`NoSuchFieldError: Class net.minecraft.class_2073 does not have member field 'net.minecraft.class_2073 field_9640'`，栈在 `IronChestsFabric.onInitialize`（与规则 evidence 里记载的失败一致） | `logs/control-no-shim-crash.log` |
| 实验 | 对照 + `mcbridge-compat-shim-0.1.0.jar` | **`Done (4.709s)`**，全日志 0 条 ERROR，`give` 正常应答（`No player was found`——控制台无 @s，属预期），正常 stop + 三维度存档 | `logs/variant-shim-boot.log` |

结论：去掉字段规则后，垫片单独把失败变回启动/进世界；规则与垫片在语义上等价
（同一空谓词构造）。

## 边界（如实）

- 验证到**专用服务器 Done + 世界加载 + 正常停服**；ironchests 的容器契约（放置/插入/NBT
  持久化）在垫片路径下未重跑（历史契约是在字段规则路径下通过的）。
- 垫片只覆盖 `ItemPredicate.ANY` 一个符号；按 A/B 的统计扩符号是后续工作
  （`build_compat_shim.py` 的 `SYNTHETIC_FIELDS` 表和 mixin 列表就是扩展点）。
- 垫片给整个目标类加字段，**所有**读该字段的代码都会拿到垫片值；若某模组需要不同语义，
  仍应走逐调用点的规则。规则与垫片同时存在时规则优先生效（调用点已被改写，垫片字段无人读）。
- mixin 注入 `required: 1`（失败会响），`fabric.mod.json` 只依赖 fabricloader。

## 复现

```text
py -3.12 tools/build_compat_shim.py --stub work/cb/data/jars/client-1.21.1-intermediary.jar \
  --lib work/instances/fabric-1.21.1-server/libraries/net/fabricmc/sponge-mixin/0.17.4+mixin.0.8.7/sponge-mixin-0.17.4+mixin.0.8.7.jar \
  --out work/shim/mcbridge-compat-shim-0.1.0.jar
# 补丁件：见 container-noany.json（= container.json 去掉 fieldRedirects 里的 ANY 条目）
mcbridge1201 patch --in work/cb/out/ironchests/ironchests-5.0.2-fabric+1.21.1.jar --out <out> \
  --rules runs/p253-compat-shim/container-noany.json --client-jar work/target/client-1.21.1.jar \
  --mappings work/target/intermediary-1.21.1-v2.jar --lib <dfu>
python tools/run_server.py --instance <inst> --log <log> --command "give @s ironchests:iron_chest" --command stop
```
