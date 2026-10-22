# 玩家版资料包（下载源 + 启动器教程）

给**不用 GitHub、不做模组适配**的玩家：直接转发即可，不需要安装任何东西。

## 文件

| 文件 | 用途 | 对方怎么用 |
|---|---|---|
| `index.html` | 网页（自包含、离线可用、可打印） | 双击用浏览器打开 |
| `玩家版.pdf` | PDF 版 | 手机/电脑直接看，可打印 |
| `玩家版长图.png` | 长图（1100×2455） | 微信群/QQ 群直接发 |
| `promo.mp4` | 50 秒宣传视频（**纯代码生成**，无素材） | 发群/发视频号 |

外层还有 `share/player-guide.zip`（约 0.9 MB），一次打包上面全部。

## 内容

- 官方下载源：版本清单、客户端 jar、库、资源、官方 Java；
- 加载器源：Fabric / Forge / NeoForge；
- 国内镜像 BMCLAPI + 校验方法（sha1）；
- **先下载 1.21.1（官方启动器/HMCL/Prism），再导入 PCL**（PCL 目前不提供版本下载）；
- 装 Fabric（可选，Fabric Installer 或本项目命令）与各启动器导入步骤；Java 21；
- 常见问题与免责声明。

**不包含**模组转换/适配内容——那部分见仓库主文档，玩家一般用不到。

## 视频

`promo.mp4` 由 `tools/make_player_guide_video.py` 生成：

```text
python tools/make_player_guide_video.py
```

Pillow 逐帧绘制（1280×720、30 fps、50 s），ffmpeg H.264 编码，约 0.6 MB；
没有使用任何图片、录屏或音频素材。

## 分享建议

- 微信群/抖音群：发 `玩家版长图.png` 或 `promo.mp4`；
- 论坛/文档：发 `index.html` 或 PDF；
- 要公网链接：把本文件夹上传到 Cloudflare Pages / Netlify Drop / Gitee Pages。
