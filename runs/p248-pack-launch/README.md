# p248 — 用本仓库启动器跑「缆车末日」整合包（1.20.1 + Forge）

日期：2026-11-07。目标：拿用户给的真实整合包，证明本仓库的**运行辅助**这一半能干活。

## 这个包是什么

- `D:\浏览器所下载文件\缆车末日整合包`：Forge 1.20.1 整合包（Forge 47.4.20）；
- 替换包 `2.拖入minecraft文件夹中替换` 里有：12 个 Forge mod、408 个 config 文件、
  一个 1.7 GB 存档（`缆车末日100天地图`）、两个光影包；
- 包里还带 **Sinytra Connector**（让 Forge 加载 Fabric 模组）和 PCL2。

## 做法

1. 新建隔离游戏根 `work/packtest`，`assets/libraries/versions` 用 junction 指回 `work/launcher-e2e`；
2. 把包里的 `overrides/mods`、`config`、`saves`、`shaderpacks` 复制进去；
3. 这套替换包**不是完整模组集**（基础模组在“拖入 PCL”的主包里，用户机器上没有那个 zip），
   启动时报缺依赖，补了两个缺失的库：
   - `architectury-9.2.14-forge.jar`（ftblibrary 要求 `architectury [9.0.8,)`）
   - `kotlinforforge-4.12.0-all.jar`（`dcrapi` 是 Kotlin 写的，缺 `kotlin/jvm/internal/Intrinsics`）
4. 用本仓库启动器（`launcher/mclaunch.py`）以 `1.20.1-forge-47.4.28` 启动，
   `--quickPlaySingleplayer 缆车末日100天地图`。

## 结果：真的进世界了

```text
[20:10:27] Forge mod loading, version 47.4.28, for MC 1.20.1 with MCP 20230612.114412
[20:17:13] Time elapsed: 3774 ms
[20:17:14] PackUser joined the game
```

截图 `in-game.png`：窗口标题 `Minecraft* Forge 1.20.1 - Singleplayer`，画面是包里的末日地图，
屏幕上还有 zombiegame 模组的提示。

## 边界（如实）

- 因为缺基础模组，日志里有大量 `Tried to load unrecognized recipe: …`（alexsmobs / exdeorum /
  tacz / grapplemod 等），世界能进但**不是完整整合包体验**；
- 装的是本机已有的 Forge **47.4.28**（包要求 47.4.20，同 47.4.x 线）；
- 存档是**副本**，原存档没动；
- 这条证明的是“启动/运行辅助”，不是“转换”。

## 复现

```text
py -3.12 runs/p248-pack-launch/probe.py
```
