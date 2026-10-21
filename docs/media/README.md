# mcbridge1201 promo video

30-second, 1080p30, code-rendered promo (Pillow frames piped to ffmpeg/libx264).
No footage was captured for this video: every frame is drawn from code, and the three screenshots
are the project's own evidence runs.

## Specs

- File: `mcbridge1201-promo.mp4`
- 1920x1080, 30 fps, 30.0 s, H.264 High, yuv420p, ~1.9 MB
- 纯字幕（无旁白、无配乐），中文字幕用微软雅黑，代码用 Consolas

## Storyboard

| 时间 | 段落 | 内容 |
|---|---|---|
| 0.0–4.8 | 标题 | `mcbridge1201` + FABRIC 1.20.1 → 1.21.1 + 三件套定位 |
| 4.8–11.0 | 问题 | 真实崩溃样例（tombstone / NoSuchMethodError / NoClassDefFoundError）+ 三个失败模式 |
| 11.0–17.6 | 流水线 | 转换 → 修补 → 桥接，每步带 capability/risk/evidence |
| 17.6–24.6 | 证据 | Mod Menu、AppleSkin、多模组联测截图 + 门禁数字（23 单测 / 627 哈希 / 桥 0 / 联测） |
| 24.6–30.0 | 收尾 | 已验证模组清单 + GitHub + 版本 + “不分发游戏/模组 jar” |

## Regenerate

```text
python tools/make_promo_video.py
```

Requires: Pillow + numpy (bundled runtime has them) and `imageio-ffmpeg` for the encoder:

```text
python -m pip install imageio-ffmpeg
```

## Notes

- 画面里的统计数字（23 tests / 627 hashes / 桥 0 / 联测）对应 2026-10-20 的门禁结果；如果后续数字变化，
  改脚本里 `scene_evidence` 的 `stats` 字符串后重渲。
- 截图来源：`runs/p94-modmenu-list/`、`runs/p101-appleskin-hover/`、`runs/p96-combined-smoke/`。
- 抽帧与缩略图在 `docs/media/frames/`（仅用于检查，可不提交）。
