# 分发与发布

最后更新：2026-10-21。本文回答三件事：**GitHub 上能发布什么**、**别人拿到后怎么复现**、
以及**怎么发给不用 GitHub 的人**（便携包）。

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
- 可选的便携启动器包（见第 2.5 节，不含任何游戏/模组 jar）；
- `runs/SHA256SUMS.txt`（生成：`python tools/hash_evidence.py`；校验：`python tools/check_hashes.py`）。

**不要**上传任何 `.jar` 游戏/模组/转换件。

## 2.5 发给不用 GitHub 的人：便携包

许可证允许：本仓库是 MIT，便携包里**只有本项目的代码 + 官方嵌入式 Python 运行时 +
可选的 `minecraft-launcher-lib`（BSD-2）及其纯 Python 依赖**，不含任何 Minecraft 或模组 jar。
对方第一次启动时仍然联网从 Mojang 下载（国内默认走 BMCLAPI 镜像），所以**玩家人不需要梯子**，
只是“拿到这个 zip”这一步需要一条不依赖 GitHub 的渠道。

构建（无参数即可，会自动下载约 11 MB 的 embeddable Python 到 `work/portable-cache/`）：

```powershell
python tools/build_portable.py --label 0.3.5
# -> dist/mcbridge-launcher-0.3.5.zip  （约 12 MB，免安装）
```

包内结构：

```text
mcbridge-launcher-0.3.5/
  run.bat                 ← 双击即用（内置 Python）
  bootstrap.py
  launcher/               ← 启动器源码
  docs/guide.md           ← 使用说明
  python/                 ← CPython 3.12 embeddable + site-packages（mll/requests/...）
  LICENSE
  THIRD-PARTY-NOTICES.md
  THIRD-PARTY-LICENSES/   ← 各组件许可证原文（构建时自动收集）
```

分享渠道（按对方情况选）：

| 渠道 | 适合 | 注意 |
|---|---|---|
| 百度网盘 / 123 云盘 / 夸克 | 国内大多数人 | 上传 zip 后把分享链接发出去即可；zip 自带说明 |
| 蓝奏云 | 小文件、免登录下载 | 单文件限制，本包约 12 MB 可用 |
| QQ 群文件 / 群共享 | 小圈子 | 最省事，但更新版本要重发 |
| GitHub Release 资产 | 能访问 GitHub 的人 | 就是本仓库 release 里附加的 zip |
| 第三方 GitHub 加速镜像（ghproxy 等） | 临时救急 | 稳定性与隐私不可控，不建议作为唯一入口 |

**别做的事**：不要把 `work/`、游戏 jar、模组 jar、整合包一起打进分享包；不要把
`launcher/config.json`（含个人路径）发出去——构建脚本已经排除了它。

包内 `README-PORTABLE.txt` 写了给小白看的三句话上手说明；更完整的教程在 `docs/guide.md`。

**依赖缺失时不会静默出包**：`vendor_deps()` 只复制构建机 import 得到的依赖，缺
`minecraft-launcher-lib` 时会直接 `RuntimeError` 退出（rc=1），不会产出一个"能启动、按下载就报错"的包。
如果确实要出一个不含依赖的源码包，显式加 `--allow-missing-deps`。

**跨平台边界（2026-10-28 实测）**：便携包**按构造只能用 Windows**——内嵌的是
`python-{pyver}-embed-amd64`，启动脚本只有 `run.bat`（没有 `.sh`），包内也没有任何 `.jar`。
`launcher/` 本身在 POSIX 上可以导入（`runs/p208-cross-platform/`：`sys.platform=linux` + 屏蔽
Windows-only 模块后 4/4 模块可导入），但要真跑 Linux/macOS 需要另一套嵌入式运行时与另一份启动脚本，
目前**没有做**，也没有声称能做。源码路径（clone + 系统 Python 3.10+ + JDK 21）是跨平台的。

打完包可以这样自检（离线部分：内置 Python、依赖、打包后的 `verify`、页面与接口）：

```powershell
python tools/test_portable.py --root <已安装的游戏目录> --version <已安装版本>
# RESULT: OK 才算打包可用；没有 dist 包时会 SKIP（退出码 2）
```

`dist/` 已被 `.gitignore` 忽略，**构建产物不提交到仓库**，只作为 release 资产或网盘文件分发。

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

## Mod Menu 列表渲染桥（p205）

`work/client/modmenu-patched.jar` 是修前的构建（列表只画黑底不画行），保留它只为让
`runs/p204-wheel-input/` 的证据仍可复现。**分发要用 `work/client/modmenu-rows.jar`**
（`runs/p205-modmenu-rows/build.py` 产出：javac 单桥 + `tools/inject_bridges.py` 注入）。
全量重打包时仍需用同一 `--bridge-dir` 走 `patch`，否则旧的 `ModMenuListRenderBridge` 会留在 jar 里。

调试：加 `-Dmcbridge.listrender.debug=true` 才会打印 `P205_LIST class=… count=… rowWidth=…`，
默认不打印。

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
