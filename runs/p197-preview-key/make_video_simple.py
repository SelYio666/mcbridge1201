#!/usr/bin/env python3
"""A deliberately simple explainer video for p197 (plain language, big visuals).

The detailed video (make_video.py) is for reviewers. This one is for "what changed, in one
breath": a misplaced config key, the F-key side effect, and the three gestures J / J+K / release.

Usage:
    python runs/p197-preview-key/make_video_simple.py
    python runs/p197-preview-key/make_video_simple.py --stills 2 7 11.5 16.5 21.5

Output: runs/p197-preview-key/p197-update-simple.mp4 (1280x720, 30 fps, 24 s).
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
FRAMES = ROOT / "work" / "tmp" / "p197-simple-frames"

W, H = 1280, 720
FPS = 30
DURATION = 24.0

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

SCENES = [(0.0, 4.5), (4.5, 9.5), (9.5, 14.0), (14.0, 19.5), (19.5, 24.0)]


def zh(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(ZH_B if bold else ZH, size)


def mono(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(MONO_B, size)


def clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def ease(v: float) -> float:
    v = clamp(v)
    return 1 - (1 - v) ** 3


def pop(v: float) -> float:
    """Overshoot a little, feels like a key press."""
    v = clamp(v)
    return 1 + 0.12 * (1 - v) * (1 - v) - 0.12


def mix(a, b, t: float):
    t = clamp(t)
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def reveal(lt: float, delay: float, dur: float = 0.4) -> float:
    return ease((lt - delay) / dur)


def text(draw, xy, s, font, fill, *, anchor="mm", alpha=1.0):
    if alpha <= 0 or not s:
        return
    draw.text(xy, s, font=font, fill=mix(BG, fill, alpha), anchor=anchor)


def keycap(draw, center, label, *, size=116, color=GREEN, pressed=0.0, alpha=1.0, font=None):
    s = size * pop(pressed) if pressed > 0 else size
    x, y = center
    off = int(6 * (1 - pressed)) if pressed > 0 else 0
    box = (x - s / 2, y - s / 2 + off, x + s / 2, y + s / 2 + off)
    draw.rounded_rectangle(box, radius=int(s * 0.22), fill=mix(BG, color, 0.18 * alpha),
                           outline=mix(BG, color, 0.85 * alpha), width=3)
    draw.rounded_rectangle((box[0] + 6, box[3] - 14, box[2] - 6, box[3] - 6),
                           radius=4, fill=mix(BG, color, 0.25 * alpha))
    text(draw, (x, y + off), label, font or mono(int(size * 0.42)), color, alpha=alpha)


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


def mini_grid(draw, center, cols, rows, shown, *, cell=26, gap=6, alpha=1.0):
    """A toy preview grid; `shown` cells are visible (0..cols*rows)."""
    cx, cy = center
    total_w = cols * cell + (cols - 1) * gap
    total_h = rows * cell + (rows - 1) * gap
    x0, y0 = cx - total_w / 2, cy - total_h / 2
    draw.rounded_rectangle((x0 - 12, y0 - 12, x0 + total_w + 12, y0 + total_h + 12), radius=10,
                           fill=mix(BG, PANEL, alpha), outline=mix(BG, LINE, alpha), width=2)
    palette = [GREEN, BLUE, AMBER, (167, 139, 250), (244, 114, 182)]
    for i in range(cols * rows):
        r, c = divmod(i, cols)
        x = x0 + c * (cell + gap)
        y = y0 + r * (cell + gap)
        if i >= shown:
            draw.rounded_rectangle((x, y, x + cell, y + cell), radius=5,
                                   outline=mix(BG, LINE, alpha), width=1)
            continue
        a = alpha * clamp((shown - i) / 3)
        draw.rounded_rectangle((x, y, x + cell, y + cell), radius=5,
                               fill=mix(BG, palette[i % len(palette)], 0.55 * a),
                               outline=mix(BG, palette[i % len(palette)], a), width=1)


def caption(draw, s, alpha=1.0, y=646):
    if alpha <= 0:
        return
    box = draw.textbbox((0, 0), s, font=zh(26))
    w = box[2] - box[0]
    draw.rounded_rectangle((W / 2 - w / 2 - 22, y - 28, W / 2 + w / 2 + 22, y + 28), radius=26,
                           fill=mix(BG, PANEL, alpha), outline=mix(BG, LINE, alpha), width=1)
    text(draw, (W / 2, y), s, zh(26), FG, alpha=alpha)


def scene_intro(base, draw, lt, dur):
    text(draw, (W / 2, 150), "这次更新其实只有一句话", zh(26), MUTED, alpha=reveal(lt, 0.0))
    text(draw, (W / 2, 226), "预览键可以自己改了", zh(64, True), FG, alpha=reveal(lt, 0.25))
    # J key pressed, a small grid pops next to it
    press = ease((lt - 1.0) / 0.35)
    keycap(draw, (400, 410), "J", size=140, pressed=press, color=GREEN, alpha=reveal(lt, 0.8))
    shown = int(9 * ease((lt - 1.35) / 0.7))
    mini_grid(draw, (700, 410), 3, 3, shown, cell=30, gap=7, alpha=reveal(lt, 1.2))
    text(draw, (980, 380), "按 J", zh(32, True), GREEN, alpha=reveal(lt, 1.3))
    text(draw, (980, 430), "出现小预览", zh(26), MUTED, alpha=reveal(lt, 1.45))
    text(draw, (980, 480), "再按 K 就全展开", zh(22), DIM, alpha=reveal(lt, 1.7))
    caption(draw, "以前改配置没反应，现在真的会跟着配置走", reveal(lt, 1.9))


def scene_drawer(base, draw, lt, dur):
    text(draw, (W / 2, 92), "之前为什么改不动？", zh(44, True), FG, alpha=reveal(lt, 0.0))
    text(draw, (W / 2, 150), "因为键被放进了错误的“抽屉”", zh(26), MUTED, alpha=reveal(lt, 0.2))
    drawers = [("preview", (300, 462), RED, "放这里 = 没用", 2.2),
               ("controls", (900, 462), GREEN, "mod 只读这里", 3.6)]
    for name, (cx, cy), color, note, note_at in drawers:
        a = reveal(lt, 0.3)
        draw.rounded_rectangle((cx - 210, cy - 110, cx + 210, cy + 110), radius=16,
                               fill=mix(BG, PANEL, a), outline=mix(BG, color, 0.5 * a), width=2)
        text(draw, (cx, cy - 68), name, mono(30), color, alpha=a)
        text(draw, (cx, cy + 72), note, zh(22), MUTED, alpha=reveal(lt, note_at))
    # the key card travels: top -> wrong drawer -> right drawer
    seg1 = ease((lt - 0.9) / 0.8)
    seg2 = ease((lt - 3.0) / 0.8)
    x = 600 + (300 - 600) * seg1 + (900 - 300) * seg2
    y = 205 + (462 - 205) * seg1
    card_a = reveal(lt, 0.6)
    edge = GREEN if seg2 > 0.6 else RED
    draw.rounded_rectangle((x - 150, y - 32, x + 150, y + 32), radius=10,
                           fill=mix(BG, (30, 42, 56), card_a),
                           outline=mix(BG, edge, 0.75 * card_a), width=2)
    text(draw, (x, y), "previewKey", mono(24), FG, alpha=card_a)
    if 1.9 < lt < 3.0:
        cross(draw, (x + 122, y - 30), size=20,
              alpha=reveal(lt, 1.9) * (1 - reveal(lt, 2.9)))
    if lt > 3.9:
        check(draw, (900, 462), alpha=reveal(lt, 3.9), size=20)
    caption(draw, "放错地方，游戏根本不读；放进 controls 才会生效", reveal(lt, 2.4))


def scene_fkey(base, draw, lt, dur):
    text(draw, (W / 2, 92), "还有一个小坑", zh(44, True), FG, alpha=reveal(lt, 0.0))
    text(draw, (W / 2, 150), "F 是原版的“换手”键", zh(26), MUTED, alpha=reveal(lt, 0.2))
    keycap(draw, (330, 430), "F", pressed=ease((lt - 0.6) / 0.3), color=AMBER, alpha=reveal(lt, 0.4))
    # two hands as rounded boxes with an item flying between them
    draw.rounded_rectangle((620, 360, 790, 500), radius=18, fill=mix(BG, PANEL, 1),
                           outline=mix(BG, LINE, 1), width=2)
    draw.rounded_rectangle((900, 360, 1070, 500), radius=18, fill=mix(BG, PANEL, 1),
                           outline=mix(BG, LINE, 1), width=2)
    text(draw, (705, 330), "主手", zh(24), MUTED, alpha=reveal(lt, 0.8))
    text(draw, (985, 330), "副手", zh(24), MUTED, alpha=reveal(lt, 0.8))
    move = ease((lt - 1.2) / 0.9)
    ix = 705 + (985 - 705) * move
    draw.rounded_rectangle((ix - 26, 404, ix + 26, 456), radius=6,
                           fill=mix(BG, GREEN, 0.6), outline=mix(BG, GREEN, 1), width=2)
    text(draw, (845, 540), "箱子被换走了", zh(24), RED, alpha=reveal(lt, 2.0))
    caption(draw, "所以按 F 的时候，东西先被换走，看起来就像预览坏了", reveal(lt, 1.6))


def scene_gestures(base, draw, lt, dur):
    text(draw, (W / 2, 88), "现在的正确手势", zh(44, True), FG, alpha=reveal(lt, 0.0))
    # phase: 0 J only, 1 J+K, 2 released
    phase = 0 if lt < 2.0 else (1 if lt < 4.2 else 2)
    cols = 3 if phase == 0 else 9
    rows = 3
    total = cols * rows
    press_j = ease((lt - 0.3) / 0.3) if phase >= 0 else 0
    press_k = ease((lt - 2.0) / 0.3) if phase >= 1 else 0
    keycap(draw, (250, 330), "J", pressed=press_j, color=GREEN, alpha=reveal(lt, 0.1))
    keycap(draw, (250, 470), "K", pressed=press_k, color=BLUE, alpha=reveal(lt, 0.2),
           size=100)
    text(draw, (250, 552), "J 打开 / 再按 K 展开", zh(20), MUTED, alpha=reveal(lt, 0.5))
    if phase == 2:
        shown = 0
        grid_a = 1 - reveal(lt, 4.2)
    else:
        shown = int(total * ease((lt - (0.5 if phase == 0 else 2.2)) / 0.7))
        grid_a = 1.0
    mini_grid(draw, (800, 360), cols, rows, shown, cell=24, gap=6, alpha=grid_a)
    labels = ["① 小预览", "② 全部展开", "③ 松手收起"]
    text(draw, (800, 496), labels[phase], zh(30, True), [GREEN, BLUE, MUTED][phase],
         alpha=reveal(lt, 0.6))
    for i in range(3):
        cx = 800 + (i - 1) * 24
        draw.ellipse((cx - 6, 540, cx + 6, 552),
                     fill=mix(BG, GREEN if i == phase else LINE, 1))
    caption(draw, "J 打开预览，按住 J 再按 K 全展开，松手就收起", reveal(lt, 0.9))


def scene_done(base, draw, lt, dur):
    text(draw, (W / 2, 96), "结果", zh(30), MUTED, alpha=reveal(lt, 0.0))
    text(draw, (W / 2, 168), "搞定", zh(76, True), GREEN, alpha=reveal(lt, 0.15))
    rows = ["7 项检查全部通过", "自动测试和哈希校验通过", "已上传 GitHub"]
    y = 300
    for i, s in enumerate(rows):
        a = reveal(lt, 0.6 + i * 0.35)
        check(draw, (390, y), alpha=a, size=26)
        text(draw, (430, y), s, zh(30), FG, anchor="lm", alpha=a)
        y += 74
    text(draw, (W / 2, 580), "想自己试：runs/p197-preview-key/", zh(20), DIM, alpha=reveal(lt, 1.8))
    text(draw, (W / 2, 612), "详细版视频也在同一个目录", zh(20), DIM, alpha=reveal(lt, 2.0))


DRAWERS = [scene_intro, scene_drawer, scene_fkey, scene_gestures, scene_done]


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
    # scene dots
    for i, (start, end) in enumerate(SCENES):
        on = start <= t < end or (i == len(SCENES) - 1 and t >= start)
        cx = W / 2 - (len(SCENES) - 1) * 22 / 2 + i * 22
        draw.ellipse((cx - 5, 686, cx + 5, 696),
                     fill=GREEN if on else mix(BG, LINE, 1))
    text(draw, (W - 60, 691), f"{int(t // 60):02d}:{int(t % 60):02d} / 00:24", mono(13), DIM)
    return base


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(RUN / "p197-update-simple.mp4"))
    ap.add_argument("--ffmpeg", default=str(FFMPEG))
    ap.add_argument("--stills", nargs="*", type=float, default=None)
    ap.add_argument("--keep-frames", action="store_true")
    args = ap.parse_args()

    if args.stills is not None:
        tmp = ROOT / "work" / "tmp"
        tmp.mkdir(parents=True, exist_ok=True)
        for t in args.stills:
            out = tmp / f"p197-simple-{t:.1f}.png"
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
