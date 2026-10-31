#!/usr/bin/env python3
"""Update explainer / tutorial video for v0.5.8–v0.5.9 (HMCL support, pooled transport, dir fix).

All frames are drawn with Pillow; ffmpeg only encodes. Output:
share/update-v059/更新介绍.mp4 (1280x720, 30 fps, ~76 s).
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import imageio_ffmpeg

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "share" / "update-v059" / "update-intro.mp4"
W, H, FPS, DUR = 1280, 720, 30, 76.0

BG = (10, 16, 26)
BG2 = (17, 28, 44)
FG = (234, 242, 252)
DIM = (138, 158, 184)
ACCENT = (56, 189, 248)
GREEN = (74, 222, 128)
AMBER = (251, 191, 36)
RED = (248, 113, 113)
CARD = (24, 36, 55)
CARD2 = (30, 45, 68)
LINE = (46, 63, 88)
WIN = (20, 30, 45)

FONT_CN = "C:/Windows/Fonts/msyh.ttc"
FONT_CN_B = "C:/Windows/Fonts/msyhbd.ttc"
FONT_CODE = "C:/Windows/Fonts/consola.ttf"
_fonts: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    key = (path, size)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(path, size)
    return _fonts[key]


SEG = [(0, 7), (7, 18), (18, 31), (31, 43), (43, 54), (54, 66), (66, 76)]


def scene_of(t: float) -> int:
    for i, (a, b) in enumerate(SEG):
        if a <= t < b:
            return i
    return len(SEG) - 1


def fade(t: float, start: float, dur: float = 0.6) -> float:
    return max(0.0, min(1.0, (t - start) / dur))


def mix(c, a: float):
    a = max(0.0, min(1.0, a))
    return tuple(int(c[i] * a + BG[i] * (1 - a)) for i in range(3))


def bg(draw: ImageDraw.ImageDraw) -> None:
    for y in range(H):
        k = y / H
        draw.line([(0, y), (W, y)], fill=tuple(int(BG[i] * (1 - k) + BG2[i] * k) for i in range(3)))
    for x in range(0, W, 64):
        draw.line([(x, 0), (x, H)], fill=(19, 29, 45), width=1)
    for y in range(0, H, 64):
        draw.line([(0, y), (W, y)], fill=(19, 29, 45), width=1)


def text(draw, xy, s, f, fill, a=1.0) -> None:
    draw.text(xy, s, font=f, fill=mix(fill, a))


def wrap(draw, s, f, width, x, y, fill, a=1.0, spacing=10) -> int:
    line = ""
    for ch in s:
        if draw.textlength(line + ch, font=f) > width:
            text(draw, (x, y), line, f, fill, a)
            y += f.size + spacing
            line = ch
        else:
            line += ch
    if line:
        text(draw, (x, y), line, f, fill, a)
        y += f.size + spacing
    return y


def card(draw, x, y, w, h, r=16, fill=CARD, outline=LINE) -> None:
    draw.rounded_rectangle([x, y, x + w, y + h], radius=r, fill=fill, outline=outline, width=2)


def pill(draw, x, y, s, f, fg=ACCENT, bgc=None) -> int:
    tw = draw.textlength(s, font=f)
    w = int(tw + 26)
    draw.rounded_rectangle([x, y, x + w, y + 30], radius=15, fill=bgc or (22, 42, 62), outline=(40, 70, 96), width=1)
    text(draw, (x + 13, y + 4), s, f, fg)
    return w


def term(draw, x, y, w, h, title, lines, shown: float, a=1.0) -> None:
    card(draw, x, y, w, h, 14, WIN, (38, 54, 78))
    draw.rounded_rectangle([x, y, x + w, y + 34], radius=14, fill=(28, 40, 60))
    for i, c in enumerate(((248, 113, 113), (251, 191, 36), (74, 222, 128))):
        draw.ellipse([x + 14 + i * 18, y + 11, x + 24 + i * 18, y + 21], fill=c)
    text(draw, (x + 78, y + 8), title, font(FONT_CN, 13), DIM, a)
    cy = y + 48
    budget = shown
    for s, col in lines:
        if budget <= 0:
            break
        s2 = s[: max(0, int(budget))]
        budget -= len(s)
        has_cn = any("\u4e00" <= ch <= "\u9fff" for ch in s2)
        f = font(FONT_CN, 15) if has_cn else font(FONT_CODE, 15)
        text(draw, (x + 16, cy), s2 + ("▌" if budget > 0 else ""), f, col, a)
        cy += 26


def draw_scene(draw, t: float) -> None:
    scene = scene_of(t)
    local = t - SEG[scene][0]

    if scene == 0:
        text(draw, (80, 150), "一键安装 · 这次更新了什么", font(FONT_CN_B, 46), FG, fade(t, 0.2))
        text(draw, (80, 220), "v0.5.8  →  v0.5.9   |   PCL + HMCL", font(FONT_CN, 24), DIM, fade(t, 0.6))
        x = 80
        for i, (s, c) in enumerate((("HMCL 支持", GREEN), ("下载更稳", ACCENT), ("目录修复", AMBER))):
            x += pill(draw, x, 300, s, font(FONT_CN, 20), c) + 14
        text(draw, (80, 380), "mcbridge1201 · Minecraft 版本迁移与运行辅助工具箱", font(FONT_CN, 18), DIM, fade(t, 1.2))
        text(draw, (80, 640), "本片只讲这次更新；完整玩法见仓库 docs/guide.md", font(FONT_CN, 16), (100, 120, 145), fade(t, 1.6))

    elif scene == 1:
        text(draw, (80, 90), "以前：一键安装只认 PCL", font(FONT_CN_B, 36), FG, fade(t, 7.2))
        term(draw, 80, 170, 700, 330, "PowerShell", [
            ("PS> from_source_install.py --version 1.21.1 --pcl", DIM),
            ("", DIM),
            ("HMCL 用户：", AMBER),
            ("  得自己找到 .minecraft，再手动填路径", FG),
        ], local * 40, fade(t, 7.4))
        card(draw, 820, 190, 360, 280, 16, CARD2)
        text(draw, (844, 214), "HMCL 的问题", font(FONT_CN_B, 22), AMBER, fade(t, 8.2))
        wrap(draw, "普通安装的配置在 %APPDATA%\\.hmcl；便携版却把游戏目录写成相对路径的 .minecraft。",
             font(FONT_CN, 17), 320, 844, 260, FG, fade(t, 8.6))
        wrap(draw, "以前只能靠人找；找错就把游戏装到陌生目录。", font(FONT_CN, 17), 320, 844, 380, DIM, fade(t, 9.4))

    elif scene == 2:
        text(draw, (80, 80), "现在：HMCL 也能一键装", font(FONT_CN_B, 34), FG, fade(t, 18.2))
        term(draw, 60, 150, 760, 360, "PowerShell", [
            ("PS> ... --version 1.21.1 --hmcl", GREEN),
            ("HMCL 游戏目录: C:\\Users\\me\\AppData\\Roaming\\.minecraft", DIM),
            ("", DIM),
            ("PS> ... --version 1.21.1 --hmcl-dir \"D:\\HMCL\\.minecraft\"", GREEN),
            ("HMCL 游戏目录（显式）: D:\\HMCL\\.minecraft", DIM),
        ], local * 46, fade(t, 18.4))
        # mock HMCL instance card
        card(draw, 860, 170, 360, 300, 18, (238, 243, 250), (200, 210, 225))
        text(draw, (884, 190), "Hello Minecraft! Launcher", font(FONT_CN_B, 15), (40, 52, 70))
        text(draw, (884, 230), "游戏", font(FONT_CN, 15), (110, 120, 135))
        draw.rounded_rectangle([884, 258, 1196, 318], radius=10, fill=(255, 255, 255), outline=(210, 218, 230))
        text(draw, (900, 270), "实例管理", font(FONT_CN, 16), (60, 72, 90))
        text(draw, (900, 294), "1.20.6", font(FONT_CN_B, 18), (37, 99, 235))
        draw.rounded_rectangle([884, 334, 1196, 396], radius=10, fill=(70, 110, 235))
        text(draw, (884 + 110, 352), "启动游戏", font(FONT_CN_B, 18), (255, 255, 255))
        text(draw, (884 + 118, 378), "1.20.6", font(FONT_CN, 14), (225, 232, 245))
        text(draw, (860, 486), "实测：HMCL 3.17.0.363 直接列出", font(FONT_CN, 15), DIM, fade(t, 20))
        text(draw, (860, 510), "（runs/p222-hmcl）", font(FONT_CN, 14), (100, 120, 145), fade(t, 20.4))

    elif scene == 3:
        text(draw, (80, 90), "下载更稳：连接池 + 重试", font(FONT_CN_B, 34), FG, fade(t, 31.2))
        term(draw, 70, 170, 1140, 350, "from_source_install.py", [
            ("GET piston-meta.mojang.com ...", DIM),
            ("ERROR  SSL: UNEXPECTED_EOF_WHILE_READING", RED),
            ("retry 1/3 ...  retry 2/3 ...", AMBER),
            ("OK  200  (urllib3 keep-alive + gzip)", GREEN),
            ("", DIM),
            ("manifest -> version json -> client jar -> libraries -> assets", DIM),
        ], local * 40, fade(t, 31.4))
        text(draw, (80, 560), "清单/JSON 3 次重试；异常只打一行可读错误，不再刷 traceback。",
             font(FONT_CN, 19), FG, fade(t, 34))
        text(draw, (80, 596), "同一时刻 urllib/requests 仍可能被 TLS 重置，urllib3 连接池能过。",
             font(FONT_CN, 16), DIM, fade(t, 35))

    elif scene == 4:
        text(draw, (80, 90), "v0.5.8：不再装进“不存在的目录”", font(FONT_CN_B, 32), FG, fade(t, 43.2))
        card(draw, 80, 180, 540, 300, 18, (46, 26, 30), (110, 55, 60))
        text(draw, (104, 200), "以前", font(FONT_CN_B, 22), RED, fade(t, 43.6))
        wrap(draw, "PCL 配置里写了目录、但目录不存在 → 直接返回该路径，mkdir 后装进去。",
             font(FONT_CN, 17), 486, 104, 244, FG, fade(t, 44))
        text(draw, (104, 380), "结果：启动器目录下多出一个陌生文件夹", font(FONT_CN, 16), (220, 180, 180), fade(t, 44.6))
        card(draw, 660, 180, 540, 300, 18, (22, 44, 32), (60, 110, 70))
        text(draw, (684, 200), "现在（p220）", font(FONT_CN_B, 22), GREEN, fade(t, 44.8))
        wrap(draw, "目录必须已存在；不存在就回退便携 .minecraft；两者都没有就报错。",
             font(FONT_CN, 17), 486, 684, 244, FG, fade(t, 45.2))
        text(draw, (684, 380), "结果：装哪儿、为什么失败，都说清楚", font(FONT_CN, 16), (170, 220, 180), fade(t, 45.8))

    elif scene == 5:
        text(draw, (80, 80), "怎么用：三条命令", font(FONT_CN_B, 34), FG, fade(t, 54.2))
        rows = [
            ("PCL2", "from_source_install.py --version 1.21.1 --pcl", ACCENT),
            ("HMCL（普通）", "from_source_install.py --version 1.21.1 --hmcl", GREEN),
            ("HMCL（便携）", "from_source_install.py --version 1.21.1 --hmcl-dir \"D:\\HMCL\\.minecraft\"", AMBER),
        ]
        y = 170
        for name, cmd, col in rows:
            card(draw, 80, y, 1120, 130, 14, CARD)
            pill(draw, 100, y + 16, name, font(FONT_CN, 16), col)
            text(draw, (100, y + 62), cmd, font(FONT_CODE, 17), FG, fade(t, 54.6))
            y += 150
        text(draw, (80, 640), "图形面板：下载 mcbridge-pcl-panel.zip 解压双击，界面里选版本即可。",
             font(FONT_CN, 17), DIM, fade(t, 57))

    else:
        text(draw, (80, 210), "Release v0.5.9", font(FONT_CN_B, 52), ACCENT, fade(t, 66.4))
        text(draw, (80, 300), "支持 HMCL · 下载更稳 · 目录不再装错", font(FONT_CN, 26), FG, fade(t, 66.8))
        text(draw, (80, 400), "github.com/SelYio666/mcbridge1201/releases", font(FONT_CODE, 22), DIM, fade(t, 67.4))
        text(draw, (80, 470), "教程：share/update-v059/README.md", font(FONT_CN, 20), DIM, fade(t, 68))
        text(draw, (80, 520), "证据：runs/p220（目录）· runs/p222（HMCL）· runs/p221（干净 clone）",
             font(FONT_CN, 16), (100, 125, 150), fade(t, 68.6))


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [ffmpeg, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "medium", "-crf", "20",
           "-movflags", "+faststart", str(OUT)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    total = int(DUR * FPS)
    for i in range(total):
        t = i / FPS
        img = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(img)
        bg(d)
        draw_scene(d, t)
        # global fade in/out
        a = min(1.0, t / 0.5, (DUR - t) / 0.6)
        if a < 1.0:
            img = Image.blend(Image.new("RGB", (W, H), (0, 0, 0)), img, a)
        proc.stdin.write(img.tobytes())
    proc.stdin.close()
    proc.wait()
    print("wrote", OUT, f"{OUT.stat().st_size / 1e6:.1f} MB", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
