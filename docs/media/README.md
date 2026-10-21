# mcbridge1201 explainer video

45-second, 1080p30, code-rendered explainer (Pillow frames piped to ffmpeg/libx264).
No footage is captured: every frame is drawn from code; the three screenshots are the project's own
evidence runs.

## What it says (plain language)

1. **问题**：1.21.1 改了大量方法名、删掉了旧入口，老模组里的调用全部指错。
2. **症状**：启动就崩（`NoSuchMethodError`），或者功能静默失效（FallingTree 砍树只掉 1 根）。
3. **工具做什么**：翻译旧调用 → 按规则打补丁 → 生成兼容小类替旧 API 干活；改完仍是原模组，
   只是换成能跑的写法。类比：给老模组配了翻译官 + 一批转接头。
4. **证据**：Mod Menu 列表能滚能搜、AppleSkin 悬停能看数值、多模组能一起进世界；9 个模组实测、
   23 项自动测试、630 条证据哈希，每个结论可逐条复核。
5. **适合谁 / 边界**：整合包作者、服主、老模组玩家；只提供工具、规则与证据，不分发游戏或模组 jar，
   个别功能仍需手工移植。

## Specs

- File: `mcbridge1201-promo.mp4`
- 1920x1080, 30 fps, 45.0 s, H.264 High, yuv420p
- 纯字幕（无旁白、无配乐）；中文用微软雅黑，代码用 Consolas

## Storyboard

| 时间 | 段落 | 画面 |
|---|---|---|
| 0–6s | 钩子 | 标题 + “1.20.1 模组 jar → 自动改写 → 1.21.1 可运行”流程 |
| 6–15.5s | 问题 | 两张症状卡（启动崩 / 功能静默失效）+ 一句人话解释 |
| 15.5–27.5s | 做什么 | 翻译 / 打补丁 / 补零件 三卡 + “翻译官 + 转接头”类比 |
| 27.5–38.5s | 证据 | 三张实测截图 + 门禁数字 + “可逐条复核” |
| 38.5–45s | 收尾 | 适合谁 + GitHub + v0.2.5 + 边界说明 |

## Regenerate

```text
python tools/make_promo_video.py
```

Requires Pillow + numpy (bundled runtime) and the encoder:

```text
python -m pip install imageio-ffmpeg
```

Numbers in the proof scene are a 2026-10-20 snapshot (23 tests / 630 hashes); edit the `stats`
string in `scene_proof` and re-render if they change.


## v2 (2026-10-21) — 辅助定位版

55 秒，1080p30，`mcbridge1201-promo-v2.mp4`，由 `tools/make_promo_v2.py` 渲染。

定位按用户要求修正为**辅助**，不替代 PCL：

1. 钩子：Minecraft 版本迁移辅助工具箱 —— “帮 1.20.1 的模组搬家，不是来替代启动器的”；
2. 问题：版本换代导致崩溃 / 功能静默失效；
3. 引擎：转换 → 修补 → 桥接（核心价值）；
4. 启动器：明确写成“顺手带个小启动器（验证用）”，三条点分别是能装能测 / 标准目录（PCL 可直接识别）/
   不抢位置（日常还是用 PCL）；
5. 证据：多模组进世界、Forge 主菜单、AppleSkin 悬停 + 9 模组 / 23 测试 / 641 哈希；
6. 收尾：把模组搬进 1.21.1 后“交回你最顺手的启动器”，并注明 NeoForge 未实测、不分发 jar。

```text
python tools/make_promo_v2.py
```
