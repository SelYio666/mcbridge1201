# 一键安装到 PCL

两种形态，任选其一。

## 方式 A0：图形面板（最直观）

1. Release 里下载 `mcbridge-pcl-panel.zip`；
2. 解压后双击 `mcbridge-pcl-panel.exe`；
3. 面板会自动列出正式版/快照、自动检测 PCL 目录；选版本 →「安装到 PCL」→ 看进度条；
4. 装完自动打开游戏目录（可关），PCL 刷新版本列表即可。

面板和命令行用的是同一套下载/校验逻辑（同一个 exe 也保留着命令行版）。

## 方式 A：免 Python（推荐）

1. 打开 <https://github.com/SelYio666/mcbridge1201/releases/tag/v0.5.5> 下载
   `mcbridge-pcl-setup.zip`（约 9 MB）；
2. 解压到任意目录（不要只把 exe 拖出来，`_internal` 文件夹要跟着）；
3. 双击 `mcbridge-pcl-setup.exe`；
4. 按提示输入版本（直接回车 = 1.21.1），确认 PCL 游戏目录；
5. 等进度结束 → 自动打开游戏目录 → 打开 PCL 刷新版本列表 → 选中版本启动（Java 选 17/21）。

它做的事：从公开下载源取清单 → 客户端 jar → 全部库 + Windows natives → 资源索引 + 资源对象，
逐文件 sha1 校验，失败自动换 BMCLAPI 镜像；完成后写 `launcher_profiles.json`（不抢占已有选中配置）。

## PCL2 便携版（自带 .minecraft）

如果 PCL2 是便携版（目录里有 `PCL\Setup.ini` 和 `.minecraft`），直接指给它：

```text
python tools/from_source_install.py --version 1.21.1 --pcl2 "D:\...\你的PCL2目录"
```

脚本会读 `PCL/Setup.ini` 的 `LaunchFolderSelect` 找到真实游戏目录；桌面有 PCL 快捷方式时，
`--pcl` 也会自动沿快捷方式定位。实测 PCL2 版本列表能直接看到新装的 1.20.4
（见 `runs/p137-pcl2-onclick/`）。

**快捷方式失效时会告诉你**（p211）：如果桌面快捷方式指向的路径已经被移动/删除，`--pcl` 不再静默
回退到 `%APPDATA%\.minecraft` 了，而是打印例如
`PCL 检测: Plain Craft Launcher 2.lnk：快捷方式指向的路径已不存在（D:\...\Plain Craft Launcher 2.exe）`
再加一句 `回退到 C:\Users\...\AppData\Roaming\.minecraft`；面板上同一条信息显示在目录框下方。
这时建议直接用 `--pcl2 "<PCL2 目录>"` 指过去（实测见 `runs/p211-pcl2-detect/`）。

## 方式 B：已有 Python 3

双击 `一键装到PCL.bat`（可带版本号：`一键装到PCL.bat 1.20.1`），或命令行：

```text
python tools/from_source_install.py --pcl
python tools/from_source_install.py --pcl-dir "D:\你的\.minecraft"
```

## 注意

- 只支持 Windows 10/11 x64；
- 需要约 1 GB 磁盘；
- 若 PCL 用了自定义游戏目录，按提示手动输入（或加 `--pcl-dir`）；
- 平台只提供工具与公开地址，不托管、不分发游戏文件；请遵守 Minecraft EULA。

## 宣传/教学视频

`promo.mp4`（56 秒，1280×720，纯代码生成）由 `tools/make_pcl_onclick_video.py` 渲染：
为什么需要 → **快捷面板（选版本/自动检测/进度）** → 下载校验流程 → PCL2 列表出现新版本 → Java 版本提示。

```text
python tools/make_pcl_onclick_video.py
```

## 已验证的启动器版本

- PCL2 **2.13.1.1**（便携版，2026-08 构建）：安装 1.20.4 后版本列表出现该版本，
  截图见 `runs/p137-pcl2-onclick/pcl2-1.20.4.png`；
- PCL2 **2.99.0.0（快照版）**：面板真点一次安装（1.20.4），「版本选择」页 **常规版本 (2)：1.21.1 / 1.20.4**，
  截图与逐步判据见 `runs/p212-pcl2-e2e/`（`verify_e2e.py` 29/29）；
- 打包后的 `mcbridge-pcl-setup.exe` 也实测通过（`--pcl2` 指定 PCL2 目录，rc=0）。

> **PCL 2.99.0.0 起不再自带 Minecraft 下载**（该版本更新日志："为遵守相关法律法规，PCL 暂时不再提供
> MC 下载功能"）。它仍然负责启动与管理已装版本，但"在 PCL 里装个新版本"这条路已经没有了——
> 本仓库的一键安装器就是补这个缺口的那一件。

## 选择版本（含快照/远古）

```text
python tools/from_source_install.py --list                    # 正式版（默认）
python tools/from_source_install.py --list --version-type all # 全部，含快照/远古
python tools/from_source_install.py --list --contains 1.20    # 按 ID 过滤

python tools/from_source_install.py --version 1.20.1 --pcl
python tools/from_source_install.py --version latest --pcl    # 最新正式版
python tools/from_source_install.py --version latest-snapshot --pcl
```

双击 exe 的交互模式会先打印最近 15 个正式版，可直接输入序号、版本 ID，或输入 `list` 看全部。

范围说明：清单里带 `assetIndex` 的版本都能装（含快照；实测 b1.7.3 安装后 verify OK）。
远古版本（约 1.6 以前）通常要 Java 8、启动参数也不同，装好后建议用 PCL 启动。
