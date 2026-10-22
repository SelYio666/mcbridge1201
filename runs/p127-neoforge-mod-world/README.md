# p127 — NeoForge 21.1.264 + 真实模组（AppleSkin）进世界

日期：2026-10-22。目标：把“NeoForge 只到主菜单”的缺口补成**带模组进世界**。过程中抓到并修了
一个启动器真 bug。

## 过程

1. 在已安装的 `neoforge-21.1.264` 实例里放入 AppleSkin 3.0.9（Modrinth，`neoforge` / 1.21.1，
   SHA-1 校验 `81cf0e66…`），把 1.21.1 服务端世界拷进 `saves/ColdWorld`；
2. 第一次启动：**只到主菜单**（标题 `Minecraft NeoForge* 1.21.1`，显示 `(3 mods)`），
   日志里 quickPlay 没出现；
3. 定位：`build_command()` 对 Forge/NeoForge 走 `backend.command()` 的**提前 return**，
   没有追加 `extra_game`（`--quickPlaySingleplayer ColdWorld` 被丢掉）；
4. 修复：早退分支补 `if extra_game: cmd += extra_game`，并加回归检查
   `NEOFORGE backend command keeps extra game args (quickPlay)`；
5. 第二次启动：**成功进入世界**，日志有 `ModUser joined the game`，AppleSkin 已加载。

## 证据

| 文件 | 内容 |
|---|---|
| `world.png` | 世界内 F3 截图（标题 `Minecraft NeoForge* 1.21.1 - Singleplayer`，100 fps） |
| `launch.log` | 启动日志：`AppleSkin 3.0.9+mc1.21 (appleskin)`、`mod/appleskin` 资源包、`joined the game` |
| `result.json` | 脚本记录：`joined: true`、mod SHA-1 校验、mod 日志行 |

## 结论

- NeoForge 21.1.264 + 第三方 NeoForge 模组 + 单人世界：**通过**；
- 顺带修复了 Forge/NeoForge 启动命令丢弃 `extra_game` 的真实 bug（quickPlay/额外参数都受影响）；
- 测试实例的 mods/saves/options 已清理（证据在 `runs/`）。

## 限制

- 只测了一个模组（AppleSkin，纯客户端/显示类），没有测需要注册方块/物品/网络的复杂模组；
- 世界来自 1.21.1 服务端，未测新建世界/多人；
- 单次启动，没有 soak。
