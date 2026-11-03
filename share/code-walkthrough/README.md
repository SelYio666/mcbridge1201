# mcbridge1201 代码走读视频

- 视频：[code-walkthrough.mp4](code-walkthrough.mp4)（**5 分 00 秒**，1280×720，30 fps，2.1 MB）
- 封面：[cover.png](cover.png)
- 生成脚本：[tools/make_code_video.py](../../tools/make_code_video.py)
  —— 全部画面由 Pillow 画出、ffmpeg 只负责编码，不依赖录屏或外部素材。

## 内容（10 段）

| # | 主题 | 讲什么 |
|---|---|---|
| 01 | 代码地图 | 92 个 Java 源文件（12,070 行）、29 份规则（1,712 行）、56 个 Python 工具（14,243 行）、226 份 evidence README |
| 02 | 转换管线 | manifest → version.json → client.jar → 库/资源 → 目标索引 → 扫描 → 分析 → 重映射 → 规则修补 → BytecodeVerify |
| 03 | 规则长什么样 | `rules/fabric-1.21.1/container.json` 里一条 `fieldRedirect` 的完整字段 |
| 04 | 桥生成 | `BridgeGenerator` 用 ASM 写字节码，构建期不依赖游戏 classpath |
| 05 | 重映射 | `JarRemapper` 的 identical-id 重映射：只换名字/描述符，保留方法体 |
| 06 | 本地启动器 | `launcher/server.py` 的 `/api/install`：目标 local / PCL2 |
| 07 | 一键安装器 | `tools/from_source_install.py`：stdlib、逐项 sha1、断点续传、BMCLAPI 回退 |
| 08 | 证据体系 | `check_hashes` / `check_manifest_coverage` / `verify_evidence` + 两道 CI 检查 |
| 09 | 发布 | `release_check.py --build <版本> --accept --ui-accept` 的 7 个步骤 |

## 边界（如实）

- 这是**走读**，不是逐行朗读全部代码：片段是从仓库里截取并适度缩短的，模块名、函数名、命令都真实存在；
- 不包含另一个 agent 正在做的“其他版本适配（TargetProfile/baseline 之外的新目标）”内容；
- 统计数字取自当前仓库快照（`git ls-files` 计数），会随开发变化。

## 重新生成

```text
python tools/make_code_video.py
```

改 `SCENES` 里的文案/片段即可；中英混排靠 `draw_code_line` 按字符切字体（中文雅黑、英文 Consolas）。
