# p233 — 两个客户端、两套独立资源包（共享 assets）

日期：2026-11-03。目标：补 p231 的边界——p231 的四客户端用 junction 共享
`assets/libraries/versions/.fabric`，**每个客户端自己的资源包从未验证过**。

## 做法

- 两个独立 gameDir：`work/tmp/p233-gamedir-{red,green}`，只把 `assets`、`libraries`、
  `versions`、`.fabric` 用 NTFS junction 指回 `work/launcher-e2e`（运行期只读），
  `mods/saves/logs/config/resourcepacks/options.txt` 各自独立；
- 各放一个自建资源包 `p233-{red,green}.zip`：`pack.mcmeta`（`pack_format: 34`）+ 6 张纯色
  `assets/minecraft/textures/gui/title/background/panorama_*.png`；
- `options.txt` 里分别写 `resourcePacks:["vanilla","file/p233-red.zip"]` /
  `...p233-green.zip`，并关掉 `onboardAccessibility`（p231 踩过的坑）；
- 客户端用 `fabric-loader-0.19.5-1.21.1` 启动到标题界面，按 pid 找窗口、截窗口矩形，
  取中下部区域的平均 RGB 作为判据。

## 结果 5/5（`result.json`）

| 检查 | 结果 |
|---|---|
| 红色客户端的画面偏红（R 明显高于 G/B） | ✅ mean `[135, 75, 75]` |
| 绿色客户端的画面偏绿（G 明显高于 R/B） | ✅ mean `[75, 135, 75]` |
| 两个客户端画面明显不同（通道差之和 ≥100） | ✅ 120 |
| 两个独立 gameDir | ✅ |
| 两套资源包都在各自目录里 | ✅ |

截图：`title-red.png`、`title-green.png`。

## 边界（如实）

- **assets 仍是共享的**（junction），本回合只证明 `resourcepacks/` + `options.txt` 按客户端独立；
  真正各自独立的 assets 目录没测（复制 4 份资源体积太大）；
- 只开 2 个客户端，不是 4 个；
- 判据是标题界面平均色，不是逐像素比对资源包内容；
- `pack_format` 用 34（1.21.1）；如果换版本要同步改。

## 复现

```text
py -3.12 runs/p233-independent-packs/probe.py
```
