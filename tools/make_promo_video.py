#!/usr/bin/env python3
"""Render the mcbridge1201 promo video from code (Pillow frames -> ffmpeg H.264)."""
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "media" / "mcbridge1201-promo.mp4"

W, H, FPS = 1920, 1080, 30
DUR = 30.0
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
        load_shot("p94-modmenu-list/modmenu-list.png", (560, 315)),
        load_shot("p101-appleskin-hover/appleskin-hover.png", (560, 315)),
        load_shot("p96-combined-smoke/combined-world.png", (560, 315)),
    ]


def caption(draw, txt, alpha=1.0):
    f = font(FONT_CN, 40)
    w = text_w(draw, txt, f)
    box = [W / 2 - w / 2 - 34, 966, W / 2 + w / 2 + 34, 1046]
    panel(draw, box, radius=18, fill=(10, 16, 30, int(190 * alpha)),
          outline=(79, 209, 255, int(90 * alpha)))
    draw.text((W / 2 - w / 2, 982), txt, font=f, fill=WHITE + (int(255 * alpha),))


def scene_title(t):
    img = BASE.copy()
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    a = fade_in(t)
    tag_f = font(FONT_CODE_B, 34)
    center_text(d, "FABRIC  1.20.1  ->  1.21.1", tag_f, W / 2, 250, CYAN + (int(220 * a),))
    title_f = font(FONT_CN_B, 168)
    y = 340 - int(26 * (1 - ease_out(t / 0.9)))
    center_text(d, "mcbridge1201", title_f, W / 2, y, WHITE + (int(255 * a),))
    sub_f = font(FONT_CN_B, 56)
    center_text(d, "让老模组在 1.21.1 里活过来", sub_f, W / 2, 560, (203, 225, 255, int(235 * a)))
    line_f = font(FONT_CN, 40)
    center_text(d, "保体积重映射 · 规则修补 · javac 桥", line_f, W / 2, 660, DIM + (int(220 * a),))
    grow = ease_out(t / 1.1)
    lw = int(560 * grow)
    d.rounded_rectangle([W / 2 - lw / 2, 742, W / 2 + lw / 2, 748], radius=3, fill=CYAN + (int(220 * a),))
    caption(d, "代码驱动的迁移工具链", a)
    img.alpha_composite(ov)
    return img


def scene_problem(t):
    img = BASE.copy()
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    a = fade_in(t)
    head_f = font(FONT_CN_B, 72)
    center_text(d, "为什么升不上去？", head_f, W / 2, 110, WHITE + (int(255 * a),))
    box = [200, 230, 1720, 600]
    panel(d, box, radius=24, fill=(6, 10, 22, 210), outline=(79, 209, 255, 70))
    lines = [
        ("CenturyBridge tombstone: class_1890.method_8222 no longer exists", AMBER),
        ("NoSuchMethodError: 'class_634.method_2883(...)'", AMBER),
        ("NoClassDefFoundError: top/mcbridge1201/bridge/CodecDispatch", AMBER),
        ("-> 换 jar = 崩；删 mixin = 假通过；旧桥 = 遮蔽新桥", GREEN),
    ]
    code_f = font(FONT_CODE, 32)
    note_f = font(FONT_CN, 34)
    line_fonts = [code_f, code_f, code_f, note_f]
    line_h = 74
    for i, (txt, col) in enumerate(lines):
        if t > 0.35 + i * 0.5:
            d.text((250, 264 + i * line_h), txt, font=line_fonts[i], fill=col + (int(240 * a),))
    chips = ["签名变了", "mixin 目标没了", "桥类版本冲突"]
    chip_f = font(FONT_CN, 40)
    for i, c in enumerate(chips):
        cw = text_w(d, c, chip_f)
        bx = 260 + i * 470
        panel(d, [bx, 700, bx + cw + 56, 786], radius=40, fill=(79, 209, 255, 26),
              outline=(79, 209, 255, 80))
        d.text((bx + 28, 714), c, font=chip_f, fill=WHITE + (int(245 * a),))
    caption(d, "直接换 jar：崩。删 mixin：假通过。", a)
    img.alpha_composite(ov)
    return img


def scene_pipeline(t):
    img = BASE.copy()
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    a = fade_in(t)
    head_f = font(FONT_CN_B, 72)
    center_text(d, "三步迁移：每一步都有证据", head_f, W / 2, 96, WHITE + (int(255 * a),))
    stages = [
        ("1  转换", "CenturyBridge 7 段重映射\n死调用标记为 tombstone", CYAN),
        ("2  修补", "field / method / body\nsuperclass / ctor / rename / mixin", BLUE),
        ("3  桥接", "javac 生成桥类\n同一 bridge-dir 对齐", GREEN),
    ]
    card_w, card_h = 560, 380
    gap = 50
    total = 3 * card_w + 2 * gap
    x0 = (W - total) / 2
    body_f = font(FONT_CN, 30)
    for i, (title, body, col) in enumerate(stages):
        local = t - i * 0.65
        if local < 0:
            continue
        k = ease_out(local / 0.6)
        x = x0 + i * (card_w + gap)
        y = 300 + int(40 * (1 - k))
        panel(d, [x, y, x + card_w, y + card_h], radius=26,
              fill=(255, 255, 255, int(12 * k)), outline=col + (int(120 * k),))
        d.text((x + 36, y + 32), title, font=font(FONT_CN_B, 54), fill=col + (int(255 * k),))
        d.text((x + 36, y + 140), body, font=body_f, fill=WHITE + (int(230 * k),), spacing=16)
        if i < 2:
            ax = x + card_w + 8
            ay = y + card_h // 2
            grow = ease_out((local - 0.7) / 0.5)
            if grow > 0:
                d.line([(ax, ay), (ax + gap * grow - 16, ay)], fill=CYAN + (int(200 * grow),), width=5)
                d.polygon([(ax + gap * grow - 16, ay - 10), (ax + gap * grow - 16, ay + 10),
                           (ax + gap * grow - 2, ay)], fill=CYAN + (int(200 * grow),))
    caption(d, "capability / risk / evidence 绑定每一条规则", a)
    img.alpha_composite(ov)
    return img


def scene_evidence(t):
    img = BASE.copy()
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    a = fade_in(t)
    head_f = font(FONT_CN_B, 72)
    center_text(d, "不是能启动，是能用", head_f, W / 2, 78, WHITE + (int(255 * a),))
    caps = ["Mod Menu 列表 / 搜索 / 配置屏", "AppleSkin 真实悬停 tooltip", "多模组联测进世界"]
    cap_f = font(FONT_CN, 32)
    for i, shot in enumerate(SHOTS if SHOTS else []):
        local = t - i * 0.55
        if local < 0:
            continue
        k = ease_out(local / 0.6)
        x = 120 + i * 600
        y = 190 + int(34 * (1 - k))
        panel(d, [x - 6, y - 6, x + 566, y + 327], radius=20,
              fill=(255, 255, 255, 0), outline=CYAN + (int(110 * k),))
        base = Image.new("RGBA", (566, 327), (12, 18, 34, 255))
        base.alpha_composite(shot, (0, 0))
        alpha_mask = Image.new("L", base.size, int(255 * k))
        img.paste(base, (x, y), alpha_mask)
        cw = text_w(d, caps[i], cap_f)
        d.text((x + 280 - cw / 2, y + 340), caps[i], font=cap_f, fill=WHITE + (int(235 * k),))
    stats_f = font(FONT_CODE_B, 30)
    stats = "23 tests  |  627 evidence hashes  |  bridge consistency: 0  |  combined smoke: in-world"
    if t > 2.2:
        k = ease_out((t - 2.2) / 0.6)
        box = [150, 780, 1770, 876]
        panel(d, box, radius=22, fill=(34, 197, 94, int(18 * k)), outline=GREEN + (int(120 * k),))
        center_text(d, stats, stats_f, W / 2, 808, (220, 255, 235, int(240 * k)))
    caption(d, "日志、截图、哈希全部入库", a)
    img.alpha_composite(ov)
    return img


def scene_close(t):
    img = BASE.copy()
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    a = fade_in(t)
    head_f = font(FONT_CN_B, 84)
    center_text(d, "已验证的模组", head_f, W / 2, 130, WHITE + (int(255 * a),))
    rows = [
        ("Lithium  ·  IronChests  ·  TrashSlot", 0.25, CYAN),
        ("AppleSkin  ·  Mod Menu  ·  Clumps", 0.50, BLUE),
        ("FallingTree  ·  ShulkerBoxTooltip  ·  FerriteCore*", 0.75, GREEN),
    ]
    row_f = font(FONT_CN_B, 48)
    for idx, (txt, delay, col) in enumerate(rows):
        if t > delay:
            k = ease_out((t - delay) / 0.6)
            center_text(d, txt, row_f, W / 2, 268 + idx * 96, col + (int(240 * k),))
    if t > 1.6:
        k = ease_out((t - 1.6) / 0.7)
        link_f = font(FONT_CODE_B, 62)
        center_text(d, "github.com/SelYio666/mcbridge1201", link_f, W / 2, 630, WHITE + (int(255 * k),))
        ver_f = font(FONT_CN, 40)
        center_text(d, "v0.2.5  ·  工具 / 规则 / 证据开源", ver_f, W / 2, 730, DIM + (int(230 * k),))
        note_f = font(FONT_CN, 32)
        center_text(d, "* FerriteCore 仅启动 + 性能降级；不分发游戏/模组 jar", note_f, W / 2, 800,
                    (148, 163, 184, int(200 * k)))
    caption(d, "从崩溃日志到可复现的兼容层", a)
    img.alpha_composite(ov)
    return img


SCENES = [
    (0.0, 4.8, scene_title),
    (4.8, 11.0, scene_problem),
    (11.0, 17.6, scene_pipeline),
    (17.6, 24.6, scene_evidence),
    (24.6, 30.0, scene_close),
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
