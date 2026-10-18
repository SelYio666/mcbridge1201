# 交接摘要（一页）

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
| 规则引擎 | `java/.../rules/` | 字段/方法/句柄重定向、构造器重定向、常量池种类修正、**签名适配**、**mixin 降级** |
| 规则包 | `rules/fabric-1.21.1/container.json` | 7 条规则，全部有触发证据 |
| 降级档案 | `rules/fabric-1.21.1/lithium-degraded.json` | mixin 剥离，显式记录 |
| 契约脚本 | `tools/run_contract.py` | 两进程重启 + 断言 + verdict.json |
| 报表 | `tools/build_reports.py` | 生成兼容档案 + 支持矩阵 |

## 当前最高证据阶段

`CONTRACT_PASSED`（**仅限**专用服务端 + 命令 API + 单进程重启）。兼容档案状态 `degraded`。

## 未解决（按优先级）

1. **`ItemPredicate` 的 registry-aware 构造**（唯一的已知语义降级）
   - 现象：`fromJson` 收到 `{"items":["minecraft:dirt"]}`，1.21.1 `ItemPredicate.CODEC` + `JsonOps` 解析失败，退回“匹配所有”。
   - 需要：从 registry 构造 `HolderSet`，而不是用 `JsonOps` 解析。
   - 已查到的 API 线索：`class_2378.method_10223(Identifier)`（registry get）、`class_6880`（HolderSet，需查 `direct` 工厂）、`class_7923`（BuiltInRegistries，需查 ITEM 字段）、`class_2073` 构造器 `(Optional, class_2096$class_2100, class_9329, Map)`。
   - 建议：把该桥写成 **Java 源码**（`java/src/bridge/java/...`），用 javac 对 `work/cb/data/jars/client-1.21.1-intermediary.jar` 编译后嵌入，而不是继续手写 ASM（JSON 解析 + 循环不适合手写字节码）。
2. **客户端侧**：GUI 打开、右键交互、渲染、两个客户端同步。本机无显示验证，需要客户端实例。
3. **调用点级签名适配**：lithium 的 `class_14.method_59`（BlockView/pos → BlockPlaceContext/坐标）需要手写桥，属语义变化。
4. **Forge 成员级分析**：目前只有命名空间级；需要 tsrg(SRG) + Mojang 映射的联合索引。
5. **`BytecodeVerify`**：CenturyBridge 自带的数据流校验未跑。

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

## 不要做的事

- 不要把 `fromJson` 的全匹配回退当作兼容成功；档案里必须保持 `degraded`。
- 不要用 mixin 剥离掩盖核心逻辑（存档/掉落/同步）。
- 不要分发游戏 jar、模组 jar 或转换件；只分发工具、规则与哈希清单。
- 不要把静态 `ANALYZED` 或 `blocked_static` 写成“可运行”。
