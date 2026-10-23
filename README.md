# mcbridge1201（P0 研发仓库）

[![ci](https://github.com/SelYio666/mcbridge1201/actions/workflows/ci.yml/badge.svg)](https://github.com/SelYio666/mcbridge1201/actions/workflows/ci.yml)

> 新手先读：**[使用说明与教程](docs/guide.md)**（启动器 10 分钟上手、PCL 共用、模组迁移教程、FAQ）。

> 最新发布：**[v0.5.0](https://github.com/SelYio666/mcbridge1201/releases/tag/v0.5.0)**（便携包 + ImmediatelyFast 1.21.1 batching 移植 + 专用服务器/mrpack 证据）。

Minecraft Java 1.20.1 模组跨版本兼容平台的第一阶段工作区。来源固定为 **1.20.1**，首个精确目标是 **Fabric 1.21.1**，同时抽样分析 Forge 1.20.1。

本仓库当前交付 P0 的事实与证据，以及 P1 的第一段运行时结果：环境锁定、上游引擎锁定、10 份真实样本、**自研静态损伤分析器**、**body-preserving 重映射器**、CenturyBridge 真实转换产物，和进世界/功能级证据。**只对 `runs/` 里有日志与截图支撑的模组声称通过**（如 EntityCulling、ImmediatelyFast 的移植），其余不宣称兼容。

## 当前状态（2026-10-22）

- **启动器**：离线安装/启动原版 + Fabric/Forge/NeoForge；下载源可选（自动/仅官方/镜像优先）+ 源健康缓存 + GUI 源检查；内嵌 Python 的便携包（v0.5.0）。
- **已验证进世界**：Fabric 1.21.1（全量安装 + EntityCulling 真生效）；ImmediatelyFast 1.21.1 batching 移植（HUD/物品/overlay 计数、Iris 1.8.1/1.8.14 + shader pack、专用服务器多人加入；`runs/p134`-`p150`）；NeoForge 21.1.264（AppleSkin / Farmer's Delight / Jade + **专用服务器客户端加入**，`runs/p161-neoforge-server/`；**带 Farmer's Delight 的服务端/客户端同模组加入**，`runs/p163-neoforge-fd-server/`）；Forge 1.20.1-47.4.28（AppleSkin / Farmer's Delight + **专用服务器客户端加入**，`runs/p159-forge-server/`；**带 Farmer's Delight 的同模组加入**，`runs/p164-forge-fd-server/`）；mrpack 真实 files 导入通过（`runs/p160-mrpack/`）。
- **未通过 / 未验证**：Sodium 1.20.1 转换探针为 `blocked_static`（missingClass=13、missingMember=15、descMismatch=16，`runs/p158-sodium-probe/`），需移植其渲染内核，本轮不做；Iris 只验证了 ImmediatelyFast 的兼容分支（没有转换 Iris 本身）；ImmediatelyFast 端口 jar 仍有 **7 个 inert mixin** 未生效（ChatHud/FontManager/BufferBuilder/MapRenderer 等，`runs/p165-mixin-audit/`）；性能**不宣称收益**——HUD 场景差异在噪声内（`runs/p148-bench/`），80 盔甲架实体压力交错两轮慢约 13%（`runs/p157-stress-interleaved/`）。
- **门禁**：Java 25/25、`test_review_fixes` 73/73、`check_hashes` 905/905、`verify_evidence` passed；CI push 触发已验证（最近 `build` success，见 Actions）。
- 详情：[总验收快照](runs/p125-final-acceptance/README.md)、[FINAL-STATUS](docs/FINAL-STATUS.md)、[使用说明](docs/guide.md)。

## 现状（2026-10-18）

| 项目 | 状态 | 证据 |
|---|---|---|
| 环境锁定（JDK 21 / Gradle 9.8.1 / 无 JDK 17） | 已记录 | [docs/baseline.md](docs/baseline.md) |
| Retromod / CenturyBridge 精确提交、许可、工件 | 已锁定 | `manifests/upstream.lock.json` |
| 10 份 1.20.1 样本（5 Fabric + 5 Forge） | 已下载并校验 sha512 | `manifests/corpus.json` |
| 静态损伤分析（Fabric 1.21.1） | 10/10 已跑通，ironchests 52/52 源索引确认 | `runs/p0-fabric-target/plan.json`、[static-matrix](docs/generated/static-matrix-fabric-1.21.1.md) |
| CenturyBridge 引擎构建 | 可编译（需本地 1 个缺失类的 stub） | [docs/engine-selection.md](docs/engine-selection.md) |
| CenturyBridge 真实转换 ironchests | 已完成，`ok_partial`（28 tombstone） | `work/cb/out/ironchests/report.md` |
| 自研重映射器（保留方法体） | 6148 类服务端 jar 可用，修复 4 类真实缺陷 | `java/.../remap/`、[docs/baseline.md](docs/baseline.md) §7.3 |
| 1.21.1 专用服务端 | **BOOTED**：`Done (4.803s)`，正常停止 | `runs/p1-server-baseline/` |
| 转换件运行时 | **BOOTED + 世界加载**：`Done (1.134s)`，42 个模组 | `runs/p3-server-accesswidener/` |
| 第一条转换规则 + 桥 | `ItemPredicate.ANY` → 空谓词；入口点通过 | `rules/fabric-1.21.1/container.json`、[rules/README.md](rules/README.md) |
| 常量池种类修正 | 123 处 Methodref→InterfaceMethodref + 3 个 method handle（含 JiJ） | `java/.../rules/JarPatcher.java` |
| 规则数 | `container.json` 7 条 + `lithium.json` 调用点/2 条 Mixin 目标/1 条实现类替换 + `trashslot.json` 4 条 NBT/3 条 Balm 调用点 | `rules/fabric-1.21.1/` |
| 容器契约（服务端命令） | **通过**：放置 → 插入 5 钻石 → NBT `Items` → 重启读回 5 | `runs/p5-contract-*/` |
| 兼容档案 | ironchests `passed_within_scope`；lithium / trashslot `booted_within_scope`；all-three bundle `passed_within_scope` | [profiles/README.md](profiles/README.md)、`profiles/bundle-all-three__fabric-1.21.1.json` |
| 支持矩阵 | 10 份样本的静态结果 + 运行时阶段（未运行 ≠ 通过） | [docs/support-matrix.md](docs/support-matrix.md) |
| 签名适配规则 | BlockEntity NBT 1 参 → 2 参（带 WrapperLookup），持久化恢复 | `rules/fabric-1.21.1/container.json` §signatureAdaptations |
| **调用点签名适配** | `callSiteAdaptations` + javac 桥；lithium `class_14.method_59` 命中 2 处，`NoSuchMethodError` 消失 | [docs/baseline.md](docs/baseline.md) §7.17、`runs/p10-lithium-signature/` |
| **嵌套 jar 桥** | 桥按 jar 嵌入使用它的层级；synthetic nested jar + ironchests ResourcefulLib 回归，契约仍通过 | [docs/baseline.md](docs/baseline.md) §7.22、`runs/p18-nested-bridges/` |
| **BytecodeVerify** | 三个补丁 jar 顶层 + nested ResourcefulLib：650 + 141 classes，0 failures；P26 安全 Codec 构建 73 + 142；P29 client bridge 47，均 0 failures | [docs/baseline.md](docs/baseline.md) §7.23、§7.30、§7.40、`runs/p19-bytecode-verify/`、`runs/p28-codec-verify/`、`runs/p38-client-bv/` |
| **Mixin 注入目标提取** | 顶层 + nested `.mixins.json`；`method` 目标 + refmap + 构造器校验 + refmap `@At` + ordinal 提取；lithium 214/86/10/3、补丁件 209/84/0；ironchests nested 1/1 | [docs/baseline.md](docs/baseline.md) §7.24–7.25、§7.36–7.38、§7.50–7.51、`runs/p21-refmap/`、`runs/p22-cross-analyze/`、`runs/p34-at-targets/`、`runs/p35-at-refmap/`、`runs/p36-patched-at/`、`runs/p48-nested-mixins/`、`runs/p49-at-ordinal/` |
| **Mixin 目标描述符适配** | `mixinCallbackAdaptations`（append/replace + refmap）；lithium `ExplosionMixin` 与 POI storage 两处通过 | [docs/baseline.md](docs/baseline.md) §7.18、`runs/p11-lithium-explosion/` |
| **Mixin 实现类替换** | `mixinClassReplacements`；chunk access 移植到 1.21.1 `ChunkResult` API，lithium 到达 `Done` | [docs/baseline.md](docs/baseline.md) §7.19、`runs/p13-chunk-port/` |
| 第二样本 lithium | 转换并加载成功；显式降级 2 条 mixin；调用点/2 处 Mixin 目标/chunk access 已适配，**专用服务端 BOOTED**（`Done (4.772s)`），224-chunk 压力测试通过；无 lithium 玩法/客户端契约 | `runs/p6-lithium/`、`runs/p10-lithium-signature/`、`runs/p11-lithium-explosion/`、`runs/p13-chunk-port/`、`runs/p23-chunk-stress/`、`rules/fabric-1.21.1/lithium.json` |
| chunk 压力测试工具 | `tools/run_chunk_stress.py`：225 chunks + save/restart + 远角断言，`passed=true` | [docs/baseline.md](docs/baseline.md) §7.27、`runs/p24-chunk-stress-tool/` |
| 证据总校验 | `tools/verify_evidence.py`：22 tests + 7 组 verdict + P35/P36 at-target + profile + no tracked jars | [docs/baseline.md](docs/baseline.md) §7.41–7.42、`runs/p39-verify-evidence/`、`runs/p40-verify-extended/` |
| Codec dispatch 安全适配 | javac `CodecDispatch` 用 `MapCodec.of` 包装旧 Codec；契约 5/5；record-codec probe 与三样本同服 probe 均通过 | [docs/baseline.md](docs/baseline.md) §7.28–7.29、§7.39、§7.45、`runs/p26-codec-safe/`、`runs/p37-codec-probe/`、`runs/p43-all-three-codec/` |
| **lithium + ironchests 联合契约** | 同一实例两进程放置/插入/NBT/重启读回 5 钻石全部通过；P26 安全 CodecDispatch 版本也通过；三样本（+trashslot/Balm）同服及 225-chunk 压力也通过 | [docs/baseline.md](docs/baseline.md) §7.20、§7.29、§7.43–7.44、`runs/p14-lithium-ironchests/`、`runs/p27-combined-safe-codec/`、`runs/p41-all-three/`、`runs/p42-all-three-chunk/` |
| 第三样本 trashslot | 原生 Balm 21 + 初始化/网络载荷桥 + 4 个 NBT 桥，**专用服务端 BOOTED**（`Done (4.655s)`）；三个包 codec（含 5 钻石）往返通过；clientbound receiver 后续已在客户端执行（p29/p64） | `runs/p15-trashslot/`、`runs/p16-balm/`、`runs/p17-balm-net/`、`runs/p29-client-receiver/`、`runs/p32-trashslot-codec/`、`runs/p33-all-packets/`、`rules/fabric-1.21.1/trashslot.json` |
| 客户端首次运行（PCL） | 1.21.1 Fabric 客户端已装，五模组加载；RL 网络/Balm 客户端初始化/ironchests 模型桥后**到达主菜单**；Balm writer + lithium `VarInt` 桥后**进入单人世界并渲染**；背包 + TrashSlot 按钮已渲染、5 钻石可进背包；trash **移入/取回/clientbound/empty 均通过**（`p63`/`p64`/`p65`）；IronChests **模型 + 同步 NBT + 箱子 GUI（真实九宫格背景）+ 取放交互 + 关箱持久化/S2C** 均通过（`p66`–`p72`），修复流水线已入仓（`p71`）；lithium 玩法冒烟通过（`p73`，非完整评估）；双客户端 **服务端→客户端内容同步 + 访客取走→主机可见的往返均通过**（`p75`/`p76`；LAN 尝试的认证墙见 `p74`）；**双端关屏通过**（`p77`；`Screen.close()`，服务端菜单回落到 46 格）；**同箱双客户端操作总数守恒、无复制**（`p78`）；**同 tick 并发点击服务端只给一人、不复制**（`p79`/`p80`，干净重跑确认输家被纠正）；物理 ESC **通过**（`p83`；传送+新方块后按 ESC，双端回落 46 格；早前失败见 `p81`/`p82`）；lithium TPS 采样 20.03（`p84`，289 区块/60 秒）；empty-trash 真实按键需悬停、悬停后按键仍无效，尚未验证（`p85`/`p86`；provider 级见 `p65`）；扩模 6 个样本：5 阻断 / 1 仅启动（`p88`，见 [mod-expansion](docs/mod-expansion.md)） | `runs/p50-client/`、`runs/p51-client-bridge/`、`runs/p52-client-balm/`、`runs/p53-client-world/`、`runs/p54-client-lithium/`、`runs/p55-client-gui/`、`runs/p56-client-item/`、`runs/p57-trash-persist/`、`runs/p58-trash-click/`、`runs/p59-trash-send/`、`runs/p60-trash-return/`、`runs/p61-trash-clean-return/`、`runs/p63-trash-debug/`、`runs/p64-trash-s2c/`、`runs/p65-trash-empty/`、`runs/p66-ironchests-gui/`、`runs/p67-ironchests-gui-nbt/`、`runs/p68-ironchests-gui/`、`runs/p69-ironchests-interaction/`、`runs/p70-ironchests-persist/`、`runs/p71-rebuild-pipeline/`、`runs/p72-ironchests-nine-slice/`、`runs/p73-lithium-play/`、`runs/p74-two-client/`、`runs/p75-two-client-server/`、`runs/p76-two-client-move/`、`runs/p77-two-client-close/`、`runs/p78-two-client-race/`、`runs/p79-two-client-simultaneous/`、`runs/p80-two-client-clean/`、`runs/p81-esc-key/`、`runs/p82-esc-onuse/`、`runs/p83-esc-teleport/`、`runs/p84-lithium-tps/`、`runs/p85-empty-key/`、`runs/p86-empty-hover/`、`runs/p87-independent-test/`、`runs/p88-mod-expansion/`、[docs/mod-expansion](docs/mod-expansion.md)、[remaining-work](docs/remaining-work.md) |

## 交接

配套的本地 GUI 启动器（离线安装/启动原版与 Fabric，界面在浏览器里）见 [docs/launcher.md](docs/launcher.md)。
要发给不用 GitHub 的人：`python tools/build_portable.py` 打一个内置 Python 的免安装便携包，
见 [docs/distribution.md](docs/distribution.md) §2.5。

先读 [docs/handoff.md](docs/handoff.md)（一页版：能做什么、当前降级、下一步、复现命令）。发布/分发边界与步骤见 [docs/distribution.md](docs/distribution.md)。

## 复现

构建前提与干净目录复现见 [docs/build.md](docs/build.md)。

所有 Python 脚本只依赖标准库（本机 PowerShell/git 的 schannel TLS 不可用，Python 的 OpenSSL 可用）。

```powershell
# 1) 锁定上游提交与许可（GitHub API 限流，改用 atom feed + codeload）
python tools/lock_upstream.py

# 2) 下载 1.21.1/1.20.1 客户端 jar、intermediary 映射、Fabric API、Fabric Loader
python tools/fetch_target_env.py

# 3) 下载 10 份 1.20.1 样本（Modrinth，记录 sha256 与 sha512 校验）
python tools/fetch_corpus.py

# 4) 构建分析器（JDK 21 + Gradle 9.8.1）
$env:JAVA_HOME='...\.toolchain\jdk'
$env:GRADLE_USER_HOME='...\.toolchain\gradle-home'
cd java; gradle --no-daemon installDist; cd ..

# 5) 静态损伤分析
java\build\install\mcbridge1201\bin\mcbridge1201.bat analyze `
  --mods work/corpus `
  --client-jar work/target/client-1.21.1.jar --mappings work/target/intermediary-1.21.1-v2.jar `
  --source-client-jar work/target/client-1.20.1.jar --source-mappings work/target/intermediary-1.20.1-v2.jar `
  --source-api "work/target/fabric-api-0.92.12+1.20.1.jar" `
  --api "work/target/fabric-api-0.102.0+1.21.1.jar" --api work/target/fabric-loader-0.19.5.jar `
  --target 1.21.1 --target-loader fabric --out runs/p0-fabric-target/plan.json
```

CenturyBridge 转换见 [docs/engine-selection.md](docs/engine-selection.md) 的“真实尝试”一节；它需要本地编译上游引擎并生成 7 节分段。

已验证范围与阻塞项（客户端 GUI/网络/多人）见 [docs/remaining-work.md](docs/remaining-work.md) 和 [docs/progress.md](docs/progress.md)。

## 目录

```text
docs/            基线、引擎选择、限制、ADR、生成报表
java/            自研分析器（Gradle，ASM + Gson）
manifests/       corpus / environment / upstream 三个锁文件
tools/           抓取、校验、服务端运行、报告脚本
runs/            证据输出（plan.json、服务端日志）
work/            本地工作集：游戏 jar、样本、上游源码、实例（不入库）
third-party/     上游许可证副本与 NOTICE
patches/         对上游缺件的显式本地补丁（带说明，不是上游代码）
```

## 边界

- `work/` 下的游戏 jar、模组 jar、转换产物**只在本机**，不随仓库分发；对外只应分发工具、规则与 hash 清单。
- 静态分析只到 `ANALYZED` 阶段。`CLEAN_STATIC` 不代表能启动，更不代表玩法通过。
- 第三方作者自报（Retromod 的 26.2 工件、CenturyBridge 的 1.21.1 案例）与本仓库独立结果分开记录。

## License

MIT，见 [LICENSE](LICENSE)。第三方组件：CenturyBridge（MIT）、minecraft-launcher-lib（BSD-2，可选依赖）。
