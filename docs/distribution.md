# 分发与发布

最后更新：2026-10-19。本文回答两件事：**GitHub 上能发布什么**，以及**别人拿到后怎么复现**。

## 1. 能发布什么

可以发布（都在本仓库内，`work/` 已被 gitignore）：

- 工具源码：`java/`、`tools/`；
- 转换规则：`rules/fabric-1.21.1/*.json`；
- 桥源码：`java/src/bridge/`；
- 文档与证据：`docs/`、`runs/`（日志、源码、我们的探针 jar）；
- hash 清单：`runs/SHA256SUMS.txt`。

**不能发布**：

- 游戏 jar（`client-*.jar`、`server-*.jar`）；
- 模组 jar（1.20.1 原版或任何 `fabric-api`/Balm 等）；
- 转换件（`*-rebuilt.jar`、`*-final.jar`、`*-patched.jar`）。

原因：转换件是原模组的衍生作品，分发需要原作者的许可；Minecraft 本体更不能分发。仓库
`README.md` 的“边界”与 `tools/verify_evidence.py` 的 `no_tracked_jars` 检查都据此设置。

`runs/` 下的探针 jar（`dedprobe.jar`、`escprobe.jar` 等）是本项目自己写的测试代码，旁边有
`.java` 源码，属于“工具”而非“游戏内容”，允许入库。

## 2. 发布到 GitHub

```powershell
cd mcbridge1201
git remote add origin https://github.com/<你的账号>/mcbridge1201.git
git push -u origin master
```

发布一个 Release 时，只上传：

- 源码压缩包（GitHub 自动生成）；
- 可选的 CLI 构建产物（`java/build/install/mcbridge1201/`，本项目自己的代码）；
- `runs/SHA256SUMS.txt`（生成：`python tools/hash_evidence.py`；校验：`python tools/check_hashes.py`）。

**不要**上传任何 `.jar` 游戏/模组/转换件。

## 3. 别人怎么用（注意：不是“原始 jar 一步到位”）

对方需要：

1. JDK 21；
2. 自己的 1.20.1 模组 jar（从 Modrinth/CurseForge 下载，不随仓库分发）；
3. `fabric-api-0.102.0+1.21.1.jar` 与 Fabric Loader 1.21.1。

**IronChests 的真实流程是三段，不能只跑单件 `patch`：**

1. **CenturyBridge 转换**：原始 `ironchests-*-fabric.jar` → 基础转换件；
2. **基础规则 + 模型适配**：得到 `ironchests-modelbridge2.jar`（中间件，不在仓库里）；
3. **本仓库重建流水线**：`tools/rebuild_ironchests_client.py --input <中间件>` 编译桥、处理嵌套
   ResourcefulLib、应用 NBT/屏幕/九宫格规则，产出 `ironchests-rebuilt.jar`。

单件 `patch` 示例只对**已经转换过的输入**有效；直接喂原始 1.20.1 jar 会在 1.21.1 启动时报
`NoSuchMethodError`（例如 `class_2073.method_8971`），这不是“单件 patch 能修好”的范围。

```powershell
git clone https://github.com/SelYio666/mcbridge1201.git
cd mcbridge1201
$env:JAVA_HOME='<JDK 21>'
cd java; gradle --no-daemon installDist; cd ..

# 单件 patch（输入必须是 CenturyBridge 转换后的 jar，不是原始 1.20.1 jar）
java\build\install\mcbridge1201\bin\mcbridge1201.bat patch `
  --in <已转换的 ironchests jar> `
  --out <输出目录>\ironchests-rebuilt.jar `
  --rules rules\fabric-1.21.1\ironchests-nbt.json `
  --rules rules\fabric-1.21.1\ironchests-draw.json `
  --bridge-dir work\bridges
```

IronChests 重建流水线（输入同样是上一步的已转换中间件）：

```powershell
python tools\rebuild_ironchests_client.py `
  --input <已转换的 ironchests 中间件 jar> `
  --fabric-api "<fabric-api-0.102.0+1.21.1.jar>" `
  --out work\client\ironchests-rebuilt.jar
```

如果缺中间件，脚本会直接报错并指出缺少的是“CenturyBridge 转换后的输入”，而不是假装成功。

## 4. 精确版本

| 组件 | 版本 |
|---|---|
| Minecraft | 1.21.1 |
| Fabric Loader | 0.19.5 |
| Fabric API | 0.102.0+1.21.1 |
| Balm | 21.0.66（fabric 构建） |
| Java | 21 |

客户端和服务端要放同一套转换件；1.20.1 原版同名模组必须移除。

## 5. 支持范围（发布时必须一起说明）

已验证：

- IronChests：模型、NBT 同步、GUI、取放、关箱持久化、九宫格背景、双客户端同步与并发；
- TrashSlot：移入/取回/clientbound/empty（provider 级）；
- Lithium：加载、玩法冒烟、289 区块 60 秒 20.03 TPS。

未验证 / 已知边角：

- empty-trash 物理按键：合成按键未进入 Balm 屏幕按键事件；
- Lithium 生物 AI、红石、长时间 soak；
- 其他任何模组。

**Lithium 是显式降级，不是“功能原样保留”：** `rules/fabric-1.21.1/lithium-degraded.json` 禁用了
`entity.collisions.movement.EntityMixin` 和 `block.flatten_states.FluidStateMixin`；区块访问替代
实现只委托原版接口，旧的多入口缓存和异线程快速路径没有重写。对外介绍应写成
“保留已验证玩法，部分优化显式降级”，降级列表以 `lithium-degraded.json` 为准。

完整证据见 `docs/baseline.md`、`docs/progress.md`、`docs/remaining-work.md`。

## Clumps 经验球 companion

转换后的 Clumps 不再合并经验球（原 `MixinExperienceOrb` 被移除，见 `runs/p93-clumps-merge/`）。
构建 companion 并与转换后的 Clumps 一起安装：

```text
python tools/build_clumps_companion.py --stub <client-1.21.1-intermediary.jar>   --lib <fabric-lifecycle-events.jar> --lib <fabric-api-base.jar> --lib <fabric-loader.jar>   --out work/compat/mcbridge-clumps-merge.jar
```

服务端每 20 tick 合并 2 格范围内的经验球（写和 + discard），不读 Clumps 配置；客户端无需安装。
仓库只提供源码与构建脚本，不附带 jar。

## 多补丁 jar 的桥版本

每个补丁 jar 都会内嵌一份桥类（如 `FabricLegacyNetworking`、`IdentifierBridge`）。多个补丁 jar
同时安装时，**先加载的那份桥生效**，其余副本被忽略。因此桥代码更新后，必须用同一个
`--bridge-dir` 重新生成**所有**补丁 jar；否则旧桥会遮蔽新方法（实测：旧 AppleSkin 的
`FabricLegacyNetworking` 缺少 `sendPacket`，导致 Shulker 握手 NoSuchMethodError）。

检查已安装的补丁 jar 是否使用同一套桥：

```text
python tools/check_bridge_consistency.py --bridge-dir work/bridges \
  --jar runs/.../a.jar --jar runs/.../b.jar
```

补丁器现在会用当前桥**覆盖** jar 内已有同名桥类（不删除未引用桥，避免多阶段管线缺类）。

## 桥编译依赖提示

LegacyTexturedButton（Mod Menu 纹理按钮桥）引用 class_2561 的字面量工厂，javac 因此需要
brigadier（com.mojang:brigadier，随 Minecraft 提供）。构建桥时把 brigadier jar 一并放进
--lib，否则只有该桥会编译失败。
