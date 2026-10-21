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

然后填版本号（如 `1.21.1`）、选加载器、点“下载 / 安装”，装完在左侧双击版本即可启动。

## 已实现

| 能力 | 状态 |
|---|---|
| 拉取 Mojang 版本清单 / 版本 JSON | ✅ 实测 |
| 原版安装：client jar、libraries、natives、assets（索引 + objects） | ✅ 实测（assets 走镜像可下） |
| Fabric 安装（官方 meta，最新稳定 loader） | ✅ 实测 |
| 离线启动（原版 / Fabric），单机与局域网 | ✅ 实测（`runs/p112-launcher/`） |
| 网页 GUI：版本列表、筛选、安装进度、控制台、启动 | ✅ 实测 |
| BMCLAPI 镜像兜底（资源 CDN 被墙时） | ✅ 实测（官方 CDN 超时时自动切镜像） |
| Forge / NeoForge 安装（官方 installer） | ⚠️ 代码已实现，**启动未打通**（模块路径 / legacyClassPath 参数） |
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
- Forge/NeoForge：安装器调用已写好，启动参数仍需按加载器版本适配；当前只验证到 Fabric。
- GUI 是本地网页，不是独立 exe；要打包成单文件 exe 需另加 PyInstaller 一类工具（未做）。
