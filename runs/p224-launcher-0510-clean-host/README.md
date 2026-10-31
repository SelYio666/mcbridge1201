# p224 — v0.5.10 启动器包的干净环境验收

日期：2026-10-31。对象：`dist/mcbridge-launcher-0.5.10.zip`（v0.5.10 发布资产，含网页启动器新功能）。
方法：复用 p208 的 `runs/p208-cross-platform/run_clean_host.py`。

## 环境

- `PATH` 只剩 `C:\Windows\System32;C:\Windows`（**没有系统 Python、没有 JDK**）；
- `HOME` / `USERPROFILE` / `APPDATA` / `LOCALAPPDATA` / `TEMP` 全部指向全新的空目录；
- 先证明 scrub 生效（`which python` / `which java` 都是 `None`），再用包内自带的解释器启动。

## 结果 8/8（`clean-host.json`）

| 检查 | 结果 |
|---|---|
| no_system_python / no_system_java | 通过 |
| bundled_python / interpreter_is_bundled | 通过（跑的是包内 `python\python.exe`） |
| hostile_pythonhome_ignored | 通过 |
| no_jars_shipped | 通过 |
| api_status / guide_page | 通过（HTTP 正常） |

包本身：230 个条目、**0 个 jar**、含 `launcher/web/*` 与 `tools/from_source_install.py`
（后者是 p223 修复的打包遗漏）。

## 顺手修的

`run_clean_host.py` 用 `sorted(glob(...))` 取“最新包”，字符串序把 `0.5.7` 排在 `0.5.10` 之后，
导致第一次跑的还是旧包。改成按版本号自然排序（`re.findall(r"\d+")`）后，确认选中的是 0.5.10。

## 边界

- 同机不同环境，不是另一台电脑；
- 仅 Windows；没有验证 `install_jvm_runtime` 的下载路径；
- 本验收覆盖的是“包能起来、接口可用”，不含游戏启动。

## 复现

```text
python runs/p208-cross-platform/run_clean_host.py --out clean-host-0510.json
```
