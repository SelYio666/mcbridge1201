# p137 — 一键对接 PCL2（真实环境验证）

日期：2026-10-24。目标：把“下载源安装”直接对接到用户机器上的 PCL2，并在 PCL2 里看到新版本。

## 环境

- PCL2 便携版：`D:\我的世界\.minecraft\涟漪专用启动器\Plain Craft Launcher 2.exe`
- 配置：`PCL\Setup.ini` 里 `LaunchFolderSelect:$.minecraft\` → 游戏目录为
  `D:\我的世界\.minecraft\涟漪专用启动器\.minecraft`（PCL2 自带的 `.minecraft`，已有多个实例）。

## 做了什么

```text
python tools/from_source_install.py --version 1.20.4 --pcl2 "D:\我的世界\.minecraft\涟漪专用启动器"
```

- `--pcl2` 读取 `PCL/Setup.ini` 的 `LaunchFolderSelect`，解析出真实游戏目录；
- 安装 1.20.4（约 9 秒，资源与已有版本复用），写 `launcher_profiles.json`；
- 打开 PCL2 →「版本选择」，**常规版本 (5)** 中出现 `1.20.4`：

![PCL2 版本列表](pcl2-1.20.4.png)

## 结论

- 文件系统层面的对接（版本目录 + profile）与 PCL2 的识别都验证通过；
- PCL2 便携版不需要手动指定游戏目录：`--pcl2 <启动器目录>` 即可；
- 命令行/双击 exe 时，若 PCL2 在桌面有快捷方式，自动检测也会走这条路径。

## 备注

- 版本列表截图为 PCL2 窗口裁剪，已去掉桌面内容；
- 本次只验证“安装后 PCL2 能列出该版本”，未做“从 PCL2 启动进游戏”（那需要真实 GPU 窗口与账号）。

## 打包 exe 复测

用 PyInstaller onedir 构建的 `mcbridge-pcl-setup.exe` 再跑一次同样的命令：

```text
mcbridge-pcl-setup.exe --version 1.20.4 --pcl2 "D:\我的世界\.minecraft\涟漪专用启动器"
```

输出 `done ... / assets ok 3788/3788 / 已写 launcher_profiles.json`，退出码 0；
PCL2 版本列表仍显示 1.20.4。

## 关于“最新版 PCL”

- 本机安装的 PCL2 文件版本为 **2.13.1.1**（2026-08-07）；官方最新为 **2.99.0.0**（2026-10-20）；
- 官方二进制只通过爱发电发布，当前网络到 `afdian.com:443` 不通，无法下载 2.99；
- 社区版 PCL2-CE 需要 .NET 9，且非官方构建，按用户要求**未使用**；
- 因此本证据基于 2.13.1.1；拿到 2.99 的 exe 后可复跑同一命令。
