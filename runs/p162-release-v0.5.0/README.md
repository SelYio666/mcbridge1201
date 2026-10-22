# p162 — v0.5.0 发布准备

日期：2026-10-23。把 ImmediatelyFast 移植与专用服务器/mrpack 的证据整理成 v0.5.0 release。

## 资产

- `dist/mcbridge-launcher-0.5.0.zip`，11,960,114 bytes；
- SHA-256 `aa881f0619430374e2631a995d79065403ef69d5785498b249ae47d70c7b7258`；
- `python tools/test_portable.py --zip dist/mcbridge-launcher-0.5.0.zip --root work/launcher-e2e
  --version neoforge-21.1.264` → **RESULT: OK**（deps=True、verify=True、/api/status=True、/guide=True）。

## 发布过程中修的真实 bug

第一次打出的 0.5.0 便携包 `verify` 失败：

```text
ModuleNotFoundError: No module named 'fetch'
```

原因：便携包使用 CPython 嵌入式发行版，`python._pth` 把 `sys.path` 固定为内置路径，
**直接运行 `mclaunch.py` 时不会把脚本目录加进去**；而 `mclaunch.py` 顶部 `import fetch`。

修复：`mclaunch.py` 在 import fetch 之前执行

```python
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
```

重新打包后 `test_portable` 全绿。回归测试已加入 `tools/test_review_fixes.py`（73/73）。

## 门禁

- `test_review_fixes` 73/73；`check_hashes` 892/892；`verify_evidence` passed；
- Java 25/25。

## Release

- tag `v0.5.0`；
- GitHub Release 附件：`mcbridge-launcher-0.5.0.zip`；
- 发布说明：`release-notes.md`。
