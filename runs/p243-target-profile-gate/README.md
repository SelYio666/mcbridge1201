# p243 — 目标门禁：错的就拦住

日期：2026-11-03。对应路线计划阶段 A 的 **A01 / A02**。本回合不新增 Minecraft 目标版本，
只做两件事：把现有 1.21.1 路线冻结成可核对的身份，并让「错目标 / 错命名空间 / 错依赖」
在写 jar 之前就失败。

## 改动

| 文件 | 作用 |
|---|---|
| `targets/fabric-1.21.1.json` | 目标身份：来源/目标命名空间与 Java、client jar 与 intermediary 映射的 SHA-256、引擎 commit、权威规则顺序、桥 ABI、资源 schema、已测范围与已知缺口 |
| `java/src/main/java/top/mcbridge1201/profile/TargetProfile.java` | 加载与校验；错误码稳定，供测试与报告断言 |
| `java/src/main/java/top/mcbridge1201/Main.java` | 新增 `profile-check`；`patch` 新增 `--profile` / `--rules-from-profile` / `--root`（不传时旧行为不变） |
| `tools/freeze_baseline.py` | 生成 `manifests/baseline.lock.json`，并支持 `--check` 复算漂移 |
| `tools/run_target_gate.py` | 本目录证据：1 个正例 + 6 个负例 + 1 个「patch 不写产物」用例 |
| `docs/multi-target-baseline.md` | 说明冻结了什么、拒绝条件表、复查命令、本轮没做什么 |

## 证据怎么产生

```powershell
$env:JAVA_HOME = "<jdk21>"
& <gradle> -p java --offline installDist
python tools\run_target_gate.py            # 写本目录 result.json + 每个用例的 problems
python tools\freeze_baseline.py --run-gates  # 写 manifests/baseline.lock.json（含门禁结果）
python tools\freeze_baseline.py --check      # 之后任何时候复算：0=未漂移，1=漂移
```

## 实测（`result.json`）

8 个用例全部符合声明（正例 rc=0，负例 rc=3 且报出预期错误码，`patch` 拒绝时 rc=2 且
输出 jar 不存在）：

| 用例 | 期望 | 实际 |
|---|---|---|
| `positive-frozen-profile` | rc 0，无 target/namespace/hash/order 错误 | rc 0，29 个规则文件、4 条跨文件重复 id 警告 |
| `wrong-target` | rc 3，`rules.target-mismatch` | 同 |
| `wrong-namespace` | rc 3，`rules.namespace-mismatch` | 同 |
| `index-hash` | rc 3，`indices.hash-mismatch` | 同 |
| `index-missing` | rc 3，`indices.missing` | 同 |
| `bridge-class-version` | rc 3，`bridge.class-version` | 同（class major 69 > 目标 65） |
| `rule-order` | rc 3，`rules.order-mismatch` | 同 |
| `patch-refuses-before-writing` | rc 2，且输出 jar 不存在 | 同 |

单元测试另有 16 个用例（`TargetProfileValidationTest`），覆盖上表之外的结构错误、
class major 与 Java 级别不一致、桥 ABI 不符、规则缺 `capability` 等。

## 这次没有证明的事

- **没有转换任何真实模组，也没有启动游戏。** 全部用例是 dry run；`profiles/` 里
  `passed_within_scope` / `booted_within_scope` 的状态来自本回合之前的轮次，未重跑。
- **没有新增目标。** `targets/` 只有 1.21.1；1.20.4 探针（A06）未做。
- **没有做输出/缓存隔离（A03）与缓存键失效（A04）。** `pipeline.output` 只记录拟用目录，
  `patch` 尚不强制写入那里，不可当作已隔离。
- **没有建立 Java 17/21/25 的桥编译矩阵。** `build_bridges.py` 仍用调用方 JDK；
  新增的只是目标侧 class major 检查这一道防线。

## 已知遗留

- 规则包里 4 个 id 跨文件重复（`identifier.ctor1/2.to-factory`、`lithium.varint.size`、
  `trashslot.balm.send-to-server`），`patch` 的按 id 命中计数会合并；已作为警告暴露，未改名。
- `profiles/*.json` 里 `engine.artifactSha256` 与产物哈希同值的记录来自旧轮次，本轮没有独立复核引擎工件；
  `targets/fabric-1.21.1.json` 因此把该字段留空，不用可疑值冒充。
