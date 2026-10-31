# v0.5.8 → v0.5.9 更新教程

一句话：**一键安装现在支持 HMCL，下载更稳，也不会再装进“不存在的目录”。**

- 视频：[update-intro.mp4](update-intro.mp4)（76 秒）
- 长图：[tutorial-long.png](tutorial-long.png)
- 发布页：<https://github.com/SelYio666/mcbridge1201/releases/tag/v0.5.9>

## 一、这次改了什么

| 版本 | 改动 | 对你意味着什么 |
|---|---|---|
| **v0.5.9** | 支持 HMCL：`--hmcl` / `--hmcl-dir` | HMCL 用户也能一键装，不用自己找 `.minecraft` |
| **v0.5.9** | 传输层换成 urllib3 连接池 + 3 次重试 | Mojang/BMCL 偶发 `SSL: UNEXPECTED_EOF_WHILE_READING` 时会自动重试，不再直接崩 |
| **v0.5.8** | PCL 目录检测修复 | 配置里写了但**不存在**的目录不会被使用；回退便携 `.minecraft`，都没有就明确报错 |

证据：`runs/p222-hmcl/`（HMCL 实测）、`runs/p220-pcl2-dir-check/`（目录修复 4/4）。

## 二、选择你的启动器

### PCL2

```powershell
python tools/from_source_install.py --version 1.21.1 --pcl
```

自动读 PCL2 的 `PCL/Setup.ini`；找不到时用 `--pcl-dir <那个 .minecraft>` 指定。

### HMCL（普通安装）

```powershell
python tools/from_source_install.py --version 1.21.1 --hmcl
```

读 `%APPDATA%\.hmcl\config\user-game-directories.json`。

### HMCL（便携版 / 自定义目录）

```powershell
python tools/from_source_install.py --version 1.21.1 --hmcl-dir "D:\HMCL\.minecraft"
```

> HMCL 便携版的配置里游戏目录写的是**相对启动目录**的 `.minecraft`，所以自动检测拿不到；
> 用 `--hmcl-dir` 直接指到那个 `.minecraft`。装完重启 HMCL，左侧「游戏 → 实例管理」就会出现新版本。

### 图形面板（不想敲命令）

1. 到 Releases 下载 `mcbridge-pcl-panel.zip`；
2. 解压，双击 `mcbridge-pcl-panel.exe`；
3. 选版本 → 点安装 → 进度条跑完，打开 PCL 的版本列表即可看到。

## 三、下载与校验

| 文件 | 用途 |
|---|---|
| `mcbridge-pcl-setup.zip` | 控制台/交互安装器（免 Python） |
| `mcbridge-pcl-panel.zip` | 图形面板（免 Python） |

两者都是绿色包：解压即用，校验值在发布的 `SHA256SUMS.txt`。

## 四、常见问题

**Q1：HMCL 里显示“没有游戏实例”？**
说明装到了它不认的目录。看 HMCL 的设置里“游戏目录”是哪个；便携版就用 `--hmcl-dir` 指到它的 `.minecraft`，然后重启 HMCL。

**Q2：下载时报 `SSL: UNEXPECTED_EOF_WHILE_READING`？**
v0.5.9 已经内置连接池和 3 次重试；如果仍失败，多半是网络整体抖动，隔一会儿重跑即可，已下载的部分会跳过。

**Q3：会不会把游戏装到我没想到的地方？**
v0.5.8 起不会：配置目录必须已存在才用；否则回退便携 `.minecraft`；都没有就报错并停下。

**Q4：装完要手动改 `launcher_profiles.json` 吗？**
不用。安装器会写；PCL/HMCL 主要看 `versions/` 目录，profile 只是顺手兼容官方启动器。

## 五、验证与证据

- HMCL 3.17.0.363 列出装进去的 1.20.6：`runs/p222-hmcl/hmcl-1.20.6.png`
- 目录检测 4/4：`runs/p220-pcl2-dir-check/`
- 干净 clone 门禁（哈希/构建/单测/总门禁）：`runs/p221-clean-clone/`
- 总状态：`docs/FINAL-STATUS.md`
