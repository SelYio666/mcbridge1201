# p236 — 负向验证：CI 的清单守卫不是摆设

日期：2026-11-03。目的：证明上一轮加的两道 CI 检查真的能拦住 ZCode 那次的问题
（`7e290e0` 改了 3 份文档却没刷新 `runs/SHA256SUMS.txt`，CI 当时仍是绿的）。

## 做法（一次性 clone，不推送）

`run.py` 在 `work/tmp/p236-neg` 里：

1. `git clone` 本仓库；
2. 往 `docs/remaining-work.md` 追加一行，**故意不刷新**清单，提交；
3. 跑 `tools/check_hashes.py`——期望失败；
4. 跑 `tools/check_manifest_coverage.py`——它是另一种检查，期望仍然通过；
5. 跑 `tools/hash_evidence.py` 刷新清单，再跑 `check_hashes`——期望恢复通过。

## 结果 3/3（`result.json`）

| 场景 | 结果 |
|---|---|
| 过期清单 | `ok=1678 mismatch=1 missing=0`，**rc=1**（会被 CI 挂红） |
| 覆盖率守卫 | `coverage OK`，rc=0（证明两道检查互补，不是重复） |
| 刷新清单后 | `ok=1679 mismatch=0 missing=0`，rc=0 |

## 边界

- 在**本地 clone** 里做，不推送到远端、不产生垃圾提交；
- `work/` 已 gitignore，clone 用完可直接删；
- CI 跑的就是这两条命令，所以本地结果可以代表 CI 行为。

## 复现

```text
py -3.12 runs/p236-ci-guard-negative/run.py
```
