# mcbridge1201 最终状态（2026-10-23）

> 定位：**Minecraft 版本迁移与运行辅助工具箱**。迁移与验证归本工具，日常启动交给 PCL。
> 最新发布：[v0.5.4](https://github.com/SelYio666/mcbridge1201/releases/tag/v0.5.4)（地图 atlas 生命周期/退出崩溃修复 + VertexBuffer fast path + 便携包）。

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
| Sodium 1.20.1 转换可行性（静态分析）：`blocked_static` 13/15/16，需移植渲染内核 | `runs/p158-sodium-probe/` |
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

- 单测 25/25；`verify_evidence` passed；哈希 1072 项（以 `runs/SHA256SUMS.txt` 实际行数为准）；桥一致性 0（ImmediatelyFast 端口 jar，p165/p181）；mixin 审计 inert=2（`listed=37`；p175 恢复 map mixin、p177 补多地图/展示框、p178 启用 VertexBuffer；剩余两个是官方 1.21.1 已删除的 1.20.4 遗留类，见 `runs/p180-inert-closure/`）；
- 外部问题汇总 20 项回归 + 9 项 NeoForge 安装/启动回归 + 10 项目录/兼容/说明回归 + 1 项加载器安装回归 + 8 项 ImmediatelyFast 移植回归 + 1 项便携包回归 + 24 项下载源/进度回归 + 6 项地图 atlas 回归 + 2 项 VertexBuffer 回归 + 1 项死 mixin 防误登记回归 + 1 项 atlas closed 守卫回归 + 1 项 TrashSlot UI empty 键回归 + 1 项 TrashSlot Shift+Delete 回归 + 1 项 TrashSlot right-click undelete 回归 + 1 项 Shulker 网格 wrapper/t2/t4 回归（`tools/test_review_fixes.py`，共 87 项；本次 **87/87**）接入统一门禁；
- 使用说明与教程 `docs/guide.md`（启动器、PCL 共用、迁移教程、FAQ），界面「使用说明」按钮直接打开；
- 启动器端到端脚本（安装→启动→主菜单，支持 `--version` / `--require` / `--screenshot`）；
- GitHub Actions：push 触发**已验证可用**（`e9ca30c` run `39796030299`；`742d133` run `39799555425`，check-run `build` success，含 API 推送）；此前“push 无 run”是 GitHub Actions `degraded_performance`（22:18 UTC）导致排队，重推 workflow 文件后索引恢复。若再遇无 run，先看 [githubstatus.com](https://www.githubstatus.com)，再重推 workflow 文件刷新索引。

## 二、未完成（如实）

| 项 | 状态 | 说明 |
|---|---|---|
| NeoForge 带第三方模组 / 进世界 | ✅ 已通过：AppleSkin（p127）、Farmer's Delight 内容模组（p128）、Jade 数据同步/HUD（p130）；**专用服务器 + 客户端 join 已通过**（p161，端口 25567；安装时曾因 maven.neoforged.net 超时失败，复用本地 client libraries 后成功）；**带 Farmer's Delight 的专用服务器 + 同模组客户端加入**（p163，端口 25568） |
| Forge 1.20.1 带模组世界 | ✅ 显示类（AppleSkin，p129）+ 内容类（Farmer's Delight，p131）；**专用服务器 + 客户端 join 已通过**（p159：端口 25566）；**带 Farmer's Delight 的专用服务器 + 同模组客户端加入**（p164：端口 25569） |
| 渲染类模组：Sodium | ❌ blocked_static | 1.20.1 的 Sodium 0.5.13 静态探针：missingClass=13、missingMember=15、descMismatch=16（`runs/p158-sodium-probe/`）；需要移植其渲染内核，本轮不做；Iris 兼容分支已在 p142/p143 跑通 |
| ImmediatelyFast 的完整度 | ✅ HUD+物品+overlay 批处理生效；地图 atlas 已恢复并覆盖动态更新/正常退出；VertexBuffer 动态上传 fast path 已启用 | 单人/专用服务器（p134/p141）、soak 95s（p140）、关闭开关归零（p137）、Iris 1.8.1/1.8.14（p142/p143）、shader pack r5.3（p145/p146，hud=11146/11168）、关闭 universal batching 的回退路径（p147）、item per-lighting（p149/p150）；**地图 atlas：p175/p177/p181（动态更新 + 退出清理 + 崩溃修复）**；**VertexBuffer：p178**；私有成员走反射 |
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
- 最新发布：v0.5.4（地图 atlas 生命周期/退出崩溃修复 + VertexBuffer fast path + 便携包）
- 证据索引：`runs/SHA256SUMS.txt`、`docs/STATUS.md`、`docs/review-fixes-2026-10-21.md`
