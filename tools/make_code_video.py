#!/usr/bin/env python3
"""Code walkthrough video for mcbridge1201 (1280x720, 30 fps, ~5 min).

Everything is drawn with Pillow; ffmpeg only encodes. The snippets are real excerpts from
this repository (shortened to fit), so the video cannot claim code that is not there.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import imageio_ffmpeg

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "share" / "code-walkthrough" / "code-walkthrough.mp4"
W, H, FPS, DUR = 1280, 720, 30, 300.0

BG = (10, 14, 22)
BG2 = (18, 26, 40)
FG = (232, 240, 250)
DIM = (138, 156, 178)
ACCENT = (86, 184, 240)
GREEN = (120, 220, 150)
AMBER = (232, 190, 110)
RED = (240, 130, 130)
CARD = (24, 34, 50)
LINE = (44, 60, 82)

FONT_CN = "C:/Windows/Fonts/msyh.ttc"
FONT_CN_B = "C:/Windows/Fonts/msyhbd.ttc"
FONT_CODE = "C:/Windows/Fonts/consola.ttf"
_fonts: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    key = (path, size)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(path, size)
    return _fonts[key]


KEYWORDS = {"package", "import", "public", "private", "static", "final", "class", "void",
            "new", "return", "if", "else", "for", "while", "try", "catch", "throws",
            "extends", "implements", "interface", "record", "this", "null", "true", "false",
            "def", "from", "as", "with", "for", "in", "not", "and", "or", "lambda"}


TOKEN = re.compile(
    r'("(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\'|//.*|#.*|[A-Za-z_][A-Za-z0-9_]*|[^A-Za-z_"\'\s]+|\s+)')


def is_cjk(ch: str) -> bool:
    return "\u4e00" <= ch <= "\u9fff" or ch in "，。：；！？（）【】、·—"


def draw_run(d: ImageDraw.ImageDraw, x: int, y: int, s: str, color, size: int) -> int:
    i = 0
    while i < len(s):
        if is_cjk(s[i]):
            f = font(FONT_CN, size - 1)
            d.text((x, y), s[i], font=f, fill=color)
            x += int(d.textlength(s[i], font=f))
            i += 1
            continue
        j = i
        while j < len(s) and not is_cjk(s[j]):
            j += 1
        seg = s[i:j]
        f = font(FONT_CODE, size)
        d.text((x, y), seg, font=f, fill=color)
        x += int(d.textlength(seg, font=f))
        i = j
    return x


def draw_code_line(d: ImageDraw.ImageDraw, x: int, y: int, s: str, size: int = 16) -> None:
    for m in TOKEN.finditer(s):
        tok = m.group(0)
        if tok.startswith("//") or tok.startswith("#"):
            color = DIM
        elif tok[:1] in "\"'":
            color = AMBER
        elif tok.replace("_", "").isalnum() and tok in KEYWORDS:
            color = ACCENT
        else:
            color = FG
        x = draw_run(d, x, y, tok, color, size)


SCENES = [
    # (start, title, subtitle lines, code lines, reveal chars/sec or None for instant)
    (0, "mcbridge1201 · 代码走读", [
        "Minecraft 1.20.1 模组 → Fabric 1.21.1 兼容工具箱",
        "转换引擎 · 规则修补 · javac/ASM 桥 · 本地启动器 · 一键安装器 · 证据体系",
    ], [], None),
    (12, "01 · 代码地图", [
        "92 个 Java 源文件（12,070 行）· 29 份规则（1,712 行）· 56 个 Python 工具（14,243 行）",
    ], [
        "mcbridge1201/",
        "├─ java/src/main/java/top/mcbridge1201/",
        "│   ├─ Main.java                  CLI 入口：convert / analyze / verify",
        "│   ├─ index/                     TinyMappings + TargetIndex（目标类索引）",
        "│   ├─ scan/                      ArtifactScanner：扫描模组 jar 的符号引用",
        "│   ├─ analyze/                   Analyzer：静态损伤分析",
        "│   ├─ remap/                     JarRemapper + Hierarchy：保留方法体的重映射",
        "│   ├─ rules/                     RuleSet / JarPatcher / BridgeGenerator",
        "│   └─ profile/                   TargetProfile（目标身份与校验）",
        "├─ rules/fabric-1.21.1/          29 份 JSON 规则：字段/方法/桥/降级",
        "├─ tools/                        安装器、面板、哈希/证据门禁、视频生成",
        "├─ launcher/                      本地网页启动器（Python 标准库 + 原生前端）",
        "└─ runs/pNNN-*/                   226 份证据 README + 日志/截图",
    ], 260),
    (34, "02 · 转换管线", [
        "从一份 1.20.1 模组 jar，到一份能在 1.21.1 进世界的 jar；每一步都有可复查的产物。",
    ], [
        "python tools/from_source_install.py --version 1.21.1 --root D:\\MC",
        "        │",
        "        ▼",
        "manifest → version.json → client.jar → libraries(+natives) → assets(sha1)",
        "        │",
        "        ▼",
        "java -cp mcbridge1201.jar Main convert <mod.jar> --target fabric-1.21.1",
        "        │",
        "        ├─ TargetIndex     目标版本的类/方法/字段索引（intermediary）",
        "        ├─ ArtifactScanner 模组里每个符号引用：类、字段、方法、签名",
        "        ├─ Analyzer        静态损伤：missingClass / missingMember / descMismatch",
        "        ├─ JarRemapper     identical-id 重映射，保留方法体",
        "        ├─ RuleSet+JarPatcher  规则驱动修补，桥与降级写进规则",
        "        └─ BytecodeVerify  逐类 AsmVerify，任何失败都让转换停下",
        "        │",
        "        ▼",
        "runs/pNNN-*/ 证据：日志、截图、result.json、SHA-256 清单",
    ], 300),
    (60, "03 · 规则长什么样", [
        "rules/fabric-1.21.1/container.json —— 一条 fieldRedirect 的完整字段",
    ], [
        "{",
        '  "schemaVersion": "0.1-draft",',
        '  "target": "fabric-1.21.1",',
        '  "fieldRedirects": [{',
        '    "id": "itempredicate.any.static-field",',
        '    "sourceOwner": "net/minecraft/class_2073",',
        '    "sourceName": "field_9640",',
        '    "sourceDesc": "Lnet/minecraft/class_2073;",',
        '    "bridgeClass": "top/mcbridge1201/bridge/ItemPredicateAny",',
        '    "bridgeMethod": "any",',
        '    "capability": "item.predicate.any",',
        '    "risk": "low",',
        '    "evidence": "1.21.1 ItemPredicate 是 record，没有 ANY 常量；',
        '                 空 predicate 与 1.20.1 的 ANY 语义一致……"',
        "  }]",
        "}",
    ], 300),
    (98, "04 · 桥：用 ASM 写，而不是 javac", [
        "桥类只调用目标版本类型；生成字节码让工具在构建期不依赖游戏 classpath。",
    ], [
        "public final class BridgeGenerator {",
        "    public static byte[] classFor(RuleSet.BridgeSpec spec) {",
        "        ClassWriter cw = new ClassWriter(0);",
        '        cw.visit(Opcodes.V17, ACC_PUBLIC | ACC_FINAL,',
        "                 spec.internalName, null,",
        '                 "java/lang/Object", null);',
        "        MethodVisitor mv = cw.visitMethod(",
        "            ACC_PUBLIC | ACC_STATIC,",
        "            spec.methodName, spec.methodDesc, null, null);",
        "        mv.visitCode();",
        "        // ... 只为目标版本类型生成调用点",
        "        return cw.toByteArray();",
        "    }",
        "}",
    ], 220),
    (134, "05 · 重映射：保留方法体", [
        "identical-id 重映射 —— 只换名字与描述符，方法体一个字节都不改。",
    ], [
        "public final class JarRemapper {",
        "    public byte[] remap(byte[] input, Map<String, String> delta) {",
        "        ClassReader cr = new ClassReader(input);",
        "        ClassWriter cw = new ClassWriter(0);",
        "        ClassVisitor cv = new ClassVisitor(ASM9, cw) {",
        "            @Override",
        "            public MethodVisitor visitMethod(int access, String name,",
        "                                             String desc, String sig,",
        "                                             String[] exceptions) {",
        "                String mapped = delta.getOrDefault(name, name);",
        "                return super.visitMethod(access, mapped, desc, sig, exceptions);",
        "            }",
        "        };",
        "        cr.accept(cv, 0);",
        "        return cw.toByteArray();",
        "    }",
        "}",
    ], 240),
    (172, "06 · 本地启动器", [
        "launcher/server.py：Python 标准库 HTTP 服务；launcher/web：原生 HTML/CSS/JS，不依赖前端框架。",
    ], [
        "class Handler(BaseHTTPRequestHandler):",
        "    def do_POST(self):",
        "        path = self.path.split('?')[0]",
        "        body = self._read_json()",
        "        if path == '/api/install':",
        "            mc = str(body.get('mc', '')).strip()",
        "            loader = str(body.get('loader', 'vanilla'))",
        "            target = str(body.get('target', 'local'))",
        "            if target == 'pcl':",
        "                root, notes = pcl_target()",
        "                if not root:",
        "                    return self._send(400, {'error': '没有找到 PCL2 游戏目录'})",
        "            threading.Thread(target=run_install,",
        "                             args=(mc, loader, version, root),",
        "                             daemon=True).start()",
        "            return self._send(200, {'started': True})",
    ], 230),
    (206, "07 · 一键安装器", [
        "tools/from_source_install.py：只用标准库；清单 → 版本 JSON → 客户端 jar → 库 → 资源，逐项 sha1。",
    ], [
        "def install(version: str, root: Path, workers: int = 16):",
        "    man = manifest()                      # piston-meta version_manifest_v2",
        "    vj = get_json(find_version(man, version)['url'])",
        "    client = vj['downloads']['client']",
        "    download(client['url'], root / 'versions' / version / f'{version}.jar',",
        "             expected_sha1=client['sha1'])",
        "    for lib in vj['libraries']:",
        "        if 'artifact' in lib.get('downloads', {}):",
        "            a = lib['downloads']['artifact']",
        "            download(a['url'], root / 'libraries' / a['path'],",
        "                     expected_sha1=a['sha1'])",
        "    index = get_json(vj['assetIndex']['url'])",
        "    for name, obj in index['objects'].items():",
        "        download(objects_url(obj['hash']),",
        "                 root / 'assets' / 'objects' / obj['hash'][:2] / obj['hash'])",
        "    write_launcher_profiles(root)",
    ], 240),
    (242, "08 · 证据体系", [
        "仓库里 0 个 jar；每份证据都在 runs/，SHA-256 清单可被干净 clone 校验。",
    ], [
        "$ python tools/check_hashes.py",
        "ok=1751 mismatch=0 missing=0",
        "",
        "$ python tools/check_manifest_coverage.py",
        "required evidence files: 337 / hashed evidence files: 337 / coverage OK",
        "",
        "$ python tools/verify_evidence.py",
        '{ "passed": true, "unit_tests": { "tests": 32, "failures": 0 }, ... }',
        "",
        "# CI 在 checkout 后直接跑这两道，防止清单悄悄过期：",
        "- name: Hash manifest matches the checkout",
        "  run: python tools/check_hashes.py",
        "- name: Every run README/result is hashed",
        "  run: python tools/check_manifest_coverage.py",
    ], 260),
    (276, "09 · 发布与下一步", [
        "v0.5.10：网页启动器支持「安装到 PCL2」；安装器 v0.5.9 支持 HMCL。",
    ], [
        "python tools/release_check.py --build <版本> --accept --ui-accept",
        "",
        "  1. hash manifest matches the tree",
        "  2. every run README/result is hashed",
        "  3. evidence gate (suite + unit tests + encoding)",
        "  4. 1.21.1 baseline lock has no drift",
        "  5. portable build dist/mcbridge-launcher-<版本>.zip",
        "  6. clean-host acceptance (p208)",
        "  7. packaged UI acceptance (p227)",
        "",
        "github.com/SelYio666/mcbridge1201",
    ], 240),
]
ENDS = [s[0] for s in SCENES[1:]] + [DUR]


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
        d.line([(x, 0), (x, H)], fill=(19, 27, 40), width=1)


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
        start, title, subs, code, speed = SCENES[si]
        local = t - start
        img = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(img)
        bg(d)

        # header
        d.rectangle([0, 0, W, 76], fill=(14, 20, 32))
        d.text((44, 22), title, font=font(FONT_CN_B, 26), fill=FG)
        d.text((W - 220, 30), f"{si + 1:02d} / {len(SCENES):02d}", font=font(FONT_CODE, 16), fill=DIM)
        for k, line in enumerate(subs):
            d.text((44, 92 + k * 26), line, font=font(FONT_CN, 16), fill=DIM)

        top = 150 + (len(subs) - 1) * 8
        if code:
            # code panel
            panel_h = min(H - top - 60, 26 + 24 * len(code))
            d.rounded_rectangle([36, top, W - 36, top + panel_h], radius=12,
                                fill=CARD, outline=LINE, width=1)
            revealed = speed * local if speed else 10 ** 6
            used = 0
            y = top + 16
            for idx, line in enumerate(code):
                if used > revealed:
                    break
                show = line
                if speed and used + len(line) > revealed:
                    show = line[: max(0, int(revealed - used))]
                d.text((52, y), f"{idx + 1:02d}", font=font(FONT_CODE, 13), fill=(72, 92, 116))
                draw_code_line(d, 92, y, show)
                used += len(line)
                y += 24
                if y > top + panel_h - 24:
                    break

        # progress bar
        d.rectangle([0, H - 6, W, H], fill=(24, 34, 50))
        d.rectangle([0, H - 6, int(W * t / DUR), H], fill=ACCENT)
        proc.stdin.write(img.tobytes())

    proc.stdin.close()
    proc.wait()
    print("wrote", OUT, f"{OUT.stat().st_size / 1e6:.1f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
