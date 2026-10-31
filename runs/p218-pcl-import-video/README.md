# p218 — “用 PCL 启动已装好的 1.21.1”通俗讲解视频（代码生成）

日期：2026-10-31。给“怎么导入 PCL / 用 PCL 启动”这件事单独做一个好懂的视频，
回答的是**B 路线**：PCL 目录里已经有 1.20.4 / 1.21.1，直接选版本启动即可。

## 成片

- `p218-pcl-launch-simple.mp4`：22 s，1280×720，30 fps，445,350 bytes；
- SHA-256 `b557b1b977ca4df70db8e27634064c0cb37139bff73cfbfc85d5276d92a076e8`；
- 生成：`python runs/p218-pcl-import-video/make_video_simple.py`
  （PIL 逐帧 + `.toolchain/ffmpeg/ffmpeg.exe` 编码，无外部依赖）。

## 五段内容

1. 这次只讲一件事：用 PCL 启动 1.21.1，**已经装好，不用“导入”**；
2. 文件在哪：`%APPDATA%\.minecraft\versions\` 下的 1.20.4 / 1.21.1，
   `1.21.1.jar` 的 SHA-1 与官方一致（`30c73b1c…`）；
3. 三步启动：打开 PCL → 版本选择 1.21.1 → 启动（离线用户名 `SelYio`）；
4. 为什么不用导入：PCL 直接扫 `versions/`；`launcher_profiles.json` 只对官方启动器有意义；
5. 两个小坑：版本隔离时模组放 `versions\1.21.1\mods`；存档离线 UUID 与用户名绑定。

## 事实依据（视频里的数字来自本机核验）

- `versions/` 下确有 1.20.4、1.21.1；
- `1.21.1.jar` 26,836,906 bytes，SHA-1 `30c73b1c5da787909b2f73340419fdf13b9def88`，
  与 Mojang 1.21.1 版本 JSON 的 `downloads.client.sha1` 一致；
- `launcher_profiles.json` 只有 `mcbridge-1.20.4`，但 PCL 列表不需要它；
- p214 已有“从 PCL 离线启动 1.21.1 进世界”的运行证据。

## 限制

- 无配音、无字幕轨，只有画面文字；
- 界面元素是代码绘制的示意，不是 PCL 实时录屏；
- 只讲“已安装 + PCL 启动”，不讲从零安装/换机器/整合包导入。

## 证据

`make_video_simple.py`、`p218-pcl-launch-simple.mp4`。
