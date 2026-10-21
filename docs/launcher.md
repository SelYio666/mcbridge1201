# mcbridge launcher（本地 GUI 启动器）

一个不打包游戏文件的离线启动器：按需从官方源（或 BMCLAPI 镜像）下载版本、安装加载器、离线启动，
界面是本地网页（Python 标准库服务器 + 原生 HTML/CSS/JS，无第三方前端依赖）。

## 快速开始

```text
python launcher/server.py
```

浏览器会自动打开 `http://127.0.0.1:8765/`（可用 `LAUNCHER_OPEN=0` 关闭自动打开，
`LAUNCHER_PORT` 改端口）。首次使用在界面里设置：

- **游戏目录**：相当于 `.minecraft`，各版本共享 `libraries/` 与 `assets/`；
- **离线用户名**：仅单机 / 局域网，UUID 由 `OfflinePlayer:<name>` 生成；
- **内存**：默认 `2G`。

然后填版本号（如 `1.21.1`；勾选“含快照/远古”可看到全部 900+ 版本）、选加载器、点“下载 / 安装”，装完在左侧双击版本即可启动。

## 已实现

| 能力 | 状态 |
|---|---|
| 拉取 Mojang 版本清单 / 版本 JSON | ✅ 实测 |
| 原版安装：client jar、libraries、natives、assets（索引 + objects） | ✅ 实测（assets 走镜像可下） |
| Fabric 安装（官方 meta，最新稳定 loader） | ✅ 实测 |
| 离线启动（原版 / Fabric），单机与局域网 | ✅ 实测（`runs/p112-launcher/`） |
| 网页 GUI：版本列表、筛选、安装进度、控制台、启动 | ✅ 实测 |
| BMCLAPI 镜像兜底（资源 CDN 被墙时） | ✅ 实测（官方 CDN 超时时自动切镜像） |
| Forge 1.20.1 安装 + 启动 | ✅ 已接入 `minecraft-launcher-lib`（BSD-2）并实测到达主菜单 |
| NeoForge 安装 + 启动 | ⚠️ 安装走库的 `mod_loader`，尚未实测 |
| 正版登录 / 皮肤 / 多人认证 | ❌ 不做，仅离线 |

## 设计约束

- **不分发游戏文件**：仓库里没有 jar / assets，全部运行时下载（Mojang 官方与 BMCLAPI 镜像）。
- 离线模式仅用于单机 / 局域网 / 自建离线服；正版服务器仍需正版认证。
- 版本清单来自 `piston-meta.mojang.com`；资源优先 BMCLAPI（`bmclapi2.bangbang93.com`）以适配国内网络。

## 代码结构

```text
launcher/
  mclaunch.py    # 安装与启动内核（无 GUI 依赖，可单独 CLI 使用）
  server.py      # 本地 HTTP 服务 + JSON API + 静态页
  web/           # index.html / app.js / style.css
```

CLI 也能直接用：

```text
python launcher/mclaunch.py install 1.21.1 "D:\mc" fabric
python launcher/mclaunch.py launch fabric-loader-0.19.5-1.21.1 "D:\mc" Player
```

## 已知限制

- 资源 CDN 在部分网络下不可达，镜像优先可绕过，但全量 assets 下载仍受带宽限制（本机实测下载 3911 个对象时很慢）。
- 本机 `.minecraft/assets` 本身缺对象（字体等），启动器可修复，但需要完整跑一次原版安装。
- Forge/NeoForge 依赖 `minecraft-launcher-lib`（`pip install minecraft-launcher-lib`，BSD-2）；Forge 已验证，NeoForge 未验证。
- Fabric / 原版使用本项目自己的命令拼装（镜像下载 + 已验证的启动参数），不依赖该库。
- GUI 是本地网页，不是独立 exe；要打包成单文件 exe 需另加 PyInstaller 一类工具（未做）。

## 版本资源与后续扩展

版本清单来自 Mojang 官方 manifest，接口当前返回全部 920 个版本（release / snapshot / old_beta / old_alpha），GUI 用“含快照/远古”开关切换。后续接入 `minecraft-launcher-lib`（BSD-2）后，Fabric/Forge/NeoForge/Quilt 与 Java 运行时都可以统一处理，调研见 [launcher-research.md](launcher-research.md)。

## 加载器后端分工

- 原版 / Fabric：本项目 `mclaunch.py`（自有镜像下载器 + 已验证启动参数）；
- Forge / NeoForge：`launcher/backend.py` 调用 `minecraft-launcher-lib`，由库处理 installer、`-DlegacyClassPath`、模块路径与 Java 版本；Java 按版本自动选（1.20.4 及以下用 17，1.20.5+ 用 21）。

## 兼容性与“换启动器”

安装出来的就是标准 `.minecraft` 结构：

```text
<root>/versions/<id>/<id>.json      # 版本描述（原版还带 <id>.jar）
<root>/libraries/                   # 共享库
<root>/assets/                      # 共享资源
<root>/launcher_profiles.json       # 安装后自动补一条 profile
```

因此**不是只能在本启动器里启动**：

- PCL / HMCL 这类启动器直接扫描 `versions/`，能看到并启动这些版本；
- 官方启动器依赖 `launcher_profiles.json`，我们的安装器现在会自动写入一条
  `lastVersionId=<id>`、`gameDir=<root>` 的 profile；
- 也可以把本启动器的“游戏目录”指向已有的 `.minecraft`，两边共用同一套版本和资源。

注意两点：

1. **离线 UUID 由用户名生成**。换启动器/换用户名后 UUID 会变，单人存档里的玩家数据（背包、坐标）
   可能看起来“清空”——保持同名即可；这不是文件损坏。
2. **隔离方式不同**。本启动器把 `mods/`、`saves/` 放在 `<root>` 下共享；PCL 默认版本隔离时用
   `versions/<id>/mods`，切换后可能“看不到模组”，改隔离设置或把模组放到对应目录即可。
