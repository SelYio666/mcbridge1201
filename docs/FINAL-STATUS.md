# mcbridge1201 最终状态（更新至 2026-10-31）

> 定位：**Minecraft 版本迁移与运行辅助工具箱**。迁移与验证归本工具，日常启动交给 PCL。
> 最新发布：[v0.5.8](https://github.com/SelYio666/mcbridge1201/releases/tag/v0.5.8)（PCL 安装器：修复“配置目录不存在仍被使用”）。
> 下文第六节之后是按轮次追加的历史更新；**最新结论以下面这一节和 [report-2026-10-30.md](report-2026-10-30.md) 为准**。

## 最新状态（2026-10-31）

- **发布**：v0.5.8（`mcbridge-pcl-setup.zip` / `mcbridge-pcl-panel.zip`，含 p220 目录修复）；
  v0.5.7 为启动器 UI 打磨；v0.5.6 另含两个 companion jar
  （`shulkerpreview 1.1.0`、`trashcreativefix 1.0.0`）。
- **CI**：最近 5 次 push 触发全部 `success`。
- **本机门禁（10-31 实测）**：`verify_evidence` passed；`test_review_fixes` **466/466**；
  `check_hashes` **1569 ok / 0 mismatch / 0 missing**；单测 **32 / 0 failures**；
  `check_text_encoding` 248 个 Markdown 全干净。
- **真机闭环**：
  - PCL2 **2.99.0.0** 上面板真的点“安装”：10.3 s，版本列表出现新版本（p212）；
  - 从 PCL2 **离线启动** 1.20.4（p213）与 **1.21.1**（p214）→ 标题界面 → 点进世界；
  - Cloth Config 配置界面在转换后的 AppleSkin 里可打开、点开关值真的翻转（p210）。
- **引擎侧**：ImmediatelyFast 1.21.1 移植验证（HUD/物品/地图 atlas/VertexBuffer）、
  Shulker 网格与服务端物品恢复、TrashSlot UI 全链路（Delete/Shift+Delete/右键取回/多客户端隔离）、
  Forge/NeoForge 专用服务器与客户端加入、mrpack 真实 files。
- **仍未完成**：多客户端/跨机器延迟；创建世界页底部按钮对合成点击无响应（p215 未形成结论）；
  1.20.4 进世界瞬间的 `Not a string` 未溯源；进世界后的玩法/多人/“带转换模组进世界”未验；
  Sodium 渲染内核评估为不可行；文本编码事故的写入者未定位。
- **细节**：[report-2026-10-30.md](report-2026-10-30.md)、[remaining-work.md](remaining-work.md)；
  p218 的 22 秒通俗视频在 `runs/p218-pcl-import-video/`。

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
| 一键安装到 PCL 图形面板/版本选择 | ✅ v0.5.8：`mcbridge-pcl-panel.zip` + `mcbridge-pcl-setup.zip`；版本下拉/搜索/进度/PCL2 自动检测；`from_source_install` 支持 release/snapshot/old_* / all / latest-snapshot；PCL2 2.13.1.1 实测 | `share/pcl-onclick/`、`runs/p137-pcl2-onclick/` |
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

- 单测 25/25；`verify_evidence` passed；哈希 1269 项（以 `runs/SHA256SUMS.txt` 实际行数为准；p201 删掉 20 条指向 gitignored `work/` 的条目）；桥一致性 0（ImmediatelyFast 端口 jar，p165/p181）；mixin 审计 inert=2（`listed=37`；p175 恢复 map mixin、p177 补多地图/展示框、p178 启用 VertexBuffer；剩余两个是官方 1.21.1 已删除的 1.20.4 遗留类，见 `runs/p180-inert-closure/`）；
- 外部问题汇总 20 项回归 + 9 项 NeoForge 安装/启动回归 + 10 项目录/兼容/说明回归 + 1 项加载器安装回归 + 8 项 ImmediatelyFast 移植回归 + 1 项便携包回归 + 24 项下载源/进度回归 + 6 项地图 atlas 回归 + 2 项 VertexBuffer 回归 + 1 项死 mixin 防误登记回归 + 1 项 atlas closed 守卫回归 + 1 项 TrashSlot UI empty 键回归 + 1 项 TrashSlot Shift+Delete 回归 + 1 项 TrashSlot right-click undelete 回归 + 1 项 Shulker 网格 wrapper/t2/t4 回归 + 1 项 PCL 一键面板/版本选择回归 + 6 项文档编码守卫回归 + 3 项转义控制字符回归 + 16 项 atlas 逐 id 落点/并排回归 + 6 项行尾确定性回归 + 32 项 OS 光标悬停/异质 NBT 回归（`tools/test_review_fixes.py`，共 162 项；本次 **162/162**）接入统一门禁；（新增项 = p187 SBT 网格 icon + 服务端物品、p188 atlas overflow、p189 creative 删除、p190 多客户端独立 trash 回归、p193 Shulker grid 残余、p194 第三 atlas/跨 atlas、p195 交付验证、p196 27 格、p198 文档编码守卫、p200 atlas 逐 id 落点、p202 OS 光标悬停 + 异质 NBT）；`verify_evidence` 另有 `text_encoding` 直接项（`tools/check_text_encoding.py`，跟踪 Markdown 8 条规则，p198/p200）；
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
- 最新发布：**v0.5.8**（PCL 安装器缺失目录修复）；PCL 面板/全版本选择继续适用
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
- **panel UI smoke**：同源 `tools/pcl_panel.py` 打开，103 个正式版、PCL 目录默认值正常（`panel-smoke.png`）；完整“安装到 PCL”点击/进度/PCL2 版本刷新未做；panel 资产下载不完整（3,361,813/12,361,982 bytes，`gh release download` 挂起已终止）；本行原来写的“本机 PCL2 路径不存在”已被 p211 更正——见第二十六节；
- 门禁：test_review_fixes **97/97**、check_hashes **1212/1212**、verify_evidence passed；无新 release（v0.5.6）；
- 边界：PCL2 当时未被检测到（p211 在另一个路径找到 2.13.1.1）、panel 资产不完整、干净/离线主机未验证；v0.5.7 视 p193–p195 与用户确认（目前无用户可见修复，可保持 v0.5.6）。
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

## 十五、2026-10-28 更新（p200：三张 atlas 并排 + 逐张 tile 落点）

- **p200**：2050 个 map id 全部**逐个**校验，不是抽样：每个 id 把自身 12 位写进 tile 第 0 行（最亮/最暗调色板色），走公共 update+draw 后从**该 id 报告出来的槽位**读回，`mapping-mismatch=0 pixel-verified=2050 pixel-mismatch=0`；p194 的盲点是 2050 个 id 共用同一个 MapState，槽位错位时"像素等于地图颜色"照样成立；
- 三张 4096² atlas 首次**同屏并排**：map 1/1025/2049 各持自己的 MapState（共用 state 会让后写的颜色刷掉另外两格），在 GUI `8,8 / 144,8 / 280,8` 画出，截图实测三块 256×256、间距 272、窗口偏移 `[8,31]` 三块一致（`layout-check.json`、`layout-crop.png`）；
- 内存：三张 NativeImage 201,326,592 字节（4096² 由"读 (4095,4095) 成功、读 (4096,4096) 抛异常"证明，不是假定）；进程工作集分配前 1556.0 → 分配后 2016.9 MB（**+460.9**），重复三次 +460.9/+548.1/+486.5（峰值 2192.0–2247.3）；**显存未测**，报告里不写；
- 退出 `map-atlas clear atlases=3`，`errors=[]`、`crash=null`；证据 `runs/p200-atlas-layout/`（`memory-runs.json` 三次运行、`repeat-runs.log` 重复运行的关键行摘录、`gate-review-fixes.log`）；
- 回归：新增 `test_map_atlas_layout_evidence()`（16 条），从提交的日志与截图校验结果**重算** README 里的每个数字，改日志/换截图/报告漂移都会失败；门禁 `124/124`、`check_hashes` **1289/1289**、`verify_evidence` passed、`check_text_encoding` 227 个 md 全绿；
- **顺手修掉的第二类文档损伤**：`docs/remaining-work.md` 里有两处"转义被解释"——`\tools/pcl_panel.py` 变成 TAB+`ools/…`、`(runs/p195-…)` 变成 `(CRuns/…`（`\t`/`\r` 被写成控制字符），p198 的 6 条规则都看不见。已按上下文修回原文，并给 `tools/check_text_encoding.py` 加 `control-tab`/`control-cr` 两条规则（``` 围栏内的 TAB 合法，不算），配 3 条回归：造 TAB+CR 样本必失败、规则名要出现、围栏内 TAB 不得报；
- 边界：真实专用服务器下发 1024+ 张地图仍未做；只用到 2050 格（未压满 3072）；VRAM 未测。

## 十六、2026-10-28 更新（p201：哈希清单在干净 clone 里可验证）

- **触发**：写"干净机器交付"之前先 `git clone` 自己跑门禁，p200 那版的 `check_hashes` 给 `ok=646 mismatch=623 missing=20`，而本机是 1289/1289——清单只在作者机上成立；
- **两个原因**：① `core.autocrlf=true` 且仓库无 `.gitattributes`，git 提交归一成 LF、检出写回 CRLF，而哈希取自一个 1224 LF / 422 CRLF / 264 混合的工作区，凡是本机是 CRLF 的文件，清单记的是别人拿不到的字节；② 20 条清单指向 gitignored 的 `work/` 构建产物，干净 clone 必然 missing；
- **修法**：`.gitattributes` 钉 `* -text`（提交什么落地就是什么；`launcher/run.bat` 是 LF 提交且在清单里，给 `.bat` 加 `eol=crlf` 反而会让它验不过）；`git checkout-index -a -f` 把工作区归一到 blob 字节（686 个"改动"纯是行尾：394940 insertions = 394940 deletions）；删掉 20 条 `work/` 条目；
- **顺手的洞**：`hash_evidence.py` 用 `git ls-files` 判断"是否跟踪"，git 默认给非 ASCII 路径加引号转义，导致 3 个已跟踪的 `share/` 交付物被误判未跟踪；改 `git ls-files -z` 后清零；
- **证据**：同一条命令、只差一个提交——clone `82e4e9f` = `ok=646 mismatch=623 missing=20`，clone `2e34a9a` = `ok=1269 mismatch=0 missing=0`，`audit_eol` 1269/1269 可复现（`runs/p201-eol-determinism/clone-before.log`、`clone-after.log`）；
- **回归 6 条**（`test_eol_determinism`）：`.gitattributes` 钉 `-text`、已提交文件零漂移、清单无未跟踪路径；未提交的改动允许漂移（清单是对已提交字节的声明）；
- 门禁：`test_review_fixes` **130/130**、`check_hashes` **1269/1269**、`verify_evidence` passed、227 个 md 全绿；
- 边界：clone 里 `test_review_fixes` 是 **125/125（`ISSUE-02` 组 skip，需已构建的 Java CLI / 网络）**，作者机 130/130（`clone-head.log`）；只在 Windows / Git for Windows 实跑过，Linux/macOS 上 `* -text` 应是无操作但未验证；无 release 变化。

## 十七、2026-10-28 更新（p202：OS 光标级悬停 + 27 格异质 NBT）

- **悬停**：p191/p193/p197 的 hover 都是探针用 accessor 写 `Mouse.field_1795/1794` 摆出来的。p202 的探针**不写鼠标状态**（`MouseReadAccessor`、`HandledScreenAccessor` 都只有 getter，编译期就没有 setter），改由外部进程把**真实光标**移到探针公布的窗口坐标（`P202_TARGET winx=686 winy=378`）；位置只能经 `WM_MOUSEMOVE → GLFW callback → Mouse.onCursorPos → Mouse.tick → Screen.render(mouseX,mouseY) → HandledScreen.focusedSlot` 变成悬停；
- **四路读数一致**：`P202_HOVER_OK` 行同时给出 `glfw=686.0,378.0 raw=686.0,378.0 mouse=686.0,378.0 target=686.0,378.0`，且 `index=10 keysSent=false` —— 悬停发生时一个合成按键都还没发；
- **一条继承结论被推翻**：p191/p193/p197 的注释写着"这台机器收不到 OS 光标移动（RES_MOUSE 一直停在窗口中心）"。第 1 轮用 `SetCursorPos` 且窗口没置顶 → 确实不悬停；加 `SetWindowPos(HWND_TOPMOST)` 置顶后，第 2/3 轮（SendInput）与**控制组（只用 SetCursorPos）**都悬停（`repeat/run3-control-warp.log`）。所以问题从来不是注入机制，而是**光标底下压着的窗口不是游戏**。`harness.log` 每次移动都记 `WindowFromPoint` 与 `underIsGame`；p193/p197 的 README 已各加一行指向本次更正；
- **27 格异质 NBT**：服务端 `/item replace` 下发 27 格，每格不同 item id、不同数量（1–3）、不同自定义名（`S00`…`S26`），并混入 `lore`（2 行）、`enchantments`（sharpness 1–5）、`custom_model_data`（100+i）。客户端读回 `stacks=27 distinctComponents=27 distinctItems=27 distinctNames=27`；渲染器 `P202_DRAWITEM index=0..26` 共 27 格、27 个不同组件映射、`type=FULL items=27`；
- **截图是真量出来的**：`verify_grid.py` 用亮度剖面**自相关**求周期（列 36 / 行 36，峰值 56817 vs 次峰 34665），相位取"离探针报的面板原点最近且最暗"的格线（列 18 / 行 18 → 原点 732,423），再取 27 个 `32×32`（16×scale）图元：**无空格、无纯色格、27 个哈希互不相同**；
- **两次返工记在报告里**：① 外层组件键写成 `shulker_box["minecraft:container"=…]` → 服务端 `Unknown item component 'minecraft:'`；为此写了 `check_snbt.py`（只起服务端、用解析阶段验 SNBT，不用等客户端 3 分钟）。② 截图校验器第一版只 hash 了格子前 8 字节（27 格同长），第二版用"边框环最干净"当对齐判据（槽位自带描边，区分度仅 6%），都推翻重写；
- 回归：新增 `test_hover_and_heterogeneous_nbt()`（32 条），从 `client.log`/`harness.log`/`grid-check.json`/`result.json` 与 **PNG 的 IHDR 头**重算报告里的每个数字；
- 门禁：`test_review_fixes` **162/162**、`check_hashes` **1301/1301**、`verify_evidence` passed、228 个 md 全绿（p203 之后为 188/188 与 1324/1324，见下节）；
- 边界：单机单显示器、DPI 未变；FULL 仍需在 `InputConstants.isKeyDown` 轮询边界伪造 J(74)/K(75)（悬停本身不需要，见 `keysSent=false`）；未测嵌套潜影盒、逐格 `custom_model_data` 的模型差异；无新 release（v0.5.6，只加探针）。

## 十八、2026-10-28 更新（p203：两个客户端同一服务端 tick 并发操作垃圾桶）

p192 结尾留下的 "concurrent same-tick trash operations from two clients" 与 "four+ clients" 两条，
关掉第一条。

- **判据放在服务端**：客户端每 50 ms 一 tick，"间隔 2 ms 可能跨 tick、间隔 40 ms 可能同 tick"，
  所以"并发"只能由有权威 tick 计数器的一侧定义。探针自己在 `END_SERVER_TICK` 里 `ticks++`，
  并在 `TrashHelper.setTrashItem`（玩家持久化 NBT 的唯一写入口）打 `tick/thread/side/wall/seeding`;
- **真的挤进同一 tick**：两个客户端都 READY 后 harness 才发同一个 epoch-ms，客户端在目标前 60 ms
  自旋到点再走真实回调路径开火，`P203_FIRE driftMs=0`（两边 `epochMs` 完全相同）；
- **结果**：`P203_SET … tick=819 … GridUser stack=empty` 与 `… tick=819 … TrashB
  stack=minecraft:diamondx3`，相隔 4 ms、同 tick、同在 `Server thread`；两条 serverbound 消息
  （`MessageDeleteFromSlot`、`MessageTrashSlotClick`）也在 tick 819。两种操作故意不同，串台会显示成
  对方的数值；B 客户端读回 `carried=minecraft:diamondx1`；
- **一次踩空**：先混入 `ServerPlayNetworkHandler.onCustomPayload`，`-Dmixin.debug=true` 确认
  `Mixing PacketMixin … into class_3244` 生效，但正式跑连一行 `P203_PKT` 都没有——Balm 桥的
  serverbound 消息不走这条派发。没有硬凑，把戳挪到状态写入点；
- **第二次返工**：分析器取"每个玩家第一条写入"，取到的是登录重置的两条 `empty`（tick 315/671，
  相隔 17 s），得出 `same_server_tick=false`。改成以开火时刻开窗（`[fire-500, fire+5000]`），
  窗口之前的写入单列成 `mutations_before_fire`；
- 回归：新增 `test_trash_concurrent_same_tick()`（26 条），从 `server.log`/`result.json`/两份客户端
  日志重算，并校验 `repeat/round1-server.log` 那一轮同样同 tick（tick 905）；
- 门禁：`test_review_fixes` **188/188**、`check_hashes` **1324/1324**、`verify_evidence` passed、
  228 个 md 全绿；无新 release（v0.5.6，只加探针）；
- 边界：四个以上客户端、同一玩家的同 tick 两次操作、跨机器真实延迟未测；本轮截图未拍成
  （`_grab_window` 需要 Pillow，本机没有），两个客户端的 UI 状态是从日志的 `P203_TRASH`（含
  `carried`）读的，不是看图。

## 十九、2026-10-28 更新（p208：干净环境交付验证 + 跨平台审计）

p195 结尾的 "clean-host portable remain open" 与 p201 的 "Verified on Windows / Git for Windows only" 各关一半。

- **干净环境**：`tools/test_portable.py` 用的是 `dict(os.environ, ...)`，继承调用者环境，因此只能证明
  "在造它的机器上能跑"。`runs/p208-cross-platform/run_clean_host.py` 改为构造环境：`PATH` 只留
  `System32` 与 `Windows`，`PYTHON*`/`JAVA_HOME` 移除，`HOME`/`USERPROFILE`/`TEMP`/`APPDATA`/
  `LOCALAPPDATA` 全指向新建空目录；**先证明剥干净**（同环境 `which python`/`which java` 均为 `None`），
  再验证包：`sys.prefix` 落在解压目录内、注入 `PYTHONHOME`/`PYTHONPATH` 不影响、`/api/status` 200、
  `/guide` 200、不含任何 `.jar`、只有 `run.bat`。**8/8**，照发原件与叠加当前源码各一份；
- **四个真缺陷**（`probe_behaviour.py` 修前 2/6 → 修后 6/6）：`default_root()` 在 `APPDATA` 未设置时
  得到相对路径 `.minecraft`（会认领启动器 CWD，这条在纯 Windows 上就能复现）；`find_java()` 只找
  `bin/java.exe`，POSIX 下 `JAVA_HOME` 被无视（探针修前返回的是另一个 JDK）；macOS 被送进 `xdg-open`
  且无异常保护；一个从未引用的 `C://Program Files\Java\...` 常量（已删）。`LOCALAPPDATA` 的回退与
  `pick_java` 的 `windows-x64` 目录名也改成按平台取。Windows 侧返回值实测不变；
- **打包脚本的假成功**：`vendor_deps()` 静默跳过 import 不到的依赖，调用处忽略返回值，零依赖也
  `done`+退出码 0。新增 `require_vendored`，缺 `minecraft_launcher_lib` 即 `rc=1` 并拒绝出包
  （`--allow-missing-deps` 为显式开关），`build-blocked.log` 是那一跑的原始输出；
- **跨平台只审计**：WSL 在本机被安全策略拦住（Program Blacklist），Linux 未执行，不绕过。静态命中
  28→22、**未保护 24→4**（剩余 4 条全是便携包的 Windows-only 构造：`python-embed-amd64` + `run.bat`）；
  POSIX 模拟（`sys.platform=linux` + 屏蔽 `winreg`/`msvcrt`/`_winapi`）下交付模块 **4/4** 可导入，
  说明启动器没有 Windows-only 的导入依赖；
- 三次"测量工具坏了"被记下来（翻 `sys.platform` 太早导致 `_posixsubprocess`、翻 `os.name` 导致
  `PosixPath` 抛错、中文路径下内嵌 Python 用 cp936 写 stdout），详见 `runs/p208-cross-platform/README.md`；
- 回归：新增 `test_cross_platform_delivery()`（39 条），从四份 JSON 与两份日志**重算**，并直接断言
  `require_vendored` 的行为与 `java_binary()`/`open_in_explorer()` 的分支；
- 门禁：`test_review_fixes` **227/227**、`check_hashes` **1338/1338**、`verify_evidence` passed、
  228 个 md 全绿；无新 release（v0.5.6 不变）；
- 边界：同一台机器不同环境而非另一台电脑；无 POSIX 内核参与；便携包按构造 Windows-only；
  `install_jvm_runtime` 的下载未跑；完整重打包因本机无 `minecraft_launcher_lib` 未做，改用的是
  "当前源码叠加到 0.5.6 包"。

## 二十、2026-10-28 更新（p204：真实滚轮 + 真实键盘打进 Mod Menu）

任务 5 的输入半条关闭；Cloth Config 半条有了带栈的结论（p210 已把它打通，见第二十五节）。

- **p104 的归因是错的**：它把"三种注入方式之后 scroll 仍是 0.0"记成"本机输入注入限制"。p202 已经证明
  同一类失败的真因是**游戏窗口不在最上层**，光标底下的点是终端的。p204 用同一套修法
  （`ShowWindow(SW_RESTORE)` + `SetWindowPos(HWND_TOPMOST)` + `BringWindowToTop`），并且每次移动都把
  `WindowFromPoint` 是否落在游戏窗口记进 `harness.log`；
- **滚轮**：探针只有 getter（`method_25341`/`method_25331`/`method_25396`/`field_22741`/控件矩形/
  `method_1882`），`method_60321` 在源码里一次都没出现。九格滚轮 → `18/36/54/72/90/108/126/144`，
  第九格被 `clamp(0,max)` 夹到 **147**（`itemHeight=36`，原版公式是 `scroll -= amount * itemHeight/2`）；
  九格在 `Mouse.method_1598` 各留一条 `dy=-1.0`；
- **两个对照**：窗口外滚 9 格 → **0 事件、列表不动**；窗口内右侧面板滚 9 格 → 事件到了（`-1`、`-8`
  两条，合计 −9）、**列表不动**。后者同时说明刻度没被注入器放大或缩小；
- **键盘**：真实左键点搜索框后 `searchFocused=true`，`SendInput` 的 `KEYEVENTF_UNICODE` 送 `m/e/n/u`，
  文本字段收到四条 `P204_CHAR`、`text="menu"`、条目 **11→1**、`max` 147→0。键事件是 `code=-1`
  （`VK_PACKET` → `GLFW_KEY_UNKNOWN`），字符从 char 回调进，所以"按键数"不是证据；
- **键盘需要真焦点**：滚轮跟着光标底下的窗口，键盘跟着前台窗口。测试前显式查
  `GetForegroundWindow()==hwnd`，抢不到就 `AttachThreadInput` 借前台线程的权限再 `SetForegroundWindow`；
- **Cloth Config 当时打不开，现在打开了**（p210，见本文第二十一节）：环境里唯一的一份是 1.20.1 的 JiJ
  （`cloth-config-fabric-11.1.136`，藏在 AppleSkin / ShulkerBoxTooltip 的 `META-INF/jars/`），
  `ConfigBuilderImpl.<init>` 读 `class_437.field_44669`（1.21.1 已移除）直接 `NoSuchFieldError`；
  Mod Menu 的 `ModsScreen` 初始化时替每个模组问配置界面，`appleskin`/`fallingtree`/
  `shulkerboxtooltip`/`trashslot` 四家各炸一次。p210 把这份 JiJ 抽出来打到 1.21.1 再塞回去，
  控制台的 5 层断点 + Cloth demo 的 2 个尾巴逐条桥接（`runs/p210-cloth-config/`）；
- **顺手纠正 p94**：它写"截图里能看到列表行"，但自己的两张截图里列表是全黑的；p204 四张也一样。视觉校验
  因此做在**滚动条**上（控件按滚动量算出来的）：一格位移预测 `18/147×(514−328)=23`、实测 **22**；满格
  预测 186、实测 **184**；过滤后（max=0）不画滑杆；
- 回归：新增 `test_real_wheel_input()`（33 条），从 `client.log`/`harness.log`/两份 `result.json`/
  `scroll-check.json` **重算**，并直接检查探针源码里没有 `setScrollAmount`；
- 门禁：`test_review_fixes` **260/260**、`check_hashes` 见提交说明、`verify_evidence` passed；
  无新 release（v0.5.6 不变）；
- 边界：单机单显示器、窗口 1280×720 / guiScale 2；只测 Mod Menu 的列表与搜索框；方向键/PageDown 未测
  （`KEYEVENTF_UNICODE` 只能送字符）；列表行不画是独立缺陷，本轮没修也没掩盖；只有两次运行。

## 二十一、2026-10-28 更新（p205：Mod Menu 列表行修复）

任务 5 落后的一条真缺陷关闭：列表原本只画黑底不画行。

- **根因**：`ModMenuListRenderBridge.renderList` 把 `left, top` 传给了 `Entry.render`，而原版
  参数是 `(ctx, index, y, x, width, height, ...)`。行底色由桥自己 `fill(left, top, ...)` 画，
  所以「行在、行里没东西」。证据：`class_350.method_44397` 与 `ModListEntry.method_25343` 的
  字节码，加修前截图里列表区 0 亮像素；
- **修法**（逐条对齐原版）：y 在前 x 在后；行宽 `getRowWidth()`（294）；行高 `itemHeight - 4`；
  可见性 `getY()`/`getBottom()`（`method_46427`/`method_55443`）；hovered 取
  `getEntryAtPosition`（`method_25308`）；先 `method_49568`（`Entry.drawBorder`）再
  `method_25343`；
- **匹配对照**（同一客户端/模组/窗口/光标点，只换桥）：0 亮像素 / 0 彩色像素 / 0 图标条带
  → 11147 / 20211 / 6 条（高度 51/44/11/67/63/74 px，判据取 30–90 px 的条带 ≥5 条）；
  两格滚轮 `scroll 0→18`，行整体上移 **−36** 设备像素，互相关最优点就是 −36；
- **调试行**：`-Dmcbridge.listrender.debug=true` 才打印
  `P205_LIST class=ModListWidget count=11 left=6 rowWidth=294 itemHeight=36 rows=67..324`，
  另有一行 `DescriptionListWidget count=0`（描述面板这一轮没选中模组，未验证）；
- **附带修复**：`launcher/mclaunch.py:build_command` 的 `extra_jvm` 形参从未被使用，导致第一次
  带 `-D` 的运行根本没带上标志（`P205 missing`）。两条组装路径都插入 `extra_jvm`，`launch()`
  透传，回归里有断言；
- **构建**：只重编 `ModMenuListRenderBridge` 一个类并用 `tools/inject_bridges.py` 注入
  （`build.py` 有日志：旧类 `48515717…` → 新类 `3336cf73…`，jar
  `9cb27e5455a2a01eb6a653111a91790184be1cd9f91367cd4ff23d51e65d9b0c`）。全量重打包仍应走
  `patch --bridge-dir`；
- 回归：新增 `test_modmenu_rows()`（27 条），从 `rows-check.json`、两份 `result.json`、
  `build.log`、桥源码与 `build_command` 实算；
- 边界：单机单显示器、guiScale 2；只验证模组列表；纹理背景未恢复（平色 `0x80000000`），
  选中高亮未画，描述面板未验证；Cloth 配置界面这一轮还打不开（p210 已解决）。

## 二十二、2026-10-29 更新（p206：选中行高亮 + 描述面板空的原因）

p205 留下的两条尾巴：一条收掉，一条查到底并如实标记为未修。

- **高亮按原版复刻**：`EntryListWidget.method_44398` 的画法是「选中色条（上下各溢出 2 px）+ 内缩 1 px 的黑芯」，也就是
  原版的"选中"其实是 1 px 描边。桥调用不到这个方法（redirect 只替换被替换方法的方法体），所以从其字节码逐条重写
  （`method_44398` 的两处 `method_25294`、`hasFocus() ? -1 : -8355712`、边框 `-16777216`）；
- **有意偏离**：1 px 白边在近黑平色行底上几乎不可见，因此再铺一层半透明底（`0x40FFFFFF` / `0x24FFFFFF`），代码注释、
  run README 与本节都写明这是偏离，不是原版行为；
- **匹配对照**（同客户端/11 模组/同窗口 guiScale 2/同一光标点 `(632,626)`/同一次真实左键）：p205 的 jar 变化 **92** 像素、
  **0 条带**；本轮 jar 变化 **47602** 像素，**变亮一条** `378..463`（86 px，预测 72）落在点中的第 3 行，**变暗一条**
  `165..244` 落在原先选中的第 0 行；`P205_SELECT` 从 `selected=0 focused=false` 到 `selected=3 focused=true`；
- **判据**：`verify_rows.py` 做有符号差分（变亮/变暗分开计），按行统计超过行宽 40% 的变化合并成条带；10 项全过
  （控制组无条带、变化量 >3×、恰好一增一减、高度 ±16、位置 ±12、选中号与焦点、描述面板在两份运行里都为 0）；
- **描述面板为空的原因（未修）**：`DescriptionListWidget.method_48579` 在打补丁的 jar 里只剩
  `ModMenuListRenderBridge.renderList(...)` 一次调用（`bytecode/render-redirected.txt`，12 行字节码）；而它的原始方法体
  （`bytecode/render-original.txt`，851 行）前 1397 个字节码是**建行**——`parent.getSelectedEntry()`、与 `lastSelected` 比较、
  `method_25339()` 清空、`method_25307(-MAX)` 回顶、`getTranslatedDescription()` 换行后逐行 `new DescriptionEntry(...)`
  （共 24 处构造），之后才是 17 处 tombstone 的 1.20.1 `BufferBuilder` 管线。整段替换等于把建行的副作用一起删了，
  所以 `count` 每帧为 0，面板只剩 ModsScreen 画的图标/名字/两枚按钮；
- **顺带**：`run.py` 的置顶改为重试三次并逐次记录 `underIsGame`（本轮第一次运行就撞上系统忽略 `SetWindowPos`，直接退出而不是
  带着空点击继续跑）；
- 回归：新增 `test_modmenu_selection()`（25 条），并把 p205 那条"只有一处 println"改成"每处 println 都在同一个 DEBUG 门后"；
- 门禁：`test_review_fixes` **312/312**；`check_hashes`、`verify_evidence`、`check_text_encoding` 见提交说明；
- 边界：单机单显示器、guiScale 2；只点第 3 行；截图有 +8 px 竖直偏差（用相对间距校验）；描述面板仍空。

## 二十三、2026-10-29 更新（p207：描述面板真的有字了）

p206 只诊断没修的那条，这一轮修掉了，方式是给 redirect 加一种新形态而不是重写 Mod Menu 的建行逻辑。

- **新能力 `keepPrefixBeforeTombstones`**（`RuleSet.BodyRedirect` 的字段 + `JarPatcher.keepPrefixThenCall()`）：
  从方法头找到第一条引用 tombstone 桩的指令，从它往前找**块入口 label**，保留之前的一切，之后整体换成
  `INVOKESTATIC bridge` + `RETURN`。**块入口优先取被跳转或异常表引用的 label**，找不到才退回最近的普通 label——
  这一条是本轮的真 bug：取"最近的 label"会切在块内部的 1397/1402，产物尾部残留 `class_289.method_1348()`
  与一次 `astore 6`（没人读的死语句）；改对之后残留消失；
- **切错不报错会变成运行期 `VerifyError`，所以三条前置检查抛异常**：保留段跳进被替换的尾部、保留段仍引用
  `centurybridge/gen/*`、被丢的尾部在写本类字段（后者等于丢状态变化，正是 p206 缺陷的另一种形状）；
  找不到 tombstone 也拒绝，而不是"什么都没做报成功"；
- **规则一条拆两条**：`modmenu.description.render-tail`（`method_25394`）与 `modmenu.description.render-tail-renamed`
  （`method_48579`），都带 `"keepPrefixBeforeTombstones": true`，一个 jar 最多命中一条；
- **匹配对照**（同客户端/11 模组/同窗口 guiScale 2/同一光标点/同一次真实左键点第 3 行，只换 `modmenu.jar`）：
  p206 的 jar `count=0`、`box=0,108`、`firstEntry=none`、面板 1 条带 204 px；本轮 `count=13`、`box=328,108`、
  `legacy=true getX=328`、`firstEntry=…DescriptionEntry`、7 条带 2920 px；两次都选中第 3 行，ModListWidget 几何未变；
- **顺手修掉一个真 bug**：面板一直画在 `x=0`。`DescriptionListWidget.method_46426()`（1.21.1 的 `getX()`）返回 0，
  因为 Mod Menu 用 1.20.1 的 `setLeftPos` 定位，而 `LegacyParentWidget` 复刻它时只写了 `field_19088`、从未同步
  `ClickableWidget.x`——**不止画错位置，面板区域里所有点击与滚轮都落到了 ModListWidget 上**。修法两头：
  `method_25333` 末尾补 `method_46421(left)`；桥优先读 legacy 四字段，没有才退回 1.21.1 访问器（`fieldOrNull`）；
- **面板画成一块底**（`0x80000000`），行条带只在 `if (!panel)` 时画（否则正文是斑马纹）；补 `drawScrollBar()`
  （右内缩 2 px、宽 6 px、平色），**只在 `maxScroll > 0` 时画**；
- **字节码判据**：产物 `method_48579` 550 行 javap，仍有 `method_25396` 与 24 处 `DescriptionEntry`（建行活着），
  **0 处 `Tombstones`**，尾部只剩 `renderDescription` + `return`；被切的方法体与 p206 记录逐行相同
  （843 行是 846 行的前缀，p206 的 dump 停在最后一个 tombstone）；相对 p206 的 jar 只有 3 个 class 变
  （`DescriptionListWidget` 9045→13335、`ModMenuListRenderBridge` 7278→9275、`LegacyParentWidget` 790→824）；
- 回归：新增 `test_modmenu_description()`（34 条）与 Java 侧的 `JarPatcherKeepPrefixTest`（3 例：保留前缀、
  拒绝跳进尾部、拒绝找不到 tombstone）；
- 门禁：`test_review_fixes` **346/346**；`check_hashes`、`verify_evidence`、`check_text_encoding` 见提交说明；
- 边界：只点第 3 行、一种描述长度；**滚动条分支本轮未被执行**（`maxScroll=0`），判据里如实打印「未绘制」而
  不算通过；面板底与滚动条是平色，原版贴图 sprite 未复刻；`legacy=true` 只对转换来的 1.20.1 子类成立。

## 二十四、2026-10-30 更新（p209：滚轮真的能滚描述面板）

p207 留下的"写了但没跑过"的那段，这一轮跑起来，并证明滚轮在两个列表之间路由正确。

- **不造数据，压窄窗口**：1280 → 800 px（guiScale 2 不变），面板 312 → 192 px 宽，换行变多；扫过 7 个可见行，
  只有第 5 行需要滚（78 行 ≈ 936 px vs 216 px 面板，`maxScroll=568`）。哪一行能滚是量出来的；
- **两个方向都测**（同一次运行）：面板上三格滚轮 → 面板 `0→10`、滑块 `110+58→113+58`、模组列表 `0→0`；
  模组列表上同样三格 → 模组列表 `0→36`、面板 `10→10`；
- **一次滚轮格 = `itemHeight/2`**（面板 5、列表 18，后者 p204 逐格量到）；三格批次实际落地 2 格（10、36），
  另一次落地 3 格（面板 15），所以判据比方向与比例而不是总数；
- **补上旧调试行的自盲**：`P207_SCROLL` 以前打在早退之后，"没滚"与"没跑到"不可区分（对照组第 6 行仍报上一行的
  `max=568`）；现在状态变化就打一次并带 `drawn=`/`view=`，空行如实 `max=0 drawn=false`；
- **探针的坑写进证据**：`p204` 探针的 `findList()` 挑 `getMaxScroll()` 最大的 `class_350`，面板可滚之后它从模组
  列表换成面板；因此"模组列表动没动"改从桥的 `P205_LIST` 行读（新增 `scroll=`/`max=`），`result.json` 记
  `probe_state_targets=[11, 78]`；
- **像素**：面板右缘滑块高 116 设备像素（= 58 gui，与公式一致），滚动 10 px 后下移 6 设备像素（比例算 5.4，
  非 1:1；第一版判据按 1:1 写误判了一次正确绘制，已记录）；正文互相关位移 −20 设备像素，零位移分数 5.69 vs 1.53；
- 回归：新增 `test_modmenu_scroll()`（24 条），并放宽 p207 里"滚动条只在该画时画"的断言（条件改成命名标志，
  语义不变）；
- 门禁：`test_review_fixes` **370/370**；`check_hashes`、`verify_evidence`、`check_text_encoding` 见提交说明；
- 边界：gui 宽 400 下面板左右各剩 2 px，该宽度下的换行数是本轮特有的；只测 7 个可见行；滚轮落地 2~3 格不稳定；
  滑块仍是平色近似；触摸板亚格输入与 Shift 横向滚轮未测。

## 二十五、2026-10-30 更新（p210：Cloth Config 配置界面能打开、画出 13 行、点得动）

AppleSkin 的配置界面是 1.20.1 的 Cloth Config 11.1.136（jar-in-jar）画的，不是 AppleSkin 画的。
这一轮把它抽出来、打到 1.21.1、塞回去，并逐层记录退化。

- **控制组（不修就是打不开）**：`work/client/appleskin-patched.jar`
  （`b415bfc2…`，1104012）→ `config.ok=false`，`NoSuchFieldError: class_437 … field_44669`，
  栈在 `ConfigBuilderImpl.<init>`，5 个模组各报一次（`runs/p210-cloth-config/before/client.log:183,203`）；
- **5 层断点**：① `Screen.field_44669` 被删 → 桥返回 1.21.1 自己的 `menu_background.png`；
  ② `method_25394` 在 `class_339` 上变 final → 改名到 `method_48579`，**必须** `onlyIfExtends: class_339`
  （否则 Cloth 的列表（`class_362` 子树）被误改，13 行构造好但一个像素不画）；③ `TextFieldWidget` 两个
  setter 各多一个 `boolean`；④ `renderBackground` 多三个参数；⑤ 立即模式渲染模型整代消失
  （`Immediate.getBuffer` / `BufferBuilder.begin` / 顶点链终点 / `Immediate.draw`）；
- **第 5 层为什么能救**：`renderList` 开头 `vcp=Immediate.getInstance(); bb=t0(vcp)` 是死代码（slot 8 全程
  未被 `aload`），行本身走 `renderItem(DrawContext, Entry, …)`。`buffer()` 返回 `null` → 13 行出现；
  只有 1–4 层时 `after/` 的崩溃报告证明了这条链活着：`t0` 从
  `DynamicEntryListWidget.method_25394:298` 抛出（`after/client.log:207`，"Rendering overlay"）；
- **两个末端尾巴**（层 6/7）：Cloth 自己的 demo 屏用 `ItemStack.setCustomName`（层 6，`keepStackName`）和
  `Enchantments.field_9131` + `addEnchantment(Enchantment,int)`（层 7）。层 6 修掉后层 7 才暴露
  （`attempt2-demo-enchantment/client.log:129`）。层 7 是**真退化**：1.21.1 的 `class_7923` 里 75 个
  `class_2378` 字段没有一个是附魔注册表，附魔只能从 per-world `DynamicRegistryManager` 取，而这个 lambda
  里没有 world，所以样例物品不附魔；层 6 同样使样例物品没有自定义名字。两条都写在规则 `evidence` 里；
- **验收**：`client_errors=[]`、`no_such_field=0`、`no_such_method=0`、`done.tick=182`、
  `rows=13 kinds={BooleanToggleBuilder$1=9, EmptyEntry=2, FloatListEntry=1, SearchFieldEntry=1}`
  （`after3/result.json`、`after3/client.log:147`），截图 `after3/config.png` 323358 B；
- **交互（P1）**：探针取第一条布尔行的 `class_4185` 中心，用 **`Screen.method_25402`** 发真实点击 →
  `handled=true`，`getValue()` 由 `true` 变 `false`，且 `direct_press=false`（不是靠直接调
  `ButtonWidget.method_25306` 兜底）；`after3/toggle.png` 里第一行按钮变 OFF、其余 8 行仍 ON
  （`after3/client.log:153-156`）；
- **退化清单（6 条装饰 + 2 条 demo）**：列表平铺背景、列表上下边缘渐变、screen dim 层、tab 阴影、
  行渐变、下拉阴影改 no-op；行本身、选中条、文字、按钮都在。逐条写在
  `rules/fabric-1.21.1/cloth-config-render.json` 的 `risk`/`evidence`；
- **未覆盖**：`GlobalizedClothConfigScreen.method_25394`（Ctrl+滚轮全局设置屏，27 处 tombstone，
  需重建 tab 栏；AppleSkin 永不打开）与 `DynamicElementListWidget$ElementEntry.method_25401(DDD)`
  （1.21.1 的 `class_4069` 已无 3 参 `isMouseOver`；`scan_refs.py` 的 `refs-after.json` 里剩这两类，
  实测路径不经过）；
- **规则命中数（构建断言）**：`buffer-accessor 5`、其余 14 条各 1、`clickable-text-override 8`、
  `render-widget-override 6`；
- 回归：新增 `test_cloth_config()`，以及 Java 侧 `JarPatcherMethodRenameTest`（4 例：直接父类、三级祖先、
  无关父类（`class_362` 场景）、祖先解析不出→不改）；判据脚本 `verify_cloth.py` 31/31；
- 门禁：`test_review_fixes` 见提交说明；`check_hashes`、`verify_evidence`、`check_text_encoding` 同；
- 边界：单机、1280×720、guiScale 2；只点第一条布尔开关，其余开关、文本框、浮点列表未交互；
  跨机器未做。

## 二十六、2026-10-30 更新（p211：PCL2 其实在机器上；失效快捷方式不再被静默跳过）

任务 6 一直按"本机没有 PCL2"记成受阻。这一轮把环境查了一遍：**PCL2 在**，只是不在记录的那个路径。

- **实际位置**：`D:\浏览器所下载文件\我的世界PCL2启动器_2.12.8.2\plain craft launcher 2.exe`
  （5,750,272 B，sha256 `30eb93c6…`），`FileVersion = 2.13.1.1`——正是 p137 实测过的那个版本；
  目录名里的 `2.12.8.2` 只是下载文件夹的名字；
- **游戏目录**：同目录 `PCL\Setup.ini` 的 `LaunchFolderSelect:C:\Users\27682\AppData\Roaming\.minecraft\`，
  与 `pcl2_game_dir()` 解析结果一致；该目录存在（`versions\1.21.1`、`launcher_profiles.json`）；
- **为什么之前判定"没有"**：p137 记录的 `D:\我的世界\.minecraft\涟漪专用启动器` 已被删除，而桌面
  快捷方式 `Plain Craft Launcher 2.lnk` 仍指向它。`pcl2_from_desktop()` 对"目标不存在"是
  **静默 continue**，于是 `detect_pcl_root()` 落到 `%APPDATA%\.minecraft` 兜底并把它当"检测到了"。
  这次恰好是同一个目录，所以看不出问题；换一台 PCL2 用自定义目录的机器，会静默装错地方；
- **修法**：新增 `pcl2_shortcut_scan(desktop=None, resolve=None)`，返回 `(游戏目录, notes)`，
  notes 逐条说明"读不到目标／目标已不存在（带路径）／目录里既无 Setup.ini 也无 .minecraft／桌面上没有
  PCL 快捷方式"；`detect_pcl_root(notes=…)` 收集并补一条"回退到 X"。CLI 打到 stderr（`PCL 检测:`），
  面板在目录框下方用一条琥珀色标签显示。**行为没有改变**：检测结果仍是同一个目录，本轮只是把
  "静默"变成"说明"；
- **证据**：`runs/p211-pcl2-detect/` —— `before/`（修前：`notes=[]`、无 scan API、快捷方式被静默丢弃、
  仍返回目录）与 `after/`（修后：点出死路径 + 回退说明），同一台机器相隔几分钟；`panel-smoke.png`
  是真实面板截图（note 标签可见，921 个版本）；`verify_detect.py` 26/26；
- 回归：新增 `test_pcl2_detect()`（21 条：`Setup.ini` 绝对/`$` 相对/portable/都没有、四种 notes 分支、
  CLI 与面板接线、提交证据、文档更正）；
- 门禁：`test_review_fixes` **430/430**（新增 `test_pcl2_detect()` 21 条）、`check_hashes` **1482/1482**、
  `verify_evidence` passed、`check_text_encoding` 238/238 clean；无新 release；
- 边界：**没有做**"从 PCL2 启动进游戏"与"面板点安装 → PCL2 版本刷新"的端到端（那要往真机
  `.minecraft` 写版本并启动 PCL2 窗口）；本轮只把环境与检测逻辑钉死。任务 6 的 E2E 仍然待做，
  但现在**不再受阻于"没有 PCL2"**。

## 二十七、2026-10-30 更新（p212：面板真点了一次安装，PCL2 里看得见；启动器更到 2.99.0.0）

p211 只把环境与检测钉死，没按过按钮。这一轮把整条链跑通，并把启动器换成快照版。

- **桌面快捷方式重建**：由死路径 `D:\我的世界\.minecraft\涟漪专用启动器\…` 改指真实启动器，旧 `.lnk`
  字节留在证据里；`pcl2_from_desktop()` 现在**沿快捷方式**解析出游戏目录（p211 时它返回 `None`，
  靠 `%APPDATA%` 兜底）——这正好补上 p211 那条修复的另一半（有效快捷方式必须能解析、且 notes 为空）；
- **干净起点**：先删掉上一轮装出来的 `versions\1.20.4` 与 `mcbridge-1.20.4` profile 并记录
  （`clean-state.json`），否则第二次点击的 `before` 里已经有它，等于什么都没证明；
- **面板真点**：直接调面板按钮的 command（`install_btn.invoke()`，与点击同一路径），状态栏走完
  `client → assets → 完成`，10.3 s；`versions` 由 `['1.21.1']` 变 `['1.20.4','1.21.1']`，写入
  `1.20.4.jar` 24,445,539 B（sha1 与官方 manifest 一致）与 `1.20.4.json` 49,394 B，`launcher_profiles.json`
  新增 `1.20.4 (mcbridge)`。**唯一的替身是模态弹窗**（`showinfo` 换成记录函数，`open_var` 关掉）；
- **启动器更新**：`PCL 快照版 2.99.0.0.zip` 里只有一个 exe，原地覆盖 `2.13.1.1 → 2.99.0.0`
  （解出的 exe 与 zip 成员 sha256 逐字节相同，旧 exe 存为 `Plain Craft Launcher 2.exe.2.13.1.1.bak`，
  `PCL\Setup.ini` 未被改动）；
- **PCL2 里看得见**：启动 2.99.0.0 → 更新日志弹窗 →「版本选择」页 **常规版本 (2)：1.21.1 / 1.20.4**
  （`pcl2-click-2.png` 与首帧差 26% 像素，说明确实是另一个页面而不是同一帧）；窗口截完就关掉，不常驻；
- **两个发现**：① PCL 2.99.0.0 的更新日志写明**不再提供 MC 下载**（"为遵守相关法律法规…"），所以
  "用 PCL 装版本"这条路在新启动器上没了，本仓库的一键安装器反而更有用；② PCL2 是**单实例**，
  已有一个在跑时新进程立刻退出，截图脚本必须先杀旧实例（否则截到上一个会话的陈旧画面）；
- **顺手修的真缺陷**：面板的 manifest 线程在窗口销毁后仍调 `root.after`，会在线程里打
  `RuntimeError: main thread is not in main loop`（本轮第一次跑就遇到了）。新增 `_post()` 统一兜住
  `RuntimeError`/`TclError`，`_drain` 的自我调度也走它；
- **判据**：`runs/p212-pcl2-e2e/verify_e2e.py` **29/29**（四段链路各查自己的产物：快捷方式、
  清场记录、面板安装、启动器与窗口；文件层面还现场重算 jar 的 sha1 与 manifest 比对）；
- 回归：新增 `test_pcl2_e2e()`（13 条，含"旧启动器可回滚""版本页是另一帧""面板容错"）；
- 门禁：`test_review_fixes`、`check_hashes`、`verify_evidence`、`check_text_encoding` 见提交说明；
- 边界：从 PCL2 点「启动游戏」这一条本轮没做（当时误写成"要账号"，其实 PCL2 有离线登录，已由 p213 补上，见第二十八节）；没有重跑 1.21.1 启动回归；
  写进真机的东西：`versions\1.20.4\`、`mcbridge-1.20.4` profile、1.20.4 新增的 asset 对象、
  启动器 exe 被替换（旧版留 `.bak`）。

## 二十八、2026-10-30 更新（p213：离线模式能启动，并且真的进了世界）

p212 结尾我写"没做：从 PCL2 进世界（要账号）"，**那句是错的**。PCL2 的「离线」登录不需要账号，
它给游戏一个占位 UUID/token，用户名自选。这一轮把"启动 → 进世界"整段跑通。

- **离线身份来自 argv，不是设置界面**：PCL2 2.99.0.0 拉起的 java 命令里有
  `--username SelYio --uuid 0000000000003006998F555B73D6DCEF --accessToken <同一个占位值>
  --userType msa`，还有 `-Dminecraft.launcher.brand=PCL` 与 `--version 1.20.4`；用的是 PCL 自带的
  `java-runtime-delta`，版本目录是 PCL 的隔离模式（`--gameDir …\versions\1.20.4`，所以日志在
  `versions\1.20.4\logs\latest.log`，不在 `.minecraft\logs`）；
- **到标题界面**：日志 `Setting user: SelYio` → `Sound engine started`，截图 367 KB（与启动闪屏差 90%），
  无崩溃；只有离线必然出现的错误（Realms 401、`Failed to fetch user properties`、`profile key pair`）；
- **进世界，全是点出来的**：标题界面「单人游戏」→ 世界列表（`新的世界 (2026/10/30 20:26) 生存模式，
  版本：1.20.4`）→ 点该行 →「进入选中的世界」，日志 `Time elapsed: 1413 ms`，窗口标题变
  `Minecraft 1.20.4 - 单人游戏`，`versions\1.20.4\saves\新的世界\` 出现（`in-game.png`：准星、生命、
  饥饿、快捷栏都在）；
- **早前一次失败如实留着**：第一次是在创建世界页点「创建新的世界」——同坐标 hover 无高亮、点击后画面
  只少了 tooltip（`world-select.png` 与 `world-clicked.png` 的全部差别就是这个）、日志没有世界加载行；
  在那一页**按 Enter** 才把世界建出来（`diag-enter.png` 是按下后出现的世界预览帧 "1×"）。所以"合成点击
  能进 GLFW 窗口"是成立的（标题界面与世界列表都点得动），但**那一个按钮**为什么不吃点击没查清，
  不据此下结论；
- **一条未查清的日志**：加入世界瞬间有 `[Server thread/ERROR]: Not a string`（紧接着
  `SelYio[local:E:…] logged in with entity id 1`），来源没查到；它在判据的允许名单里被**单独点名**，
  没有悄悄过滤；
- **三个坑**（都写进 run README）：① 后台进程直接 `SetForegroundWindow` 常被拒——点击落到终端而脚本
  还"成功"返回，改用 `AttachThreadInput` 抢前台并把 `foreground` 写进证据；② 被最小化的窗口
  （`-32000,-32000`）必须先 `SW_RESTORE` 再量矩形，否则坐标过期（第一次偏 119 px，点到「允许作弊」）；
  ③ "窗口出现"是 Mojang 闪屏，要等日志的 `Sound engine started` 才算到标题界面；
- **判据**：`runs/p213-pcl2-offline-launch/verify_launch.py` **24/24**；
- 回归：新增 `test_pcl2_launch()`（12 条，含"离线身份在 argv 里""标题截图不是闪屏""进世界靠点击"）；
- 门禁：`test_review_fixes`、`check_hashes`、`verify_evidence`、`check_text_encoding` 见提交说明；
- 边界：创建世界页那个按钮不吃合成点击未查清；没重跑 1.21.1 启动回归；截图是 `PrintWindow` 的窗口位图；
  跑完已关闭游戏进程。

## 二十九、2026-10-30 更新（p214：1.21.1 也走通同一条离线路径）

p213 证明的是 **1.20.4**（面板装出来的那个）。1.21.1 早就由 PCL2 自己装在机器上，是本仓库所有模组
转换的目标版本，却**从没在 PCL2 里启动过一次**。这一轮用同一套驱动把它跑了一遍。

- **启动与身份**：PCL2 2.99.0.0 →「版本选择」点 `1.21.1` →「启动游戏」；java 命令行里
  `--username SelYio`、`--uuid`/`--accessToken` = `0000000000003006998F555B73D6DCEF`、`--userType msa`、
  `--version 1.21.1`、`-Dminecraft.launcher.brand=PCL`，用 PCL 自带 `java-runtime-delta`；
- **标题界面**：`Setting user: SelYio` → `Sound engine started`，截图 350 KB（与闪屏差 90%）；
- **进世界（点击）**：「单人游戏」→ 世界列表 → 点该行 →「进入选中的世界」→ `Time elapsed: 229 ms`，
  `versions\1.21.1\saves\新的世界\` 存在，`in-game.png` 是草地/天空/准星/生命/快捷栏的第一人称画面；
- **错误只有离线必然的两条**（`Failed to fetch user properties`、`Couldn't connect to realms`）；
  1.20.4 那条来源未查清的 `Not a string` 在 1.21.1 上**没有出现**——这条也做成了判据；
- **创建那个世界仍是按 Enter**：点「创建新的世界」按钮不生效（与 p213 记录的 1.20.4 一致），
  那两帧留作 `world-entry.png` / `after-enter.png`；本轮断言的是**点击进入**这条已被复现的路径；
- **判据**：`runs/p214-pcl2-1211/verify_1211.py` **19/19**；驱动复用
  `runs/p213-pcl2-offline-launch/drive_pcl.py`（同一套坐标/等待逻辑，`930,472` 是 1.21.1 那一行）；
- 回归：新增 `test_pcl2_1211()`（8 条）；
- 门禁：`test_review_fixes`、`check_hashes`、`verify_evidence`、`check_text_encoding` 见提交说明；
- 边界：只到「离线启动 → 标题界面 → 进世界」，没做游戏内玩法/多人/模组加载（这个实例里没有转换件）；
  结束后游戏与启动器进程都已关闭；写进真机的东西是 `versions\1.21.1\saves\新的世界\`。
