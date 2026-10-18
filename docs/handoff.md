# 交接摘要（一页）


更新（2026-10-18 20:50）：**调用点签名适配已实现并用 lithium 的 `class_14.method_59` 验收**。补丁后 `NoSuchMethodError` 消失，启动推进到下一失败 `world.explosions.ExplosionMixin`（注入目标变化）。规则 `rules/fabric-1.21.1/lithium.json`，证据 `runs/p10-lithium-signature/`，说明 `docs/baseline.md` §7.17。
更新（2026-10-18 20:20）：`ItemPredicate.fromJson` 的降级已消除——改用反射读取 BuiltInRegistries 并通过 RegistryOps 解析 codec，启动日志不再出现 falling back，兼容档案已升为 `passed_within_scope`（服务端范围）。
日期：2026-10-18。给下一个接手者：先读这页，再按需展开 `docs/baseline.md`。

## 现在能做什么

在 `work/instances/fabric-1.21.1-server`（Fabric 1.21.1 + Fabric API 0.102.0）里：

- 归档的 `ironchests 5.0.2`（1.20.1 原始 jar）经过 CenturyBridge 转换 + 本项目规则补丁后，**随服务端启动并加载世界**（`Done (1.2s)`，42 个模组）。
- **容器契约通过**（服务端命令范围）：放置 `ironchests:iron_chest` → 插入 5 钻石 → NBT 出现 `Items` → 进程重启 → 读回 `count=5`。一键：

```powershell
$env:JAVA_HOME='C:\Users\27682\Documents\新建文件夹\.toolchain\jdk'
python tools/run_contract.py --instance work/instances/fabric-1.21.1-server --out runs/contract
```

## 关键机制（都已实现并实测）

| 机制 | 位置 | 作用 |
|---|---|---|
| body-preserving 重映射 | `java/.../remap/JarRemapper.java` | 解决本机 Fabric remap 被 zipfs 只读阻塞；方法/字段/lambda 名称传播 |
| 规则引擎 | `java/.../rules/` | 字段/方法/句柄重定向、构造器重定向、常量池种类修正、**调用点签名适配**（javac 桥）、覆写签名适配、**mixin 降级** |
| 规则包 | `rules/fabric-1.21.1/container.json`、`lithium.json` | ironchests 7 条 + lithium 调用点规则，全部有触发证据 |
| 降级档案 | `rules/fabric-1.21.1/lithium-degraded.json` | mixin 剥离，显式记录 |
| 契约脚本 | `tools/run_contract.py` | 两进程重启 + 断言 + verdict.json |
| 报表 | `tools/build_reports.py` | 生成兼容档案 + 支持矩阵 |

## 当前最高证据阶段

`CONTRACT_PASSED`（**仅限**专用服务端 + 命令 API + 单进程重启）。ironchests 兼容档案状态 `passed_within_scope`；lithium 仅到“启动推进到下一失败”，未通过。

## 未解决（按优先级）

1. **lithium 的下一个阻断：`ExplosionMixin` 注入目标变化**：1.21.1 的 `Explosion` 构造器改为接收 `Holder`/注册表项，旧 `@Inject` 描述符不存在。需要改注入点或显式记录降级；不得删核心逻辑 mixin。
2. **调用点适配的覆盖面**：已覆盖顶层 jar 的直接调用和 `MethodHandle`；嵌套 jar（JiJ）内的调用点尚未覆盖。
3. **客户端侧**：GUI 打开、右键交互、渲染、两个客户端同步。本机无显示验证，需要客户端实例。
4. **Forge 成员级分析**：目前只有命名空间级；需要 tsrg(SRG) + Mojang 映射的联合索引。
5. **`BytecodeVerify`**：CenturyBridge 自带的数据流校验未跑。
6. **Mixin 注入点级分析**：只看目标类是否存在，未看 ordinal/slice/局部变量。

> 已完成（不要再当未解决）：`ItemPredicate.fromJson` 的 registry-aware 构造（2026-10-18 20:20，profile `passed_within_scope`）；lithium 的 `class_14.method_59` 调用点签名适配（2026-10-18 20:50，见 §7.17）。

## 复现路径（从零）

```powershell
python tools/fetch_target_env.py     # 1.21.1 client jar / mappings / Fabric API / loader
python tools/fetch_corpus.py         # 10 份样本（校验 sha512）
cd java; gradle --no-daemon installDist; cd ..
python tools/setup_server.py --instance work/instances/fabric-1.21.1-server
python tools/remap_server.py --instance work/instances/fabric-1.21.1-server --loader 0.19.5 `
  --mappings work/cb/data/mappings/intermediary-1.21.1.tiny
python tools/run_server.py --instance work/instances/fabric-1.21.1-server --log runs/boot.log
```

转换 ironchests 需要 CenturyBridge 引擎（`work/upstream/src/...`，编译脚本见 `docs/baseline.md` §6），然后：

```powershell
mcbridge1201 patch --in <converted.jar> --out patched.jar --rules rules/fabric-1.21.1/container.json `
  --client-jar work/target/client-1.21.1.jar --mappings work/target/intermediary-1.21.1-v2.jar `
  --lib <datafixerupper.jar>
python tools/inject_aw.py --jar patched.jar --out final.jar --aw rules/fabric-1.21.1/mcbridge.accesswidener
```

lithium 调用点适配（完整命令和日志见 `runs/p10-lithium-signature/README.md`）：

```powershell
python tools/build_bridges.py --stub work/cb/data/jars/client-1.21.1-intermediary.jar `
  --lib work/lib/gson-2.11.0.jar --lib <datafixerupper.jar> --out work/bridges
mcbridge1201 patch --in <lithium converted.jar> --out lithium-patched.jar `
  --rules rules/fabric-1.21.1/lithium-degraded.json `
  --rules rules/fabric-1.21.1/lithium.json --bridge-dir work/bridges
```

## 不要做的事

- 不要把 `fromJson` 的全匹配回退当作兼容成功；如果未来重新出现，档案里必须保持 `degraded`。
- 不要用 mixin 剥离掩盖核心逻辑（存档/掉落/同步）。
- 不要分发游戏 jar、模组 jar 或转换件；只分发工具、规则与哈希清单。
- 不要把静态 `ANALYZED` 或 `blocked_static` 写成“可运行”。
