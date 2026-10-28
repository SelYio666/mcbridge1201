# p125 — 总验收（2026-10-22）
本文件是一次**可交接的验收快照**：在这台机器上把仓库的自动化门禁全部重跑了一遍，并把
“已验证 / 未验证”的边界写清楚。结论只覆盖下面列出的范围，不外推。
## 门禁结果（本次重跑）

| 门禁 | 结果 |
|---|---|
| `gradle -p java test installDist` | ✅ BUILD SUCCESSFUL |
| Java JUnit | ✅ 25/25 |
| `python tools/test_review_fixes.py` | ✅ **73/73** |
| `python tools/check_hashes.py` | ✅ **946/946**（mismatch 0 / missing 0） |
| `python tools/verify_evidence.py` | ✅ passed（73/73） |
| GitHub CI（master，push+dispatch） | ✅ push 触发已验证（多次 `build` success，最新见 Actions）；此前无 run 是 GitHub Actions degraded performance |
| Release 资产 | ✅ `v0.5.1` / `mcbridge-launcher-0.5.1.zip` |
| 工作区 | ✅ 干净（`git status` 无改动） |

环境：Windows + JDK 21（`.toolchain/jdk`）、Gradle 9.8.1（`.toolchain/gradle`）、 本地 CPython 3.12 运行时；网络为中国大陆环境（官方源 + BMCL 镜像）。
## 已验证（可以对外说）

| 能力 | 证据 |
|---|---|
| Fabric 1.21.1 全量冷安装（3,911/3,911 assets、933.6 MB、0 失败）并进入单人世界 | `runs/p118-full-install-world/`（含世界截图、install-summary.json） |
| NeoForge 21.1.264 安装并到达主菜单 | `runs/p116-neoforge-launch/`（含主菜单截图、installer/launch 日志） |
| NeoForge 带模组进世界：AppleSkin / Farmer's Delight / Jade | `runs/p127`、`runs/p128`、`runs/p130`（含世界截图、模组日志、Jade tooltip） |
| Forge 1.20.1-47.4.28 带模组进世界：AppleSkin / Farmer's Delight | `runs/p129`、`runs/p131` |
| Forge/NeoForge 安装自动补原版 base（quickPlay 参数不丢） | `runs/p127`、`runs/p129`、LOADER/NEOFORGE 回归 |
| 渲染模组能力：EntityCulling 的 mixin 移植后真正生效 | `runs/p119-entityculling-mixin/`（F3 `Skipped: 1`）+ `runs/p121-entityculling-ab/`（开/关对照） |
| 下载源：按路径验证的 BMCL 镜像（含 intermediary）、404 快退、超时重试、SHA-1、来源记录 | `runs/p122-source-canary/`、`docs/download-sources.md` |
| 下载源模式：自动 / 仅官方 / 镜像优先；失败 host 健康缓存 + GUI canary 回写 | `runs/p122`、`runs/p123`、`runs/p124` |
| 1.20.1 全量冷安装 111.7 s / 739 MB / verify OK（测完删除） | `runs/p122-source-canary/full-1.20.1.json` |
| 便携包（内嵌 Python、无需梯子/无需 Python 环境） | v0.4.6 资产，`tools/test_portable.py` OK |
| 规则引擎 + 证据门禁 + CI（规则/桥/证据绑定） | `docs/FINAL-STATUS.md`、`runs/SHA256SUMS.txt` |

## 未验证 / 明确不算通过（不能对外说）
| 项 | 状态 |
|---|---|
| ImmediatelyFast 渲染批处理 | ✅ 已移植并生效：单人 + 专用服务器多人（hud=4659、itemModel=2258、itemOverlay=1129），关闭开关归零（`runs/p134`、`runs/p141`、`runs/p137`）；Iris 1.8.1/1.8.14 + shader pack r5.3（`runs/p142`/`p143`/`p145`/`p146`）、item per-lighting（`runs/p149`/`p150`） |
| Sodium / Iris | ❌ 未触碰 |
| 渲染模组“性能提升”数字 | ❌ 未测（只有 EntityCulling 的 F3 计数，不是帧率基准） |
| 完整镜像模式全量安装 | ❌ 只做了有界链路（客户端+库+120 资源）；全量镜像太慢已中止（p123） |
| NeoForge/Forge 的**带模组**世界 | ✅ 已做（p127–p131：显示/内容/数据同步）；**未测** NeoForge/Forge 专用服务器、复杂多方块模组 |
| 多人**专用**服务器（dedicated server） | ✅ Fabric 1.21.1：早期双客户端（p75/p76）+ 启动器客户端加入（p132）；**未测** NeoForge/Forge 专用服务器 |
| 便携包在其他机器/无网环境 | ❌ 未验证（仅本机解包 + `test_portable`） |
| 真实浏览器里的 UI 点击 E2E | ❌ 未做（只验证了 HTTP 端点与返回 JSON） |
| 长时间 soak / 崩溃恢复 | ❌ 未做 |

## 复现命令

```text
# Java
gradle -p java test installDist

# Python 门禁
python tools/test_review_fixes.py
python tools/check_hashes.py
python tools/verify_evidence.py

# 下载源健康（可选）
python tools/check_download_sources.py
python tools/check_download_sources.py --strict

# 安装/启动（示例）
python launcher/mclaunch.py install 1.21.1 <游戏目录>
python launcher/server.py

# 便携包 python tools/build_portable.py --label 0.4.4
python tools/test_portable.py --root <测试目录> --version 1.21.1
```

## p175 增量验收（2026-10-23）
| 门禁 | 结果 |
|---|---|
| `gradle -p java test installDist` | ✅ BUILD SUCCESSFUL |
| Java JUnit | ✅ 25/25 |
| `python tools/test_review_fixes.py` | ✅ **79/79**（新增 6 条地图 atlas 规则/源码回归） |
| `python tools/check_hashes.py` | ✅ **962/962**（mismatch 0 / missing 0） |
| `python tools/verify_evidence.py` | ✅ passed（79/79） |
| ImmediatelyFast mixin 审计 | `listed=36 inert=3`；两个 map mixin 不再 inert（`runs/p175-map-atlas/audit.log`） |
| 地图 atlas 真实渲染 | ✅ 单人 `ColdWorldMap` 手持 `filled_map`；`map-atlas bind … immediatelyfast:map_atlas/0`；无 ClassCastException/无 crash（`runs/p175-map-atlas/`） |
| Release 资产 | ✅ `v0.5.2` / `mcbridge-launcher-0.5.2.zip` |

剩余 3 个 inert 仍是 `MixinBufferBuilder`、`MixinVertexBuffer`、`MixinFontManager`（与地图无关） 原因见 `runs/p169-inert-analysis/`）。地图只验证了单人第一人称手持地图，物品展示框/多地图 动态更新 未测。
## p178 增量验收（2026-10-23）
| 门禁 | 结果 |
|---|---|
| `gradle -p java test installDist` | ✅ BUILD SUCCESSFUL |
| Java JUnit | ✅ 25/25 |
| `python tools/test_review_fixes.py` | ✅ **81/81**（新增 2 条 VertexBuffer 规则/证据回归） |
| `python tools/check_hashes.py` | ✅ **1000/1000**（mismatch 0 / missing 0） |
| `python tools/verify_evidence.py` | ✅ passed（81/81） |
| ImmediatelyFast mixin 审计 | `listed=37 inert=2`；仅剩 `MixinBufferBuilder`、`MixinFontManager`（`runs/p178-vertex-upload/audit.log`） |
| VertexBuffer 动态上传 fast path | ✅ 80 盔甲架压力、off/off + on/on 对照；on 侧 60/79 条 fast 标记、最高 76k 次 `glBufferSubData`；off/on 像素差 0.0087%（低于 off/off 对照 0.214%）；无 GL/mixin 错误 |
| 地图 atlas 边界 | ✅ p177：两张地图 tile 0/1 + 物品展示框同屏渲染 |
| Release 资产 | ✅ `v0.5.3` / `mcbridge-launcher-0.5.3.zip` |

不宣称性能收益：p178 只证明 fast path 执行且无视觉/GL 回归，没有帧率基准；只测了一台 NVIDIA
机器和一个合成压力场景。
## p180 增量验收（2026-10-23）
| 门禁 | 结果 |
|---|---|
| `python tools/test_review_fixes.py` | ✅ **82/82**（新增 1 条“不得误登记死 mixin”回归） |
| `python tools/check_hashes.py` | ✅ **1005/1005** |
| `python tools/verify_evidence.py` | ✅ passed（82/82） |
| 官方 1.21.1 mixin 审计 | `listed=37 inert=0 problems=0`（`runs/p180-inert-closure/audit-native.log`） |
| 端口 mixin 审计 | `listed=37 inert=2 problems=0`；两个 inert 在官方 jar 中不存在（1.20.4 遗留死代码） |
| Release | 无新 release；v0.5.3 仍是当前发布（p180 只有文档/证据/回归） |

## p181 增量验收（2026-10-23）
| 门禁 | 结果 |
|---|---|
| `python tools/test_review_fixes.py` | ✅ 共 **83 项**（本次 **82/82** + `/api/jvm` 网络超时 skip；新增 1 条 atlas closed 守卫回归） |
| `python tools/check_hashes.py` | ✅ **1022/1022** |
| `python tools/verify_evidence.py` | ✅ passed（接受 `/api/jvm` skip） |
| 地图动态更新 | ✅ `locked=0` held map，数据包移动玩家；`map-atlas update count=2`，截图显示地形覆盖初始图案 |
| 正常退出清理 | ✅ client stop → `Stopping!` → `keep-dummy` → `close id=0` → `clear atlases=1`；exit 0、crash=null |
| 退出崩溃修复 | ✅ 修复前 `Image is not allocated`（`crash-before-fix-map.txt`）；`MapAtlasTexture.isClosed` 守卫后不再崩 |
| Release 资产 | ✅ `v0.5.4` / `mcbridge-launcher-0.5.4.zip` |

## p183 增量验收（2026-10-23）
| 门禁 | 结果 |
|---|---|
| `python tools/test_review_fixes.py` | ✅ 共 **84 项**（本次 **84/84**；新增 1 条 TrashSlot UI empty 键回归，`/api/jvm` 本次未 skip） |
| `python tools/check_hashes.py` | ✅ **1035/1035** |
| `python tools/verify_evidence.py` | ✅ passed（接受 `/api/jvm` skip） |
| TrashSlot 真实 empty 键 | ✅ inventory 悬停 trash → Delete(261) → `DEBUG_EMPTY_PROVIDER` → `SERVER_TRASH empty=true`；`after.png` 显示 trash 空 |
| 失败根因 | ✅ p65/p85/p86 的 Delete 失败是注入漏 `KEYEVENTF_EXTENDEDKEY`（收到 KP_DECIMAL 330），不是 Balm/mod；无产品代码改动 |
| Release | 仅证据/回归，沿用 `v0.5.4`（无新版本） |

## p184 增量验收（2026-10-23）
| 门禁 | 结果 |
|---|---|
| `python tools/test_review_fixes.py` | ✅ 共 **85 项**（本次 **85/85**；新增 1 条 TrashSlot Shift+Delete 回归） |
| `python tools/check_hashes.py` | ✅ **1048/1048** |
| `python tools/verify_evidence.py` | ✅ passed |
| Shift+Delete 跨槽 | ✅ 两叠 5+3 钻石（slot 0/1），Shift+Delete → `DEBUG_DELETE_CONTAINER all=true` → 服务端/客户端 8→0；`after.png` 空 |
| 第一次尝试 | ⚠️ `give` 5+3 合并成一叠 8，虽 `all=true` 但无法证明跨槽；最终改为 `method_5447` 直接写两个槽位 |
| Release | 仅证据/回归，沿用 `v0.5.4`（无新版本） |

## p185 增量验收（2026-10-23）
| 门禁 | 结果 |
|---|---|
| `python tools/test_review_fixes.py` | ✅ 共 **86 项**（本次 **86/86**；新增 1 条 TrashSlot right-click undelete 回归） |
| `python tools/check_hashes.py` | ✅ **1061/1061** |
| `python tools/verify_evidence.py` | ✅ passed |
| 空 cursor 右键 undelete | ✅ trash 5 → 右键 → cursor 1、trash 4、服务端 4；`DEBUG_CLICK button=1 hovering=true`、`DEBUG_PROVIDER_UNDELETE right=true` |
| focus/origin | ✅ 先 `focus_window` 再 `ClientToScreen`，避免 `ShowWindow` 后原点漂移；中性左键吃掉激活点击 |
| Release | 仅证据/回归，沿用 `v0.5.4`（无新版本） |

## p186 增量验收（2026-10-24）
| 门禁 | 结果 |
|---|---|
| `python tools/test_review_fixes.py` | ✅ 共 **87 项**（本次 **87/87**；新增 1 条 Shulker grid wrapper/t2/t4 回归） |
| `python tools/check_hashes.py` | ✅ **1072/1072** |
| `python tools/verify_evidence.py` | ✅ passed |
| Shulker grid 部分恢复 | ✅ client-side component + wrapper：`SBT_WRAP show=true inv=27 nonAir=1`；tooltip 出现预览框与 `Diamond ×5`（`grid.png`） |
| 仍未解决 | ⚠️ 网格 slot 内 item icon 未画；真实 server `/item replace` 栈仍 `!minecraft:container` |
| Release | 仅部分证据/回归，沿用 `v0.5.4`（无新版本） |

## v0.5.5 一键安装到 PCL 增量验收（2026-10-24）
| 门禁 | 结果 |
|---|---|
| `python tools/test_review_fixes.py` | ✅ 共 **88 项**（本次 **88/88**；新增 1 条 PCL 一键面板/版本选择回归） |
| `python tools/check_hashes.py` | ✅ **1085/1085** |
| `python tools/verify_evidence.py` | ✅ passed |
| 图形面板 | ✅ `mcbridge-pcl-panel.zip`（Release v0.5.5）：版本下拉/搜索、release/snapshot/old_* / all、进度条/日志、PCL2 目录自动检测 |
| 免 Python 安装器 | ✅ `mcbridge-pcl-setup.zip`；PCL2 2.13.1.1 便携版实测 1.20.4 版本列表出现（`runs/p137-pcl2-onclick/`） |
| 版本选择 | ✅ `from_source_install.py --list --version-type all`、`--version latest-snapshot`；v0.5.5 release |
| Release | **v0.5.5**（主工具 v0.5.4） |

## 已知风险

- 镜像节点会随时间/地区变化，canary 只是单次采样； - 规则文件按 `capability/risk/evidence` 绑定，新增能力必须先有真实 boot/进世界证据；
- `work/` 与 `dist/` 不入库；仓库不分发游戏/模组/转换后的 jar； - ImmediatelyFast 已完成 batching 引擎移植（HUD/物品批处理生效，A/B 可复现）；Iris、per-lighting 物品变体与帧率基准仍未做。

## p187 Shulker 网格 icon + 服务端物品 增量验收（2026-10-24，本段为正常 UTF-8；上文历史段落保持原样）

| 门禁 | 结果 |
|---|---|
| `python tools/test_review_fixes.py` | ✅ 共 **89 项**（本次 **89/89**；新增 1 条 SBT grid icon + server-box 回归） |
| `python tools/check_hashes.py` | ✅ **1098/1098** |
| `python tools/verify_evidence.py` | ✅ passed |
| 网格 icon | ✅ `GRID_DRAWITEMS ... items=1 first=minecraft:diamondx5`、`GRID_DRAWITEM stack=minecraft:diamond count=5`；`grid.png` 槽内 diamond 图标 ×5 正常绘制 |
| 服务端物品 | ✅ `/item replace ... container.3` 同步的 shulker：`GRID_SERVERBOX slot=3 nonAir=1`，HUD 源 `source=server`，同一条管线渲染 |
| 根因 | set-as-get（`method_57379(type,null)`=set，首次读即清空 CONTAINER，p110 起服务端物品坏掉）→ 改为 `getComponents().get`；转换剥掉了 mod 的 ItemStackMixin → companion 1.1.0 重新注入 getTooltipData + 注册 component-first provider；harness 写 `preview.alwaysOn=true` |
| Release | 沿用 `v0.5.5`（主工具 v0.5.4；p187 无新 release） |
| CI | run `40109967951` success（head `31a0494`） |
| 隐患 | 未验证：FULL 预览类型、多物品网格、预览键交互、真实鼠标 hover（harness 改用 HudRenderCallback 驱动同一条管线，OS 光标注入不可靠） |

## p188 map atlas 1024 溢出 增量验收（2026-10-25，正常 UTF-8）

| 门禁 | 结果 |
|---|---|
| `python tools/test_review_fixes.py` | ✅ 共 **90 项**（本次 **90/90**；新增 1 条 map atlas overflow 回归） |
| `python tools/check_hashes.py` | ✅ **1110/1110** |
| `python tools/verify_evidence.py` | ✅ passed |
| 溢出 | ✅ 1024 张填满 atlas 0 后：`map-atlas create id=1`（恰好一次）、`assign map=1025 packed=65536`（atlas 1 tile 0）、`bind map=map/1025 texture=immediatelyfast:map_atlas/1` |
| 上传证明 | ✅ `atlas1-pixel-check mismatches=0`（4 采样点读回 atlas 1 NativeImage 与 MapState 颜色一致；update marker 节流故用像素） |
| 退出清理 | ✅ `map-atlas clear atlases=2`、exit 0、errors=[]、crash=null |
| Release | 沿用 `v0.5.5`（主工具 v0.5.4；p188 无新 release，实现零改动） |
| 隐患 | 第三个 atlas（2048+ 张）、跨 atlas 同屏视觉、真实服务端 1024+ 张地图端到端未测 |

## p189/p190 TrashSlot creative 删除 + 多客户端 增量验收（2026-10-25，正常 UTF-8）

| 门禁 | 结果 |
|---|---|
| `python tools/test_review_fixes.py` | ✅ 共 **92 项**（本次 **92/92**；新增 p189 creative 删除 + p190 多客户端两条回归） |
| `python tools/check_hashes.py` | ✅ **1143/1143** |
| `python tools/verify_evidence.py` | ✅ passed |
| p189 creative | ✅ 真缺陷修复：1.21.1 creative 界面 hoveredSlot 恒 null + SlotWrapper 消失使原分支永不可达；companion 重写后 Shift+Delete 连锁（slot=36 all=true，InventoryMenu 46 槽）+ Delete + 清 trash 全通过 |
| p190 多客户端 | ✅ A：5→4（右键取 1）→empty（Delete）；B 服务端 trash 全程 diamondx3、客户端 UI 不变（reply 只回发送者） |
| Release | 沿用 `v0.5.5`（主工具 v0.5.4；无新 release） |
| 隐患 | creative inventory tab 27 格、creative 右键 undelete、B 主动操作、三客户端、重进保持未测 |

## p191/p192 TrashSlot creative/多客户端残余 增量验收（2026-10-25，正常 UTF-8）

| 门禁 | 结果 |
|---|---|
| `python tools/test_review_fixes.py` | ✅ 共 **94 项**（本次 **94/94**；新增 p191 creative tab + p192 三客户端两条回归） |
| `python tools/check_hashes.py` | ✅ **1175/1175** |
| `python tools/verify_evidence.py` | ✅ passed |
| p191 | ✅ inventory tab 主背包格删除（SERVER_DELETE slot=18，class_484 identity 映射）；creative 列表格上游不删；右键 undelete 不适用（无画布） |
| p192 | ✅ B 主动 4→3→empty 只影响 B；C 服务端/客户端不变；A 重进 trash=empty（上游登录重置） |
| Release | 沿用 `v0.5.5`（主工具 v0.5.4；无新 release） |
| 隐患 | 双端同时操作、四客户端未测 |

## v0.5.6 release 增量（2026-10-25，正常 UTF-8）

- tag `v0.5.6`（target `44b5528`），5 资产：主工具便携包 0.5.6（`tools/test_portable.py` OK）、
  shulkerpreview/trashcreativefix companion jar、PCL 面板/setup（沿用 v0.5.5 字节一致）；
- 服务端 sha256 与本地记录全部一致（见 acceptance.json `release_v056`）；
- 一键 PCL 仍为 v0.5.5 资产（未变更）。

## p193 Shulker grid 残余 增量验收（2026-10-26，正常 UTF-8）

| 门禁 | 结果 |
|---|---|
| `python tools/test_review_fixes.py` | ✅ 共 **95 项**（本次 **95/95**；新增 1 条 p193 Shulker grid 残余回归） |
| `python tools/check_hashes.py` | ✅ **1194/1194** |
| `python tools/verify_evidence.py` | ✅ passed |
| p193 | ✅ client 多物品 3 钻 + 2 绿宝石、FULL、真实 tooltip 路径、server box 2 钻 + 4 绿宝石；`result.json` 4/4 true |
| Release | 沿用 `v0.5.6`（p193 无 mod 改动、无新 release） |
| 隐患 | GLFW 回调级输入（非 OS 光标）、FULL 依赖 alwaysOn+预览键、27 格全满未测 |
## p194 第三 atlas / 跨 atlas 同帧 增量验收（2026-10-26，正常 UTF-8）

| 门禁 | 结果 |
|---|---|
| `python tools/test_review_fixes.py` | ✅ 共 **96 项**（本次 **96/96**；新增 1 条 p194 第三 atlas/跨 atlas 回归） |
| `python tools/check_hashes.py` | ✅ **1206/1206** |
| `python tools/verify_evidence.py` | ✅ passed |
| p194 | ✅ 2050 map ids：`create id=2` 一次、`assign map=2049 packed=131072`/`2050=131328`、`bind map_atlas/2`；HUD 同帧 map 1/1025/2049；atlas1/2 像素 0；退出 `clear atlases=3` |
| Release | 沿用 `v0.5.6`（p194 无 mod 改动、无新 release） |
| 隐患 | 真实服务端 1024+ 张地图端到端、三 atlas 并排视觉（HUD 原点）、3×4096² ≈192 MB 压力未测 |
## p195 v0.5.6 交付验证 增量（2026-10-26，正常 UTF-8）

| 门禁 | 结果 |
|---|---|
| `python tools/test_review_fixes.py` | ✅ 共 **97 项**（本次 **97/97**；新增 1 条 p195 交付验证回归） |
| `python tools/check_hashes.py` | ✅ **1212/1212** |
| `python tools/verify_evidence.py` | ✅ passed |
| p195 portable | ✅ `dist/mcbridge-launcher-0.5.6.zip` 在全新 `work/tmp/p195-portable` 根目录 `test_portable.py --version 1.21.1`：deps + `/api/status` + `/guide` 全过（RESULT: OK） |
| p195 panel smoke | ✅ `tools/pcl_panel.py` 打开，103 个正式版、PCL 目录默认值正常（`panel-smoke.png`）；PCL2 本机路径不存在 |
| panel 资产 | ⚠️ 只下载到 3,361,813/12,361,982 bytes，`gh release download` 挂起已终止 |
| Release | 沿用 `v0.5.6`（无 mod 改动、无新 release） |
| 隐患 | 完整 PCL2 安装点击/进度/PCL2 版本刷新、干净/离线主机、panel 资产重下未验证 |
## p196 Shulker grid 27 格全满 增量（2026-10-26，正常 UTF-8）

| 门禁 | 结果 |
|---|---|
| `python tools/test_review_fixes.py` | ✅ 共 **98 项**（本次 **98/98**；新增 1 条 p196 27 格回归） |
| `python tools/check_hashes.py` | ✅ **1231/1231** |
| `python tools/verify_evidence.py` | ✅ passed |
| p196 | ✅ 27 种物品 `GRID_DRAWITEMS items=27`、FULL、server box、真实 hover；`result.json` 4/4 true |
| Release | 沿用 `v0.5.6`（p196 无 mod 改动、无新 release） |
| 隐患 | 预览键重绑定当轮未生效（写错 config 分类 + F 触发交换副手）；27 格不同 NBT/附魔未测（重绑定已由 p197 关闭） |
## p197 Shulker 预览键重绑定 增量（2026-10-26，正常 UTF-8）

| 门禁 | 结果 |
|---|---|
| `python tools/test_review_fixes.py` | ✅ 共 **99 项**（本次 **99/99**；新增 1 条 p197 重绑定回归） |
| `python tools/check_hashes.py` | ✅ **1254/1254** |
| `python tools/verify_evidence.py` | ✅ passed |
| p197 | ✅ `controls.previewKey=J(74)`/`fullPreviewKey=K(75)`、`alwaysOn=false`；mod 状态机 `NO_PREVIEW→COMPACT→FULL→COMPACT→NO_PREVIEW`；27 格 `GRID_DRAWITEMS items=27`；`result.json` 7/7 true |
| 更正 | p196 “mod 忽略 config previewKey” 为误判（字段写在 `preview` 分类）；bytecode 显示读取 `controls.previewKey/fullPreviewKey` |
| Release | 沿用 `v0.5.6`（无 mod 改动、无新 release） |
| 隐患 | 键状态仍在 `isKeyDown` 轮询边界注入（无 OS 级物理按键）；27 格不同 NBT/附魔未测 |
## p198 文档双重编码修复 + 编码守卫 增量（2026-10-28，正常 UTF-8）

| 门禁 | 结果 |
|---|---|
| `python tools/test_review_fixes.py` | ✅ 共 **105 项**（本次 **105/105**；新增 6 条文档编码守卫回归） |
| `python tools/check_hashes.py` | ✅ **1264/1264** |
| `python tools/verify_evidence.py` | ✅ passed（新增 `text_encoding` 直接项） |
| `python tools/check_text_encoding.py` | ✅ 223 个跟踪 `*.md` 全绿；修复前三个文件 892 条 finding（`runs/p198-text-encoding/encoding-scan-before.log`） |
| p198 修复 | ✅ `README.md` / `docs/FINAL-STATUS.md` / `runs/p125-final-acceptance/README.md` 可正常阅读；行数不变（151/267/286） |
| 修复性质 | ⚠️ 受损 13385 字符中可逆还原 2599（19.4%），10786（80.6%）为按上下文重写；行级 386 未动 / 12 还原 / 306 重写 |
| Release | 沿用 `v0.5.6`（无 mod 改动、无新 release） |
| 隐患 | 重写段落是语义等价重述而非逐字原文；守卫只扫 `*.md`；p195 的写入路径未追溯 |
## p200 atlas 逐 id 落点 + 三张并排 增量（2026-10-28，正常 UTF-8）

| 门禁 | 结果 |
|---|---|
| `python tools/test_review_fixes.py` | ✅ 共 **124 项**（本次 **124/124**；新增 16 条 atlas 逐 id 落点/并排回归 + 3 条转义控制字符回归） |
| `python tools/check_hashes.py` | ✅ **1289/1289**（mismatch 0 / missing 0；p201 起清单为 1269/1269，见下） |
| `python tools/verify_evidence.py` | ✅ passed（`text_encoding` 226 个 md 全绿、`review_regressions` 124/124） |
| 顺手修的第二类损伤 | ✅ `docs/remaining-work.md` 中 `\t`/`\r` 被解释成控制字符的两处已修回；守卫加 `control-tab`/`control-cr`（围栏内 TAB 合法）+ 3 条回归 |
| 逐 id 校验 | ✅ `mapping-mismatch=0 pixel-verified=2050 pixel-mismatch=0`（不是抽样，也不是 p194 的共用内容校验） |
| 三张同屏 | ✅ 三块 256×256、间距 272、窗口偏移一致（`runs/p200-atlas-layout/layout-check.json`） |
| 192 MiB | ✅ 读 `(4095,4095)` 成功、读 `(4096,4096)` 抛异常，证明缓冲 4096²，×4×3 = 201,326,592 字节 |
| 工作集 | ⚠️ 实测 +460.9 / +548.1 / +486.5 MB（三次），峰值 2192.0–2247.3；**显存未测** |
| Release | 沿用 `v0.5.6`（无 mod 改动、无新 release） |
| 隐患 | 真实专用服务器 1024+ 张地图未做；只用到 2050 格（未压满 3072）；VRAM 未测 |

## p201 哈希清单在干净 clone 里可验证 增量（2026-10-28，正常 UTF-8）

| 门禁 | 结果 |
|---|---|
| `python tools/test_review_fixes.py` | ✅ 共 **130 项**（本次 **130/130**；新增 6 条行尾确定性回归） |
| `python tools/check_hashes.py` | ✅ **1269/1269**（mismatch 0 / missing 0；条目由 1289 减到 1269，删掉 20 条指向 gitignored `work/` 的） |
| `python tools/verify_evidence.py` | ✅ passed（`text_encoding` 227 个 md 全绿、`review_regressions` 130/130） |
| 干净 clone（修复前） | ❌ clone `82e4e9f`：`ok=646 mismatch=623 missing=20` |
| 干净 clone（修复后） | ✅ clone `2e34a9a`：`ok=1269 mismatch=0 missing=0`；`audit_eol` 1269/1269 可复现 |
| 修法 | ✅ `.gitattributes` 钉 `* -text`、工作区归一到 blob 字节（纯行尾）、删 `work/` 条目、`git ls-files -z` |
| Release | 沿用 `v0.5.6`（无 mod 改动、无新 release） |
| 隐患 | clone 里 `test_review_fixes` 125/125（`ISSUE-02` skip，需已构建 CLI），作者机 130/130；只在 Windows / Git for Windows 实跑 |

## p202 OS 光标级悬停 + 27 格异质 NBT 增量（2026-10-28，正常 UTF-8）

| 门禁 | 结果 |
|---|---|
| `python tools/test_review_fixes.py` | ✅ 共 **227 项**（本次 **227/227**；p202 悬停/异质 NBT 32 条、p203 并发 trash 26 条、p208 交付/跨平台 39 条） |
| `python tools/check_hashes.py` | ✅ **1338/1338**（mismatch 0 / missing 0） |
| `python tools/verify_evidence.py` | ✅ passed（`text_encoding` 228 个 md 全绿、`review_regressions` 227/227） |
| 悬停来源 | ✅ 探针不写鼠标字段；外部进程移真实光标；`glfw`/`raw`/`mouse`/`target` 四者同为 `686,378`；`index=10 keysSent=false` |
| 悬停更正 | ✅ 控制组只用 `SetCursorPos`、窗口置顶也能悬停 → 原"这台机器收不到 OS 光标"的结论作废（原因是窗口没置顶） |
| 27 格异质 | ✅ `stacks=27 distinctComponents=27 distinctItems=27 distinctNames=27`；27 个 index 全部画出；27 个不同 payload |
| 截图 | ✅ 自相关测出 36 px 周期（=18×guiScale 2）；27 格无空白、27 个哈希互不相同 |
| Release | 沿用 `v0.5.6`（无 mod 改动、无新 release） |
| 隐患 | 单机单显示器；FULL 仍需轮询边界伪造 J/K；嵌套潜影盒与逐格自定义模型未测 |

## p203 同一服务端 tick 并发 trash 增量（2026-10-28，正常 UTF-8）

| 项 | 结果 |
|---|---|
| 开火对齐 | 两个客户端读同一个 epoch-ms，客户端线程自旋到点：`P203_FIRE … epochMs=1793197755075 driftMs=0`（A/B 相同） |
| 服务端并发 | `P203_SET … tick=819 … GridUser stack=empty` 与 `… tick=819 … TrashB stack=minecraft:diamondx3`，相隔 4 ms，均在 `Server thread` |
| 包与写入同 tick | `P203_S2C tick=819 MessageDeleteFromSlot` / `MessageTrashSlotClick`，与两条写入同 tick |
| 隔离 | A 最终 `trash=empty`、B `trash=minecraft:diamondx3`，B 客户端 `carried=minecraft:diamondx1` |
| 登录重置 | 加入时各有一条 `seeding=false … stack=empty`（tick 278 / 620），与 p65 的上游语义一致 |
| 独立复现 | `repeat/round1-*` 那一轮两次写入同在 tick 905 |
| 门禁 | `test_review_fixes` **227/227**、`check_hashes` **1338/1338**、`verify_evidence` passed |

## p208 干净环境与跨平台审计增量（2026-10-28，正常 UTF-8）

| 项 | 结果 |
|---|---|
| 剥离环境 | `PATH=C://Windows//System32;C://Windows`，`PYTHON*`/`JAVA_HOME` 移除，`HOME`/`APPDATA`/`LOCALAPPDATA` 指向新建空目录 |
| 剥干净的证据 | 同环境 `which python`/`which java` 均为 `None` |
| 照发原件跑包 | **8/8**（`clean-host-shipped.json`） |
| 叠加当前源码跑包 | **8/8**（`clean-host-current.json`，`overlaid` 4 个模块） |
| 干净环境的接口 | `/api/status` 200，`versions: 0`，`java: null`，`java_error: "Java not found: ..."` |
| 包内容 | 231 条目、0 个 `.jar`、启动脚本只有 `run.bat` |
| 平台探针 | 修前 **2/6** → 修后 **6/6** |
| 静态命中 | 28（未保护 24）→ 22（未保护 4） |
| POSIX 模拟导入 | 4/4 |
| 依赖缺失时打包 | `rc=1` 拒绝，`build-blocked.log` |
| 门禁 | `test_review_fixes` **227/227**、`check_hashes` **1338/1338** |
