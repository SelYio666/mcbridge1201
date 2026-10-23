#!/usr/bin/env python3
"""Promo/tutorial video for the one-click PCL installer, drawn entirely in code.

Output: share/pcl-onclick/promo.mp4 (1280x720, 30 fps, ~52 s). No assets are used.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import imageio_ffmpeg

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "share" / "pcl-onclick" / "promo.mp4"
W, H, FPS, DUR = 1280, 720, 30, 52.0

BG = (10, 16, 26)
BG2 = (16, 27, 43)
FG = (234, 242, 252)
DIM = (138, 158, 184)
ACCENT = (56, 189, 248)
GREEN = (74, 222, 128)
AMBER = (251, 191, 36)
CARD = (22, 34, 52)
LINE = (44, 60, 84)

FONT_CN = "C:/Windows/Fonts/msyh.ttc"
FONT_CN_B = "C:/Windows/Fonts/msyhbd.ttc"
FONT_CODE = "C:/Windows/Fonts/consola.ttf"
_fonts: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}


def font(path: str, size: int):
    key = (path, size)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(path, size)
    return _fonts[key]


SEG = [(0, 5), (5, 15), (15, 26), (26, 38), (38, 47), (47, 52)]


def scene_index(t: float) -> int:
    for i, (a, b) in enumerate(SEG):
        if a <= t < b:
            return i
    return len(SEG) - 1


def blend(c, a: float):
    a = max(0.0, min(1.0, a))
    return tuple(int(c[i] * a + BG[i] * (1 - a)) for i in range(3))


def fade(t: float, start: float, dur: float = 0.5) -> float:
    return max(0.0, min(1.0, (t - start) / dur))


def background(draw: ImageDraw.ImageDraw) -> None:
    for y in range(H):
        k = y / H
        draw.line([(0, y), (W, y)],
                  fill=tuple(int(BG[i] * (1 - k) + BG2[i] * k) for i in range(3)))
    for x in range(0, W, 64):
        draw.line([(x, 0), (x, H)], fill=(19, 29, 45), width=1)
    for y in range(0, H, 64):
        draw.line([(0, y), (W, y)], fill=(19, 29, 45), width=1)


def header(draw, title: str, sub: str = "") -> None:
    draw.rectangle([0, 0, W, 6], fill=ACCENT)
    draw.text((72, 44), title, font=font(FONT_CN_B, 34), fill=FG)
    if sub:
        draw.text((72, 90), sub, font=font(FONT_CN, 19), fill=DIM)


def progress(draw, t: float) -> None:
    draw.rectangle([72, H - 26, W - 72, H - 22], fill=(28, 42, 62))
    draw.rectangle([72, H - 26, int(72 + (W - 144) * t / DUR), H - 22], fill=ACCENT)
    draw.text((W - 168, H - 56), f"{t:04.1f}s", font=font(FONT_CODE, 14), fill=DIM)


def line(draw, x, y, text, f, color, t, start, dx=36):
    a = fade(t, start)
    if a <= 0:
        return
    draw.text((x + int(dx * (1 - a)), y), text, font=f, fill=blend(color, a))


def scene_intro(draw, t):
    a = min(1.0, t / 1.0)
    draw.text((72, 238), "一键把 Minecraft 装进 PCL",
              font=font(FONT_CN_B, 52), fill=blend(FG, a))
    draw.text((74, 318), "免 Python · 自动检测 PCL2 · 逐文件 sha1 校验",
              font=font(FONT_CN, 23), fill=blend(DIM, a))
    draw.text((74, 376), "Windows 10 / 11 x64 · 公开下载源",
              font=font(FONT_CN, 19), fill=blend(ACCENT, a))


def scene_problem(draw, t):
    header(draw, "为什么需要它", "PCL 不再提供版本下载，游戏文件要自己准备")
    line(draw, 96, 168, "① 需要一份完整的游戏文件", font(FONT_CN, 24), FG, t, 5.4)
    line(draw, 96, 220, "客户端 jar、库、资源、natives，少一个就崩", font(FONT_CN, 18), DIM, t, 5.9)
    line(draw, 96, 286, "② 手动拼目录容易出错", font(FONT_CN, 24), FG, t, 6.8)
    line(draw, 96, 338, "目录名、版本 json、classpath，任何一处不对都启动不了", font(FONT_CN, 18), DIM, t, 7.3)
    line(draw, 96, 404, "③ 下载慢或中断，还得从头来", font(FONT_CN, 24), FG, t, 8.2)
    line(draw, 96, 456, "官方 CDN 慢、镜像也会波动，需要校验和回退", font(FONT_CN, 18), DIM, t, 8.7)


def scene_three(draw, t):
    header(draw, "三步：下载 → 解压 → 双击", "Release 里下载 mcbridge-pcl-setup.zip（约 9 MB）")
    steps = [("1", "下载 zip"), ("2", "解压"), ("3", "双击 exe")]
    for i, (n, label) in enumerate(steps):
        start = 15.4 + i * 1.0
        a = fade(t, start)
        if a <= 0:
            continue
        x = 120 + i * 360
        draw.rounded_rectangle([x, 220, x + 300, 400], radius=18, fill=CARD, outline=LINE, width=2)
        draw.text((x + 26, 244), n, font=font(FONT_CN_B, 44), fill=blend(ACCENT, a))
        draw.text((x + 26, 320), label, font=font(FONT_CN_B, 26), fill=blend(FG, a))
    line(draw, 120, 470, "不需要安装 Python；双击后按提示回车即可", font(FONT_CN, 19), DIM, t, 18.6)


def scene_flow(draw, t):
    header(draw, "它替你做了什么", "每一步都校验，失败自动换 BMCLAPI 镜像")
    rows = [
        ("版本清单", "找到目标版本的 JSON"),
        ("客户端 jar", "下载 + sha1 校验"),
        ("库与 natives", "70 个库，解压 Windows dll"),
        ("资源对象", "约 3900 个，逐个校验"),
        ("启动器配置", "写 launcher_profiles.json"),
    ]
    y = 158
    for i, (k, v) in enumerate(rows):
        start = 26.4 + i * 1.7
        line(draw, 96, y, k, font(FONT_CN_B, 23), ACCENT, t, start)
        line(draw, 420, y + 2, v, font(FONT_CN, 19), FG, t, start + 0.2, dx=18)
        y += 84


def scene_result(draw, t):
    header(draw, "实测：PCL2 版本列表直接出现", "在 PCL2 2.13.1.1 上安装 1.20.4 后截图")
    a = fade(t, 38.4)
    if a > 0:
        draw.rounded_rectangle([96, 170, 760, 470], radius=16, fill=CARD, outline=LINE, width=2)
        draw.text((124, 196), "版本选择 · 常规版本", font=font(FONT_CN_B, 22), fill=blend(FG, a))
        for i, v in enumerate(("1.21.1", "1.20.4", "1.16.5")):
            yy = 258 + i * 62
            draw.rounded_rectangle([124, yy, 700, yy + 46], radius=10,
                                   fill=(28, 44, 66) if v == "1.20.4" else (20, 31, 48))
            draw.text((146, yy + 10), v, font=font(FONT_CODE, 20),
                      fill=blend(GREEN if v == "1.20.4" else FG, a))
        draw.text((124, 440), "新装的版本会自动出现在列表里", font=font(FONT_CN, 17), fill=blend(DIM, a))
    line(draw, 820, 210, "Java 要选对", font(FONT_CN_B, 24), AMBER, t, 40.2)
    line(draw, 820, 252, "1.20.1 → 17", font(FONT_CN, 19), FG, t, 40.7)
    line(draw, 820, 288, "1.21.1 → 21", font(FONT_CN, 19), FG, t, 41.0)


def scene_end(draw, t):
    a = fade(t, 47.3)
    draw.text((72, 252), "一键安装到 PCL", font=font(FONT_CN_B, 48), fill=blend(FG, a))
    draw.text((74, 326), "Release v0.5.5 · mcbridge-pcl-setup.zip", font=font(FONT_CODE, 20),
              fill=blend(ACCENT, a))
    draw.text((74, 372), "公开下载源 · 不托管、不分发游戏文件", font=font(FONT_CN, 18),
              fill=blend(DIM, a))


def render_at(t: float) -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    background(d)
    s = scene_index(t)
    if s == 0:
        scene_intro(d, t)
    elif s == 1:
        scene_problem(d, t)
    elif s == 2:
        scene_three(d, t)
    elif s == 3:
        scene_flow(d, t)
    elif s == 4:
        scene_result(d, t)
    else:
        scene_end(d, t)
    progress(d, t)
    return img


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-c:v", "libx264", "-preset", "medium", "-crf", "23", "-pix_fmt", "yuv420p",
           "-movflags", "+faststart", str(OUT)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    try:
        for i in range(int(DUR * FPS)):
            proc.stdin.write(render_at(i / FPS).tobytes())
    finally:
        proc.stdin.close()
        rc = proc.wait()
    if rc != 0:
        raise SystemExit(f"ffmpeg failed rc={rc}")
    print("wrote", OUT, f"{OUT.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
