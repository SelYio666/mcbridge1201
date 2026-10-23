#!/usr/bin/env python3
"""Promo/tutorial video v2 for the one-click PCL installer + quick panel.

Everything is drawn with Pillow; ffmpeg only encodes. Output:
share/pcl-onclick/promo.mp4 (1280x720, 30 fps, ~56 s).
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import imageio_ffmpeg

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "share" / "pcl-onclick" / "promo.mp4"
W, H, FPS, DUR = 1280, 720, 30, 56.0

BG = (10, 16, 26)
BG2 = (17, 28, 44)
FG = (234, 242, 252)
DIM = (138, 158, 184)
ACCENT = (56, 189, 248)
GREEN = (74, 222, 128)
AMBER = (251, 191, 36)
CARD = (24, 36, 55)
CARD2 = (30, 45, 68)
LINE = (46, 63, 88)
WIN = (22, 32, 48)

FONT_CN = "C:/Windows/Fonts/msyh.ttc"
FONT_CN_B = "C:/Windows/Fonts/msyhbd.ttc"
FONT_CODE = "C:/Windows/Fonts/consola.ttf"
_fonts: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}


def font(path: str, size: int):
    key = (path, size)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(path, size)
    return _fonts[key]


SEG = [(0, 5), (5, 14), (14, 27), (27, 38), (38, 48), (48, 56)]


def scene_of(t: float) -> int:
    for i, (a, b) in enumerate(SEG):
        if a <= t < b:
            return i
    return len(SEG) - 1


def mix(c, a: float):
    a = max(0.0, min(1.0, a))
    return tuple(int(c[i] * a + BG[i] * (1 - a)) for i in range(3))


def fade(t: float, start: float, dur: float = 0.5) -> float:
    return max(0.0, min(1.0, (t - start) / dur))


def bg(draw: ImageDraw.ImageDraw) -> None:
    for y in range(H):
        k = y / H
        draw.line([(0, y), (W, y)], fill=tuple(int(BG[i] * (1 - k) + BG2[i] * k) for i in range(3)))
    for x in range(0, W, 64):
        draw.line([(x, 0), (x, H)], fill=(19, 29, 45), width=1)
    for y in range(0, H, 64):
        draw.line([(0, y), (W, y)], fill=(19, 29, 45), width=1)


def header(draw, title: str, sub: str = "") -> None:
    draw.rectangle([0, 0, W, 6], fill=ACCENT)
    draw.text((72, 44), title, font=font(FONT_CN_B, 34), fill=FG)
    if sub:
        draw.text((72, 90), sub, font=font(FONT_CN, 19), fill=DIM)


def bar(draw, t: float) -> None:
    draw.rectangle([72, H - 26, W - 72, H - 22], fill=(28, 42, 62))
    draw.rectangle([72, H - 26, int(72 + (W - 144) * t / DUR), H - 22], fill=ACCENT)
    draw.text((W - 168, H - 56), f"{t:04.1f}s", font=font(FONT_CODE, 14), fill=DIM)


def line(draw, x, y, text, f, color, t, start, dx=34):
    a = fade(t, start)
    if a <= 0:
        return
    draw.text((x + int(dx * (1 - a)), y), text, font=f, fill=mix(color, a))


def scene_intro(d, t):
    a = min(1.0, t)
    d.text((72, 210), "一键把 Minecraft 装进 PCL", font=font(FONT_CN_B, 52), fill=mix(FG, a))
    d.text((74, 292), "图形面板 · 自动检测 PCL2 · 逐文件 sha1", font=font(FONT_CN, 23), fill=mix(DIM, a))
    d.text((74, 350), "正式版 / 快照 / 远古，全都能选", font=font(FONT_CN, 21), fill=mix(ACCENT, a))


def scene_problem(d, t):
    header(d, "为什么需要它", "PCL 不再提供版本下载，游戏文件要自己准备")
    line(d, 96, 160, "① 需要完整游戏文件", font(FONT_CN_B, 24), FG, t, 5.4)
    line(d, 96, 204, "客户端 jar、库、资源、natives，少一个就崩", font(FONT_CN, 18), DIM, t, 5.9)
    line(d, 96, 286, "② 手动拼目录容易出错", font(FONT_CN_B, 24), FG, t, 6.9)
    line(d, 96, 330, "版本 json、classpath、资源索引，任何一处不对都启动不了", font(FONT_CN, 18), DIM, t, 7.4)
    line(d, 96, 412, "③ 下载慢或中断，还得从头来", font(FONT_CN_B, 24), FG, t, 8.4)
    line(d, 96, 456, "官方 CDN 慢、镜像会波动，需要校验和回退", font(FONT_CN, 18), DIM, t, 8.9)


def scene_panel(d, t):
    header(d, "快捷面板：选版本 → 点安装", "自动检测 PCL2 目录，进度、日志都看得见")
    a = fade(t, 14.5, 0.6)
    if a <= 0:
        return
    x0, y0, x1, y1 = 120, 150, 1160, 560
    d.rounded_rectangle([x0, y0, x1, y1], radius=14, fill=mix(WIN, a), outline=LINE, width=2)
    d.rectangle([x0, y0, x1, y0 + 34], fill=mix(CARD2, a))
    d.text((x0 + 14, y0 + 8), "mcbridge · 一键安装到 PCL", font=font(FONT_CN, 14), fill=mix(FG, a))

    d.text((x0 + 24, y0 + 58), "版本", font=font(FONT_CN, 16), fill=mix(DIM, a))
    d.rounded_rectangle([x0 + 90, y0 + 52, x0 + 360, y0 + 86], radius=6, fill=mix(CARD, a), outline=LINE)
    d.text((x0 + 104, y0 + 58), "26.3", font=font(FONT_CODE, 16), fill=mix(FG, a))
    d.rounded_rectangle([x0 + 376, y0 + 52, x0 + 500, y0 + 86], radius=6, fill=mix(CARD, a), outline=LINE)
    d.text((x0 + 392, y0 + 58), "正式版", font=font(FONT_CN, 15), fill=mix(FG, a))

    d.text((x0 + 24, y0 + 112), "目录", font=font(FONT_CN, 16), fill=mix(DIM, a))
    d.rounded_rectangle([x0 + 90, y0 + 106, x0 + 900, y0 + 140], radius=6, fill=mix(CARD, a), outline=LINE)
    d.text((x0 + 104, y0 + 112), "D:\\我的世界\\.minecraft\\涟漪专用启动器\\.minecraft",
           font=font(FONT_CN, 14), fill=mix(FG, a))

    d.rounded_rectangle([x0 + 24, y0 + 176, x0 + 190, y0 + 216], radius=6, fill=mix(ACCENT, a))
    d.text((x0 + 46, y0 + 184), "安装到 PCL", font=font(FONT_CN_B, 16), fill=mix(BG, a))

    d.rectangle([x0 + 24, y0 + 244, x0 + 900, y0 + 256], fill=(28, 42, 62))
    prog = 0.62 + 0.2 * min(1.0, max(0.0, (t - 20) / 6))
    d.rectangle([x0 + 24, y0 + 244, int(x0 + 24 + 876 * prog), y0 + 256], fill=GREEN)
    d.text((x0 + 24, y0 + 270), "assets 2600/3911 · 校验中", font=font(FONT_CN, 14), fill=mix(DIM, a))
    for i, txt in enumerate(("版本清单 OK", "客户端 jar OK", "库与 natives OK", "资源对象 ...")):
        d.text((x0 + 24 + i * 210, y0 + 318), txt, font=font(FONT_CN, 15),
               fill=mix(FG if i < 3 else DIM, a))


def scene_flow(d, t):
    header(d, "它替你做了什么", "每步校验，失败自动换 BMCLAPI 镜像")
    rows = [
        ("版本清单", "定位版本 JSON"),
        ("客户端 jar", "下载 + sha1 校验"),
        ("库与 natives", "70 个库，解压 Windows dll"),
        ("资源对象", "约 3900 个，逐个校验"),
        ("启动器配置", "写 launcher_profiles.json"),
    ]
    y = 152
    for i, (k, v) in enumerate(rows):
        start = 27.4 + i * 1.5
        line(d, 96, y, k, font(FONT_CN_B, 22), ACCENT, t, start)
        line(d, 400, y + 2, v, font(FONT_CN, 18), FG, t, start + 0.2, dx=16)
        y += 80


def scene_result(d, t):
    header(d, "实测：装完直接出现在 PCL2", "PCL2 2.13.1.1 上安装 1.20.4 后截图")
    a = fade(t, 38.4)
    if a > 0:
        d.rounded_rectangle([96, 160, 720, 470], radius=14, fill=mix(CARD, a), outline=LINE, width=2)
        d.text((124, 184), "版本选择 · 常规版本", font=font(FONT_CN_B, 21), fill=mix(FG, a))
        for i, v in enumerate(("1.21.1", "1.20.4", "1.16.5")):
            yy = 244 + i * 60
            d.rounded_rectangle([124, yy, 660, yy + 44], radius=8,
                                fill=(30, 48, 70) if v == "1.20.4" else mix(CARD2, a))
            d.text((146, yy + 9), v, font=font(FONT_CODE, 19),
                   fill=mix(GREEN if v == "1.20.4" else FG, a))
        d.text((124, 438), "新装版本自动出现", font=font(FONT_CN, 16), fill=mix(DIM, a))
    line(d, 776, 200, "Java 要选对", font(FONT_CN_B, 23), AMBER, t, 40.2)
    line(d, 776, 244, "1.20.1 → 17", font(FONT_CN, 18), FG, t, 40.7)
    line(d, 776, 280, "1.21.1 → 21", font(FONT_CN, 18), FG, t, 41.0)
    line(d, 776, 336, "远古版本 → 8", font(FONT_CN, 18), FG, t, 41.4)


def scene_end(d, t):
    a = fade(t, 48.4)
    d.text((72, 230), "一键安装到 PCL", font=font(FONT_CN_B, 48), fill=mix(FG, a))
    d.text((74, 304), "Release v0.5.5", font=font(FONT_CODE, 20), fill=mix(ACCENT, a))
    d.text((74, 344), "mcbridge-pcl-panel.zip  ·  mcbridge-pcl-setup.zip", font=font(FONT_CODE, 16),
           fill=mix(DIM, a))
    d.text((74, 392), "公开下载源 · 不托管、不分发游戏文件", font=font(FONT_CN, 17), fill=mix(DIM, a))


def render_at(t: float) -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    bg(d)
    s = scene_of(t)
    if s == 0:
        scene_intro(d, t)
    elif s == 1:
        scene_problem(d, t)
    elif s == 2:
        scene_panel(d, t)
    elif s == 3:
        scene_flow(d, t)
    elif s == 4:
        scene_result(d, t)
    else:
        scene_end(d, t)
    bar(d, t)
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
