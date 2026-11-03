# p242 — 发版一条命令：门禁 + 打包 + 干净宿主 + 发布包 UI 点击

日期：2026-11-03。p240 做到“门禁 + 打包”，p241 加了“干净宿主验收”，本回合把最后一段
**发布包网页 UI 验收（p227）** 也接进 `release_check.py`，发版流程不再需要手工步骤。

## 改动

- `runs/p227-shipped-launcher-pcl/drive.py` 参数化：`P227_ZIP` / `P227_OUT` / `P227_PORT`
  环境变量，默认行为与历史记录一致；
- `tools/release_check.py` 新增 `--ui-accept`：`--build <label> --ui-accept` 时，打包后用
  `P227_ZIP=<那个 zip>` 起发布包本身，CDP 驱动网页选 `1.20.6 + 原版 + 安装到 PCL2`，点按钮，
  等「已装进 PCL2」文案；端口用 8773 避免和开发服务冲突。

## 实测（test-0.5.12，测试标签，产物已删）

```text
== hash manifest            rc 0  ok=1702 mismatch=0 missing=0
== coverage                 rc 0  327/327 OK
== evidence gate            rc 0  passed
== portable build           rc 0  11,976,725 B
== clean-host acceptance    rc 0  8/8
== packaged UI acceptance   rc 0  msg="已装进 PCL2：…\\.minecraft —— 打开 PCL 的版本列表即可看到", button="安装到 PCL"
release_check: PASS
```

证据：`result.json`（整条流程）、`packaged-result.json` / `packaged-after-import.png`
（发布包里的 UI 实际点击结果）。

## 边界

- UI 验收依赖本机 Edge + 真实 `%APPDATA%`（要检测 PCL 目录）；换机器要确认 Edge 路径；
- 测试标签不是正式版本；正式发版用真实版本号；
- 干净宿主仍是“同机不同环境”。

## 复现

```text
py -3.12 tools/release_check.py --build test-0.5.12 --accept --ui-accept
```
