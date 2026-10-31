# p221 — 干净 clone 门禁（2026-10-31）

目的：确认当前仓库不是“只在作者机上绿”。用一个全新的 `git clone` 跑哈希、构建、单测和统一门禁。

## 环境与命令

```text
git clone --no-hardlinks <repo> work/tmp/clone-check
cd work/tmp/clone-check
python tools/check_hashes.py
gradle -p java installDist
gradle -p java test
python tools/verify_evidence.py
```

clone 的 HEAD：`6a3f953`（`docs: refresh README status to v0.5.8 / 2026-10-31`）。

## 结果

| 检查 | 结果 | 证据 |
|---|---|---|
| 仓库内 jar | **0 个** | `Get-ChildItem -Recurse -Filter *.jar` 计数 |
| `check_hashes` | **ok=1573 / mismatch=0 / missing=0** | `check-hashes.txt` |
| Java 单测 | **32 / 0 failures** | `gradle-test.txt` |
| `verify_evidence` | **passed** | `clone-verify.json` |
| 回归套件 | **460/460**，3 项 skip | `review-suite.txt` |

### clone 里 skip 的 3 项（都依赖未入库的本地产物）

- `ISSUE-02`：需要已经转换好的样例 jar（`work/` 被 gitignore）；
- `p205 build_command`：同上，需要本地构建产物；
- `p210 shipped jar hash`：需要先跑 `runs/p210-cloth-config/build.py` 生成 jar。

作者机上同一棵树跑出 **467/467**；差的 7 项就是这些本地产物相关检查。clone 的
`verify_evidence` 把这些记为 skip 而不是假绿。

## 结论

- 新 clone 可以独立校验哈希清单（1573 个路径全部存在且匹配）；
- 构建与单测在 clone 里可通过；
- `verify_evidence` 在 clone 里 passed，并对缺本地产物的检查如实 skip。

## 复现

按上面的命令即可；需要 Java 21 与 Gradle 9.8.1（项目本身不带 wrapper）。
