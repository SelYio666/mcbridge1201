#!/usr/bin/env python3
"""Generate the player-guide promo video entirely from code (Pillow frames -> ffmpeg).

Output: share/player-guide/promo.mp4 (1280x720, 30 fps, ~50 s).
No images, screenshots or audio assets are used; every pixel is drawn here.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import imageio_ffmpeg

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "share" / "player-guide" / "promo.mp4"
W, H, FPS, DUR = 1280, 720, 30, 50.0

BG = (12, 18, 30)
BG2 = (18, 28, 45)
FG = (232, 240, 250)
DIM = (140, 160, 185)
ACCENT = (56, 189, 248)
GREEN = (74, 222, 128)
AMBER = (251, 191, 36)
CARD = (23, 34, 52)
LINE = (45, 60, 82)

FONT_CN = "C:/Windows/Fonts/msyh.ttc"
FONT_CN_B = "C:/Windows/Fonts/msyhbd.ttc"
FONT_CODE = "C:/Windows/Fonts/consola.ttf"
_fonts: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}


def font(path: str, size: int):
    key = (path, size)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(path, size)
    return _fonts[key]


def scene_progress(t: float, segments: list[tuple[float, float]]) -> int:
    for i, (a, b) in enumerate(segments):
        if a <= t < b:
            return i
    return len(segments) - 1


SEG = [(0, 5), (5, 16), (16, 26), (26, 38), (38, 46), (46, 50)]


def background(draw: ImageDraw.ImageDraw) -> None:
    for y in range(H):
        k = y / H
        c = tuple(int(BG[i] * (1 - k) + BG2[i] * k) for i in range(3))
        draw.line([(0, y), (W, y)], fill=c)
    for x in range(0, W, 64):
        draw.line([(x, 0), (x, H)], fill=(20, 30, 46), width=1)
    for y in range(0, H, 64):
        draw.line([(0, y), (W, y)], fill=(20, 30, 46), width=1)


def header(draw: ImageDraw.ImageDraw, title: str, sub: str = "") -> None:
    draw.rectangle([0, 0, W, 6], fill=ACCENT)
    draw.text((72, 46), title, font=font(FONT_CN_B, 34), fill=FG)
    if sub:
        draw.text((72, 92), sub, font=font(FONT_CN, 19), fill=DIM)


def progress_bar(draw: ImageDraw.ImageDraw, t: float) -> None:
    draw.rectangle([72, H - 28, W - 72, H - 24], fill=(30, 44, 64))
    x = 72 + (W - 144) * (t / DUR)
    draw.rectangle([72, H - 28, int(x), H - 24], fill=ACCENT)
    draw.text((W - 160, H - 60), f"{t:04.1f}s", font=font(FONT_CODE, 14), fill=DIM)


def fade_alpha(t: float, start: float, dur: float = 0.5) -> float:
    return max(0.0, min(1.0, (t - start) / dur))


def blend(fill, a: float):
    return tuple(int(c * a + BG[i] * (1 - a)) for i, c in enumerate(fill))


def line_in(draw, x, y, txt, f, fill, t, start, dx=40):
    a = fade_alpha(t, start, 0.5)
    if a <= 0:
        return
    off = int(dx * (1 - a))
    draw.text((x + off, y), txt, font=f, fill=blend(fill, a))


def scene_intro(draw, t):
    a = min(1.0, t / 1.0)
    draw.text((72, 250), "Minecraft 下载源 + 启动器教程",
              font=font(FONT_CN_B, 54), fill=blend(FG, a))
    draw.text((74, 330), "玩家版 · 不用 GitHub · 不用改模组",
              font=font(FONT_CN, 24), fill=blend(DIM, a))
    draw.text((74, 392), "网页 / PDF / 长图，直接转发",
              font=font(FONT_CN, 20), fill=blend(ACCENT, a))


def scene_official(draw, t):
    header(draw, "① 下载源：给谁用", "普通玩家用启动器即可；这份清单用于排障/手动/自建")
    rows = [
        ("版本清单", "piston-meta.mojang.com/mc/game/version_manifest_v2.json"),
        ("资源文件", "resources.download.minecraft.net/<first2>/<hash>"),
        ("库文件", "libraries.minecraft.net/  (full URL from version JSON)"),
        ("Fabric", "meta.fabricmc.net/v2/versions/loader/<mc>"),
        ("Forge", "files.minecraftforge.net/.../promotions_slim.json"),
        ("NeoForge", "maven.neoforged.net/api/maven/versions/releases/..."),
    ]
    y = 150
    for i, (k, v) in enumerate(rows):
        start = 5.3 + i * 1.3
        if t < start:
            break
        line_in(draw, 96, y, k, font(FONT_CN_B, 22), ACCENT, t, start)
        line_in(draw, 96, y + 30, v, font(FONT_CODE, 17), FG, t, start + 0.15, dx=20)
        y += 86


def scene_mirror(draw, t):
    header(draw, "② 官方慢？镜像 + 校验", "BMCLAPI 是社区镜像，非官方；速度会波动")
    line_in(draw, 96, 160, "BMCLAPI 资源", font(FONT_CN_B, 22), AMBER, t, 16.3)
    line_in(draw, 96, 192, "https://bmclapi2.bangbang93.com/assets/<first2>/<hash>",
            font(FONT_CODE, 17), FG, t, 16.5, dx=20)
    line_in(draw, 96, 250, "BMCLAPI Maven（库/加载器）", font(FONT_CN_B, 22), AMBER, t, 17.2)
    line_in(draw, 96, 282, "https://bmclapi2.bangbang93.com/maven/<path>",
            font(FONT_CODE, 17), FG, t, 17.4, dx=20)
    line_in(draw, 96, 360, "下载后校验 sha1：Get-FileHash -Algorithm SHA1",
            font(FONT_CN, 20), FG, t, 18.6)
    line_in(draw, 96, 400, "资源对象没有文件名，路径本身就是校验值",
            font(FONT_CN, 19), DIM, t, 19.4)
    line_in(draw, 96, 470, "两个线路互不影响：Mojang CDN ≠ 加载器 Maven",
            font(FONT_CN, 19), DIM, t, 20.6)


def scene_launchers(draw, t):
    header(draw, "③ 先装好，再导入启动", "PCL 不提供下载；HMCL / Prism 可下载或导入")
    cards = [
        ("PCL", ["先下载好 1.21.1", "游戏目录指向它", "选中版本 → 启动"]),
        ("HMCL", ["可下载或导入", "版本列表里选中", "Java 路径选 21"]),
        ("Prism", ["可下载或导入", "Loader 选 Fabric", "Edit → Java 21"]),
    ]
    cw, ch, gap = 340, 250, 30
    total = len(cards) * cw + (len(cards) - 1) * gap
    x0 = (W - total) // 2
    for i, (name, steps) in enumerate(cards):
        start = 26.4 + i * 1.2
        a = fade_alpha(t, start)
        if a <= 0:
            continue
        x = x0 + i * (cw + gap)
        lift = int(24 * (1 - a))
        draw.rounded_rectangle([x, 160 - lift, x + cw, 160 - lift + ch], radius=16,
                               fill=CARD, outline=LINE, width=2)
        draw.text((x + 22, 176 - lift), name, font=font(FONT_CN_B, 30), fill=ACCENT)
        for j, s in enumerate(steps):
            draw.text((x + 22, 232 - lift + j * 44), f"{j + 1}. {s}",
                      font=font(FONT_CN, 19), fill=blend(FG, a))


def scene_share(draw, t):
    header(draw, "④ 拿资料：四种形态，任选", "对方不需要 GitHub，也不需要会改模组")
    items = [
        ("网页", "双击 index.html 即看，离线可用"),
        ("PDF", "打印 / 发文件都行"),
        ("长图", "微信群、QQ 群直接发"),
        ("文案", "复制粘贴到公告"),
    ]
    for i, (k, v) in enumerate(items):
        start = 38.5 + i * 0.9
        a = fade_alpha(t, start)
        if a <= 0:
            continue
        x = 96 + (i % 2) * 560
        y = 180 + (i // 2) * 170
        draw.rounded_rectangle([x, y, x + 500, y + 130], radius=14,
                               fill=CARD, outline=LINE, width=2)
        draw.text((x + 24, y + 20), k, font=font(FONT_CN_B, 28), fill=GREEN)
        draw.text((x + 24, y + 72), v, font=font(FONT_CN, 18), fill=blend(DIM, a))


def scene_end(draw, t):
    a = fade_alpha(t, 46.3)
    draw.text((72, 260), "Minecraft 下载源 + 启动器教程",
              font=font(FONT_CN_B, 46), fill=blend(FG, a))
    draw.text((74, 330), "纯代码生成 · 无素材 · 可自由转发",
              font=font(FONT_CN, 22), fill=blend(DIM, a))
    draw.text((74, 380), "2026-10-22", font=font(FONT_CODE, 18), fill=blend(ACCENT, a))


def render_at(t: float) -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    background(draw)
    scene = scene_progress(t, SEG)
    if scene == 0:
        scene_intro(draw, t)
    elif scene == 1:
        scene_official(draw, t)
    elif scene == 2:
        scene_mirror(draw, t)
    elif scene == 3:
        scene_launchers(draw, t)
    elif scene == 4:
        scene_share(draw, t)
    else:
        scene_end(draw, t)
    progress_bar(draw, t)
    return img


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [
        ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-c:v", "libx264", "-preset", "medium", "-crf", "23", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", str(OUT),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    total = int(DUR * FPS)
    try:
        for i in range(total):
            proc.stdin.write(render_at(i / FPS).tobytes())
    finally:
        proc.stdin.close()
        rc = proc.wait()
    if rc != 0:
        raise SystemExit(f"ffmpeg failed rc={rc}")
    print("wrote", OUT, f"{OUT.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
