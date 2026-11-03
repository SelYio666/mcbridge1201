# p247 — 审计 ZCode 的基线冻结工具：真抓到了漂移

日期：2026-11-03。ZCode 提交的 TargetProfile / baseline 代码没人审过，本鱼跑它自己提供的入口做审计。

## 审计对象

- `tools/freeze_baseline.py --check`：把 1.20.1 → Fabric 1.21.1 的转换契约逐叶子复算，
  与 `manifests/baseline.lock.json` 比对，输出 `DRIFT <路径>: 旧 -> 新`；
- 锁定内容：29 个规则文件、65 个源码、目标 profile、证据状态与显式降级，全部按 SHA-256。

## 结果

1. **第一次 `--check` 就报漂移**：

```text
DRIFT historical.currentDocs[0].sha256: bfca7c28… -> 5ba846b9…
baseline DRIFTED (1 change(s))
rc=1
```

   漂移的正是本鱼刚更新过的 `docs/FINAL-STATUS.md`（锁会把几份“当前文档”按哈希钉住）。

2. 按设计重新冻结：`python tools/freeze_baseline.py`（写回 lock）→ 复检：

```text
baseline unchanged (0 change(s))
rc=0
```

3. 结构化结果见 `check-after.json`（`drift: []`）。

## 发现的问题（已顺手补上）

`freeze_baseline --check` **没有接进任何门禁**：CI 和 `release_check.py` 都不跑它。
也就是说，钉住的文档/规则被改动后，漂移可以一直不被发现（本鱼这次就是先改了文档才发现）。

已在 `tools/release_check.py` 的步骤里加入：

```text
("1.21.1 baseline lock has no drift", [python, "tools/freeze_baseline.py", "--check"])
```

发版时若基线漂移，检查会当场失败。

## 边界

- 本回合只做了审计 + 重冻 + 接门禁，没有改 `freeze_baseline.py` 的判定逻辑；
- 重冻是设计内的更新方式（改被钉住的文档后必须重冻），不是绕过检查；
- Java 单测在本鱼之前已跑过（ZCode 的 TargetProfile 测试通过）。
