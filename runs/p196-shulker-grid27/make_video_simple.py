#!/usr/bin/env python3
"""A deliberately simple explainer video for p196 (plain language, big visuals).

p196 verified the 27-slot shulker-box preview (FULL grid) and recorded the preview-key
boundary that p197 later corrected. This script draws a 22 s clip for non-reviewers.

Usage:
    python runs/p196-shulker-grid27/make_video_simple.py
    python runs/p196-shulker-grid27/make_video_simple.py --stills 2 7 11 16 21

Output: runs/p196-shulker-grid27/p196-update-simple.mp4 (1280x720, 30 fps, 22 s).
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[1]
FFMPEG = ROOT.parent / ".toolchain" / "ffmpeg" / "ffmpeg.exe"
FRAMES = ROOT / "work" / "tmp" / "p196-simple-frames"

W, H = 1280, 720
FPS = 30
DURATION = 22.0

BG = (10, 14, 20)
FG = (232, 238, 245)
MUTED = (154, 170, 188)
DIM = (105, 122, 140)
GREEN = (52, 211, 153)
RED = (248, 113, 133)
BLUE = (96, 165, 250)
AMBER = (251, 191, 36)
PANEL = (20, 28, 38)
LINE = (40, 54, 70)

ZH = "C:/Windows/Fonts/msyh.ttc"
ZH_B = "C:/Windows/Fonts/msyhbd.ttc"
MONO_B = "C:/Windows/Fonts/consolab.ttf"

SCENES = [(0.0, 4.4), (4.4, 8.8), (8.8, 13.2), (13.2, 17.6), (17.6, 22.0)]


def zh(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(ZH_B if bold else ZH, size)


def mono(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(MONO_B, size)


def clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def ease(v: float) -> float:
    v = clamp(v)
    return 1 - (1 - v) ** 3


def mix(a, b, t: float):
    t = clamp(t)
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def reveal(lt: float, delay: float, dur: float = 0.4) -> float:
    return ease((lt - delay) / dur)


def text(draw, xy, s, font, fill, *, anchor="mm", alpha=1.0):
    if alpha <= 0 or not s:
        return
    draw.text(xy, s, font=font, fill=mix(BG, fill, alpha), anchor=anchor)


def check(draw, center, color=GREEN, size=28, alpha=1.0):
    x, y = center
    c = mix(BG, color, alpha)
    draw.line((x - size * 0.45, y, x - size * 0.1, y + size * 0.35), fill=c, width=5)
    draw.line((x - size * 0.1, y + size * 0.35, x + size * 0.5, y - size * 0.4), fill=c, width=5)


def cross(draw, center, color=RED, size=26, alpha=1.0):
    x, y = center
    c = mix(BG, color, alpha)
    draw.line((x - size / 2, y - size / 2, x + size / 2, y + size / 2), fill=c, width=5)
    draw.line((x + size / 2, y - size / 2, x - size / 2, y + size / 2), fill=c, width=5)


def mini_grid(draw, center, cols, rows, shown, *, cell=24, gap=6, alpha=1.0,
              colors=None, labels=None):
    """A toy shulker grid; `shown` cells are visible (0..cols*rows)."""
    cx, cy = center
    total_w = cols * cell + (cols - 1) * gap
    total_h = rows * cell + (rows - 1) * gap
    x0, y0 = cx - total_w / 2, cy - total_h / 2
    draw.rounded_rectangle((x0 - 12, y0 - 12, x0 + total_w + 12, y0 + total_h + 12), radius=10,
                           fill=mix(BG, PANEL, alpha), outline=mix(BG, LINE, alpha), width=2)
    palette = colors or [GREEN, BLUE, AMBER, (167, 139, 250), (244, 114, 182)]
    for i in range(cols * rows):
        r, c = divmod(i, cols)
        x = x0 + c * (cell + gap)
        y = y0 + r * (cell + gap)
        if i >= shown:
            draw.rounded_rectangle((x, y, x + cell, y + cell), radius=5,
                                   outline=mix(BG, LINE, alpha), width=1)
            continue
        a = alpha * clamp((shown - i) / 3)
        col = palette[i % len(palette)]
        draw.rounded_rectangle((x, y, x + cell, y + cell), radius=5,
                               fill=mix(BG, col, 0.55 * a), outline=mix(BG, col, a), width=1)
        if labels:
            text(draw, (x + cell / 2, y + cell / 2), labels[i % len(labels)], mono(11),
                 FG, alpha=a)


def caption(draw, s, alpha=1.0, y=646):
    if alpha <= 0:
        return
    box = draw.textbbox((0, 0), s, font=zh(26))
    w = box[2] - box[0]
    draw.rounded_rectangle((W / 2 - w / 2 - 22, y - 28, W / 2 + w / 2 + 22, y + 28), radius=26,
                           fill=mix(BG, PANEL, alpha), outline=mix(BG, LINE, alpha), width=1)
    text(draw, (W / 2, y), s, zh(26), FG, alpha=alpha)


def scene_intro(base, draw, lt, dur):
    text(draw, (W / 2, 150), "这次验证其实只有一句话", zh(26), MUTED, alpha=reveal(lt, 0.0))
    text(draw, (W / 2, 226), "箱子 27 格，预览全画出来", zh(58, True), FG,
         alpha=reveal(lt, 0.25))
    shown = int(27 * ease((lt - 0.9) / 1.4))
    mini_grid(draw, (W / 2, 430), 9, 3, shown, cell=30, gap=7, alpha=reveal(lt, 0.7))
    text(draw, (W / 2, 540), f"{shown} / 27 格", mono(24), GREEN, alpha=reveal(lt, 1.6))
    caption(draw, "27 格在 FULL 预览里全部有 icon 和数量", reveal(lt, 2.0))


def scene_why(base, draw, lt, dur):
    text(draw, (W / 2, 92), "为什么是 27？", zh(44, True), FG, alpha=reveal(lt, 0.0))
    text(draw, (W / 2, 150), "箱子就是 3 行 × 9 列", zh(26), MUTED, alpha=reveal(lt, 0.2))
    cols, rows = 9, 3
    cell, gap = 54, 10
    total_w = cols * cell + (cols - 1) * gap
    x0, y0 = W / 2 - total_w / 2, 250
    # draw three rows, row by row, with row labels
    for r in range(rows):
        a = reveal(lt, 0.4 + r * 0.35)
        for c in range(cols):
            x = x0 + c * (cell + gap)
            y = y0 + r * (cell + gap)
            draw.rounded_rectangle((x, y, x + cell, y + cell), radius=6,
                                   fill=mix(BG, PANEL, a), outline=mix(BG, GREEN, 0.7 * a),
                                   width=2)
        text(draw, (x0 - 46, y0 + r * (cell + gap) + cell / 2), f"第 {r + 1} 行",
             zh(20), MUTED, alpha=a)
    text(draw, (W / 2, y0 + 3 * (cell + gap) + 40), "9 × 3 = 27", mono(30), GREEN,
         alpha=reveal(lt, 1.5))
    caption(draw, "一个 shulker box 固定 27 格，预览要一格不落", reveal(lt, 1.8))


def scene_pitfall(base, draw, lt, dur):
    text(draw, (W / 2, 92), "踩过一个坑", zh(44, True), FG, alpha=reveal(lt, 0.0))
    text(draw, (W / 2, 150), "27 个一样的钻石，会被合并成一堆", zh(26), MUTED,
         alpha=reveal(lt, 0.2))
    # left: 27 identical cells
    a = reveal(lt, 0.4)
    mini_grid(draw, (360, 400), 9, 3, 27, cell=20, gap=5, alpha=a,
              colors=[(147, 197, 253)])
    text(draw, (360, 300), "27 × 钻石", zh(24, True), BLUE, alpha=a)
    # arrow
    seg = ease((lt - 0.9) / 0.7)
    draw.line((560, 400, 560 + 140 * seg, 400), fill=mix(BG, MUTED, 1), width=5)
    draw.polygon([(560 + 140 * seg, 400), (560 + 140 * seg - 16, 388),
                  (560 + 140 * seg - 16, 412)], fill=mix(BG, MUTED, 1))
    # right: one merged stack
    b = reveal(lt, 1.2)
    draw.rounded_rectangle((780, 340, 1080, 460), radius=12, fill=mix(BG, PANEL, b),
                           outline=mix(BG, RED, 0.7 * b), width=2)
    text(draw, (930, 378), "ContainerComponent 合并", zh(20), MUTED, alpha=b)
    text(draw, (930, 424), "diamond × 135", mono(26), RED, alpha=b)
    text(draw, (W / 2, 540), "所以改用 27 种不同物品，每格 1..3 个",
         zh(24, True), GREEN, alpha=reveal(lt, 1.9))
    caption(draw, "换 27 种物品后，GRID_DRAWITEMS 才稳定报 items=27", reveal(lt, 2.2))


def scene_evidence(base, draw, lt, dur):
    text(draw, (W / 2, 92), "这次拿到的证据", zh(44, True), FG, alpha=reveal(lt, 0.0))
    rows = [
        ("客户端 27 格：GRID_DRAWITEMS items=27", 0.4),
        ("FULL 预览 27 格，COMPACT 也是 27", 0.9),
        ("server box 的 2 铁 + 4 绿宝石正常", 1.4),
        ("真实 hover 的 tooltip 路径正常", 1.9),
    ]
    y = 220
    for s, at in rows:
        a = reveal(lt, at)
        check(draw, (330, y), alpha=a, size=26)
        text(draw, (372, y), s, zh(28), FG, anchor="lm", alpha=a)
        y += 74
    text(draw, (W / 2, 560), "27 格渲染没问题；键位那部分是另一个故事",
         zh(22), MUTED, alpha=reveal(lt, 2.4))
    caption(draw, "证据在 runs/p196-shulker-grid27/（日志 + 截图）", reveal(lt, 2.6))


def scene_boundary(base, draw, lt, dur):
    text(draw, (W / 2, 88), "诚实边界", zh(44, True), FG, alpha=reveal(lt, 0.0))
    a = reveal(lt, 0.3)
    draw.rounded_rectangle((150, 170, 1130, 300), radius=14, fill=mix(BG, PANEL, a),
                           outline=mix(BG, RED, 0.6 * a), width=2)
    text(draw, (640, 210), "这轮的“预览键重绑定”没有生效", zh(30, True), RED, alpha=a)
    text(draw, (640, 262), "配置字段写进了 preview 分类（忽略）+ F 触发了原版换副手",
         zh(23), MUTED, alpha=a)
    b = reveal(lt, 1.3)
    draw.rounded_rectangle((150, 330, 1130, 460), radius=14, fill=mix(BG, PANEL, b),
                           outline=mix(BG, GREEN, 0.6 * b), width=2)
    text(draw, (640, 370), "已在 p197 更正并验证", zh(30, True), GREEN, alpha=b)
    text(draw, (640, 422), "键位写在 controls 分类，换用无原版冲突的键后全部可复现",
         zh(23), MUTED, alpha=b)
    text(draw, (W / 2, 540), "27 格本身通过；键位结论以 p197 为准",
         zh(24, True), AMBER, alpha=reveal(lt, 2.0))
    caption(draw, "不懂技术也能记住：格子画全了，键位解释后来修好了", reveal(lt, 2.2))


DRAWERS = [scene_intro, scene_why, scene_pitfall, scene_evidence, scene_boundary]


def render_frame(t: float) -> Image.Image:
    base = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(base)
    for i, (start, end) in enumerate(SCENES):
        if start <= t < end or (i == len(SCENES) - 1 and t >= start):
            lt = t - start
            DRAWERS[i](base, draw, lt, end - start)
            a = clamp(lt / 0.35)
            if a < 1.0:
                base = Image.blend(Image.new("RGB", (W, H), BG), base, a)
                draw = ImageDraw.Draw(base)
            break
    for i, (start, end) in enumerate(SCENES):
        on = start <= t < end or (i == len(SCENES) - 1 and t >= start)
        cx = W / 2 - (len(SCENES) - 1) * 22 / 2 + i * 22
        draw.ellipse((cx - 5, 686, cx + 5, 696),
                     fill=GREEN if on else mix(BG, LINE, 1))
    text(draw, (W - 60, 691), f"{int(t // 60):02d}:{int(t % 60):02d} / 00:22", mono(13), DIM)
    return base


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(RUN / "p196-update-simple.mp4"))
    ap.add_argument("--ffmpeg", default=str(FFMPEG))
    ap.add_argument("--stills", nargs="*", type=float, default=None)
    ap.add_argument("--keep-frames", action="store_true")
    args = ap.parse_args()

    if args.stills is not None:
        tmp = ROOT / "work" / "tmp"
        tmp.mkdir(parents=True, exist_ok=True)
        for t in args.stills:
            out = tmp / f"p196-simple-{t:.1f}.png"
            render_frame(t).save(out)
            print(out)
        return 0

    ffmpeg = Path(args.ffmpeg)
    if not ffmpeg.exists():
        print(f"missing ffmpeg: {ffmpeg}", file=sys.stderr)
        return 2
    if FRAMES.exists():
        shutil.rmtree(FRAMES)
    FRAMES.mkdir(parents=True)
    total = int(DURATION * FPS)
    for i in range(total):
        render_frame(i / FPS).save(FRAMES / f"f{i:05d}.png")
        if i % 90 == 0:
            print(f"frame {i}/{total}", flush=True)
    out = Path(args.out)
    subprocess.run([str(ffmpeg), "-y", "-loglevel", "error", "-framerate", str(FPS),
                    "-i", str(FRAMES / "f%05d.png"), "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-crf", "20", "-preset", "medium", "-movflags", "+faststart", str(out)],
                   check=True)
    print(f"video: {out} ({out.stat().st_size} bytes)")
    if not args.keep_frames:
        shutil.rmtree(FRAMES)
    return 0


if __name__ == "__main__":
    sys.exit(main())
