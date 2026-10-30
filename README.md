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
- **门禁**：Java 25/25、`test_review_fixes` 共 227 项（本次 **227/227**）、`check_hashes` **1338/1338**、`verify_evidence` passed（含 `text_encoding` 直接项）；CI push 触发已验证（最近 `build` success，见 Actions）。
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
| **Cloth Config 配置界面（p210）** | AppleSkin 的 1.20.1 JiJ `cloth-config-fabric-11.1.136` 在 1.21.1 上**能开、能画 13 行、点得动**：`rows=13 kinds={BooleanToggleBuilder$1=9, …}`、`client_errors=[]`，真实点击把第一条开关由 ON 翻成 OFF；6 处装饰降级为 no-op，`GlobalizedClothConfigScreen` 未覆盖 | `runs/p210-cloth-config/`、`rules/fabric-1.21.1/cloth-config.json`、`rules/fabric-1.21.1/cloth-config-render.json` |

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

## p202 OS 光标级悬停 + 27 格异质 NBT 增量（2026-10-28，正常 UTF-8）

- **悬停这次是窗口系统送进来的**：探针不写任何鼠标字段（两个 accessor 只有 getter），由外部进程把真实光标移到探针公布的窗口坐标；`P202_HOVER_OK index=10 keysSent=false` 时 `glfwGetCursorPos` / 回调原始字段 / `Mouse.getX/getY` / 探针独立算的目标值四者同为 `686,378`。
- **纠正一条继承下来的错误结论**：p191/p193/p197 记的"这台机器收不到 OS 光标移动"是错的。控制组只做 `SetCursorPos`（不做 SendInput）也能悬停 —— 真正原因是游戏窗口没在最上层，光标底下压着的是终端。`_focus()` 现在 `SetWindowPos(HWND_TOPMOST)` 并在每次移动后记 `WindowFromPoint`。
- **27 格 27 套 NBT**：服务端下发不同 item id / 数量 / 自定义名 + lore / 附魔 / custom_model_data 的混搭；客户端读出 `stacks=27 distinctComponents=27 distinctItems=27 distinctNames=27`，27 个不同 payload 到达 `drawItem`，截图按自相关测出的 36 px 周期（= 18×guiScale 2）定位后 27 格互不相同。
- **返工两次也记下来**：第一次服务端回 `Unknown item component 'minecraft:'`（外层组件键被加了引号），为此写了不需要客户端的 `check_snbt.py`；截图校验器前两版分别栽在"只 hash 前 8 字节"和"用边框环当对齐判据"。
- **门禁**：`test_review_fixes` **162/162**（新增 32 条，从日志/截图/PNG 头**重算**）、`check_hashes` **1301/1301**、`verify_evidence` passed、228 个 md 全绿；无新 release（v0.5.6，只加探针）。

## p203 两个客户端同一服务端 tick 并发操作垃圾桶增量（2026-10-28，正常 UTF-8）

- **"并发"定义在有权威 tick 的那一侧**：判据放在专用服务端，探针自己数 tick，并在 `TrashHelper.setTrashItem`（玩家持久化 NBT 的唯一写入口）打戳；两个不同玩家的写入带**同一个 tick 号**才算并发。两个客户端先在各自线程上自旋到**同一个 epoch-ms 时刻**再开火，`P203_FIRE driftMs=0`。
- **结果**：`P203_SET side=SERVER thread=Server thread tick=819 … user=GridUser stack=empty` 与 `… TrashB stack=minecraft:diamondx3` 相差 4 ms、同一 tick；两条 serverbound 消息（`MessageDeleteFromSlot`、`MessageTrashSlotClick`）也在 tick 819。两种操作故意不同（A 清空 5→empty，B 取 1 4→3），串台就没法蒙混；B 的鼠标读回 `carried=minecraft:diamondx1`。
- **一次踩空并记下来**：先混入 `ServerPlayNetworkHandler.onCustomPayload`，`mixin.debug` 确认注入成功，正式跑却一行都没拦到（Balm 桥的 serverbound 消息不走这条派发）；于是把戳挪到状态写入点。第二次是分析器取错写点（取到登录重置那两条 `empty`），改成以开火时刻开窗。
- **门禁**：`test_review_fixes` **188/188**（新增 26 条，从 `server.log`/`result.json`/两份客户端日志**重算**）、`check_hashes` **1324/1324**、`verify_evidence` passed、228 个 md 全绿；无新 release（v0.5.6，只加探针）。

## p208 交付验证：干净环境 + 跨平台审计（2026-10-28，正常 UTF-8）

- **"干净环境"要真的剥掉环境**：`tools/test_portable.py` 是 `dict(os.environ, ...)`，继承调用者环境，只能证明"在造它的机器上能跑"。`run_clean_host.py` 用 `PATH=C://Windows//System32;C://Windows`（无 Python、无 JDK）、`HOME/USERPROFILE/TEMP/APPDATA/LOCALAPPDATA` 全指向新建空目录，跑了 **8/8**（照发原件、叠加当前源码各一份）。
- **先证明剥干净了**：同一环境里 `shutil.which("python")` 与 `which("java")` 都是 `None`；包的 `sys.prefix` 落在解压目录内；注入 `PYTHONHOME/PYTHONPATH` 后 prefix 不变（嵌入式 Python 的 `._pth` 生效）。干净环境里 `/api/status` 返回 `200` + `versions: 0` + `java: null` + `java_error`，即"缺 JDK 是错误字段而不是崩溃"。
- **交付路径的四个真缺陷**（修前 2/6，修后 6/6，`probe_behaviour.py` 同一脚本跑出两份 JSON）：`default_root()` 在 `APPDATA` 未设置时用相对路径 `.minecraft`，会认领启动器的工作目录；POSIX 下 `JAVA_HOME` 因只找 `bin/java.exe` 被无视；macOS 走 `xdg-open`（通常没有）且无异常保护；一个从未引用的 `C://Program Files\Java\...` 常量。
- **打包脚本的假成功**：`vendor_deps()` 跳过 import 不到的依赖，调用处不接返回值，于是零依赖也 `done`、退出码 0。新增 `require_vendored`：缺 `minecraft_launcher_lib` 直接 `rc=1` 拒包（`--allow-missing-deps` 是显式开关）。
- **跨平台只做审计，不假装跑过**：WSL 被本机安全策略拦住（`wsl.exe` 在 Program Blacklist），Linux 没有执行。静态命中 28→22、未保护 24→4（剩余 4 条是便携包按构造的 Windows-only 部分）；POSIX 模拟下交付模块 **4/4** 全部可导入。
- **门禁**：`test_review_fixes` **227/227**（新增 39 条，从四份 JSON 与两份日志重算）、`check_hashes` **1338/1338**、`verify_evidence` passed；无新 release（v0.5.6 不变）。
- 边界：**同一台机器、不同环境**（不是另一台电脑）；没有 POSIX 内核参与；便携包按构造 Windows-only；`install_jvm_runtime` 的下载未跑；完整重打包因本机缺依赖未做（改用的是叠加源码）。
- 边界：四客户端及以上、同一玩家的同 tick 两次操作、跨机器真实延迟均未测。
- 边界：单机单显示器；FULL 仍需在轮询边界伪造 J/K（悬停本身不需要）；未测嵌套潜影盒与逐格自定义模型。

## p204 真实滚轮 + 真实键盘打进 Mod Menu（2026-10-28，正常 UTF-8）

- **p104 那句"这台机器收不到滚轮"是错的**：当时窗口没在最上层，光标底下压着终端（同一个根因 p202 已经纠正过）。这次用 `SetWindowPos(HWND_TOPMOST)` 抬起窗口、每次移动都记 `underIsGame`，九格滚轮在 `Mouse.method_1598`（GLFW 回调落地处）留下九条 `dy=-1.0`。
- **滚动量不是探针写的**：探针只有 getter（`method_25341`/`method_25331`/`method_25396`/`field_22741`/四个控件矩形/`method_1882`），`method_60321` 在源码里一次都没出现（测试会去源码里找，找到就红）。列表走的是原版 `scroll -= amount * itemHeight/2`。
- **阶梯正好对上原版算术**：`itemHeight=36` → 一格 18，实测 `18/36/54/72/90/108/126/144`，第九格被 `clamp(0,max)` 夹到 **147**。
- **两个对照**：窗口外滚 9 格 → **0 事件、列表不动**；窗口内右侧面板滚 9 格 → 事件到了（`-1` 和 `-8` 两条，合计 −9）、**列表不动**。说明位置命中测试在起作用，不是"窗口收到滚轮就全局滚"。
- **键盘**：真实左键点搜索框（`searchFocused=true`）后 `SendInput` 送 `m/e/n/u`，`chars=4`、`text="menu"`、条目 **11→1**、`max` 147→0。键事件是 `code=-1`（`VK_PACKET`），字符从 char 回调进——所以"按键数"不能当证据。
- **Cloth Config 半条当时关不了，p210 已关**：环境里只有 **1.20.1 的 JiJ**（`cloth-config-fabric-11.1.136`），`ConfigBuilderImpl.<init>` 一碰 `class_437.field_44669` 就 `NoSuchFieldError`；Mod Menu 初始化时替每个模组问配置界面，`trashslot`/`fallingtree`/`shulkerboxtooltip`/`appleskin` 四家全炸。当时的结论是"打不开"，栈在 `client.log` 里；p210 把这份 JiJ 抽出来打到 1.21.1 再塞回去，界面现在能开、能画 13 行、点得动（见下文 p210 一节）。
- **顺手纠正 p94 的一句话**：它的截图里列表其实是全黑的，p204 四张截图也一样——列表行不画、滚动条画。视觉校验因此做在**滚动条**上（控件自己按滚动量算出来的）：一格位移预测 `18/147×(514−328)=23`、实测 **22**；满格预测 186、实测 **184**；过滤后不画滑杆。
- **门禁**：`test_review_fixes` **260/260**（新增 33 条，从 `client.log`/`harness.log`/两份 `result.json`/`scroll-check.json` 重算）、`check_hashes` 见下、`verify_evidence` passed；无新 release（v0.5.6，只加探针）。
- 边界：单机单显示器；只测 Mod Menu 的列表与搜索框；方向键/PageDown 未测（`KEYEVENTF_UNICODE` 只能送字符）；列表行不画是独立缺陷，本轮没修也没假装它不存在；两次运行。

## p205 修掉 Mod Menu 列表行不画（2026-10-28，正常 UTF-8）

p204 把「列表全黑」记成独立缺陷并明说没修；这一轮修掉。

- **根因是参数顺序**，不是缺资源也不是绘制被裁掉：桥调用 `Entry.render` 时传的是
  `(ctx, index, left, top, ...)`，而原版的参数是 `(ctx, index, y, x, ...)`。行底色是桥自己用
  `fill(left, top, ...)` 画的，坐标没错，所以现象是「黑底上有行、行里没东西」。
- **三处独立证据**：`class_350.method_44397` 的字节码（`iload 7` 先当 y、`iload 6` 当 x）、
  `ModListEntry.method_25343` 的字节码（`iload 4` 加偏移当 x、`iload 3` 当 y）、修前清单里
  列表区**零**亮像素。
- **顺手对齐原版其余口径**：行宽取 `getRowWidth()`（ModListWidget 是 **294**，不是
  `widgetWidth - 8`）、行高 `itemHeight - 4`、可见性对 `getY()`/`getBottom()`、hovered 用
  `getEntryAtPosition`、先 `Entry.drawBorder` 再 `Entry.render`。
- **匹配对照**：同一套模组、同一窗口（1280×720 / guiScale 2）、同一光标点，只换 `modmenu.jar`。
  旧桥列表区亮像素 **0**、彩色像素 **0**、图标条带 **0**；新桥 **11147 / 20211 / 6 条**，
  两格滚轮后行**整体上移 36 设备像素**（`scroll 0→18` × scale 2，互相关最优点正是 −36）。
- **顺带修了一个启动器缺陷**：`mclaunch.build_command` 的 `extra_jvm` 只有形参、从没进命令行
  （第一次跑就是这么变成"以为开了调试其实没开"的）。两条组装路径都补上，回归里直接断言
  「标志紧跟 `-Xmx`」。
- **调试行**：`-Dmcbridge.listrender.debug=true` 时打印一次
  `P205_LIST class=ModListWidget count=11 left=6 rowWidth=294 itemHeight=36 rows=67..324`；默认关，
  发布 jar 不打印。
- **门禁**：`test_review_fixes` **287/287**（新增 27 条，全部从 `rows-check.json`、两份
  `result.json`、`build.log` 与桥源码重算）、`check_hashes` 见下、`verify_evidence` passed；
  无新 release（v0.5.6，只改桥）。
- 边界：单机单显示器、guiScale 2；只验证模组列表；纹理背景没有恢复（仍是平色带），选中高亮
  （`method_44398`）没画，描述面板这一轮 `count=0` 没验证；Cloth 配置界面这一轮还打不开（p204 的栈，p210 已解决）。

## p206 选中行高亮（2026-10-29，正常 UTF-8）

p205 修好行渲染时留下两条尾巴，这条收掉一条、把另一条查到底。

- **原版的"选中"是一条 1 px 描边**：`method_44398` 先按 `hasFocus() ? -1 : -8355712` 铺一条上下各溢出 2 px 的条，再用
  `-16777216` 铺一层内缩 1 px 的黑芯。桥照字节码复刻（redirect 只换被替换方法的方法体，`method_44398` 仍是 protected，调用不到）。
- **额外加了一层半透明底**（聚焦 `0x40FFFFFF` / 未聚焦 `0x24FFFFFF`）：只有 1 px 白边压在近黑行底上根本看不出来——这是
  **有意偏离原版**，代码注释与本段落都写了。
- **匹配对照**：同一客户端/11 个模组/1280×720 guiScale 2/同一个光标点 `(632,626)`/同样真实左键点第 3 行，只换 jar。
  p205 的 jar：变化 **92** 像素、**0 条带**；本轮 jar：**47602** 像素，**多一条** `378..463`（86 px 高，预测 72）在点中的行，
  **少一条** `165..244` 在第 0 行。选中 `0 → 3`、列表 `focused false → true`。
- **判据不看屏幕外的说法**：`verify_rows.py` 对有符号差分（变亮/变暗分开）按行计数、超过行宽 40% 合并成条带，10 项全过。
- **描述面板正文是空的，原因不是"没测"**：`DescriptionListWidget.method_48579` 被整段替换成一次 `renderList(...)`，
  而被换掉的方法体前 1397 个字节码正是**建行**（24 处 `DescriptionEntry`，从 `getSelectedEntry()` + 换行后的描述文本逐行塞），
  后面才是 17 处 tombstone 的 1.20.1 `BufferBuilder` 管线——**副作用与崩溃同处一体**。于是 `count` 每帧都是 0，面板只剩
  ModsScreen 自己画的图标/名字/两个按钮。字节码在 `runs/p206-modmenu-select/bytecode/`；**本轮不修**，因为它要么把那段建行逻辑
  按 1.21.1 重写，要么只替换尾部 tombstone，两条都不是一行改动。
- **顺手加了置顶重试**：第一次跑撞上 `underIsGame=False`（系统忽略了 `SetWindowPos`），`run.py` 现在重试三次并逐次记录，三次都
  失败才退出——不是"重试到通过"。
- **门禁**：`test_review_fixes` **312/312**（+25 条，全部从 `highlight-check.json`、两份 `result.json`、桥源码、两份字节码导出与
  `run.py` 重算）、`check_hashes` 见提交说明、`verify_evidence` passed；无新 release（v0.5.6，只改桥）。
- 边界：单机单显示器、guiScale 2；只点第 3 行，未测键盘选择与多行框选；截图相对客户区有 +8 px 竖直偏差（判据用相对间距校验）；
  描述面板仍是空的。

## p207 描述面板（2026-10-29，正常 UTF-8）

p206 把「面板为什么是全空」查到底但没修；这一轮修掉了。

- **新能力 `keepPrefixBeforeTombstones`**：redirect 不再只能整段替换。`JarPatcher.keepPrefixThenCall()`
  从方法头找到第一条引用 tombstone 桩的指令，再从它往前找**块入口 label**（优先取被跳转/异常表引用的那个），
  保留之前的一切、只把之后换成 `INVOKESTATIC bridge` + `RETURN`。切点取错不是报错而是运行期 `VerifyError`，
  所以三种不安全的切法**抛异常**：保留段跳进被替换的尾部、保留段仍引用 tombstone、被丢的尾部在写本类字段
  （后者正是 p206 那个缺陷的另一种形状——丢状态变化）。找不到 tombstone 也拒绝，不静默算成功。
- **第一次实现是错的，被产物自己抓出来**：取「最近的 label」切在 1402（块内部的行号 label），产物尾部残留了
  `class_289.method_1348()` 与一次 `astore 6`；改成优先取被引用的 label，切点回到 1397，残留消失。
- **规则拆成两条**：`modmenu.description.render-tail`（`method_25394`，转换后的 jar 上的老名字）与
  `modmenu.description.render-tail-renamed`（`method_48579`，改名后的入口），都带 `keepPrefixBeforeTombstones: true`；
  一个 jar 最多命中一条（`build.log` 里是 `applied 1 time(s)`）。
- **顺手修掉一个真 bug**：面板一直画在 `x=0`。Mod Menu 用 1.20.1 的 `setLeftPos` 定位，1.21.1 删了它，
  `LegacyParentWidget` 复刻成写 `field_19088`，却从没同步 `ClickableWidget.x`，于是 `getX()` 返回 0——不止画错位置，
  **面板区域里所有点击与滚轮都落到了 ModListWidget 上**。修法两头：`method_25333` 补一次 `method_46421(left)`，
  桥优先读 legacy 四字段（`field_19088/19087/19085/19086`），没有才退回 1.21.1 的访问器（`fieldOrNull` 让"没有"是正常答案）。
- **面板画成一块底**（`PANEL_BACKDROP = 0x80000000`），行条带只在 `if (!panel)` 时画——否则正文会变成斑马纹。
  补了 `drawScrollBar()`（右内缩 2 px、宽 6 px，平色），**只在 `maxScroll > 0` 时画**。
- **匹配对照**：同一客户端/11 个模组/1280×720 guiScale 2/同一光标点 `(632,626)`/同样真实左键点第 3 行，只换 jar。
  p206 的 jar：`count=0`、`box=0,108`、`firstEntry=none`、面板 1 条带 204 px；本轮 jar：`count=13`、`box=328,108`、
  `legacy=true getX=328`、`firstEntry=…DescriptionEntry`、7 条带 2920 px。两次都选中第 3 行，ModListWidget 几何未变。
- **字节码**：产物 `method_48579` 550 行 javap，仍有 `method_25396` 与 24 处 `DescriptionEntry`（建行活着），
  **0 处 `Tombstones`**，尾部只剩 `renderDescription` + `return`；被切的方法体与 p206 记录逐行相同（843 行是 846 行的前缀）。
  相对 p206 的 jar **只有 3 个 class 变**：`DescriptionListWidget` 9045→13335、`ModMenuListRenderBridge` 7278→9275、
  `LegacyParentWidget` 790→824。
- **门禁**：`test_review_fixes` **346/346**（+34 条，全部从 `description-check.json`、两份 `result.json`、`build.log`、
  桥/`LegacyParentWidget`/`JarPatcher`/规则文件与新增的 Java 回归测试重算）、`check_hashes` 见提交说明、`verify_evidence` passed；
  无新 release（v0.5.6，只改桥与 patcher）。
- 边界：只点第 3 行、一种描述长度；**滚动条分支本轮未被执行**（`maxScroll=0`，无描述长到需要滚动），
  `verify_description.py` 把它如实打印成「未绘制」，没有算成一条通过的检查；面板底与滚动条是平色，原版贴图 sprite 未复刻；
  `legacy=true` 只对转换来的 1.20.1 子类成立。

## p209 描述面板的滚轮与滚动条（2026-10-30，正常 UTF-8）

p207 结尾留下的「写了但没跑过」的那段代码，这一轮跑起来了，并且证明滚轮在两个列表之间的路由是对的。

- **不造假描述，压窄窗口**：1280 → 800 px（guiScale 2 不变，gui 400×360），面板从 312 宽变 192 宽，
  同一段文字换行变多。扫过 7 个可见行后只有第 5 行需要滚（78 行 ≈ 936 px 内容 vs 216 px 面板，
  `maxScroll=568`）——是**量出来的**，不是挑一个看起来描述长的模组。
- **两个方向都测**：光标在面板上发三格滚轮 → 面板 `scroll 0→10`、滑块 `110+58→113+58`、
  **模组列表 0→0**；光标移到模组列表发同样三格 → **模组列表 0→36**、**面板 10→10**。
  只测一个方向无法排除"任何位置的滚轮都同时喂给两个列表"。
- **一次滚轮格 = `itemHeight/2`**：面板 5 px（行高 10）、模组列表 18 px（行高 36，p204 逐格量到）。
  这批三格实际落地 2 格（5×2=10、18×2=36），另一次尝试落地 3 格（面板 15）——所以判据比方向与比例，
  不比总数，否则会写出一条偶然通过的断言。
- **顺手补上 p207 那行的自盲**：旧 `P207_SCROLL` 打在早退之后，只有画了才打，于是"没有可滚内容"和
  "这帧根本没跑到"长得一样——对照组的日志里第 6 行（描述为空）仍报着上一行的 `max=568`。现在改为
  **状态变化打一次**并带上 `drawn=` / `view=`，空行如实报 `max=0 drawn=false`。
- **探针的坑**：`runs/p204-wheel-input` 的 `findList()` 挑 `getMaxScroll()` 最大的 `class_350`，
  面板一旦可滚（568 > 147）它就从模组列表换成面板，于是"模组列表动没动"改从桥的 `P205_LIST` 行读
  （本轮给它加了 `scroll=` / `max=`）。`result.json` 记成 `probe_state_targets=[11, 78]`。
- **像素**：面板右缘 6 px 列上滑块高 **116 设备像素**（= 58 gui，与 `max(16, round(212×212/780))=58`
  完全一致），滚动 10 px 后下移 **6** 设备像素（比例算 5.4，不是 1:1——第一版判据按 1:1 写，
  误判了一次正确的绘制）；正文互相关位移 **−20** 设备像素 = 10 gui × 2，零位移分数 5.69 vs 1.53。
- **门禁**：`test_review_fixes` **370/370**（+24 条，全部从 `scroll-check.json`、两份 `result.json`、
  `build.log`、桥源码与 harness/verdict 源码重算）、`check_hashes` 见提交说明、`verify_evidence` passed；
  无新 release（v0.5.6，只改桥的调试输出）。
- 边界：gui 宽只有 400，面板左右各剩 2 px 余量，这个宽度下的换行数是本轮特有的；只测 7 个可见行；
  滚轮格数落地 2~3 格不稳定；滑块颜色/宽度仍是 p207 的平色近似；触摸板的亚格输入与 Shift 横向滚轮没测。

## p210 Cloth Config 配置界面（2026-10-30，正常 UTF-8）

AppleSkin 的配置界面是 **1.20.1 的 Cloth Config 11.1.136**（jar-in-jar，
`META-INF/jars/cloth-config-fabric-11.1.136.jar`）画的。p204 把它记成"打不开"，这一轮把它打通：
界面能开、能画 13 行、点得动。规则在 `rules/fabric-1.21.1/cloth-config.json`（层 1/3/4）与
`cloth-config-render.json`（层 5–7），桥在 `java/src/bridge/.../Cloth*Bridge.java`，全过程与逐条退化
写在 `runs/p210-cloth-config/README.md`。

- **5 层断点**：① `Screen.field_44669` 被删（桥返回 1.21.1 自己的 `menu_background.png`）；
  ② `method_25394` 在 `class_339` 上变成 final（改名到 `method_48579`，**必须**加 `onlyIfExtends`）；
  ③ `TextFieldWidget.setCursor*` 各多一个 `boolean`；④ `renderBackground` 多三个参数；
  ⑤ 立即模式渲染模型整代消失（`Immediate.getBuffer` / `BufferBuilder.begin` / 顶点链终点 / `draw`）。
- **没 `onlyIfExtends` 会怎样**（这是本轮修的真缺陷）：Cloth 的列表继承 `class_362`，它**仍然需要**
  `method_25394` 被调用；无闸门的通配改名把 13 行的列表改成"行都在、一个像素不画"。
  `JarPatcherMethodRenameTest` 用 4 个合成 jar 用例把这个闸门钉住（直接父类 / 三级祖先 / 无关父类 /
  祖先解析不出→不改）。
- **第 5 层为什么救得回来**：`DynamicEntryListWidget.renderList` 开头 `vcp=Immediate.getInstance();
  bb=t0(vcp)` 是死代码（slot 8 全程没被 `aload`），行本身走 `renderItem(DrawContext, Entry, …)`。
  桥让 `buffer()` 返回 `null`，13 行就出来了。只有 1–4 层时的崩溃报告反过来证明这条链是活的
  （`t0` 从 `DynamicEntryListWidget.method_25394:298` 抛出）。
- **两个末端尾巴**：Cloth 自己的 demo 屏用 `ItemStack.setCustomName`（层 6）和
  `Enchantments.field_9131` + `addEnchantment(Enchantment,int)`（层 7）。不处理就每次进模组列表都报
  `Error from mod 'cloth-config'`。层 7 是**真退化**：1.21.1 的 `class_7923` 里 75 个 `class_2378` 字段
  没有一个是附魔注册表，附魔只能从 per-world 的 `DynamicRegistryManager` 拿，而这个 lambda 里没有 world，
  所以样例物品不附魔（层 6 同样让它没有自定义名字）。两条都写在规则 `evidence` 里。
- **验收**：`client_errors=[]`、`no_such_field=0`、`no_such_method=0`、`done.tick=182`、
  `rows=13 kinds={BooleanToggleBuilder$1=9, EmptyEntry=2, FloatListEntry=1, SearchFieldEntry=1}`
  （`runs/p210-cloth-config/after3/`）；对照组同一操作是
  `NoSuchFieldError: class_437 … field_44669`（`before/`）。
- **交互**：探针用 **`Screen.method_25402`** 在第一条布尔行的 ON 按钮中心发真实点击 → `handled=true`，
  `getValue()` `true→false`，`direct_press=false`（不是靠直接调 `onPress` 兜底）；
  `after3/toggle.png` 里第一行按钮变 OFF、其余 8 行仍 ON。
- **降级（写进规则，没藏）**：列表平铺背景、列表上下边缘渐变、screen dim 层、tab 阴影、行渐变、
  下拉阴影共 6 处装饰改 no-op；行本身、选中条、文字、按钮都在。
- **未覆盖**：`GlobalizedClothConfigScreen.method_25394`（Ctrl+滚轮全局设置屏，27 处 tombstone，需重建
  tab 栏；AppleSkin 永不打开）与 `DynamicElementListWidget$ElementEntry.method_25401(DDD)`
  （`class_4069` 在 1.21.1 已无 3 参 `isMouseOver`；`scan_refs.py` 的 `refs-after.json` 里就剩这两类）。
- **判据**：`runs/p210-cloth-config/verify_cloth.py` 31/31（同时读 `before/` 与 `after3/`，两边的
  sha256 都与 `result.json` 和现场 jar 比对）；`test_review_fixes` 新增 `test_cloth_config()`。
- 边界：单机、1280×720、guiScale 2；只点第一条布尔开关，其余开关/文本框/浮点列表未交互；跨机器未做。
