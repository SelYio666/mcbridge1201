"""p226: p215's create-world click missed the button by ~25 px (static evidence, no clicking)."""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import json

RUN = Path(r"C:\Users\27682\Documents\新建文件夹\mcbridge1201\runs\p215-pcl2-create-button")
OUT = Path(r"C:\Users\27682\Documents\新建文件夹\mcbridge1201\runs\p226-p215-coordinate")

img = Image.open(RUN / "attempt1.png").convert("RGB")
W, H = img.size
px = img.load()


def clusters(vals, gap=6, minlen=6):
    out = []
    for v in vals:
        if out and v - out[-1][-1] <= gap:
            out[-1].append(v)
        else:
            out.append([v])
    return [c for c in out if len(c) >= minlen]


# button borders are near-white; find their rows/columns in the bottom half
band = range(400, H)
rows = [y for y in band if sum(1 for x in range(0, W, 2)
        if px[x, y][0] > 95 and abs(px[x, y][0] - px[x, y][1]) < 6
        and abs(px[x, y][1] - px[x, y][2]) < 6) > 40]
row_clusters = clusters(rows, gap=4, minlen=2)
result = {"image": str(RUN / "attempt1.png"), "size": [W, H], "rows": []}
boxes = []
for rc in row_clusters:
    y0, y1 = rc[0], rc[-1]
    cols = [x for x in range(W) if any(
        px[x, y][0] > 95 and abs(px[x, y][0] - px[x, y][1]) < 6
        and abs(px[x, y][1] - px[x, y][2]) < 6 for y in range(y0, y1 + 1))]
    for cc in clusters(cols, gap=20, minlen=40):
        boxes.append((cc[0], y0, cc[-1], y1))
result["button_boxes_screenshot"] = boxes
print("button boxes (screenshot coords):", boxes)

clicks = [(277, 437), (585, 437)]
result["clicks"] = clicks
for cx, cy in clicks:
    hit = [b for b in boxes if b[0] <= cx <= b[2] and b[1] <= cy <= b[3]]
    print("click", (cx, cy), "inside", hit)
    result.setdefault("click_checks", []).append({"click": [cx, cy], "inside": hit})

# client-area inset from the window frame (854x480 client in an 870x519 shot)
inset_x, inset_y = (W - 854) // 2, H - 480 - 9
result["frame_inset"] = [inset_x, inset_y]
result["button_boxes_client"] = [[b[0] - inset_x, b[1] - inset_y, b[2] - inset_x, b[3] - inset_y]
                                 for b in boxes]
result["clicks_client"] = [[c[0] - inset_x, c[1] - inset_y] for c in clicks]

annot = img.copy()
d = ImageDraw.Draw(annot)
f = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 15)
for b in boxes:
    d.rectangle(b, outline=(90, 220, 120), width=2)
for (cx, cy), col in zip(clicks, ((255, 80, 80), (255, 170, 40))):
    d.line([(cx - 9, cy), (cx + 9, cy)], fill=col, width=3)
    d.line([(cx, cy - 9), (cx, cy + 9)], fill=col, width=3)
    d.text((cx + 12, cy - 26), f"click ({cx},{cy})", font=f, fill=col)
top = min(b[1] for b in boxes)
d.text((20, top - 26), f"button top y={top}; clicks y=437 are {top - 437}px above", font=f,
       fill=(255, 255, 255))
OUT.mkdir(parents=True, exist_ok=True)
annot.save(OUT / "annotated.png")
(OUT / "coords.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps(result, indent=2)[:1200])
