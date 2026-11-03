#!/usr/bin/env python3
"""Plain-language code/project explainer for mcbridge1201 (1280x720, 30 fps, ~4 min).

Deliberately low-density: at most 6 short lines per screen, big type, one tiny config excerpt.
Everything is drawn with Pillow; ffmpeg only encodes.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import imageio_ffmpeg

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "share" / "code-walkthrough" / "code-walkthrough.mp4"
W, H, FPS, DUR = 1280, 720, 30, 232.0

BG = (10, 15, 24)
BG2 = (20, 30, 46)
FG = (236, 243, 252)
DIM = (150, 168, 190)
ACCENT = (96, 190, 245)
GREEN = (130, 225, 160)
AMBER = (238, 196, 118)
CARD = (26, 37, 54)
LINE = (48, 66, 90)

FONT_CN = "C:/Windows/Fonts/msyh.ttc"
FONT_CN_B = "C:/Windows/Fonts/msyhbd.ttc"
FONT_CODE = "C:/Windows/Fonts/consola.ttf"
_fonts: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    key = (path, size)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(path, size)
    return _fonts[key]


# (start, kicker, title, lines[(text, color, size)], kind)
# kind: "title" = big centered; "plain" = bullets; "code" = bullets + small monospace box
SCENES = [
    (0, "", "mcbridge1201", [
        ("把 1.20.1 的 Minecraft 模组，搬到 1.21.1 继续用", FG, 30),
        ("转换引擎 · 本地启动器 · 一键安装到 PCL", DIM, 22),
    ], "title"),
    (11, "01", "为什么需要它？", [
        ("模组像插件：它要跟游戏里的“零件”对上号", FG, 26),
        ("Minecraft 升级后，很多零件改了名字、换了位置", FG, 26),
        ("旧模组直接放进新版：启动就崩，或者根本加载不出来", AMBER, 26),
        ("这个工具做的事：帮你把旧模组“翻译”成新版本能认的样子", GREEN, 26),
    ], "plain"),
    (45, "02", "它只做三件事", [
        ("读：把模组拆开，找出它引用了哪些游戏零件", FG, 28),
        ("翻：把旧名字换成新名字；新版删掉的，就补一个“桥”", FG, 28),
        ("验：真的启动一次，确认能进世界、能进服务器", FG, 28),
        ("每一步都留下日志和截图，谁都能复查", DIM, 22),
    ], "plain"),
    (79, "03", "“翻译”长什么样", [
        ("仓库里是一张张规则表，写明：旧零件 → 新零件", FG, 25),
        ("下面是一条真实规则（删掉了很多字段，只留骨架）", DIM, 20),
    ], "code"),
    (113, "04", "新版删掉的东西，用“桥”补回来", [
        ("例：新版游戏里没有某个常量了，但旧模组还要用它", FG, 25),
        ("桥 = 一小段新代码，替旧模组把这个东西重新提供出来", FG, 25),
        ("桥是工具自己生成的，不依赖游戏本体，构建时也能跑", DIM, 21),
        ("哪些能修、哪些修不了，都写在规则里，不偷偷糊弄", AMBER, 23),
    ], "plain"),
    (146, "05", "做到什么程度了？", [
        ("10 个真实模组做过完整转换与运行验证", GREEN, 27),
        ("Lithium · IronChests · TrashSlot · AppleSkin · Mod Menu", FG, 23),
        ("Clumps · FallingTree · ShulkerBoxTooltip · FerriteCore · ImmediatelyFast", FG, 23),
        ("进过世界、进过服务器，也有单人/多人/专服的证据", FG, 23),
        ("修不了的（比如 Sodium 的渲染内核）会明说“不支持”", AMBER, 23),
    ], "plain"),
    (180, "06", "配套的两个工具", [
        ("网页启动器：选版本 → 安装 → 启动，点点点就行", FG, 26),
        ("一键安装：图形面板或安装器，直接装进 PCL 的版本列表", FG, 26),
        ("也可以装进 HMCL（命令行参数），换启动器不用重下", DIM, 21),
    ], "plain"),
    (204, "07", "为什么可以信", [
        ("仓库里 0 个游戏/模组 jar，只有工具、规则和证据", FG, 24),
        ("每个结论都有 runs/ 下的日志、截图、结果文件", FG, 24),
        ("文件哈希清单 + 自动检查，改坏了 CI 会红", FG, 24),
        ("想看细节：README → FINAL-STATUS → remaining-work", DIM, 20),
    ], "plain"),
    (226, "", "github.com/SelYio666/mcbridge1201", [
        ("代码走读版视频见 share/code-walkthrough/", DIM, 20),
    ], "title"),
]
ENDS = [s[0] for s in SCENES[1:]] + [DUR]

RULE_LINES = [
    '{ "id": "itempredicate.any",',
    '  "sourceName": "field_9640",',
    '  "bridgeClass": "top/mcbridge1201/bridge/ItemPredicateAny" }',
]


def scene_at(t: float) -> int:
    for i, s in enumerate(SCENES):
        if s[0] <= t < ENDS[i]:
            return i
    return len(SCENES) - 1


def bg(d: ImageDraw.ImageDraw) -> None:
    for y in range(H):
        k = y / H
        d.line([(0, y), (W, y)], fill=tuple(int(BG[i] * (1 - k) + BG2[i] * k) for i in range(3)))
    for x in range(0, W, 64):
        d.line([(x, 0), (x, H)], fill=(18, 26, 38), width=1)


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    proc = subprocess.Popen(
        [ffmpeg, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
         "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast",
         "-crf", "21", "-movflags", "+faststart", str(OUT)],
        stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    total = int(DUR * FPS)
    for i in range(total):
        t = i / FPS
        si = scene_at(t)
        start, kicker, title, lines, kind = SCENES[si]
        local = t - start
        img = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(img)
        bg(d)

        if kind == "title":
            tw = d.textlength(title, font=font(FONT_CN_B, 56))
            d.text(((W - tw) / 2, 220), title, font=font(FONT_CN_B, 56), fill=FG)
            y = 320
            for text, color, size in lines:
                tw = d.textlength(text, font=font(FONT_CN, size))
                d.text(((W - tw) / 2, y), text, font=font(FONT_CN, size), fill=color)
                y += size + 18
        elif kind == "code":
            d.text((70, 56), f"{kicker} · {title}", font=font(FONT_CN_B, 34), fill=ACCENT)
            y = 130
            for text, color, size in lines:
                d.text((70, y), text, font=font(FONT_CN, size), fill=color)
                y += size + 16
            box_top = y + 16
            d.rounded_rectangle([70, box_top, W - 70, box_top + 150], radius=14,
                                fill=CARD, outline=LINE, width=1)
            yy = box_top + 18
            shown = min(len(RULE_LINES), int(local * 6))
            for line in RULE_LINES[:shown]:
                d.text((90, yy), line, font=font(FONT_CODE, 19), fill=GREEN)
                yy += 30
            d.text((90, yy + 8), "旧常量 → 新写法（简化展示）", font=font(FONT_CN, 18), fill=DIM)
        else:
            d.text((70, 54), f"{kicker} · {title}", font=font(FONT_CN_B, 36), fill=ACCENT)
            y = 140
            shown = int(local * 12)
            used = 0
            for text, color, size in lines:
                if used > shown:
                    break
                d.text((70, y), text, font=font(FONT_CN, size), fill=color)
                used += len(text)
                y += size + 26

        d.rectangle([0, H - 6, W, H], fill=(26, 36, 52))
        d.rectangle([0, H - 6, int(W * t / DUR), H], fill=ACCENT)
        proc.stdin.write(img.tobytes())

    proc.stdin.close()
    proc.wait()
    print("wrote", OUT, f"{OUT.stat().st_size / 1e6:.1f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
