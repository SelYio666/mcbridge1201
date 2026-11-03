# p234 — 真实 OS 级键鼠：悬停高亮、点击换屏、Esc 返回

日期：2026-11-03。目标：把“OS 级 SendInput 未测”这条从菜单层面关掉（不做游戏内动作，也不写存档）。

## 安全约束（先写）

- 每次输入前都断言 `GetForegroundWindow() == 游戏窗口`，不是就直接退出、**不发任何点击**；
- 只做菜单动作：悬停「Singleplayer」、点一下、Esc 返回；
- 开始时记录并恢复鼠标原位置；
- 用全新的 `work/tmp/p234-gamedir`（junction 共享 assets/libraries/versions/.fabric，
  自己的 saves/mods/logs），不碰玩家存档。

## 做法

1. 用 `fabric-loader-0.19.5-1.21.1` 启动到标题界面，按 PID 找窗口；
2. 截窗口图 → 灰色按钮检测 → 取最上面那个按钮（Singleplayer）的中心；
3. 鼠标移到按钮上，再截一次图：按钮区域平均亮度 **119.8 → 125.2**（真实 hover 高亮）；
4. 真实 `mouse_event` 点击，3 秒后截图：画面差异 12 分以上（换屏）；
5. 真实 `keybd_event` 发 Esc，2 秒后截图：与标题画面的差异小于点击后的差异（回到标题）。

## 结果 4/4（`result.json`）

| 检查 | 结果 |
|---|---|
| 输入前窗口在前台 | ✅ |
| 悬停使按钮变亮 | ✅ 119.8 → 125.2 |
| 点击改变了画面 | ✅ |
| Esc 回到标题 | ✅ |

画面：`title-before.png`（标题）、`title-hover.png`（悬停）、`after-click.png`、`after-esc.png`。

**实际观察**：这个测试 gameDir 没有存档，点 Singleplayer 后游戏直接停在「创建新世界」页，
不是世界列表；Esc 回到标题（标题页 Singleplayer 按钮带高亮）。README 按实际画面写，不按预期写。

## 边界（如实）

- 只验证**菜单级**真实键鼠；游戏内动作（走位/开箱）仍按 p191/p192 的 GLFW 回调边界合成输入，
  没有声称；
- 单客户端、1.21.1 + Fabric、单显示器；
- 判据是窗口像素与前台断言，不是系统级输入日志；
- 本回合没有写入任何世界数据。

## 复现

```text
py -3.12 runs/p234-os-input/probe.py
```
