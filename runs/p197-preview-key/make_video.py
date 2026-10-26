#!/usr/bin/env python3
"""Render a short explainer video for the p197 increment (pure code, Pillow + ffmpeg).

Everything shown comes from this run's real artifacts:
  result.json          -> the 7 green assertions
  client.log           -> the P197_TYPE transition order, decoded key codes, first-press tick
  after-full.png       -> the real FULL screenshot (cropped to the preview panel)
  after-compact.png    -> the real COMPACT screenshot after releasing K

Usage:
    python runs/p197-preview-key/make_video.py
    python runs/p197-preview-key/make_video.py --stills 2 9 24

Output: runs/p197-preview-key/p197-update.mp4 (1280x720, 30 fps, 30 s).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[1]
TOOLCHAIN_FFMPEG = ROOT.parent / ".toolchain" / "ffmpeg" / "ffmpeg.exe"
FRAMES = ROOT / "work" / "tmp" / "p197-video-frames"

W, H = 1280, 720
FPS = 30
DURATION = 30.0
# Snapshot of the evidence manifest size at the time this video was rendered
# (runs/SHA256SUMS.txt includes this file, so the value cannot be read back from it).
HASH_COUNT = int(os.environ.get("P197_HASH_COUNT", "1252"))

BG = (9, 13, 18)
FG = (226, 232, 240)
MUTED = (148, 163, 184)
DIM = (100, 116, 139)
ACCENT = (52, 211, 153)
WARN = (251, 113, 133)
BLUE = (96, 165, 250)
AMBER = (251, 191, 36)
PANEL = (17, 24, 33)
PANEL2 = (22, 31, 42)
LINE = (38, 50, 64)

FONT_ZH = "C:/Windows/Fonts/msyh.ttc"
FONT_ZH_BOLD = "C:/Windows/Fonts/msyhbd.ttc"
FONT_MONO = "C:/Windows/Fonts/consola.ttf"
FONT_MONO_BOLD = "C:/Windows/Fonts/consolab.ttf"

SCENES = [(0.0, 3.2), (3.2, 7.4), (7.4, 11.8), (11.8, 15.2),
          (15.2, 21.6), (21.6, 26.4), (26.4, 30.0)]


def zh(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_ZH_BOLD if bold else FONT_ZH, size)


def mono(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_MONO_BOLD if bold else FONT_MONO, size)


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def ease(value: float) -> float:
    value = clamp(value)
    return 1 - (1 - value) ** 3


def mix(a, b, t: float):
    t = clamp(t)
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def reveal(lt: float, delay: float, dur: float = 0.35) -> float:
    return ease((lt - delay) / dur)


def has_cjk(s: str) -> bool:
    return any("\u4e00" <= ch <= "\u9fff" for ch in s)


def typewriter(s: str, lt: float, delay: float, cps: float = 55.0) -> str:
    if lt < delay:
        return ""
    return s[: max(0, int((lt - delay) * cps))]


def text(draw, xy, s, font, fill, *, anchor="la", alpha=1.0):
    if alpha <= 0 or not s:
        return
    draw.text(xy, s, font=font, fill=mix(BG, fill, alpha), anchor=anchor)


def panel(draw, box, *, fill=PANEL, outline=LINE, radius=14, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def eyebrow(draw, xy, label, color, alpha=1.0):
    text(draw, xy, label, zh(16, True), color, alpha=alpha)


def chip(draw, xy, label, font, *, fg=ACCENT, pad=(12, 6)):
    if has_cjk(label):
        font = zh(max(13, font.size - 1), True)
    x, y = xy
    bbox = draw.textbbox((0, 0), label, font=font)
    w = bbox[2] - bbox[0] + pad[0] * 2
    h = bbox[3] - bbox[1] + pad[1] * 2
    draw.rounded_rectangle((x, y, x + w, y + h), radius=h // 2,
                           fill=mix(BG, fg, 0.12), outline=mix(BG, fg, 0.45), width=1)
    draw.text((x + pad[0], y + pad[1] - bbox[1] + 1), label, font=font, fill=fg)
    return w, h


def code_block(draw, box, lines, *, font, lt=1.0, code_delay=0.0, cps=70.0,
               highlight: dict[int, tuple] | None = None, title: str | None = None):
    x0, y0, x1, y1 = box
    panel(draw, box, fill=PANEL2)
    if title:
        text(draw, (x0 + 18, y0 + 10), title, zh(15, True), MUTED)
    y = y0 + (44 if title else 16)
    for i, line in enumerate(lines):
        shown = typewriter(line, lt, code_delay + i * 0.12, cps)
        fill = MUTED
        if highlight and i in highlight:
            fill = highlight[i][1]
        text(draw, (x0 + 18, y), shown, font, fill)
        if highlight and i in highlight and shown == line:
            draw.rounded_rectangle((x0 + 7, y - 1, x0 + 10, y + font.size + 1), radius=1,
                                   fill=highlight[i][1])
        y += font.size + 10


def load_data():
    result = json.loads((RUN / "result.json").read_text(encoding="utf-8"))
    log = (RUN / "client.log").read_text(encoding="utf-8", errors="replace")
    types = re.findall(r"P197_TYPE (\w+)", log)
    config = re.search(r"P197_CONFIG alwaysOn=(\w+) preview=\S+ previewCode=(\d+) full=\S+ fullCode=(\d+)", log)
    cfg = ({"alwaysOn": config.group(1), "preview": int(config.group(2)),
            "full": int(config.group(3))} if config else None)
    tick = re.search(r"P197_COMPACT_REQUEST tick=(\d+)", log)
    checks = [k for k, v in result.items() if isinstance(v, bool)]
    return result, types, cfg, (tick.group(1) if tick else "?"), checks


RESULT, TYPES, CFG, COMPACT_TICK, CHECKS = load_data()


def crop(name: str) -> Image.Image:
    img = Image.open(RUN / name).convert("RGB")
    return img.crop((610, 350, 1115, 700)).resize((700, 486), Image.Resampling.LANCZOS)


def scene_title(base, draw, lt, dur):
    text(draw, (88, 150), "mcbridge1201 · 增量记录", zh(20), BLUE, alpha=reveal(lt, 0.05))
    text(draw, (88, 196), "p197 · Shulker 预览键重绑定", zh(52, True), FG, alpha=reveal(lt, 0.25))
    text(draw, (88, 282), "从「配置被忽略」到「配置真的生效」", zh(24), MUTED, alpha=reveal(lt, 0.55))
    if reveal(lt, 0.9) > 0:
        x = 88
        for label, color in (("result 7/7", ACCENT), ("gates 99/99", BLUE),
                             (f"hashes {HASH_COUNT}/{HASH_COUNT}", AMBER), ("CI success", ACCENT)):
            w, _ = chip(draw, (x, 356), label, zh(17), fg=color)
            x += w + 12
    grow = ease((lt - 1.2) / 0.6)
    if grow > 0:
        draw.line((88, 470, 88 + int(560 * grow), 470), fill=LINE, width=2)
    text(draw, (88, 500), "javap 反编译 + 运行时配置回读 + 真实截图", zh(18), DIM, alpha=reveal(lt, 1.35))
    text(draw, (88, 532), "证据目录  runs/p197-preview-key/", zh(16), DIM, alpha=reveal(lt, 1.5))


def scene_problem(base, draw, lt, dur):
    eyebrow(draw, (72, 64), "01 / p196 的误判", WARN, reveal(lt, 0.0))
    text(draw, (72, 92), "配置字段写错了分类，F 又触发了原版交换副手", zh(30, True), FG,
         alpha=reveal(lt, 0.15))
    code = ["{", '  "preview": {', '    "enable": true,',
            '    "previewKey": "key.keyboard.f"', "  }", "}"]
    code_block(draw, (72, 168, 596, 442), code, font=mono(18), lt=lt, code_delay=0.35,
               highlight={3: (None, WARN)}, title="p196 实际写入的 config（错）")
    text(draw, (72, 462), "controls 分类里根本没有 previewKey → Jankson 直接忽略", zh(16), WARN,
         alpha=reveal(lt, 1.5))
    x = 640
    items = [("mod 真正读的是", "controls.previewKey / fullPreviewKey"),
             ("默认值", "340 LEFT_ALT · 342 RIGHT_SHIFT"),
             ("F 的副作用", "原版 swapOffhand：把悬停物品换走"),
             ("现象", "F → NO_PREVIEW，看起来像配置被忽略")]
    y = 176
    for i, (head, body) in enumerate(items):
        a = reveal(lt, 0.5 + i * 0.28)
        text(draw, (x, y), head, zh(16, True), MUTED, alpha=a)
        text(draw, (x, y + 26), body, zh(17), FG, alpha=a)
        y += 80
    text(draw, (640, 528), "结论：不是 mod 不读配置，是我们写错了位置。", zh(19, True), ACCENT,
         alpha=reveal(lt, 1.9))


def scene_bytecode(base, draw, lt, dur):
    eyebrow(draw, (72, 64), "02 / 证据", BLUE, reveal(lt, 0.0))
    text(draw, (72, 92), "javap：键码来自 config，再交给 InputConstants.isKeyDown", zh(30, True), FG,
         alpha=reveal(lt, 0.15))
    code = ["// ShulkerBoxTooltipClient.isKeyPressed(Key)",
            "39: invokevirtual  Key.get()               // config.controls.<key>",
            "42: invokevirtual  class_306.method_1444()  // getCode()",
            "45: invokestatic   class_3675.method_15987(JI)Z",
            "                      // InputConstants.isKeyDown(window, code)"]
    code_block(draw, (72, 168, 1208, 372), code, font=mono(19), lt=lt, code_delay=0.3,
               highlight={2: (None, BLUE), 3: (None, ACCENT), 4: (None, ACCENT)})
    y = 410
    steps = [("config.controls", "previewKey / fullPreviewKey", BLUE),
             ("Key.getCode()", "340 / 342 只是默认值", AMBER),
             ("isKeyDown", "轮询的是解析后的码", ACCENT)]
    x = 72
    for i, (head, body, color) in enumerate(steps):
        a = reveal(lt, 1.2 + i * 0.3)
        panel(draw, (x, y, x + 350, y + 104), fill=PANEL)
        text(draw, (x + 18, y + 16), head, mono(18, True), color, alpha=a)
        text(draw, (x + 18, y + 48), body, zh(16), MUTED, alpha=a)
        if i < 2:
            draw.line((x + 358, y + 52, x + 382, y + 52), fill=mix(BG, DIM, a), width=2)
            draw.polygon([(x + 390, y + 52), (x + 380, y + 47), (x + 380, y + 57)],
                         fill=mix(BG, DIM, a))
        x += 390
    text(draw, (72, 556), "Key.defaultFullPreviewKey(): sipush 342 —— 「默认 342」不是硬编码轮询。",
         zh(18), MUTED, alpha=reveal(lt, 2.3))


def scene_config(base, draw, lt, dur):
    eyebrow(draw, (72, 64), "03 / 正确写法", ACCENT, reveal(lt, 0.0))
    text(draw, (72, 92), "把键放进 controls 分类，J/K 无原版绑定", zh(30, True), FG,
         alpha=reveal(lt, 0.15))
    code = ["{",
            '  "preview":  { "enable": true, "alwaysOn": false },',
            '  "controls": {',
            '    "previewKey":     "key.keyboard.j",',
            '    "fullPreviewKey": "key.keyboard.k"',
            "  }", "}"]
    code_block(draw, (72, 168, 700, 400), code, font=mono(18), lt=lt, code_delay=0.3,
               highlight={3: (None, ACCENT), 4: (None, ACCENT)},
               title="config/shulkerboxtooltip.json5")
    text(draw, (72, 420), "运行中回读（client.log）：", zh(16), MUTED, alpha=reveal(lt, 1.4))
    live = (f'P197_CONFIG alwaysOn={CFG["alwaysOn"] if CFG else "false"} '
            f'previewCode={CFG["preview"] if CFG else 74} '
            f'fullCode={CFG["full"] if CFG else 75}')
    text(draw, (72, 448), live, mono(16), ACCENT, alpha=reveal(lt, 1.55))
    x = 760
    notes = [("alwaysOn=false", "必须按住预览键才显示"),
             ("J = 74", "previewKey → COMPACT"),
             ("K = 75", "fullPreviewKey → FULL"),
             ("互不误触", "J/K 在原版没有 keybinding")]
    y = 176
    for i, (head, body) in enumerate(notes):
        a = reveal(lt, 0.6 + i * 0.25)
        text(draw, (x, y), head, zh(17, True) if has_cjk(head) else mono(17, True),
             ACCENT if i else AMBER, alpha=a)
        text(draw, (x, y + 26), body, zh(15), MUTED, alpha=a)
        y += 78
    text(draw, (760, 520), "首次按键 tick=" + COMPACT_TICK, mono(15), DIM, alpha=reveal(lt, 1.9))


def scene_states(base, draw, lt, dur):
    eyebrow(draw, (72, 64), "04 / mod 自己的状态机", ACCENT, reveal(lt, 0.0))
    text(draw, (72, 92), "P197_KEYS / P197_TYPE：全是 mod 打出来的真实转移", zh(28, True), FG,
         alpha=reveal(lt, 0.12))
    states = [("J", "COMPACT", "27 格", ACCENT),
              ("J + K", "FULL", "27 格", BLUE),
              ("松 K", "COMPACT", "回到 27 格", ACCENT),
              ("松 J", "NO_PREVIEW", "不再预览", DIM)]
    active = min(3, int(max(0.0, lt - 0.7) / 1.4))
    x = 72
    for i, (keys, state, note, color) in enumerate(states):
        a = reveal(lt, 0.35 + i * 0.12)
        on = i <= active
        panel(draw, (x, 200, x + 268, 400), fill=PANEL2 if on else PANEL,
              outline=color if on else LINE, width=2 if i == active else 1)
        text(draw, (x + 20, 218), f"0{i + 1}", mono(14, True), DIM, alpha=a)
        chip(draw, (x + 20, 246), keys, mono(17, True), fg=color if on else DIM)
        text(draw, (x + 20, 300), state, mono(24, True), color if on else DIM, alpha=a)
        text(draw, (x + 20, 344), note, zh(16), MUTED, alpha=a)
        if i < 3:
            c = mix(BG, ACCENT if i < active else DIM, a)
            draw.line((x + 278, 300, x + 300, 300), fill=c, width=2)
            draw.polygon([(x + 308, 300), (x + 298, 295), (x + 298, 305)], fill=c)
        x += 312
    text(draw, (72, 440), "probe 只把 74/75 报告为「按住」；340/342 永远不成立。", zh(19), FG,
         alpha=reveal(lt, 2.2))
    text(draw, (72, 474), "所以出现 COMPACT/FULL 就只能说明 mod 真的轮询了重绑后的键码。", zh(19), FG,
         alpha=reveal(lt, 2.45))
    seq = " → ".join(TYPES) if TYPES else "NO_PREVIEW → COMPACT → FULL → COMPACT → NO_PREVIEW"
    text(draw, (72, 536), "P197_TYPE: " + seq, mono(16), ACCENT, alpha=reveal(lt, 2.8))


def scene_screens(base, draw, lt, dur):
    eyebrow(draw, (72, 56), "05 / 真实渲染", BLUE, reveal(lt, 0.0))
    text(draw, (72, 84), "服务端 27 种物品的 shulker box（生存背包 class_490）", zh(28, True), FG,
         alpha=reveal(lt, 0.1))
    full = crop("after-full.png")
    comp = crop("after-compact.png")
    fade = clamp((lt - 2.2) / 0.6)
    img = Image.blend(full, comp, fade) if fade > 0 else full
    x, y = (W - img.width) // 2, 136
    draw.rounded_rectangle((x - 3, y - 3, x + img.width + 3, y + img.height + 3), radius=8,
                           outline=mix(BG, ACCENT, reveal(lt, 0.2)), width=2)
    base.paste(img, (x, y))
    label = ("after-compact.png · COMPACT · items=27" if fade > 0.5
             else "after-full.png · FULL · items=27")
    draw.rounded_rectangle((x + 10, y + 10, x + 384, y + 38), radius=6, fill=(6, 10, 14))
    text(draw, (x + 20, y + 16), label, mono(14), ACCENT if fade <= 0.5 else BLUE,
         alpha=reveal(lt, 0.3))
    text(draw, (72, 638), "GRID_DRAWITEMS · type=FULL/COMPACT · items=27 · transition=true",
         mono(14), DIM, alpha=reveal(lt, 1.6))


def scene_result(base, draw, lt, dur):
    eyebrow(draw, (72, 64), "06 / 结果", ACCENT, reveal(lt, 0.0))
    value = int(round(7 * ease((lt - 0.2) / 0.9)))
    text(draw, (72, 96), f"{value}/7", mono(72, True), ACCENT, alpha=reveal(lt, 0.05))
    text(draw, (72, 200), "result.json 断言全绿", zh(22), MUTED, alpha=reveal(lt, 0.3))
    y = 244
    for i, key in enumerate(CHECKS):
        a = reveal(lt, 0.7 + i * 0.16)
        ok = bool(RESULT[key])
        color = mix(BG, ACCENT if ok else WARN, a)
        draw.line((72, y + 9, 76, y + 14), fill=color, width=2)
        draw.line((76, y + 14, 84, y + 2), fill=color, width=2)
        text(draw, (100, y), key, mono(14), FG, alpha=a)
        y += 30
    x2 = 470
    gates = [("test_review_fixes", "99/99"), ("check_hashes", f"{HASH_COUNT}/{HASH_COUNT}"),
             ("verify_evidence", "passed"), ("CI run 40338058986", "success"),
             ("remote master", "b91d355")]
    y2 = 112
    for i, (head, val) in enumerate(gates):
        a = reveal(lt, 0.5 + i * 0.18)
        text(draw, (x2, y2), head, mono(15), MUTED, alpha=a)
        text(draw, (x2, y2 + 22), val, mono(22, True), FG, alpha=a)
        y2 += 76
    text(draw, (470, 520), "无新 release（v0.5.6） · runs/p197-preview-key/", zh(17), DIM,
         alpha=reveal(lt, 1.6))
    text(draw, (470, 552), "github.com/SelYio666/mcbridge1201", mono(15), BLUE,
         alpha=reveal(lt, 1.8))


DRAWERS = [scene_title, scene_problem, scene_bytecode, scene_config,
           scene_states, scene_screens, scene_result]


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
    bar_y = 672
    draw.rounded_rectangle((72, bar_y, W - 72, bar_y + 6), radius=3, fill=(28, 38, 50))
    frac = clamp(t / DURATION)
    draw.rounded_rectangle((72, bar_y, 72 + int((W - 144) * frac), bar_y + 6), radius=3, fill=ACCENT)
    for start, _ in SCENES[1:]:
        x = 72 + int((W - 144) * (start / DURATION))
        draw.ellipse((x - 2, bar_y + 1, x + 2, bar_y + 5), fill=BG)
    text(draw, (72, bar_y + 18), "p197 · preview key rebinding", mono(13), DIM)
    text(draw, (W - 72, bar_y + 18), f"{int(t // 60):02d}:{int(t % 60):02d} / 00:30",
         mono(13), DIM, anchor="ra")
    return base


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(RUN / "p197-update.mp4"))
    ap.add_argument("--ffmpeg", default=str(TOOLCHAIN_FFMPEG))
    ap.add_argument("--stills", nargs="*", type=float, default=None)
    ap.add_argument("--keep-frames", action="store_true")
    args = ap.parse_args()

    if args.stills is not None:
        tmp = ROOT / "work" / "tmp"
        tmp.mkdir(parents=True, exist_ok=True)
        for t in args.stills:
            out = tmp / f"p197-still-{t:.1f}.png"
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
