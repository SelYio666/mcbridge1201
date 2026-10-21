# mcbridge1201 最终状态（2026-10-21）

> 定位：**Minecraft 版本迁移与运行辅助工具箱**。迁移与验证归本工具，日常启动交给 PCL。

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
| 加载器版本选择（Fabric 255 / Forge 137 实测；指定 Fabric 0.20.1 安装成功） | `runs/p112`、docs/launcher.md |
| Java 运行时安装（OpenJDK 21.0.7）+ 启动优先使用 | docs/launcher.md |
| Modrinth mrpack：扫描/安装/overrides/自动启动 | docs/launcher.md |
| 删除版本（路径穿越防护）、模组启停 | docs/launcher.md |
| 与其他启动器共用：目录按钮（root/mods/存档/版本）、`/api/dirs`、`/api/open-dir`、profile 同步 | docs/launcher.md |
| 免 GitHub 便携包：内置 Python 3.12 + 第三方许可证，双击 `run.bat` | docs/distribution.md §2.5、`tools/build_portable.py` |
| 下载源策略：逐路径镜像 + 有限重试 + 侧车 SHA-1 + 来源记录（`/api/downloads`） | docs/download-sources.md |
| 下载进度：字节 / 速度 / 当前来源（`/api/task`），前端显示且不编造剩余时间 | docs/launcher.md |
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

### 工程与门禁

- 单测 23/23；`verify_evidence` passed；哈希 672 项；桥一致性 0；mixin 审计 0；
- 外部问题汇总 20 项回归 + 8 项 NeoForge 安装回归 + 7 项目录/兼容/说明回归 + 15 项下载源/进度回归（`tools/test_review_fixes.py`，50/50）接入统一门禁；
- 使用说明与教程 `docs/guide.md`（启动器、PCL 共用、迁移教程、FAQ），界面「使用说明」按钮直接打开；
- 启动器端到端脚本（安装→启动→主菜单，支持 `--version` / `--require` / `--screenshot`）；
- GitHub Actions CI（手动 dispatch 触发，run 39614386108 通过）。

## 二、未完成（如实）

| 项 | 状态 | 说明 |
|---|---|---|
| NeoForge 带第三方模组 / 进世界 | ⏳ | 空 NeoForge 21.1.264 已到主菜单（p116）；未测装 NeoForge 模组与进世界 |
| 渲染类模组（Sodium/Iris/EntityCulling/ImmediatelyFast） | ❌ | 需要 mixin 重写能力；目前只能剥离 load-bearing mixin，不算通过 |
| Shulker 网格预览 | ⏸ 封存 | 环境侧容器组件问题，需抓包复现 |
| TrashSlot 完整 UI 流程 | ⏸ | 旧桥版本已跑通（p63–p65）；当前桥只做 bridge 级 + 探针 |
| mrpack 含 files 的真实包 | ⏸ | 只测过无 files 的最小包 |
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

# CI（API 推送不会自动触发）
gh api --method POST repos/SelYio666/mcbridge1201/actions/workflows/ci.yml/dispatches -f ref=master
```

## 四、发布

- 仓库：https://github.com/SelYio666/mcbridge1201
- 最新发布：v0.3.1（启动器：加载器版本 / Java 运行时 / 整合包 / 删除版本）
- 证据索引：`runs/SHA256SUMS.txt`、`docs/STATUS.md`、`docs/review-fixes-2026-10-21.md`
