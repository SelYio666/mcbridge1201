# p195 — v0.5.6 交付验证：portable 干净根目录 + panel UI smoke

日期：2026-10-26
结论：v0.5.6 portable 在**新的临时根目录**完成 deps/server API 验证；同源 `tools/pcl_panel.py` 面板能打开、加载 103 个正式版、PCL 目录默认值正常。完整 PCL2 点击安装本轮**未完成**：本机 PCL2 路径不存在，panel 资产下载只到 3.3/12.36 MB。

## Portable（v0.5.6）

```text
python tools/test_portable.py --zip dist/mcbridge-launcher-0.5.6.zip \
    --root work/tmp/p195-portable --version 1.21.1
package: dist/mcbridge-launcher-0.5.6.zip 11960113 bytes
deps: True
server /api/status: True  /guide: True
RESULT: OK
```

- 使用**新的** `work/tmp/p195-portable`，不是 `work/launcher-e2e` 的已有缓存；
- embedded Python、依赖解压、服务器 `/api/status` 与 `/guide` 都通过（`portable-test.log`）；
- 未在另一台干净主机/完全断网环境验证，见边界。

## Panel UI smoke

- 用同源 `python tools/pcl_panel.py` 打开面板（panel 资产下载不完整，见边界）；
- 截图 `panel-smoke.png`：版本下拉显示 `26.3`，类型 `正式版`，日志 `已加载 103 个版本（正式版）`；PCL 目录默认 `C:\Users\27682\AppData\Roaming\.minecraft`；
- 面板进程正常启动/退出（stdout/stderr 均无异常）；
- **未完成**：真实点击“安装到 PCL”、进度条、完成打开目录、PCL2 版本列表刷新——本机没有 PCL2。

## 边界（如实）

- **PCL2 不存在**：p137 记录的 `D:\我的世界\.minecraft\涟漪专用启动器\Plain Craft Launcher 2.exe` 在本机 `Test-Path` 为 False；因此不能宣称 panel 真实安装 E2E 通过。
- **panel 资产不完整**：`mcbridge-pcl-panel.zip` 只下载到 3,361,813 / 12,361,982 bytes（`gh release download` 挂起，已终止）；用源码面板做 UI smoke，资产本身未完整解压/运行。
- **干净/离线主机**：portable 用的是本机新根目录，不是另一台机器/完全断网；p195 的“干净机器”边界仍开。
- 无新 release：v0.5.6 保持；p194/p195 都是验证轮，无 mod 改动。

## 证据

`runs/p195-delivery-validation/`：`result.json`、`portable-test.log`、`panel-smoke.png`、`panel-out.log`、`panel-err.log`、`README.md`。

## 后续

- 在装有 PCL2 的机器上重跑 panel 真实点击（版本选择 → 安装 → 进度 → PCL2 出现版本）；
- 在另一台干净/离线机器上重跑 portable；
- v0.5.7 视 p193–p195 结果与用户确认（目前无用户可见修复，可保持 v0.5.6）。
