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
