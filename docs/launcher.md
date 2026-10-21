# mcbridge launcher（本地 GUI 启动器）

一个不打包游戏文件的离线启动器：按需从官方源（或 BMCLAPI 镜像）下载版本、安装加载器、离线启动，
界面是本地网页（Python 标准库服务器 + 原生 HTML/CSS/JS，无第三方前端依赖）。

## 快速开始（一键）

双击 `launcher/run.bat`（需要系统里有 Python 3.10+）：

```text
launcher\run.bat
```

浏览器会自动打开界面。只做三步：

1. 填版本号（例如 `1.21.1`）；
2. 加载器保持默认 `Fabric（推荐）`（也可选原版 / Forge / NeoForge）；
3. 点 **“安装并启动”**（可选：在“加载器版本”下拉里指定 Fabric/Forge/NeoForge 版本，
   默认是“最新”）。

没装过的版本会先自动下载安装，装完**自动进游戏**；已安装的直接启动。用户名、内存、游戏目录
都收在“高级设置”里，首次运行会自动探测已有的 `.minecraft`。

命令行方式等价：

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

## 一键流程做了什么

`安装并启动` = 安装（原版 / Fabric / Forge / NeoForge 按选择）→ 轮询任务 → 成功后自动调用启动，日志同时显示在界面下方的控制台里。失败会保留错误信息，不会静默。

## 只认真正的游戏版本

启动器只列出**符合 Minecraft 版本名或加载器命名规则**的版本（`1.21.1`、`1.20.1-forge-47.4.16`、
`fabric-loader-0.19.5-1.21.1` 等）。像 PCL 的整合包实例（例如 `One Prime Piece 1.7.6`、
`Bloodbathen-1.20.1`）不会被当成 MC 版本列出来。

启动器也**不会读取、复制或上传**你的 `mods/`、`saves/`、整合包目录；它只写
`versions/`、`libraries/`、`assets/` 和 `launcher_profiles.json`。仓库里同样不含任何模组 jar。

## 怎么验证“真的下载到了版本”

不用信界面，直接看文件 + 用内置校验命令。

### 方法一：命令行（推荐）

```text
python launcher/mclaunch.py install 1.21.1 <一个空目录> vanilla
python launcher/mclaunch.py verify  1.21.1 <同一个目录>
```

`verify` 会逐项报告，缺什么一目了然：

```text
version: 1.21.1
root:    ...
  version json : ok
  client jar   : ok (26836906 bytes)
  libraries    : 70/70 present
  natives      : 9 dll ['OpenAL.dll', 'freetype.dll', 'glfw.dll', 'jemalloc.dll']
  assets       : 3911/3911 present
RESULT: OK
```

- `RESULT: OK` = 版本 JSON、客户端 jar、库、natives、资源对象全部齐了；
- `INCOMPLETE` = 有缺失（会显示缺的库名/资源数量），通常是网络没下完，重跑 `install` 会续传补齐；
- 退出码：`0` 完整，`3` 不完整，方便脚本判断。

### 方法二：看目录

| 路径 | 应看到什么 |
|---|---|
| `versions/1.21.1/1.21.1.json` | 版本描述 |
| `versions/1.21.1/1.21.1.jar` | 客户端 jar，约 26.8 MB |
| `versions/1.21.1/natives/*.dll` | 8~9 个原生库 |
| `libraries/` | ~70 个 jar（按包路径分目录） |
| `assets/indexes/<id>.json` | 资源索引 |
| `assets/objects/ab/<hash>` | 每两个十六进制一个目录，文件按 sha1 命名 |

`assets/objects` 的文件名就是 **sha1**，所以“有没有下对”可以直接用哈希判断。

### 实测下载速度（2026-10-21）

在全新空目录安装 `1.21.1` 原版，官方源优先 + 24 并发：

| 项目 | 数据 |
|---|---|
| 总耗时 | **114 秒**（约 2 分钟） |
| 总量 | **877 MB**（客户端 jar 25.6 MB + 库 63.6 MB + 资源 787.8 MB） |
| 吞吐 | **约 7.7 MB/s**，资源约 **34 个对象/秒** |
| 资源对象 | 3911 / 3911 全部下齐，`verify` 返回 `RESULT: OK` |

对比：如果优先走 BMCLAPI 镜像，实测只有约 **0.6 个对象/秒**（逐个新建 TLS 连接、服务端限速），
3911 个资源要一个多小时。所以下载器改成**官方优先、镜像兜底**：官方失败/超时才切镜像。

- 客户端 jar（25.6 MB）通常几秒内完成；
- 库文件 70 个，随 jar 一起很快；
- 资源是多小文件，耗时主要在这里，但 24 并发下约 2 分钟。

## 校验工具与退出码

- `mcbridge1201 patch --require-hit <rule-id>`：关键规则零命中时退出 3；输入看起来已经修补时退出 4；
  规则 schema/target 不合法时退出 2。
- `python tools/audit_mixins.py --jar <jar>`：mixin 配置损坏计入 problems，非零退出。
- `python launcher/mclaunch.py verify <version> <root>`：安装完整性，0 完整 / 3 不完整。

## 加载器版本选择

- 接口：`GET /api/loader-versions?loader=fabric|forge|neoforge&mc=<游戏版本>`；
- Fabric 走官方 meta（实测 1.21.1 返回 255 个 loader 版本），Forge/NeoForge 走
  `minecraft-launcher-lib` 的 `mod_loader`（实测 1.20.1 Forge 返回 137 个）；
- 安装请求可带 `loader_version`，不传则用最新稳定版；实测指定 Fabric `0.20.1` 安装出
  `fabric-loader-0.20.1-1.21.1` 配置。

## Java 运行时

“高级设置”里有一行 **Java 运行时**：

- 下拉列出 Mojang 官方 JVM 组件（`jre-legacy`、`java-runtime-gamma/delta/epsilon` 等）；
- 点“安装到游戏目录”会装到 `<root>/runtime/<组件>/...`，启动器会**优先使用**这份 Java；
- 接口：`GET /api/jvm`（可用 + 已安装）、`POST /api/install-jvm {"id":"java-runtime-delta"}`。

实测：`java-runtime-delta` 装进临时目录，得到 OpenJDK **21.0.7**；`find_runtime_java(root)` 能选中它，
空目录返回 None。由于 Mojang 的 launchermeta/piston-meta 在本网络下偶发 SSL 断连，安装做了 **3 次重试**，
第二次尝试成功。

注意：这是给“本机没有 Java”的用户兜底的方案；如果系统已有合适 JDK，仍优先用系统/官方启动器运行时。

## Modrinth 整合包（.mrpack）

“高级设置 → 整合包”会**自动扫描** `<root>/packs` 和 `~/Downloads`（也可传 `dir` 参数），
下拉选择或手填路径，点“安装整合包”；接口：

- `GET /api/mrpacks?dir=<可选目录>`：列出发现的包（名称 / 包版本 / MC 版本）
- `POST /api/install-mrpack {"path":"<本地 .mrpack>"}`

实现策略：**依赖由本项目自己装**（原版走我们的镜像下载器、Fabric/Forge/NeoForge 走已验证路径），
然后调用 `minecraft-launcher-lib` 的 `install_mrpack(..., skipDependenciesInstall=True)` 只装
`files` 与 `overrides`。这样绕开了库内置 Fabric installer 对 `java` 参数的要求（本机 PATH 无 java 会
报 WinError 2）。

实测：自建最小包（`minecraft 1.21.1` + `fabric-loader 0.19.5`，无 files，overrides 放一个测试文件）
安装成功，任务消息为 `mcbridge test pack 1.0.0|fabric-loader-0.19.5-1.21.1`，
`config/mcbridge-test.txt` 内容正确。

安装完成后界面会**自动选中并启动** `|` 后面的启动版本（`get_mrpack_launch_version` 给出）。

## 删除已安装版本

“已安装”列表里每个版本带一个“删除”链接（二次确认）。接口：

- `POST /api/delete-version {"id":"<版本 id>"}`

只删 `<root>/versions/<id>` 目录，不动 `saves/`、`mods/`、`libraries/`、`assets/`；返回释放的字节数。
路径穿越（`../`）会被拒绝（400）。回归套件覆盖“删除成功”和“拒绝穿越”两项。
