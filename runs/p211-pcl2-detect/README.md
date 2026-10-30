# p211：PCL2 到底在哪，以及"快捷方式失效"为什么没被说出来

任务 6 一直被记成"本机没有 PCL2，所以只能静态验证"。查完这台机器：**PCL2 在**，
只是不在 p137 记录的那条路径下；而且当桌面快捷方式指向一个已被删除的目录时，
我们的检测会**静默**退回 `%APPDATA%\.minecraft` 并把它当成"检测到了"。

这一轮只做两件事：把环境写成可复核的事实，并把静默改成为说明。**没有**启动 PCL2、
**没有**往真机 `.minecraft` 写任何东西（探针是只读的，脚本里没有 `startfile`/`install()`）。

## 结论

| 事项 | 结果 | 证据 |
|---|---|---|
| PCL2 存在 | ✅ `D:\浏览器所下载文件\我的世界PCL2启动器_2.12.8.2\plain craft launcher 2.exe`，5,750,272 B | `before/probe.json`、`verify_detect.py` |
| 版本 | `FileVersion = 2.13.1.1`（= p137 实测的那个），目录名 `…_2.12.8.2` 只是下载文件夹名 | 同上 |
| 游戏目录 | `PCL\Setup.ini` 的 `LaunchFolderSelect:C:\Users\27682\AppData\Roaming\.minecraft\`，解析结果完全一致；该目录有 `versions\1.21.1` | `before/probe.json` |
| 桌面快捷方式 | `Plain Craft Launcher 2.lnk` → `D:\我的世界\.minecraft\涟漪专用启动器\Plain Craft Launcher 2.exe`，**该路径已不存在** | `before/probe.json` 的 `desktop_shortcuts[0].target_exists=false` |
| 修前行为 | 快捷方式被静默丢弃（`notes=[]`、无 scan API、`pcl2_from_desktop=None`），`detect_pcl_root()` 仍返回同一个游戏目录 | `before/probe.json` |
| 修后行为 | 同一次调用点出死路径（带完整路径）+ 说明"回退到 %APPDATA%\.minecraft"，**返回的目录不变** | `after/probe.json` |
| 面板 | 同一条说明显示在目录框下方（琥珀色标签，可换行），截图 `panel-smoke.png`（921 个版本已加载） | `panel-smoke.json` |
| 判定 | `verify_detect.py` **26/26** | `detect-check.json` |

## 复现

```bash
export JAVA_HOME="/c/Users/27682/Documents/新建文件夹/.toolchain/jdk"   # 本目录不需要 java
cd "/c/Users/27682/Documents/新建文件夹/mcbridge1201"

# 1. 修前/修后各跑一次探针（--exe 必须给：PCL2 的安装位置是"用户机器事实"）
py -3.12 runs/p211-pcl2-detect/probe_pcl.py --label before-fix \
    --exe "D:\浏览器所下载文件\我的世界PCL2启动器_2.12.8.2\plain craft launcher 2.exe" \
    --out runs/p211-pcl2-detect/before
# （应用 from_source_install.py 的修复后）
py -3.12 runs/p211-pcl2-detect/probe_pcl.py --label after-fix \
    --exe "D:\浏览器所下载文件\我的世界PCL2启动器_2.12.8.2\plain craft launcher 2.exe" \
    --out runs/p211-pcl2-detect/after

# 2. 真实面板（Tk 窗口 + PrintWindow 截图）
py -3.12 runs/p211-pcl2-detect/panel_smoke.py

# 3. 判据
py -3.12 runs/p211-pcl2-detect/verify_detect.py
```

`before/` 与 `after/` 是同一台机器相隔几分钟的两次采集：两者的 `exe_sha256`
`30eb93c62fc51ede0898648e67455478a3d5a4f279938ae65aec77b84cb9703f` 必须相同，
所以"差异只来自代码"这件事是判据里明写的检查（`both_runs_saw_the_same_launcher_bytes`）。

## 修了什么

`tools/from_source_install.py`：

- 新增 `pcl2_shortcut_scan(desktop=None, resolve=None) -> (game_dir | None, notes)`。
  逐条产生说明：`读不到快捷方式目标` / `快捷方式指向的路径已不存在（<完整路径>）` /
  `<目标> 里既没有 PCL/Setup.ini 也没有 .minecraft` / `桌面上没有 PCL 快捷方式`。
  `desktop` 与 `resolve` 可注入——这样"目标不存在"的分支能在没有 COM、没有桌面的环境下被测到。
- `pcl2_from_desktop()` 变成 `pcl2_shortcut_scan()[0]`（对外行为不变）。
- `detect_pcl_root(notes: list[str] | None = None)`：收集快捷方式的 notes，并在走兜底时补一条
  `快捷方式没有给出游戏目录，回退到 <目录>`。不传 `notes` 时行为与旧版一致。
- CLI：`--pcl` / 交互模式把每条 note 打到 stderr（`PCL 检测: …`），不再只报目录。

`tools/pcl_panel.py`：

- 目录框下方加一条琥珀色、可换行的 `ttk.Label`，内容是 `detect_pcl_root(notes)` 的 notes。

**这不是"改了检测结果"**：游戏目录还是 `C:\Users\27682\AppData\Roaming\.minecraft`，
`the_fix_does_not_move_the_detected_folder` 就是钉这一点的。修的是可观测性——
`share/pcl-onclick/README.md` 里"`--pcl` 会自动沿快捷方式定位"这句话，现在失效时会自己承认。

## 为什么这件事值得修（不是洁癖）

1. 这次兜底目录**恰好**等于 PCL2 的真实游戏目录（`Setup.ini` 就指着默认位置），所以没暴露；
2. 换一台 PCL2 用自定义目录的机器，快捷方式一失效，`--pcl` 会把版本装到
   `%APPDATA%\.minecraft`，而 PCL2 根本看不到——用户看到的是"装完了但列表没有"；
3. 面板同理：目录框里有个看起来正常的路径，用户没有任何线索去怀疑它。

## 已知边界（本轮没做）

- 探针记录的是**这一台**机器的路径；换机器时 `--exe` 要换，JSON 里的 `given`/`exe` 会跟着变；
- 面板 smoke 只读版本清单（921 条），不点安装按钮——**这一条已被 p212 关掉**：面板真点了一次安装，
  并在 PCL2 的版本列表里看到了装出来的 1.20.4（`runs/p212-pcl2-e2e/`）；
- **启动器后来被 p212 更新到 2.99.0.0**：本目录 `before/after/probe.json` 记录的是 2.13.1.1
  （`30eb93c6…`），那是本轮取证时的状态，保留原样；新 exe 的 sha256 与备份见
  `runs/p212-pcl2-e2e/launcher-update.json`；
- 桌面快捷方式当时仍指向死路径——**p212 已重建**，并验证"有效快捷方式能被解析且 notes 为空"；
