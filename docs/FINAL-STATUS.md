# mcbridge1201 最终状态（2026-10-23）

> 定位：**Minecraft 版本迁移与运行辅助工具箱**。迁移与验证归本工具，日常启动交给 PCL。
> 最新发布：[v0.5.6](https://github.com/SelYio666/mcbridge1201/releases/tag/v0.5.6)（一键安装到 PCL：图形面板/全版本选择；主工具 v0.5.4）。

## 一、已验证（有日志/截图/哈希）

### 转换与兼容引擎

| 能力 | 证据 |
|---|---|
| CenturyBridge 分段转换 + 规则修补（field/method/body/superclass/ctor/rename/mixin/签名） | `docs/baseline.md`、`rules/fabric-1.21.1/` |
| 三样本功能级：Lithium / IronChests / TrashSlot | `runs/p14`、`p27`、`p41`、`p43`、`p78`–`p80` |
| 6 个扩展样本：AppleSkin / Mod Menu / Clumps / FallingTree / ShulkerBoxTooltip / FerriteCore（仅启动） | `docs/mod-expansion.md`、`runs/p88`–`p109` |
| 热门模组抽样（VeinMiner 启动；EntityCulling 进服但剥离 load-bearing mixin；ImmediatelyFast 崩溃） | `runs/p111` |
| TrashSlot 严格桥：save/writeItem/readItem/load + 两条失败分支（运行期） | `runs/p113-trashslot-strict` |

### 启动器

| 能力 | 证据 |
|---|---|
| 全量 920 版本浏览/搜索、快照/远古可选 | `launcher/web`、`runs/p112` |
| 一键安装并启动；原版 + Fabric 实测 | `runs/p112`、`runs/p114` |
| Forge 1.20.1 启动到主菜单 | `runs/p112` |
| NeoForge 1.21.1（21.1.264）安装 + 启动到主菜单 | `runs/p116-neoforge-launch`（见下文根因与修复） |
| NeoForge 21.1.264 + 第三方模组（AppleSkin）+ 单人世界 | `runs/p127-neoforge-mod-world`（含世界截图、`joined`、模组加载日志） |
| NeoForge 21.1.264 + 内容模组（Farmer's Delight，方块/物品/标签）+ 单人世界 | `runs/p128-neoforge-content-mod/`（F3 出现 farmersdelight 标签） |
| Forge 1.20.1-47.4.28 + AppleSkin 模组 + 单人世界 | `runs/p129-forge-mod-world/`（quickPlay、`joined`、AppleSkin 配置生成） |
| Forge 1.20.1-47.4.28 + Farmer's Delight 内容模组 + 单人世界 | `runs/p131-forge-content-mod/`（配置生成、无注册错误、`joined`） |
| NeoForge 21.1.264 + Jade（数据同步/HUD）+ 单人世界 | `runs/p130-neoforge-jade/`（Jade tooltip 可见） |
| Fabric 1.21.1 专用服务器 + 启动器客户端加入（quickPlayMultiplayer） | `runs/p132-dedicated-join/`（早期 p75/p76 双客户端同步） |
| ImmediatelyFast 1.21.1 batching 移植：单人 + 多人 + soak + Iris（含 shader pack），HUD/物品/overlay 计数 + 关闭归零 | `runs/p134`、`runs/p137`、`runs/p139`、`runs/p140`、`runs/p141`、`runs/p142`、`runs/p143`、`runs/p145`、`runs/p146` |
| ImmediatelyFast HUD batching on/off 帧率对照（实测无正收益，见报告） | `runs/p148-bench/` |
| ImmediatelyFast 实体压力（80 盔甲架）交错 on/off：开启 universal batching 慢约 13%（550 vs 636，两轮一致）；不宣称收益 | `runs/p157-stress-interleaved/`（p153–p157） |
| Sodium 1.20.1 转换可行性（静态分析）：`blocked_static` 13/15/16，需移植渲染内核 | `runs/p158-sodium-probe/`；逐条定性见 `docs/sodium-plan.md`（p199） |
| ImmediatelyFast 端口 mixin 审计：inert 7 → 6（重登记 ChatHud） | `runs/p165-mixin-audit/`、`runs/p166-chat-hud/` |
| ImmediatelyFast 端口 mixin 审计：inert 6 → 5（重登记 MixinMinecraftClient） | `runs/p167-minecraft-client/` |
| ImmediatelyFast 端口 mixin 审计：inert 5 → 4（重登记 MixinBufferRenderer） | `runs/p168-buffer-renderer/` |
| 剩余 inert 的阻塞原因（目标缺失/GL 路径）；p175 后剩 3 个 | `runs/p169-inert-analysis/` |
| MixinVertexBuffer 静态截图 A/B（差 0.018%，证据不足，未启用） | `runs/p170-vertex-verify/` |
| 半启用的 MapTexture mixin 显式 strip（避免地图渲染 ClassCastException） | `runs/p171-map-strip/` |
| ImmediatelyFast 地图 atlas 恢复：两个 map mixin 按 1.21.1 重写，单人世界真实手持 filled_map 渲染（atlas 绑定 + UV 重定向） | `runs/p175-map-atlas/`（`world.png`、`map-atlas bind … immediatelyfast:map_atlas/0`、无 crash；p172 的失败点保留） |
| ImmediatelyFast 地图 atlas 边界：两张地图分别落到 tile 0/1（packed 0 / 256），并与物品展示框地图同屏渲染 | `runs/p177-map-atlas-edge/`（`world.png`、两条 bind 日志、无 ClassCastException/crash） |
| ImmediatelyFast `MixinVertexBuffer` 动态上传 fast path：80 盔甲架压力，off/off、on/on 对照；60/79 条 fast 标记、最高 76k 次 `glBufferSubData`；off/on 像素差 0.0087% | `runs/p178-vertex-upload/`（`on1/world.png`、`off1/world.png`、`compare-*.png`、`result.json`、无 GL/mixin 错误） |
| ImmediatelyFast 端口收尾：官方 1.21.1 jar 没有 `MixinBufferBuilder`/`MixinFontManager`，端口剩余 2 个 inert 是 1.20.4 多版本 jar 的遗留死代码，不是待移植功能 | `runs/p180-inert-closure/`（native `listed=37 inert=0` vs 端口 `listed=37 inert=2`；规则级防误登记回归） |
| ImmediatelyFast 地图 atlas 生命周期：locked=0 地图第二次上传（地形覆盖初始图案）+ 正常客户端 stop 的 keep-dummy/close/clear；修复退出时向已释放 NativeImage 写入的崩溃 | `runs/p181-map-atlas-lifecycle/`（`map-atlas update count=2`、`clear atlases=1`、exit 0、无 crash；`crash-before-fix-map.txt` 保留修复前崩溃） |
| TrashSlot 真实 empty-trash Delete UI 键：inventory 悬停 trash → `DEBUG_KEY key=261` → provider → 服务端清空；p65 的 Delete 失败根因是注入漏 `KEYEVENTF_EXTENDEDKEY`（收到 KP_DECIMAL 330） | `runs/p183-trash-key/`（`DEBUG_EMPTY_PROVIDER`、`DEBUG_RUN_RETURN=true`、`SERVER_TRASH empty=true`；`after.png`） |
| TrashSlot Shift+Delete (`delete_all`)：两叠 5+3 钻石跨槽删除，`DEBUG_DELETE_CONTAINER all=true`，服务端/客户端 8→0 | `runs/p184-trash-delete-all/`（`shift_seen`/`delete_seen`/`server_zero`/`client_zero` 全 true；`after.png`） |
| TrashSlot 空 cursor 右键 undelete：trash 5 → 右键 → cursor 1、trash 4、服务端 4；Balm 屏幕事件确实分发右键 | `runs/p185-trash-undelete-right/`（`DEBUG_CLICK button=1 hovering=true`、`DEBUG_PROVIDER_UNDELETE right=true`、`RIGHT_STATE carried=1 trash=4`；`after.png`） |
| ShulkerBoxTooltip 网格预览（部分恢复）：client-side ContainerComponent + wrapper 读取 component + grid renderer 的 t2/t4 桥；tooltip 出现预览框与 `Diamond ×5`，但网格 item icon 仍缺、真实 server item 仍空 | `runs/p186-shulker-grid-client-item/`（`SBT_WRAP show=true inv=27 nonAir=1`；`grid.png`） |
| ShulkerBoxTooltip 网格 item icon + 服务端物品恢复 | ✅ | p187：两个根因修复——桥接/companion 把 `method_57379(type,null)`（=set）当读用、首次读即清空服务端栈的 container（p110 起服务端物品坏掉）；转换剥掉 mod 的 ItemStackMixin 导致无人提供 PreviewTooltipData。companion 1.1.0 注入 getTooltipData + 注册 component-first provider（17 个 shulker 物品）；harness 写 `preview.alwaysOn=true`。实测 `GRID_DRAWITEMS ... first=minecraft:diamondx5`、`GRID_DRAWITEM stack=minecraft:diamond count=5`、`GRID_SERVERBOX slot=3 nonAir=1`（`/item replace` 真实服务端 shulker，HUD 源 source=server），截图槽内 diamond ×5 图标正常绘制；未验证：FULL 预览类型、多物品网格、预览键交互、真实鼠标 hover | `runs/p187-grid-draw-probe/`（`grid.png`、`result.json`、`client.log`、README） |
| 地图 atlas 1024 溢出（第二个 atlas） | ✅ | p188 纯验证轮（实现零改动）：探针用 map 1 的真实 MapState 连续分配 1026 个 map id，`map-atlas create id=1` 恰好一次（1024 满后溢出）、编码正确（`assign map=1025 packed=65536`=atlas 1 tile 0、`mapping1024=7967`=atlas 0 最后一格）、`bind map=map/1025 texture=immediatelyfast:map_atlas/1`；HUD 内 `MapRenderer.draw` 触发真实上传后 `atlas1-pixel-check mismatches=0`（4 采样点读回 atlas 1 NativeImage 与 MapState 颜色一致；update marker 有节流故用像素）；`map-atlas clear atlases=2` 正常退出；未测：第三个 atlas（2048+）、跨 atlas 同屏视觉、真实服务端 1024+ 张地图端到端 | `runs/p188-atlas-overflow/`（`result.json`、`client.log`、README） |
| TrashSlot creative 删除键 | ✅ | p189：**真缺陷修复**——1.21.1 creative 界面（class_481）hoveredSlot 恒 null 且 SlotWrapper 已删除，1.20.x 的 creative 分支永不可达（DEBUG_HOVERED hovered=null 实证）；companion `trashcreativefix` 重写分支（hotbar menu 45..53 → 服务端 InventoryMenu 36..44，`callIsHovering` 定位，无画布时直接发 MessageDeleteFromSlot）。实测 Shift+Delete 连锁删 hotbar 0+1（SERVER_DELETE slot=36 all=true，menu=class_1723 menuSize=46）、普通 Delete、删除后 trash 清空（slot=-1）；未测：creative inventory tab 27 格、右键 undelete | `runs/p189-trash-creative/`（`after-delete-all.png`、`result.json`、`java/src/trashcreative/`） |
| TrashSlot 多客户端独立 trash | ✅ | p190：双客户端（GridUser/TrashB，online-mode=false dedicated）+ 服务端 probe 分别 seed 5/3 钻；A 右键取 1（服务端 5→4）+ Delete 清空（→empty），B 的服务端 trash 全程 diamondx3、B 的客户端 UI 全程不变（reply 语义只回发送者）；未测：B 主动操作、三客户端、重进保持 | `runs/p190-trash-multi/`（`result.json`、`client-a/b.log`、`after.png`） |
| TrashSlot creative inventory tab + 三客户端残余 | ✅ | p191/p192：inventory tab 的 36 格走 class_484 wrapper（field_7874 恒 0，列表位置=服务端 InventoryMenu 逐槽一致），companion 泛化 identity 映射——实测主背包格 Delete（SERVER_DELETE slot=18、inv18=empty）+ creative 列表格不可删（上游语义，无 SERVER_DELETE）+ 右键 undelete 不适用（creative 屏无 trash 画布，上游 undeleteLast 空实现）；三客户端 B 主动 4→3（右键取 1）→empty（Delete）只影响 B，C 服务端/客户端全程不变，A 重进后 trash 变 empty（上游 PlayerLoginEvent 重置，非 bug） | `runs/p191-trash-residual/`、`runs/p192-trash-multi-active/`（result.json、截图、双端日志） |
| 一键安装到 PCL 图形面板/版本选择 | ✅ v0.5.5：`mcbridge-pcl-panel.zip` + `mcbridge-pcl-setup.zip`；版本下拉/搜索/进度/PCL2 自动检测；`from_source_install` 支持 release/snapshot/old_* / all / latest-snapshot；PCL2 2.13.1.1 实测 | `share/pcl-onclick/`、`runs/p137-pcl2-onclick/` |
| Forge 1.20.1-47.4.28 专用服务器 + 客户端 quickPlayMultiplayer 加入 | `runs/p159-forge-server/` |
| mrpack 含真实 files（HTTP 下载 + SHA-1 校验 + overrides） | `runs/p160-mrpack/` |
| NeoForge 21.1.264 专用服务器 + 客户端 quickPlayMultiplayer 加入 | `runs/p161-neoforge-server/` |
| NeoForge 专用服务器 + Farmer's Delight 1.3.4（服务端/客户端同模组加入） | `runs/p163-neoforge-fd-server/` |
| Forge 专用服务器 + Farmer's Delight 1.3.4（服务端/客户端同模组加入） | `runs/p164-forge-fd-server/` |
| ImmediatelyFast 移植规则/源码回归（6 类替换 + 2 条配置补充 + Identifier 桥 + 无 tombstone + 无二次释放 + Iris 分支） | `rules/fabric-1.21.1/immediatelyfast-batching-port.json`、`tools/test_review_fixes.py` IFPORT 组 |
| Forge/NeoForge 安装自动补原版 base | `runs/p129`、回归检查（LOADER 组） |
| Forge/NeoForge 启动命令保留 `extra_game`（quickPlay 等参数） | `runs/p127`、回归检查（NEOFORGE 组） |
| 加载器版本选择（Fabric 255 / Forge 137 实测；指定 Fabric 0.20.1 安装成功） | `runs/p112`、docs/launcher.md |
| Java 运行时安装（OpenJDK 21.0.7）+ 启动优先使用 | docs/launcher.md |
| Modrinth mrpack：扫描/安装/overrides/自动启动 | docs/launcher.md |
| 删除版本（路径穿越防护）、模组启停 | docs/launcher.md |
| 与其他启动器共用：目录按钮（root/mods/存档/版本）、`/api/dirs`、`/api/open-dir`、profile 同步 | docs/launcher.md |
| 免 GitHub 便携包：内置 Python 3.12 + 第三方许可证，双击 `run.bat` | docs/distribution.md §2.5、`tools/build_portable.py` |
| 下载源策略：逐路径镜像 + 有限重试 + 侧车 SHA-1 + 来源记录（`/api/downloads`） | docs/download-sources.md |
| 下载进度：字节 / 速度 / 当前来源（`/api/task`），前端显示且不编造剩余时间 | docs/launcher.md |
| 下载源设置（自动/仅官方/镜像优先）+ 失败 host 排序 + 分层测试（canary / 1.20.1 全量） | docs/download-sources.md、runs/p122-source-canary/ |
| mirror 模式真实有界验证：288/305 走镜像、191/191 SHA-1 匹配、镜像慢且有失败重试 | runs/p123-mirror-mode-install/ |
| 分段下载评估：客户端 jar 4 段仅 1.23×，决定不实现（runs/p126） | runs/p126-segment-bench/ |
| 总验收快照：全套门禁重跑 + 已验证/未验证边界（可交接） | runs/p125-final-acceptance/ |
| GUI 源健康检查：`/api/source-health`、`/api/check-sources`（canary 输出到游戏目录并回写健康缓存） | docs/launcher.md、runs/p124-gui-source-check/ |
| 下载冷/热对照（客户端 + 全部允许库 + assets 样本 + Fabric） | docs/download-sources.md、runs/p117-download-bench/ |
| 全量冷安装 + 真进世界（原版 1.21.1：3911/3911 assets，115 s，quickPlay 进世界） | runs/p118-full-install-world/ |
| EntityCulling 1.21.1：剥离的 mixin 移植 + 重新启用，进世界且 F3 culling 计数生效 | runs/p119-entityculling-mixin/ |
| EntityCulling 开关 A/B：关闭跳过时无 Culling 计数，开启时 Skipped 1（独立复现） | runs/p121-entityculling-ab/ |
| 标准目录 + launcher_profiles，PCL 可直接复用 | docs/launcher.md |

### NeoForge 启动修复（2026-10-21，p115 → p116）

p115 的猜测（classpath / `-p` 模块路径）被证伪：启动命令与官方 `version.json` 完全一致。
真实根因是**安装不完整**——官方安装器的客户端处理器（jarsplitter → AutoRenamingTool →
binarypatcher）因 Java 网络超时从未跑成，FML 游戏层里没有 `neoforge` 模块，
`DisplayWindow.updateModuleReads` 就在 `layer.findModule("neoforge").orElseThrow()` 处崩溃。

修复：启动器先用 Python 下载器预置安装器所需库（SHA1 校验，可镜像），再让官方处理器离线执行；
安装/校验以四件游戏文件（`neoforge-client`、`neoforge-universal`、`client-*-srg`、
`client-*-extra`）齐全为准；同时修掉 `_run_installer` 相对路径 + `cwd` 的真实 bug。
单测新增 8 项（`tools/test_review_fixes.py` 的 NEOFORGE 组）。

### EntityCulling mixin 移植（2026-10-22，p119）

EntityCulling 被剥离的 `EntityRendererMixin` 已按 1.21.1 的 6 参 shadow 重写并**重新启用**：
新增规则 `mixinConfigAdditions`（把类加回 mixin config）+ `mixinClassReplacements`，
并把 bundled transition 的 `new Identifier(...)` 改走 `IdentifierBridge.of(...)`。
实测 Fabric 1.21.1 + Fabric API 进世界，F3 中 EntityCulling 计数
`Rendered Entities: 3 Skipped: 1`，配置 `skipEntityCulling:false`，无 mixin 报错。

### 工程与门禁

- 单测 25/25；`verify_evidence` passed；哈希 1270 项（以 `runs/SHA256SUMS.txt` 实际行数为准）；桥一致性 0（ImmediatelyFast 端口 jar，p165/p181）；mixin 审计 inert=2（`listed=37`；p175 恢复 map mixin、p177 补多地图/展示框、p178 启用 VertexBuffer；剩余两个是官方 1.21.1 已删除的 1.20.4 遗留类，见 `runs/p180-inert-closure/`）；
- 外部问题汇总 20 项回归 + 9 项 NeoForge 安装/启动回归 + 10 项目录/兼容/说明回归 + 1 项加载器安装回归 + 8 项 ImmediatelyFast 移植回归 + 1 项便携包回归 + 24 项下载源/进度回归 + 6 项地图 atlas 回归 + 2 项 VertexBuffer 回归 + 1 项死 mixin 防误登记回归 + 1 项 atlas closed 守卫回归 + 1 项 TrashSlot UI empty 键回归 + 1 项 TrashSlot Shift+Delete 回归 + 1 项 TrashSlot right-click undelete 回归 + 1 项 Shulker 网格 wrapper/t2/t4 回归 + 1 项 PCL 一键面板/版本选择回归 + 6 项文档编码守卫回归（`tools/test_review_fixes.py`，共 105 项；本次 **105/105**）接入统一门禁；（新增项 = p187 SBT 网格 icon + 服务端物品、p188 atlas overflow、p189 creative 删除、p190 多客户端独立 trash 回归、p193 Shulker grid 残余、p194 第三 atlas/跨 atlas、p195 交付验证、p196 27 格、p198 文档编码守卫）；`verify_evidence` 另有 `text_encoding` 直接项（`tools/check_text_encoding.py`，跟踪 Markdown 6 条规则，p198）；
- 使用说明与教程 `docs/guide.md`（启动器、PCL 共用、迁移教程、FAQ），界面「使用说明」按钮直接打开；
- 启动器端到端脚本（安装→启动→主菜单，支持 `--version` / `--require` / `--screenshot`）；
- GitHub Actions：push 触发**已验证可用**（`e9ca30c` run `39796030299`；`742d133` run `39799555425`，check-run `build` success，含 API 推送）；此前“push 无 run”是 GitHub Actions `degraded_performance`（22:18 UTC）导致排队，重推 workflow 文件后索引恢复。若再遇无 run，先看 [githubstatus.com](https://www.githubstatus.com)，再重推 workflow 文件刷新索引。

## 二、未完成（如实）

| 项 | 状态 | 说明 |
|---|---|---|
| NeoForge 带第三方模组 / 进世界 | ✅ 已通过：AppleSkin（p127）、Farmer's Delight 内容模组（p128）、Jade 数据同步/HUD（p130）；**专用服务器 + 客户端 join 已通过**（p161，端口 25567；安装时曾因 maven.neoforged.net 超时失败，复用本地 client libraries 后成功）；**带 Farmer's Delight 的专用服务器 + 同模组客户端加入**（p163，端口 25568） |
| Forge 1.20.1 带模组世界 | ✅ 显示类（AppleSkin，p129）+ 内容类（Farmer's Delight，p131）；**专用服务器 + 客户端 join 已通过**（p159：端口 25566）；**带 Farmer's Delight 的专用服务器 + 同模组客户端加入**（p164：端口 25569） |
| 渲染类模组：Sodium | ❌ blocked_static | 1.20.1 的 Sodium 0.5.13 静态探针：missingClass=13、missingMember=15、descMismatch=16（`runs/p158-sodium-probe/`）；**p199 已把 44 条逐条定性**（`docs/sodium-plan.md`）：6 条来自 Sodium 内嵌的 1.20.1 Fabric API 模块、7 条纯 id 变化、7 条签名变化有明确写法、24 条落在被 1.21.1 换掉的即时模式顶点管线 → 仍需重写渲染内核，本轮不做；Iris 兼容分支已在 p142/p143 跑通 |
| ImmediatelyFast 的完整度 | ✅ HUD+物品+overlay 批处理生效；地图 atlas 已恢复并覆盖动态更新 正常退出；VertexBuffer 动态上传 fast path 已启用 | 单人/专用服务器（p134/p141）、soak 95s（p140）、关闭开关归零（p137）、Iris 1.8.1/1.8.14（p142/p143）、shader pack r5.3（p145/p146，hud=11146/11168）、关闭 universal batching 的回退路径（p147）、item per-lighting（p149/p150）；**地图 atlas：p175/p177/p181（动态更新 + 退出清理 + 崩溃修复）**；**VertexBuffer：p178**；私有成员走反射 |
| Shulker 网格预览 | 🟡 部分恢复 | p186：client-side component + wrapper + t2/t4 桥，预览框和 `Diamond ×5` 出现；网格 item icon 仍缺，真实 server item 仍空 |
| TrashSlot 完整 UI 流程 | ✅ empty Delete + Shift+Delete + right-click undelete | p183：Delete 清空；p184：两叠 5+3 跨槽 Shift+Delete；p185：空 cursor 右键取 1 留 4；p63–p65 的移入/取回/clientbound/provider empty 仍有效 |
| mrpack 含 files 的真实包 | ✅ | p160：本地 HTTP 下载 + SHA-1/SHA-512 校验 + overrides 落盘通过；包内含 mod jar，不提交（`runs/p160-mrpack/`） |
| LICENSE | ✅ MIT | 见仓库根目录 `LICENSE`（第三方 CenturyBridge 为 MIT，minecraft-launcher-lib 为 BSD-2 可选依赖） |
| 干净机器构建 / Gradle Wrapper | ⚠️ | 干净目录已验证；无 wrapper（与“仓库不放 jar”策略冲突） |
| 平台 | ⚠️ | 启动器仅 Windows 实测 |

## 三、复现命令

先看 **[使用说明与教程](guide.md)**（安装、PCL 共用、迁移教程、FAQ）。

```text
# 工具链
cd java && gradle test installDist
python tools/test_review_fixes.py
python tools/verify_evidence.py

# 启动器
launcher\run.bat              # 或 python launcher/server.py
python launcher/mclaunch.py verify 1.21.1 <root>
python tools/test_launcher_e2e.py --root <root> --no-install

# CI（push 与 API 推送都会触发；如无 run 先看 githubstatus.com，再重推 workflow 文件）
gh api --method POST repos/SelYio666/mcbridge1201/actions/workflows/ci.yml/dispatches -f ref=master
```

## 四、独立分享文档

`share/download-sources/`：不依赖 GitHub 的下载源速查（自包含 HTML + Markdown + 预览图），
可直接发送文件或部署到任意静态托管，见该目录 README。

## 五、发布

- 仓库：https://github.com/SelYio666/mcbridge1201
- 最新发布：v0.5.5（一键安装到 PCL：图形面板/全版本选择；主工具 v0.5.4）
- 证据索引：`runs/SHA256SUMS.txt`、`docs/STATUS.md`、`docs/review-fixes-2026-10-21.md`


## 六、2026-10-24 更新（p187：Shulker 网格 icon + 服务端物品恢复）

p187 修复两个真实根因并恢复 ShulkerBoxTooltip 网格预览（证据 `runs/p187-grid-draw-probe/`）：

1. **组件读损坏**：桥接/companion 里所有组件"读"都写成 `ItemStack.method_57379(type, null)`——
   该方法是 `set(type, value)`，传 null 等于清空 CONTAINER 组件。服务端同步来的 shulker
   第一次被读取就被清空，这就是 p110/p186 "真实服务端 item 仍是 !minecraft:container" 的根因。
   现统一改为 `method_57353().method_57829(type)`（getComponents().get）。
2. **无 PreviewTooltipData**：转换把 mod 的 ItemStackMixin 全部剥掉（1.20.4 目标已死），
   vanilla `getTooltipData()` 永远 empty，p186 的"框"只是 vanilla 加高的 tooltip 背景。
   companion 1.1.0 现在注入 getTooltipData、注册 component-first provider（17 个 shulker 物品）、
   `CompanionInit` 首个 client tick 注册（registry 解锁 + 优先级覆盖）。
3. mod 默认 `preview.alwaysOn=false`（按住预览键才显示），harness 写
   `config/shulkerboxtooltip.json5` 强制开启。

实测（`result.json`/`client.log`/`grid.png`）：`GRID_DRAWITEMS ... items=1
first=minecraft:diamondx5`、`GRID_DRAWITEM stack=minecraft:diamond count=5`、
`GRID_SERVERBOX slot=3 nonAir=1`（服务端 `/item replace` 放入的真实 shulker，
HUD 源切到 `source=server`），截图网格槽内 diamond 图标 ×5 正常绘制。
AppleSkin 的 `AppleSkinFoodBridge` 同样的 set-as-get 问题一并修复。
未覆盖：FULL 预览类型、多物品网格、真实鼠标 hover 路径（harness 用 HudRenderCallback
驱动同一条管线，OS 光标注入不可靠）、预览键交互。

## 七、2026-10-25 更新（p188：地图 atlas 1024 溢出验证）

p188 补上 p181 留下的 "Atlas overflow (1024 maps) is still untested"（证据
`runs/p188-atlas-overflow/`，实现零改动）：

- 探针用 map 1 的真实 MapState 连续 `MapRenderer.method_1769` 分配 1026 个 map id：
  前 1024 张填满 atlas 0，id 1025/1026 溢出；`map-atlas create id=1` 恰好出现一次；
- packed 编码正确：`mapping1024=7967`（atlas 0 最后一格 31<<8|31）、`mapping1025=65536`
  （atlas 1 tile 0）、`mapping1026=65792`（tile 0,1）；
- `MapRenderer.draw`（HUD 内直调）触发 atlas 1 的真实上传，`atlas1-pixel-check mismatches=0`
  （4 个采样点读回 NativeImage 与 MapState 颜色一致；update marker 有节流所以用像素证明）；
- 正常退出：`map-atlas clear atlases=2`，exit 0，无 crash/errors；
- 门禁：90/90、hashes 1110/1110、verify_evidence passed；沿用 v0.5.5 release。
- 未测：第三个 atlas（2048+ 张）、跨 atlas 同屏视觉、真实服务端 1024+ 张地图端到端。

测试侧记录：integrated server 的 mcfunction 不接受 `item replace ... filled_map[map_id=N]`
组件语法（dedicated server 可过），渲染验证因此改为客户端内 `MapRenderer.draw` 直调；
`NativeImage` 像素读取是 `method_4315(x,y)`（int），`method_4311` 返回 byte。

## 八、2026-10-25 更新（p189/p190：TrashSlot creative 删除 + 多客户端独立 trash）

- **p189 发现并修复真缺陷**：1.21.1 creative 界面（class_481）覆写 hover 处理使
  `AbstractContainerScreen.hoveredSlot` 恒 null，且 SlotWrapper 内部类已删除——转换后的
  TrashSlot creative 删除分支（`getClass() == Slot.class` / SlotWrapper 名字匹配）**永不可达**。
  companion `java/src/trashcreative/`（mod id `trashcreativefix`）重写该分支，实测
  Shift+Delete 连锁 + 普通 Delete + creative 清 trash 全通过；
- **p190 多客户端隔离**：A 右键取 1 / Delete 清空只影响 A 的服务端 trash（5→4→empty），
  B 的服务端 trash 与客户端 UI 全程不变——`reply` 只回发送者（p64 语义的多人侧确认）；
- 门禁：test_review_fixes **92/92**、check_hashes **1143/1143**、verify_evidence passed；
  测试环境已恢复（server 25565 + 原版 trashslot；client ImmediatelyFast + Fabric API + p181 probe）。

## 九、2026-10-25 更新（p191/p192：TrashSlot creative/多客户端残余闭环）

- **p191**：摸清 1.21.1 creative 菜单两种槽型（item tab 纯 Slot hotbar 45..53；inventory tab
  class_484 wrapper，field_7874 无用但列表位置=服务端 InventoryMenu 逐槽一致），companion
  映射泛化。实测主背包格 Delete（slot=18）✓、creative 列表格 Delete 无效（上游语义）✓、
  creative 右键 undelete 不适用（无 trash 画布 + 上游空实现）✓；
- **p192**：三客户端（A/B/C）+ B 主动（右键取 1 → Delete 清空，全程真实 GLFW 回调路径）
  → B 4→3→empty、C 服务端/客户端不变、A 重进后 trash=empty（上游登录重置设计）；
- OS 输入在本机完全不可靠（游戏内鼠标恒停窗口中心、键盘焦点间歇丢失），p191 确立最终
  测试形态：探针写 Mouse raw 字段瞄准 + 在 GLFW 回调边界合成按键（与真实输入同代码路径）；
- 门禁：test_review_fixes **94/94**、check_hashes **1175/1175**、verify_evidence passed；
  测试环境已恢复。TrashSlot 的已验收范围至此覆盖：p63–p65、p183–p185、p189–p192。

## 十、v0.5.6 发布（2026-10-25）

- 主工具便携包 `mcbridge-launcher-0.5.6.zip`（11,960,113 bytes，
  sha256 `f7110027…ec7a`，`tools/test_portable.py` 通过）；
- 新增 companion 资产：`mcbridge-companion-shulkerpreview-1.1.0.jar`
  （sha256 `7d754e5f…d490`，装了转换后 ShulkerBoxTooltip 的客户端需要）、
  `mcbridge-companion-trashcreativefix-1.0.0.jar`（sha256 `f4b79662…a9d0`，
  装了转换后 TrashSlot 的客户端需要）；
- 一键 PCL 资产沿用 v0.5.5（`mcbridge-pcl-panel.zip` 40cfc0ea…、`mcbridge-pcl-setup.zip`
  ade34ecc…，字节一致重新上传）；
- release notes 覆盖 p187–p192 的修复与边界（无性能声明）；tag `v0.5.6`，
  5 个资产的服务端 sha256 与本地一致。

## 十、2026-10-26 更新（p193：Shulker grid 多物品/FULL/真实 hover/服务端 box）

- **p193**：多物品网格（3 钻 + 2 绿宝石）+ FULL 预览 + 真实 tooltip 路径（pre-FULL `DRAWTOOLTIP data=PreviewTooltipData`，p191 的 GLFW 回调级输入）+ 服务端 box（2 钻 + 4 绿宝石，`/item replace container.10`）；`result.json` 4/4 true；`runs/p193-shulker-grid-residual/`（`after-full/after-server/after-compact.png`）；
- 门禁：test_review_fixes **95/95**、check_hashes **1194/1194**、verify_evidence passed；无新 release（v0.5.6，p193 无 mod 改动）；
- 边界：输入是 GLFW 回调级（非 OS 光标）、FULL 依赖 `preview.alwaysOn` + 预览键 342、27 格全满未测。
## 十一、2026-10-26 更新（p194：第三个 atlas + 跨 atlas 同帧）

- **p194**：2050 个 map id（1..2050，复用 map 1 的真实 MapState）：1..1024 → atlas 0，1025..2048 → atlas 1，2049/2050 → atlas 2；`map-atlas create id=2` 恰好一次；`assign map=2049 packed=131072`、`map=2050 packed=131328`；`bind map=map/2049 ... map_atlas/2`；
- HUD 同一帧调用 `MapRenderer.method_1773` 画 map 1/1025/2049（atlas 0/1/2），atlas1/atlas2 的 NativeImage 像素检查均为 0 mismatch；正常退出 `map-atlas clear atlases=3`；`errors=[]`、`crash=null`（`exit_code 1` 是客户端进程，runner exit 0）；证据 `runs/p194-atlas-third/`；
- 门禁：test_review_fixes **96/96**、check_hashes **1206/1206**、verify_evidence passed；无新 release（v0.5.6）；
- 边界：真实服务端 1024+ 张地图端到端未测；HUD 四边形在原点，三 atlas 并排视觉未截；p188 的第三 atlas/跨 atlas 边界关闭，真实服务端 1024+ 仍开放。
## 十二、2026-10-26 更新（p195：v0.5.6 交付验证）

- **portable**：`dist/mcbridge-launcher-0.5.6.zip` 在全新 `work/tmp/p195-portable` 根目录通过 `test_portable.py --version 1.21.1`（deps + `/api/status` + `/guide`，`RESULT: OK`）；证据 `runs/p195-delivery-validation/portable-test.log`；
- **panel UI smoke**：同源 `tools/pcl_panel.py` 打开，103 个正式版、PCL 目录默认值正常（`panel-smoke.png`）；本机 PCL2 路径不存在，完整“安装到 PCL”点击/进度/PCL2 版本刷新未做；panel 资产下载不完整（3,361,813/12,361,982 bytes，`gh release download` 挂起已终止）；
- 门禁：test_review_fixes **97/97**、check_hashes **1212/1212**、verify_evidence passed；无新 release（v0.5.6）；
- 边界：PCL2 缺失、panel 资产不完整、干净/离线主机未验证；v0.5.7 视 p193–p195 与用户确认（目前无用户可见修复，可保持 v0.5.6）。
## 十三、2026-10-26 更新（p196：Shulker grid 27 格全满）

- **p196**：27 种不同物品（diamond/emerald/iron_ingot/.../slime_ball），`GRID_SETRENDER inv=27`、`GRID_DRAWITEMS items=27`，FULL 网格 27 格；server box（2 钻 + 4 绿宝石）与真实 tooltip 路径仍正常；`result.json` 4/4 true；证据 `runs/p196-shulker-grid27/`；
- 预览键重绑定当轮未生效：p196 把 `previewKey` 写进 `preview` 分类（被忽略），F 又触发原版交换副手；p197 已更正（mod 实际读 `controls.previewKey/fullPreviewKey`）；
- 门禁：test_review_fixes **98/98**、check_hashes **1231/1231**、verify_evidence passed；无新 release（v0.5.6）。
## 十四、2026-10-26 更新（p197：Shulker 预览键重绑定）

- **p197**：`javap` 证明 `ShulkerBoxTooltipClient.isKeyPressed` 用 `config.controls.<key>.get().getCode()` + `InputConstants.isKeyDown`（默认 previewKey=340、fullPreviewKey=342）；p196 的“config 被忽略”是字段写错分类导致的误判；
- 配置 `controls.previewKey=key.keyboard.j(74)`、`controls.fullPreviewKey=key.keyboard.k(75)`、`alwaysOn=false`；J/K 无原版绑定，避免 F 交换副手把悬停物品换走；
- 单屏生存背包 + 服务端 27 种物品 shulker box，mod 状态机 `NO_PREVIEW → COMPACT(J) → FULL(J+K) → COMPACT(松 K) → NO_PREVIEW(松 J)`，`GRID_DRAWITEMS items=27`；`result.json` 7/7 true；证据 `runs/p197-preview-key/`；
- 门禁：test_review_fixes **99/99**、check_hashes **1254/1254**、verify_evidence passed；无新 release（无 mod 改动，v0.5.6）；
- 边界：键状态仍在 `InputConstants.isKeyDown` 轮询边界注入，未做 OS 级物理按键；27 格不同 NBT/附魔未测。
