#!/usr/bin/env python3
"""A deliberately simple explainer video for p218 (use PCL to launch the installed 1.21.1).

Plain language, big visuals: the install is already on disk, PCL only needs to scan versions/,
the offline name stays SelYio, and mods live under the isolated version folder.

Usage:
    python runs/p218-pcl-import-video/make_video_simple.py
    python runs/p218-pcl-import-video/make_video_simple.py --stills 2 7 11 16 21

Output: runs/p218-pcl-import-video/p218-pcl-launch-simple.mp4 (1280x720, 30 fps, 22 s).
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
FRAMES = ROOT / "work" / "tmp" / "p218-simple-frames"

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


def keycap(draw, center, label, *, w=210, h=64, color=GREEN, alpha=1.0, font=None):
    cx, cy = center
    draw.rounded_rectangle((cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), radius=12,
                           fill=mix(BG, color, 0.14 * alpha),
                           outline=mix(BG, color, 0.85 * alpha), width=2)
    text(draw, (cx, cy), label, font or mono(22), color, alpha=alpha)


def caption(draw, s, alpha=1.0, y=646):
    if alpha <= 0:
        return
    box = draw.textbbox((0, 0), s, font=zh(26))
    w = box[2] - box[0]
    draw.rounded_rectangle((W / 2 - w / 2 - 22, y - 28, W / 2 + w / 2 + 22, y + 28), radius=26,
                           fill=mix(BG, PANEL, alpha), outline=mix(BG, LINE, alpha), width=1)
    text(draw, (W / 2, y), s, zh(26), FG, alpha=alpha)


def scene_intro(base, draw, lt, dur):
    text(draw, (W / 2, 150), "这次只讲一件事", zh(26), MUTED, alpha=reveal(lt, 0.0))
    text(draw, (W / 2, 226), "用 PCL 启动 1.21.1", zh(62, True), FG, alpha=reveal(lt, 0.25))
    text(draw, (W / 2, 300), "已经装好了，不用再“导入”", zh(30), GREEN, alpha=reveal(lt, 0.7))
    keycap(draw, (W / 2, 430), "1.21.1  ·  SelYio", w=420, h=84, color=GREEN,
           alpha=reveal(lt, 1.1), font=mono(30))
    caption(draw, "PCL 扫 versions/ 就能看见，离线启动不需要账号", reveal(lt, 1.7))


def scene_where(base, draw, lt, dur):
    text(draw, (W / 2, 88), "文件在哪", zh(44, True), FG, alpha=reveal(lt, 0.0))
    a = reveal(lt, 0.3)
    draw.rounded_rectangle((150, 150, 1130, 300), radius=14, fill=mix(BG, PANEL, a),
                           outline=mix(BG, LINE, a), width=2)
    text(draw, (190, 186), "%APPDATA%\\.minecraft\\versions\\", mono(22), BLUE, anchor="lm", alpha=a)
    for i, (name, typ) in enumerate([("1.20.4", "正式版"), ("1.21.1", "正式版")]):
        y = 232 + i * 34
        text(draw, (210, y), name, mono(22), FG, anchor="lm", alpha=reveal(lt, 0.6 + i * 0.2))
        text(draw, (360, y), typ, zh(18), MUTED, anchor="lm", alpha=reveal(lt, 0.6 + i * 0.2))
        check(draw, (1050, y), size=20, alpha=reveal(lt, 0.9 + i * 0.2))
    text(draw, (W / 2, 360), "1.21.1.jar 的 SHA-1 和官方一致", zh(26), MUTED, alpha=reveal(lt, 1.4))
    text(draw, (W / 2, 410), "30c73b1c…  ==  30c73b1c…   MATCH", mono(24), GREEN, alpha=reveal(lt, 1.6))
    caption(draw, "文件完整，不需要重新下载 26 MB 的客户端", reveal(lt, 1.9))


def scene_steps(base, draw, lt, dur):
    text(draw, (W / 2, 88), "三步启动", zh(44, True), FG, alpha=reveal(lt, 0.0))
    cards = [("1", "打开 PCL", "启动页"), ("2", "选 1.21.1", "版本选择"), ("3", "启动游戏", "离线即可")]
    for i, (n, title_, sub) in enumerate(cards):
        a = reveal(lt, 0.3 + i * 0.45)
        x = 170 + i * 330
        draw.rounded_rectangle((x, 190, x + 290, 430), radius=16, fill=mix(BG, PANEL, a),
                               outline=mix(BG, GREEN, 0.5 * a), width=2)
        draw.ellipse((x + 22, 214, x + 62, 254), fill=mix(BG, GREEN, 0.25 * a),
                     outline=mix(BG, GREEN, a), width=2)
        text(draw, (x + 42, 234), n, mono(20), FG, alpha=a)
        text(draw, (x + 145, 292), title_, zh(26, True), FG, alpha=a)
        text(draw, (x + 145, 340), sub, zh(20), MUTED, alpha=a)
    keycap(draw, (W / 2 - 150, 520), "1.21.1", w=220, color=BLUE, alpha=reveal(lt, 2.0))
    keycap(draw, (W / 2 + 150, 520), "SelYio", w=220, color=AMBER, alpha=reveal(lt, 2.2))
    caption(draw, "PCL 启动页 → 版本选择 → 1.21.1 → 启动；用户名保持 SelYio", reveal(lt, 1.8))


def scene_why(base, draw, lt, dur):
    text(draw, (W / 2, 88), "为什么不用“导入”", zh(44, True), FG, alpha=reveal(lt, 0.0))
    a = reveal(lt, 0.3)
    b = reveal(lt, 0.9)
    draw.rounded_rectangle((150, 170, 1130, 300), radius=14, fill=mix(BG, PANEL, a),
                           outline=mix(BG, GREEN, 0.5 * a), width=2)
    text(draw, (W / 2, 212), "PCL 直接扫描 versions/ 目录", zh(28, True), GREEN, alpha=a)
    text(draw, (W / 2, 258), "不需要 launcher_profiles.json，也不需要跑安装面板", zh(22), MUTED, alpha=a)
    draw.rounded_rectangle((150, 330, 1130, 460), radius=14, fill=mix(BG, PANEL, b),
                           outline=mix(BG, AMBER, 0.5 * b), width=2)
    text(draw, (W / 2, 372), "只有官方启动器才需要“让其他启动器识别”", zh(26, True), AMBER, alpha=b)
    text(draw, (W / 2, 418), "写的是 launcher_profiles.json；与 PCL 无关", zh(22), MUTED, alpha=b)
    caption(draw, "所以这一步不是导入文件，是让 PCL 看见游戏目录", reveal(lt, 1.8))


def scene_care(base, draw, lt, dur):
    text(draw, (W / 2, 88), "两个小坑", zh(44, True), FG, alpha=reveal(lt, 0.0))
    a = reveal(lt, 0.3)
    draw.rounded_rectangle((150, 165, 1130, 300), radius=14, fill=mix(BG, PANEL, a),
                           outline=mix(BG, LINE, a), width=2)
    text(draw, (W / 2, 205), "版本隔离：模组放 versions\\1.21.1\\mods", zh(24, True), FG, alpha=a)
    text(draw, (W / 2, 252), "关掉隔离才读根目录 mods；别只丢在 .minecraft\\mods", zh(20), MUTED, alpha=a)
    b = reveal(lt, 1.2)
    draw.rounded_rectangle((150, 330, 1130, 465), radius=14, fill=mix(BG, PANEL, b),
                           outline=mix(BG, LINE, b), width=2)
    text(draw, (W / 2, 370), "存档的离线 UUID 跟用户名绑定", zh(24, True), FG, alpha=b)
    text(draw, (W / 2, 417), "换名字开同一个存档会像“清空”，保持 SelYio 即可", zh(20), MUTED, alpha=b)
    caption(draw, "记住这两条，PCL 这边就不会“看起来没装/存档没了”", reveal(lt, 1.9))


DRAWERS = [scene_intro, scene_where, scene_steps, scene_why, scene_care]


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
        draw.ellipse((cx - 5, 686, cx + 5, 696), fill=GREEN if on else mix(BG, LINE, 1))
    text(draw, (W - 60, 691), f"{int(t // 60):02d}:{int(t % 60):02d} / 00:22", mono(13), DIM)
    return base


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(RUN / "p218-pcl-launch-simple.mp4"))
    ap.add_argument("--ffmpeg", default=str(FFMPEG))
    ap.add_argument("--stills", nargs="*", type=float, default=None)
    ap.add_argument("--keep-frames", action="store_true")
    args = ap.parse_args()

    if args.stills is not None:
        tmp = ROOT / "work" / "tmp"
        tmp.mkdir(parents=True, exist_ok=True)
        for t in args.stills:
            out = tmp / f"p218-simple-{t:.1f}.png"
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
