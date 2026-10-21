#!/usr/bin/env python3
"""Render the mcbridge1201 explainer video from code (Pillow frames -> ffmpeg H.264)."""
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "media" / "mcbridge1201-promo.mp4"

W, H, FPS = 1920, 1080, 30
DUR = 45.0
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
    gdraw = ImageDraw.Draw(grid)
    for x in range(0, W, 80):
        gdraw.line([(x, 0), (x, H)], fill=(70, 110, 170, 18), width=1)
    for y in range(0, H, 80):
        gdraw.line([(0, y), (W, y)], fill=(70, 110, 170, 18), width=1)
    img.alpha_composite(grid)
    for (gx, gy, gr, col) in ((260, 180, 420, (56, 130, 246, 26)),
                              (1680, 880, 520, (34, 211, 238, 20))):
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
    path = ROOT / "runs" / name
    img = Image.open(path).convert("RGB")
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
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, tw - 1, th - 1], radius=16, fill=255)
    out = Image.new("RGBA", size, (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)
    return out


BASE = None
SHOTS = None


def init_assets():
    global BASE, SHOTS
    BASE = bg_image()
    SHOTS = [
        load_shot("p94-modmenu-list/modmenu-list.png", (520, 293)),
        load_shot("p101-appleskin-hover/appleskin-hover.png", (520, 293)),
        load_shot("p96-combined-smoke/combined-world.png", (520, 293)),
    ]


def caption(draw, txt, alpha=1.0):
    f = font(FONT_CN, 40)
    w = text_w(draw, txt, f)
    box = [W / 2 - w / 2 - 34, 966, W / 2 + w / 2 + 34, 1046]
    panel(draw, box, radius=18, fill=(10, 16, 30, int(190 * alpha)),
          outline=(79, 209, 255, int(90 * alpha)))
    draw.text((W / 2 - w / 2, 982), txt, font=f, fill=WHITE + (int(255 * alpha),))


def scene_hook(t):
    img = BASE.copy()
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    a = fade_in(t)
    tag_f = font(FONT_CN, 36)
    center_text(d, "MINECRAFT 1.20.1  →  1.21.1  ·  FABRIC", tag_f, W / 2, 196, CYAN + (int(220 * a),))
    head_f = font(FONT_CN_B, 100)
    center_text(d, "让老模组在 1.21.1 上跑起来", head_f, W / 2, 268, WHITE + (int(255 * a),))
    sub_f = font(FONT_CN_B, 54)
    center_text(d, "mcbridge1201", sub_f, W / 2, 452, (203, 225, 255, int(235 * a)))
    plain_f = font(FONT_CN, 44)
    center_text(d, "自动转换  +  打补丁  +  兼容小类", plain_f, W / 2, 548, DIM + (int(225 * a),))
    # flow diagram: old jar -> tool -> new jar
    y = 700
    box_f = font(FONT_CN, 36)
    items = [("1.20.1 模组 jar", AMBER), ("自动改写", CYAN), ("1.21.1 可运行", GREEN)]
    xs = [330, 960, 1590]
    for i, ((label, col), x) in enumerate(zip(items, xs)):
        k = ease_out((t - 0.4 - i * 0.35) / 0.5)
        if k <= 0:
            continue
        bw = 330
        panel(d, [x - bw / 2, y, x + bw / 2, y + 110], radius=20,
              fill=(255, 255, 255, int(10 * k)), outline=col + (int(130 * k),))
        cw = text_w(d, label, box_f)
        d.text((x - cw / 2, y + 32), label, font=box_f, fill=col + (int(240 * k),))
        if i < 2:
            ax = x + bw / 2 + 20
            grow = ease_out((t - 0.9 - i * 0.35) / 0.5)
            if grow > 0:
                d.line([(ax, y + 55), (ax + 300 * grow - 40, y + 55)],
                       fill=CYAN + (int(200 * grow),), width=5)
                d.polygon([(ax + 300 * grow - 44, y + 45), (ax + 300 * grow - 44, y + 65),
                           (ax + 300 * grow - 26, y + 55)], fill=CYAN + (int(200 * grow),))
    caption(d, "不用等作者更新，也不用改源码", a)
    img.alpha_composite(ov)
    return img


def scene_problem(t):
    img = BASE.copy()
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    a = fade_in(t)
    head_f = font(FONT_CN_B, 76)
    center_text(d, "不处理会怎样？", head_f, W / 2, 100, WHITE + (int(255 * a),))
    plain_f = font(FONT_CN, 40)
    center_text(d, "1.21.1 改了大量方法名，还删掉了旧入口——老模组里的调用全指错。",
                plain_f, W / 2, 208, (203, 225, 255, int(235 * a)))
    cards = [
        ("启动就崩", "NoSuchMethodError:\nclass_634.method_2883", AMBER),
        ("功能静默失效", "FallingTree 砍树\n只掉 1 根", (239, 68, 68)),
    ]
    card_f = font(FONT_CN_B, 48)
    line_f = font(FONT_CODE, 30)
    cn_f = font(FONT_CN, 36)
    body_fonts = [line_f, cn_f]
    for i, (title, body, col) in enumerate(cards):
        k = ease_out((t - 0.4 - i * 0.45) / 0.6)
        if k <= 0:
            continue
        x = 230 + i * 760
        panel(d, [x, 300, x + 700, 610], radius=26,
              fill=(255, 255, 255, int(10 * k)), outline=col + (int(140 * k),))
        d.text((x + 44, 336), title, font=card_f, fill=col + (int(255 * k),))
        d.text((x + 44, 430), body, font=body_fonts[i], fill=WHITE + (int(235 * k),), spacing=14)
    note_f = font(FONT_CN, 38)
    if t > 2.6:
        k = ease_out((t - 2.6) / 0.6)
        center_text(d, "> 这不是 bug，是版本换代——需要有人把旧调用翻译成新写法。",
                    note_f, W / 2, 690, (220, 255, 235, int(235 * k)))
    caption(d, "模组写死了 1.20.1 的调用，升级后找不到", a)
    img.alpha_composite(ov)
    return img


def scene_what(t):
    img = BASE.copy()
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    a = fade_in(t)
    head_f = font(FONT_CN_B, 76)
    center_text(d, "这个工具做三件事", head_f, W / 2, 92, WHITE + (int(255 * a),))
    stages = [
        ("1  翻译", "把旧方法名、字段名\n换成 1.21.1 的；\n翻不了的先标记出来", CYAN),
        ("2  打补丁", "按规则改代码：\n方法、字段、构造器、\n父类、混入、渲染", BLUE),
        ("3  补零件", "生成兼容小类，\n替旧 API 干活：\n网络、NBT、食物、预览…", GREEN),
    ]
    card_w, card_h = 560, 400
    gap = 50
    x0 = (W - (3 * card_w + 2 * gap)) / 2
    body_f = font(FONT_CN, 30)
    for i, (title, body, col) in enumerate(stages):
        local = t - i * 0.8
        if local < 0:
            continue
        k = ease_out(local / 0.6)
        x = x0 + i * (card_w + gap)
        y = 250 + int(40 * (1 - k))
        panel(d, [x, y, x + card_w, y + card_h], radius=26,
              fill=(255, 255, 255, int(10 * k)), outline=col + (int(120 * k),))
        d.text((x + 36, y + 30), title, font=font(FONT_CN_B, 54), fill=col + (int(255 * k),))
        d.text((x + 36, y + 130), body, font=body_f, fill=WHITE + (int(230 * k),), spacing=18)
    analogy_f = font(FONT_CN_B, 46)
    if t > 3.4:
        k = ease_out((t - 3.4) / 0.6)
        center_text(d, "像给老模组配了一个翻译官 + 一批转接头。", analogy_f, W / 2, 720,
                    (220, 255, 235, int(240 * k)))
    caption(d, "改完仍是原模组，只是换了个能跑的写法", a)
    img.alpha_composite(ov)
    return img


def scene_proof(t):
    img = BASE.copy()
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    a = fade_in(t)
    head_f = font(FONT_CN_B, 76)
    center_text(d, "不是能启动，是真能用", head_f, W / 2, 78, WHITE + (int(255 * a),))
    caps = ["Mod Menu：列表能滚、能搜、能开配置", "AppleSkin：悬停看到食物数值", "多模组一起进世界"]
    cap_f = font(FONT_CN, 32)
    for i, shot in enumerate(SHOTS if SHOTS else []):
        local = t - i * 0.55
        if local < 0:
            continue
        k = ease_out(local / 0.6)
        x = 130 + i * 560
        y = 180 + int(34 * (1 - k))
        panel(d, [x - 6, y - 6, x + 526, y + 299], radius=20,
              fill=(255, 255, 255, 0), outline=CYAN + (int(110 * k),))
        base = Image.new("RGBA", (520, 293), (12, 18, 34, 255))
        base.alpha_composite(shot, (0, 0))
        alpha_mask = Image.new("L", base.size, int(255 * k))
        img.paste(base, (x, y), alpha_mask)
        cw = text_w(d, caps[i], cap_f)
        d.text((x + 260 - cw / 2, y + 312), caps[i], font=cap_f, fill=WHITE + (int(235 * k),))
    stats_f = font(FONT_CN, 36)
    stats = "9 个模组实测   ·   23 项自动测试   ·   630 条证据哈希"
    if t > 2.4:
        k = ease_out((t - 2.4) / 0.6)
        box = [330, 760, 1590, 862]
        panel(d, box, radius=22, fill=(34, 197, 94, int(18 * k)), outline=GREEN + (int(120 * k),))
        center_text(d, stats, stats_f, W / 2, 792, (220, 255, 235, int(240 * k)))
    if t > 3.2:
        k = ease_out((t - 3.2) / 0.6)
        note_f = font(FONT_CN, 34)
        center_text(d, "每个结论都有日志 / 截图 / 哈希，可以逐条复核。", note_f, W / 2, 888,
                    (148, 163, 184, int(220 * k)))
    caption(d, "证据在仓库里，不是嘴上说", a)
    img.alpha_composite(ov)
    return img


def scene_close(t):
    img = BASE.copy()
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    a = fade_in(t)
    head_f = font(FONT_CN_B, 72)
    center_text(d, "适合谁？", head_f, W / 2, 120, WHITE + (int(255 * a),))
    chips = ["整合包作者", "服务器服主", "老模组玩家"]
    chip_f = font(FONT_CN, 44)
    for i, c in enumerate(chips):
        cw = text_w(d, c, chip_f)
        bx = W / 2 - (cw + 56) / 2 + (i - 1) * 360
        k = ease_out((t - 0.3 - i * 0.2) / 0.5)
        if k <= 0:
            continue
        panel(d, [bx, 250, bx + cw + 56, 340], radius=45, fill=(79, 209, 255, int(24 * k)),
              outline=(79, 209, 255, int(110 * k)))
        d.text((bx + 28, 262), c, font=chip_f, fill=WHITE + (int(245 * k),))
    if t > 1.4:
        k = ease_out((t - 1.4) / 0.6)
        line_f = font(FONT_CN_B, 50)
        center_text(d, "把 1.20.1 的模组，搬进 1.21.1", line_f, W / 2, 430, (203, 225, 255, int(240 * k)))
    if t > 2.2:
        k = ease_out((t - 2.2) / 0.7)
        link_f = font(FONT_CODE_B, 60)
        center_text(d, "github.com/SelYio666/mcbridge1201", link_f, W / 2, 560, WHITE + (int(255 * k),))
        ver_f = font(FONT_CN, 38)
        center_text(d, "v0.2.5  ·  只提供工具 / 规则 / 证据", ver_f, W / 2, 668, DIM + (int(230 * k),))
        note_f = font(FONT_CN, 32)
        center_text(d, "* 不分发游戏或模组 jar；个别功能仍需手工移植", note_f, W / 2, 728,
                    (148, 163, 184, int(200 * k)))
    caption(d, "mcbridge1201 · 开源兼容层", a)
    img.alpha_composite(ov)
    return img


SCENES = [
    (0.0, 6.0, scene_hook),
    (6.0, 15.5, scene_problem),
    (15.5, 27.5, scene_what),
    (27.5, 38.5, scene_proof),
    (38.5, 45.0, scene_close),
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
            if i % 60 == 0:
                print(f"frame {i}/{total}", flush=True)
    finally:
        proc.stdin.close()
        rc = proc.wait()
    if rc != 0:
        raise SystemExit(f"ffmpeg failed rc={rc}")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
