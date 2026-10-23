# 一键安装到 PCL

两种形态，任选其一。

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

`promo.mp4`（52 秒，1280×720，纯代码生成）由 `tools/make_pcl_onclick_video.py` 渲染：
下载 → 解压 → 双击 → 自动检测 → 下载校验 → PCL2 列表出现新版本。

```text
python tools/make_pcl_onclick_video.py
```

## 已验证的启动器版本

- PCL2 **2.13.1.1**（便携版，2026-08 构建）：安装 1.20.4 后版本列表出现该版本，
  截图见 `runs/p137-pcl2-onclick/pcl2-1.20.4.png`；
- 打包后的 `mcbridge-pcl-setup.exe` 也实测通过（`--pcl2` 指定 PCL2 目录，rc=0）。

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
