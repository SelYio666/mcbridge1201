#!/usr/bin/env python3
"""Render the current mcbridge1201 promo (converter + launcher) from code."""
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "media" / "mcbridge1201-promo-v2.mp4"

W, H, FPS = 1920, 1080, 30
DUR = 55.0
FONT_CN = "C:/Windows/Fonts/msyh.ttc"
FONT_CN_B = "C:/Windows/Fonts/msyhbd.ttc"
FONT_CODE = "C:/Windows/Fonts/consola.ttf"
FONT_CODE_B = "C:/Windows/Fonts/consolab.ttf"

BG_TOP = (8, 12, 26)
BG_BOT = (14, 24, 48)
CYAN = (79, 209, 255)
BLUE = (96, 165, 250)
GREEN = (34, 197, 94)
AMBER = (245, 158, 11)
RED = (239, 68, 68)
WHITE = (235, 242, 255)
DIM = (148, 163, 184)

_fonts = {}


def font(path, size):
    key = (path, size)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(path, size)
    return _fonts[key]


def text_w(draw, txt, f):
    return draw.textbbox((0, 0), txt, font=f)[2]


def center_text(draw, txt, f, cx, y, fill):
    w = text_w(draw, txt, f)
    draw.text((cx - w / 2, y), txt, font=f, fill=fill)


def bg_image():
    top = np.array(BG_TOP, dtype=np.float32)
    bot = np.array(BG_BOT, dtype=np.float32)
    ys = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    arr = top[None, None, :] * (1 - ys) + bot[None, None, :] * ys
    arr = np.repeat(arr, W, axis=1)
    img = Image.fromarray(arr.astype(np.uint8), "RGB").convert("RGBA")
    grid = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    g = ImageDraw.Draw(grid)
    for x in range(0, W, 80):
        g.line([(x, 0), (x, H)], fill=(70, 110, 170, 18), width=1)
    for y in range(0, H, 80):
        g.line([(0, y), (W, y)], fill=(70, 110, 170, 18), width=1)
    img.alpha_composite(grid)
    for (gx, gy, gr, col) in ((240, 170, 430, (56, 130, 246, 26)),
                              (1700, 900, 520, (34, 211, 238, 20))):
        layer = Image.new("RGBA", (gr * 2, gr * 2), (0, 0, 0, 0))
        gd = ImageDraw.Draw(layer)
        for r in range(gr, 0, -18):
            a = int(col[3] * (1 - r / gr) ** 2)
            gd.ellipse([gr - r, gr - r, gr + r, gr + r], fill=col[:3] + (a,))
        img.alpha_composite(layer, (gx - gr, gy - gr))
    return img


def panel(draw, box, radius=22, fill=(255, 255, 255, 12), outline=(79, 209, 255, 60), width=2):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def fade_in(t, dur=0.5):
    return min(1.0, t / dur) if t < dur else 1.0


def ease_out(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def load_shot(name, size):
    img = Image.open(ROOT / "runs" / name).convert("RGB")
    tw, th = size
    ar = tw / th
    w, h = img.size
    if w / h > ar:
        nw = int(h * ar)
        img = img.crop(((w - nw) // 2, 0, (w + nw) // 2, h))
    else:
        nh = int(w / ar)
        img = img.crop((0, (h - nh) // 2, w, (h + nh) // 2))
    img = img.resize(size, Image.LANCZOS)
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, tw - 1, th - 1], radius=14, fill=255)
    out = Image.new("RGBA", size, (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)
    return out


BASE = None
SHOTS = {}


def init_assets():
    global BASE, SHOTS
    BASE = bg_image()
    SHOTS["ui"] = load_shot("p112-launcher/launcher-gui-versions.png", (660, 413))
    SHOTS["combined"] = load_shot("p96-combined-smoke/combined-world.png", (480, 287))
    SHOTS["forge"] = load_shot("p112-launcher/launcher-forge-menu.png", (480, 287))
    SHOTS["appleskin"] = load_shot("p101-appleskin-hover/appleskin-hover.png", (480, 287))


def caption(draw, txt, alpha=1.0):
    f = font(FONT_CN, 38)
    w = text_w(draw, txt, f)
    box = [W / 2 - w / 2 - 32, 972, W / 2 + w / 2 + 32, 1046]
    panel(draw, box, radius=18, fill=(10, 16, 30, int(190 * alpha)),
          outline=(79, 209, 255, int(90 * alpha)))
    draw.text((W / 2 - w / 2, 986), txt, font=f, fill=WHITE + (int(255 * alpha),))


def scene_hook(t):
    img = BASE.copy()
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    a = fade_in(t)
    center_text(d, "MINECRAFT 1.20.1  →  1.21.1  ·  FABRIC", font(FONT_CN, 34), W / 2, 176,
                CYAN + (int(220 * a),))
    center_text(d, "mcbridge1201", font(FONT_CN_B, 150), W / 2, 240, WHITE + (int(255 * a),))
    center_text(d, "Minecraft 版本迁移辅助工具箱", font(FONT_CN_B, 50), W / 2, 432, (203, 225, 255, int(235 * a)))
    center_text(d, "帮 1.20.1 的模组搬家——不是来替代启动器的", font(FONT_CN, 40), W / 2, 520,
                DIM + (int(225 * a),))
    chips = [("迁移转换", CYAN), ("证据验证", GREEN), ("配合 PCL 使用", AMBER)]
    chip_f = font(FONT_CN, 40)
    for i, (text, col) in enumerate(chips):
        cw = text_w(d, text, chip_f)
        bx = W / 2 + (i - 1) * 400 - cw / 2
        k = ease_out((t - 0.5 - i * 0.15) / 0.5)
        if k <= 0:
            continue
        panel(d, [bx - 30, 650, bx + cw + 30, 740], radius=45,
              fill=col + (int(22 * k),), outline=col + (int(120 * k),))
        d.text((bx, 664), text, font=chip_f, fill=col + (int(245 * k),))
    caption(d, "辅助定位：我们只管迁移与验证", a)
    img.alpha_composite(ov)
    return img


def scene_problem(t):
    img = BASE.copy()
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    a = fade_in(t)
    center_text(d, "不处理会怎样？", font(FONT_CN_B, 76), W / 2, 96, WHITE + (int(255 * a),))
    center_text(d, "1.21.1 改了方法名、删了旧入口，老模组的调用全指错。", font(FONT_CN, 38),
                W / 2, 200, (203, 225, 255, int(235 * a)))
    cards = [("启动就崩", "NoSuchMethodError", AMBER), ("功能静默失效", "FallingTree 砍树只掉 1 根", RED)]
    for i, (title, body, col) in enumerate(cards):
        k = ease_out((t - 0.4 - i * 0.4) / 0.6)
        if k <= 0:
            continue
        x = 250 + i * 760
        panel(d, [x, 300, x + 700, 610], radius=26,
              fill=(255, 255, 255, int(10 * k)), outline=col + (int(140 * k),))
        d.text((x + 44, 340), title, font=font(FONT_CN_B, 52), fill=col + (int(255 * k),))
        d.text((x + 44, 450), body, font=font(FONT_CN, 34) if i else font(FONT_CODE, 30),
               fill=WHITE + (int(235 * k),), spacing=14)
    if t > 2.4:
        k = ease_out((t - 2.4) / 0.6)
        center_text(d, "> 直接换 jar 会崩，删 mixin 是假通过——需要真正的迁移。", font(FONT_CN, 38),
                    W / 2, 700, (220, 255, 235, int(235 * k)))
    caption(d, "升级失败不是 bug，是版本换代", a)
    img.alpha_composite(ov)
    return img


def scene_engine(t):
    img = BASE.copy()
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    a = fade_in(t)
    center_text(d, "引擎：三步迁移", font(FONT_CN_B, 76), W / 2, 92, WHITE + (int(255 * a),))
    stages = [
        ("1  转换", "CenturyBridge 分段重映射\n死调用标记为 tombstone", CYAN),
        ("2  修补", "方法 / 字段 / 构造器\n父类 / 混入 / 签名适配", BLUE),
        ("3  桥接", "javac 生成兼容小类\n替旧 API 干活", GREEN),
    ]
    card_w, card_h, gap = 560, 380, 50
    x0 = (W - (3 * card_w + 2 * gap)) / 2
    for i, (title, body, col) in enumerate(stages):
        local = t - i * 0.7
        if local < 0:
            continue
        k = ease_out(local / 0.6)
        x = x0 + i * (card_w + gap)
        y = 260 + int(40 * (1 - k))
        panel(d, [x, y, x + card_w, y + card_h], radius=26,
              fill=(255, 255, 255, int(10 * k)), outline=col + (int(120 * k),))
        d.text((x + 36, y + 30), title, font=font(FONT_CN_B, 54), fill=col + (int(255 * k),))
        d.text((x + 36, y + 140), body, font=font(FONT_CN, 30), fill=WHITE + (int(230 * k),), spacing=18)
    if t > 3.2:
        k = ease_out((t - 3.2) / 0.6)
        center_text(d, "像给老模组配了翻译官 + 一批转接头。", font(FONT_CN_B, 44), W / 2, 720,
                    (220, 255, 235, int(240 * k)))
    caption(d, "每条规则都绑定 capability / risk / evidence", a)
    img.alpha_composite(ov)
    return img


def scene_launcher(t):
    img = BASE.copy()
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    a = fade_in(t)
    center_text(d, "顺手带个小启动器（验证用）", font(FONT_CN_B, 70), W / 2, 80, WHITE + (int(255 * a),))
    if SHOTS:
        k = ease_out((t - 0.3) / 0.6)
        if k > 0:
            shot = SHOTS["ui"]
            img.paste(shot, (120, 210), Image.new("L", shot.size, int(255 * k)))
            panel(d, [114, 204, 120 + 666, 210 + 419], radius=18,
                  fill=(255, 255, 255, 0), outline=CYAN + (int(110 * k),))
    bullets = [
        ("能装能测", "转换完直接装起来验证，不用手动折腾", GREEN),
        ("标准目录", "装进 .minecraft，PCL 直接能识别", CYAN),
        ("不抢位置", "日常还是用 PCL，我们只管迁移和验证", BLUE),
    ]
    for i, (title, sub, col) in enumerate(bullets):
        k = ease_out((t - 0.8 - i * 0.4) / 0.6)
        if k <= 0:
            continue
        y = 250 + i * 150
        d.ellipse([840, y + 14, 864, y + 38], fill=col + (int(255 * k),))
        d.text((890, y), title, font=font(FONT_CN_B, 40), fill=col + (int(250 * k),))
        d.text((890, y + 56), sub, font=font(FONT_CN, 28), fill=DIM + (int(230 * k),))
    caption(d, "它只是辅助：装好、验好，然后交回 PCL", a)
    img.alpha_composite(ov)
    return img


def scene_evidence(t):
    img = BASE.copy()
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    a = fade_in(t)
    center_text(d, "不是能启动，是真能用", font(FONT_CN_B, 72), W / 2, 70, WHITE + (int(255 * a),))
    caps = ["多模组一起进世界", "Forge 1.20.1 主菜单", "AppleSkin 悬停数值"]
    keys = ["combined", "forge", "appleskin"]
    for i, key in enumerate(keys):
        local = t - i * 0.5
        if local < 0 or not SHOTS:
            continue
        k = ease_out(local / 0.6)
        x = 150 + i * 560
        y = 170 + int(30 * (1 - k))
        shot = SHOTS[key]
        img.paste(shot, (x, y), Image.new("L", shot.size, int(255 * k)))
        panel(d, [x - 6, y - 6, x + 486, y + 293], radius=18,
              fill=(255, 255, 255, 0), outline=CYAN + (int(110 * k),))
        cw = text_w(d, caps[i], font(FONT_CN, 30))
        d.text((x + 240 - cw / 2, y + 306), caps[i], font=font(FONT_CN, 30),
               fill=WHITE + (int(235 * k),))
    stats = "9 个模组实测   ·   23 项自动测试   ·   641 条证据哈希"
    if t > 2.4:
        k = ease_out((t - 2.4) / 0.6)
        panel(d, [320, 780, 1600, 876], radius=22, fill=(34, 197, 94, int(18 * k)),
              outline=GREEN + (int(120 * k),))
        center_text(d, stats, font(FONT_CN, 36), W / 2, 808, (220, 255, 235, int(240 * k)))
    caption(d, "日志、截图、哈希都能逐条复核", a)
    img.alpha_composite(ov)
    return img


def scene_close(t):
    img = BASE.copy()
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    a = fade_in(t)
    center_text(d, "适合谁？", font(FONT_CN_B, 70), W / 2, 120, WHITE + (int(255 * a),))
    chips = ["整合包作者", "服务器服主", "老模组玩家"]
    chip_f = font(FONT_CN, 42)
    for i, c in enumerate(chips):
        cw = text_w(d, c, chip_f)
        bx = W / 2 - (cw + 52) / 2 + (i - 1) * 360
        k = ease_out((t - 0.3 - i * 0.18) / 0.5)
        if k <= 0:
            continue
        panel(d, [bx, 240, bx + cw + 52, 326], radius=43, fill=(79, 209, 255, int(24 * k)),
              outline=(79, 209, 255, int(110 * k)))
        d.text((bx + 26, 250), c, font=chip_f, fill=WHITE + (int(245 * k),))
    if t > 1.3:
        k = ease_out((t - 1.3) / 0.6)
        center_text(d, "把 1.20.1 的模组搬进 1.21.1，再交回你最顺手的启动器", font(FONT_CN_B, 40), W / 2, 410,
                    (203, 225, 255, int(240 * k)))
    if t > 2.1:
        k = ease_out((t - 2.1) / 0.7)
        center_text(d, "github.com/SelYio666/mcbridge1201", font(FONT_CODE_B, 58), W / 2, 540,
                    WHITE + (int(255 * k),))
        center_text(d, "v0.3.0  ·  工具 / 规则 / 证据 / 启动器", font(FONT_CN, 36), W / 2, 646,
                    DIM + (int(230 * k),))
        center_text(d, "* NeoForge 尚未实测；不分发游戏或模组 jar", font(FONT_CN, 30), W / 2, 710,
                    (148, 163, 184, int(200 * k)))
    caption(d, "mcbridge1201 · 辅助 PCL 使用的开源迁移工具", a)
    img.alpha_composite(ov)
    return img


SCENES = [
    (0.0, 7.0, scene_hook),
    (7.0, 16.0, scene_problem),
    (16.0, 27.0, scene_engine),
    (27.0, 38.0, scene_launcher),
    (38.0, 47.0, scene_evidence),
    (47.0, 55.0, scene_close),
]
FADE = 0.5


def render_at(t):
    for idx, (s, e, fn) in enumerate(SCENES):
        if s <= t < e:
            local = t - s
            if idx > 0 and local < FADE:
                ps, pe, pfn = SCENES[idx - 1]
                a = pfn((s - 0.0001) - ps)
                b = fn(local)
                return Image.blend(a.convert("RGB"), b.convert("RGB"), local / FADE).convert("RGBA")
            return fn(local).convert("RGB")
    return BASE.convert("RGB")


def main():
    init_assets()
    import imageio_ffmpeg
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", str(OUT),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    total = int(DUR * FPS)
    try:
        for i in range(total):
            t = i / FPS
            frame = render_at(t).convert("RGB")
            if t < 0.4:
                frame = Image.blend(Image.new("RGB", (W, H), (0, 0, 0)), frame, t / 0.4)
            elif t > DUR - 0.5:
                frame = Image.blend(frame, Image.new("RGB", (W, H), (0, 0, 0)),
                                    (t - (DUR - 0.5)) / 0.5)
            proc.stdin.write(frame.tobytes())
            if i % 150 == 0:
                print(f"frame {i}/{total}", flush=True)
    finally:
        proc.stdin.close()
        rc = proc.wait()
    if rc != 0:
        raise SystemExit(f"ffmpeg failed rc={rc}")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
