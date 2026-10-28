# mcbridge1201（P0 研发仓库）

[![ci](https://github.com/SelYio666/mcbridge1201/actions/workflows/ci.yml/badge.svg)](https://github.com/SelYio666/mcbridge1201/actions/workflows/ci.yml)

> 新手先读：**[使用说明与教程](docs/guide.md)**（启动器 10 分钟上手、PCL 共用、模组迁移教程、FAQ）。

> 最新发布：**[v0.5.6](https://github.com/SelYio666/mcbridge1201/releases/tag/v0.5.6)**（一键安装到 PCL：图形面板/全版本选择；主工具 v0.5.4）。

Minecraft Java 1.20.1 模组跨版本兼容平台的第一阶段工作区。来源固定为 **1.20.1**，首个精确目标是 **Fabric 1.21.1**，同时抽样分析 Forge 1.20.1。

本仓库当前交付 P0 的事实与证据，以及 P1 的第一段运行时结果：环境锁定、上游引擎锁定、10 份真实样本、**自研静态损伤分析器**、**body-preserving 重映射器**、CenturyBridge 真实转换产物，和进世界/功能级证据。**只对 `runs/` 里有日志与截图支撑的模组声称通过**（如 EntityCulling、ImmediatelyFast 的移植），其余不宣称兼容。

## 当前状态（2026-10-23）

- **启动器**：离线安装/启动原版 + Fabric/Forge/NeoForge；下载源可选（自动/仅官方/镜像优先）+ 源健康缓存 + GUI 源检查；内嵌 Python 的便携包（v0.5.2）。
- **已验证进世界**：Fabric 1.21.1（全量安装 + EntityCulling 真生效）；ImmediatelyFast 1.21.1 batching 移植（HUD/物品/overlay 计数、Iris 1.8.1/1.8.14 + shader pack、专用服务器多人加入；`runs/p134`-`p150`）；**ImmediatelyFast 地图 atlas 恢复：p175 单人真实手持 filled_map 渲染；p177 两张地图分别落到 atlas tile 0/1 并与物品展示框地图同屏渲染；p181 动态更新（第二次上传）+ 正常退出清理，并修复退出时向已释放 NativeImage 写入的崩溃；p178 在 80 盔甲架压力下启用 VertexBuffer 动态上传 fast path（on 侧最高 76k 次 glBufferSubData，off/on 截图差 0.0087%，低于 off/off 对照，无 GL/mixin 错误）**（`runs/p175-map-atlas/`、`runs/p177-map-atlas-edge/`、`runs/p181-map-atlas-lifecycle/`、`runs/p178-vertex-upload/`）；NeoForge 21.1.264（AppleSkin / Farmer's Delight / Jade + **专用服务器客户端加入**，`runs/p161-neoforge-server/`；**带 Farmer's Delight 的服务端/客户端同模组加入**，`runs/p163-neoforge-fd-server/`）；Forge 1.20.1-47.4.28（AppleSkin / Farmer's Delight + **专用服务器客户端加入**，`runs/p159-forge-server/`；**带 Farmer's Delight 的同模组加入**，`runs/p164-forge-fd-server/`）；mrpack 真实 files 导入通过（`runs/p160-mrpack/`）。
- **未通过 / 未验证**：Sodium 1.20.1 转换探针为 `blocked_static`（missingClass=13、missingMember=15、descMismatch=16，`runs/p158-sodium-probe/`），需移植其渲染内核，本轮不做（p199 逐条定性 44 条：6 条为内嵌 Fabric API、7 条纯 id、7 条签名有明确写法、24 条卡在被换掉的即时模式顶点管线，见 [docs/sodium-plan.md](docs/sodium-plan.md)）；Iris 只验证了 ImmediatelyFast 的兼容分支（没有转换 Iris 本身）；ImmediatelyFast 端口 jar 仍有 **2 个 inert**，但它们是官方 1.21.1 已删除的 1.20.4 遗留类（BufferBuilder/FontManager；ChatHud/MinecraftClient/BufferRenderer 已在 p166–p168 重登记，两个 map mixin 在 p175 恢复，VertexBuffer 在 p178 启用；对照见 `runs/p180-inert-closure/`）；地图 atlas 已验证单人手持 + 两张地图（tile 0/1）+ 物品展示框 + p181 动态更新+正常退出清理；atlas 满 1024 张未测；性能**不宣称收益**——HUD 场景差异在噪声内（`runs/p148-bench/`），80 盔甲架实体压力交错两轮慢约 13%（`runs/p157-stress-interleaved/`）。
- **门禁**：Java 25/25、`test_review_fixes` 共 130 项（本次 **130/130**）、`check_hashes` 1269/1269、`verify_evidence` passed（新增 `text_encoding` 直接项）；CI push 触发已验证（最近 `build` success，见 Actions）。
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
| 客户端首次运行（PCL） | 1.21.1 Fabric 客户端已装，五模组加载；RL 网络/Balm 客户端初始化/ironchests 模型桥后**到达主菜单**；Balm writer + lithium `VarInt` 桥后**进入单人世界并渲染**；背包 + TrashSlot 按钮已渲染、5 钻石可进背包；trash **移入/取回/clientbound/empty 均通过**（`p63`/`p64`/`p65`）；IronChests **模型 + 同步 NBT + 箱子 GUI（真实九宫格背景）+ 取放交互 + 关箱持久化/S2C** 均通过（`p66`–`p72`），修复流水线已入仓（`p71`）；lithium 玩法冒烟通过（`p73`，非完整评估）；双客户端 **服务端→客户端内容同步 + 访客取走→主机可见的往返均通过**（`p75`/`p76`；LAN 尝试的认证墙见 `p74`）；**双端关屏通过**（`p77`；`Screen.close()`，服务端菜单回落到 46 格）；**同箱双客户端操作总数守恒、无复制**（`p78`）；**同 tick 并发点击服务端只给一人、不复制**（`p79`/`p80`，干净重跑确认输家被纠正）；物理 ESC **通过**（`p83`；传送+新方块后按 ESC，双端回落 46 格；早前失败见 `p81`/`p82`）；lithium TPS 采样 20.03（`p84`，289 区块/60 秒）；empty-trash 真实 Delete 键已通过（`p183`；`p85`/`p86` 的按键失败根因是注入漏 `KEYEVENTF_EXTENDEDKEY`，provider 级见 `p65`）；Shift+Delete 跨槽删除（两叠 5+3）通过（`p184`）；空 cursor 右键取 1 留 4 通过（`p185`）；扩模 6 个样本：5 阻断 / 1 仅启动（`p88`，见 [mod-expansion](docs/mod-expansion.md)） | `runs/p50-client/`、`runs/p51-client-bridge/`、`runs/p52-client-balm/`、`runs/p53-client-world/`、`runs/p54-client-lithium/`、`runs/p55-client-gui/`、`runs/p56-client-item/`、`runs/p57-trash-persist/`、`runs/p58-trash-click/`、`runs/p59-trash-send/`、`runs/p60-trash-return/`、`runs/p61-trash-clean-return/`、`runs/p63-trash-debug/`、`runs/p64-trash-s2c/`、`runs/p65-trash-empty/`、`runs/p66-ironchests-gui/`、`runs/p67-ironchests-gui-nbt/`、`runs/p68-ironchests-gui/`、`runs/p69-ironchests-interaction/`、`runs/p70-ironchests-persist/`、`runs/p71-rebuild-pipeline/`、`runs/p72-ironchests-nine-slice/`、`runs/p73-lithium-play/`、`runs/p74-two-client/`、`runs/p75-two-client-server/`、`runs/p76-two-client-move/`、`runs/p77-two-client-close/`、`runs/p78-two-client-race/`、`runs/p79-two-client-simultaneous/`、`runs/p80-two-client-clean/`、`runs/p81-esc-key/`、`runs/p82-esc-onuse/`、`runs/p83-esc-teleport/`、`runs/p84-lithium-tps/`、`runs/p85-empty-key/`、`runs/p86-empty-hover/`、`runs/p87-independent-test/`、`runs/p88-mod-expansion/`、`runs/p183-trash-key/`、`runs/p184-trash-delete-all/`、`runs/p185-trash-undelete-right/`、[docs/mod-expansion](docs/mod-expansion.md)、[remaining-work](docs/remaining-work.md) |
| **ShulkerBoxTooltip 网格预览（部分）** | p186：client-side `ContainerComponent` + `ComponentPreviewProvider` + grid renderer 的 t2/t4 桥，tooltip 出现预览框与 `Diamond ×5`；网格 item icon 仍缺、真实 server item 仍空 | `runs/p186-shulker-grid-client-item/` |
| **一键安装到 PCL（v0.5.5）** | 图形面板 `mcbridge-pcl-panel.zip` + 免 Python `mcbridge-pcl-setup.zip`；版本下拉/搜索/进度/PCL2 自动检测；`from_source_install` 支持 release/snapshot/old_* / all / latest-snapshot；PCL2 2.13.1.1 实测 | `share/pcl-onclick/`、`runs/p137-pcl2-onclick/` |

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

## p193 Shulker grid 残余 增量验收（2026-10-26，正常 UTF-8）

- 多物品网格（3 钻 + 2 绿宝石）、FULL 预览、真实 tooltip 路径、服务端 box（2 钻 + 4 绿宝石）四项全过；`runs/p193-shulker-grid-residual/`（`result.json` 4/4 true、`client.log`/`server.log`、`after-full/after-server/after-compact.png`）。
- 门禁：`test_review_fixes` 95/95、`check_hashes` 1194/1194、`verify_evidence` passed；无新 release（v0.5.6）。
- 边界：输入是 GLFW 回调级注入（非 OS 光标）；FULL 依赖 `preview.alwaysOn=true` + 预览键；服务端 box 只验证 dedicated `/item replace container.10`；27 格全满未测。
## p194 第三 atlas / 跨 atlas 同帧 增量验收（2026-10-26，正常 UTF-8）

- 2050 map ids：atlas 0/1 各 1024 张，2049/2050 创建并填充 atlas 2；`map-atlas create id=2` 一次、`assign map=2049 packed=131072`、`assign map=2050 packed=131328`、`bind map=map/2049 ... map_atlas/2`；HUD 同帧画 map 1/1025/2049，atlas1/atlas2 像素检查 0；退出 `map-atlas clear atlases=3`。证据 `runs/p194-atlas-third/`。
- 门禁：`test_review_fixes` 96/96、`check_hashes` 1206/1206、`verify_evidence` passed；无新 release（v0.5.6）。
- 边界：真实服务端 1024+ 张地图端到端未测；HUD 四边形在原点（与 p188 同），三 atlas 并排视觉未截；3×4096² NativeImage ≈192 MB。
## p195 v0.5.6 交付验证 增量（2026-10-26，正常 UTF-8）

- portable：`dist/mcbridge-launcher-0.5.6.zip` 在全新 `work/tmp/p195-portable` 根目录跑 `test_portable.py --version 1.21.1`，deps + `/api/status` + `/guide` 全过（`RESULT: OK`）；`runs/p195-delivery-validation/portable-test.log`。
- panel：同源 `tools/pcl_panel.py` 打开面板，103 个正式版、PCL 目录默认值正常（`panel-smoke.png`）；PCL2 本机路径不存在，完整点击安装 E2E 未做；面板资产只下载到 3,361,813/12,361,982 bytes。
- 门禁：`test_review_fixes` 97/97、`check_hashes` 1212/1212、`verify_evidence` passed；无新 release（v0.5.6）。
- 边界：PCL2 缺失、panel 资产不完整、干净/离线主机未验证。
## p196 Shulker grid 27 格全满 增量（2026-10-26，正常 UTF-8）

- 27 种不同物品（`GRID_DRAWITEMS items=27`、`GRID_SETRENDER inv=27`）、FULL、server box、真实 tooltip 路径四项全过；`runs/p196-shulker-grid27/`（`after-full/after-server/after-compact.png`）。
- 预览键重绑定当轮**未生效**：p196 把 `previewKey` 写进了 `preview` 分类（未知字段被忽略），F 又触发原版交换副手；p197 已用 javap + 运行时配置回读更正（mod 读的是 `controls.previewKey/fullPreviewKey`）。
- 门禁：`test_review_fixes` 98/98、`check_hashes` 1231/1231、`verify_evidence` passed；无新 release（v0.5.6）。
## p197 Shulker 预览键重绑定 增量（2026-10-26，正常 UTF-8）

- **更正 p196 的误判**：`javap` 证明 `ShulkerBoxTooltipClient.isKeyPressed` 取 `config.controls.<key>.get().getCode()` 再调 `InputConstants.isKeyDown`；默认值是 previewKey=340(LEFT_ALT)、fullPreviewKey=342(RIGHT_SHIFT)。p196 写错了分类，等于没生效。
- 正确用法：`controls.previewKey=key.keyboard.j(74)`、`controls.fullPreviewKey=key.keyboard.k(75)`、`alwaysOn=false`；J/K 无原版绑定，避免 F 的交换副手把悬停物品换走。
- 单屏（生存背包 `class_490`）+ 服务端 `/item replace` 放的 27 种物品 shulker box，mod 自身状态机走完 `NO_PREVIEW → COMPACT(J) → FULL(J+K) → COMPACT(松 K) → NO_PREVIEW(松 J)`；`result.json` 7/7 true；证据 `runs/p197-preview-key/`（`after-full.png`、`after-compact.png`、`client.log`、`P197_CONFIG`/`P197_KEYS`/`P197_TYPE`）。
- 边界：键状态仍在 `InputConstants.isKeyDown` 轮询边界注入（p191/p193 同一约定），未做 OS 级物理按键；27 格不同 NBT/附魔仍未测；无新 release（无 mod 改动，v0.5.6）。
- 门禁：`test_review_fixes` 99/99、`check_hashes` 1254/1254、`verify_evidence` passed。

## p198 文档双重编码修复 + 编码守卫 增量（2026-10-28）

- 修复 p195 期间被“UTF-8 当 cp936 读、再存 UTF-8”写坏的三个文档：`README.md`、`docs/FINAL-STATUS.md`、`runs/p125-final-acceptance/README.md`。行数不变（151/267/286），损坏前 892 条 finding、修复后 0 条；证据 `runs/p198-text-encoding/`。
- **如实标注修复性质**：受损 13385 个字符里只有 2599 个（19.4%）是字节级可逆还原，其余 10786 个（80.6%）所在的字节已被损坏器写成 `?`，是按同文件的完好句子、路径/数字骨架与 `runs/` 证据重写的；行级是 386 行未动、12 行整行还原、306 行重写。提交说明里同样分开写，不把重写说成还原。
- 新增 `tools/check_text_encoding.py`（6 条规则：`bad-utf8`/`fffd`/`pua`/`signature`/`question`/`double-enc`），并作为 `text_encoding` 直接项接进 `tools/verify_evidence.py`（不是只靠回归套件间接覆盖，避免 CLI 未构建时连带 skip）。
- 回归 6 条（`test_review_fixes.py`）：守卫存在、跟踪文档全绿、干净样本通过、按 p195 同法造的损坏样本必须报错且给出明细、豁免表只指向真实文档。
- 豁免机制：引用乱码当例子的 p198 报告放在 `EXEMPT` 表里（带理由），只放行四条内容规则，`bad-utf8`/`fffd` 照查，且每次都打印抑制了几条。
- 门禁：`test_review_fixes` 105/105、`check_hashes` 1270/1270、`verify_evidence` passed；无新 release（无 mod 改动，v0.5.6）。
- 边界：重写段落是语义等价重述，不是原作者逐字原文；守卫只扫 `*.md`；p195 的写入路径（哪个工具写坏的）未追溯。

## p200 atlas 逐 id 落点 + 三张并排 增量（2026-10-28，正常 UTF-8）

- 2050 个 map id **逐个**校验，不是抽样：每个 id 把自己的 12 位写进 tile 第 0 行（最亮/最暗调色板色当 1/0），走公共 update+draw 后从**该 id 报告出来的槽位**读回 → `mapping-mismatch=0 pixel-verified=2050 pixel-mismatch=0`。p194 的盲点是 2050 个 id 共用同一个 MapState，槽位错位时"像素等于地图颜色"照样成立。
- 三张 4096² atlas 首次**同屏并排**：map 1/1025/2049 各持自己的 MapState（共用会让后写的颜色刷掉另外两格——第一版就是三块全灰），GUI `8,8 / 144,8 / 280,8` 画出；截图实测三块 256×256（=128×guiScale 2）、间距 272、窗口偏移 `[8,31]` 三块一致（`layout-check.json`）。
- 192 MiB 是账不是估：每张图读 `(4095,4095)` 成功、读 `(4096,4096)` 抛异常，证明缓冲恰好 4096²，×4×3 = 201,326,592 字节；进程工作集分配前 1556.0 → 后 2016.9 MB（+460.9），重复三次 +460.9/+548.1/+486.5、峰值 2192.0–2247.3。**显存未测**，不写"约 192 MB 显存"。
- 门禁：`test_review_fixes` 124/124（新增 16 条，从日志与截图**重算**报告里每个数字）、`check_hashes` 1289/1289、`verify_evidence` passed；无新 release（无 mod 改动，v0.5.6）。
- 顺手修掉第二类文档损伤：`docs/remaining-work.md` 有两处 `\t`/`\r` 被当成转义写成控制字符（`\tools/…` 变 TAB+`ools/…`、`(runs/…` 变 `(CRuns/…`），已修回原文；守卫加 `control-tab`/`control-cr` 两条规则（围栏内 TAB 不算）+ 3 条回归。
- 边界：真实专用服务器下发 1024+ 张地图未做；只用到 2050 格（未压满 3072 看第四张 atlas）；VRAM 未测。证据 `runs/p200-atlas-layout/`。

## p201 哈希清单在干净 clone 里可验证 增量（2026-10-28，正常 UTF-8）

- 先 clone 自己跑门禁，才发现 p200 那版的清单只在作者机上成立：clone 得到 `ok=646 mismatch=623 missing=20`，本机却打印 1289/1289。
- 原因一：`core.autocrlf=true` 且无 `.gitattributes`——blob 存 LF、检出写 CRLF，而哈希取自 1224 LF / 422 CRLF / 264 混合的工作区。原因二：20 条清单指向 gitignored 的 `work/` 构建产物，别人clone 出来必然 missing。
- 修：`.gitattributes` 钉 `* -text`；`git checkout-index -a -f` 把工作区归一到 blob 字节（纯行尾差异，无内容变化）；删 20 条 `work/` 条目；`hash_evidence.py` 改用 `git ls-files -z`（否则非 ASCII 路径被引号转义，3 个已跟踪的 `share/` 文件会误判未跟踪）。
- 现在 clone：`ok=1269 mismatch=0 missing=0`、`audit_eol` 1269/1269 可复现、227 个 md 全绿；回归 6 条（`test_eol_determinism`），允许未提交改动漂移。
- 边界：clone 里 `test_review_fixes` **125/125**（`ISSUE-02` 组 skip，需已构建 CLI），作者机 130/130；只在 Windows / Git for Windows 实跑。证据 `runs/p201-eol-determinism/`。
