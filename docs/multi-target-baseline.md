# 多目标基线与目标身份（阶段 A）

本文件记录路线计划 `MCBridge-多版本兼容规划-2026-11-03` 里 **阶段 A** 的落地结果：
A01（冻结 1.21.1 基线）与 A02（`TargetProfile` 与计划身份）。

范围声明：本阶段**没有**新增任何 Minecraft 目标版本，**没有**重新运行游戏侧契约，
**没有**修改 1.21.1 的转换行为。新增的是「把现有 1.21.1 路线固定成可核对的身份」和
「让错误的目标/命名空间/依赖在转换前就失败」这两件事。

## 1. A01：基线冻结

产物：[`manifests/baseline.lock.json`](../manifests/baseline.lock.json)，
由 [`tools/freeze_baseline.py`](../tools/freeze_baseline.py) 生成。

它把 1.20.1 → Fabric 1.21.1 的转换固定成一份按 SHA-256 记录的契约：

| 分区 | 内容 | 为什么需要 |
|---|---|---|
| `git` | commit、分支、已修改/未跟踪文件 | 说明冻结发生在什么树上；`--check` **不比对**这一节 |
| `environment` | 引用的环境锁及其哈希，以及 1.20.1/1.21.1 的 client jar / mappings / loader / API 哈希 | 目标索引换一个字节，成员查找结果就可能不同 |
| `inputs.rules` | `rules/fabric-1.21.1/` 每个文件的哈希 + 包级哈希 | 规则包才是转换逻辑本身 |
| `inputs.sources` | `java/src/{main,bridge,bridge-shim,mixin,test}` 的 `.java` 哈希 | 桥与转换器源码就是产物的另一半 |
| `inputs.tools` | 门禁脚本哈希（含 `freeze_baseline.py` 自身） | 门禁换了，结果不可比 |
| `inputs.manifests` | environment / upstream / corpus 三个锁 | 上游引擎与语料也会漂移 |
| `targetProfiles` | `targets/*.json` 的身份字段与哈希 | 见第 2 节 |
| `evidence` | `profiles/` 每个制品的 `status` 与契约通过/待办计数 | 支持状态是逐制品、带范围的 |
| `degradations` | 规则包里声明的 `mixinStrips` | 降级必须显式，不能是静默成功 |
| `historical` | `progress.md` / `baseline.md` / `handoff*.md` 的哈希与处置策略 | 历史结论不因本轮复核而改写 |

### 复查方式

```powershell
python tools/freeze_baseline.py --check
python tools/freeze_baseline.py --check --run-gates --json work/tmp/baseline-drift.json
```

`--check` 把当前树重新算一遍，与冻结值逐叶子比较，输出 `DRIFT <路径>: 旧值 -> 新值`：

- 退出码 `0` = 输入未变；`1` = 有漂移（或 `--run-gates` 失败）；`2` = 用法/环境问题。
- 比对**不含** `git`、`generatedAt`、`gates` 三节：工作区领先于它冻结时所在的 commit 是常态，
  那不是契约移动。**只有 `inputs.*`、`environment`、`targetProfiles`、`evidence`、
  `degradations` 变化才算基线移动。**
- 每次有意改动规则、桥源码或目标 profile 后，重新生成一次锁，并在提交信息里写清
  「基线移动的原因」，否则 `--check` 会一直报漂移。

### 历史与当前分开

`docs/progress.md`、`docs/baseline.md`、`docs/handoff.md`、`docs/handover-zcode.md`
是追加式历史记录。**本轮没有重新判定它们早期的结论**：旧轮次的说法仍然是旧轮次的说法。
「当前契约」以 `docs/FINAL-STATUS.md` 的最新一节、`profiles/` 与 `manifests/baseline.lock.json` 为准。

## 2. A02：TargetProfile

产物：[`targets/fabric-1.21.1.json`](../targets/fabric-1.21.1.json) 与
[`TargetProfile.java`](../java/src/main/java/top/mcbridge1201/profile/TargetProfile.java)。

`TargetProfile` 是**配置身份**，不是支持声明。它回答「这次转换用的是哪个精确目标」，
`profiles/*.json` 回答「这个制品到底过没过契约」。

### 记录的内容

```text
source    : MC、loader、namespace、Java、输入 class major（原始 jar 哈希逐制品记在 profiles/）
target    : id、MC、loader 构建、Fabric API、javaMajor、classMajorMax、namespace、映射策略
indices   : client jar / intermediary 映射 / loader / API / 桥编译库，各带 SHA-256
pipeline  : 上游引擎 commit、ruleOrder（权威顺序）、bridgeAbi、声明能力、输出与缓存目录
resources : dataVersion、资源包格式、已声明的转换能力
verification: fixture 版本、已测范围、已知缺口
```

### 校验命令

```powershell
# 只校验，不产出 jar：便宜、可在 CI 里跑
mcbridge1201 profile-check --profile targets/fabric-1.21.1.json --rules-from-profile --root .

# 转换时带上门禁；失败则不写任何 jar
mcbridge1201 patch --profile targets/fabric-1.21.1.json --rules-from-profile `
  --in <converted.jar> --out <patched.jar> --bridge-dir work/bridges
```

`--rules-from-profile` 从 `pipeline.ruleOrder` 取规则文件与顺序，避免不同调用方用不同
glob 顺序喂同一批规则。旧入口保持不变：`patch --in --out --rules ...` 不传 `--profile`
时行为与本阶段之前完全一致。

### 拒绝条件

`profile-check` 与 `patch --profile` 共用同一套检查，错误即退出码 `3`（`patch` 为 `2`），
且 `patch` 在任何 jar 落盘前停止：

| code | 拒绝理由 |
|---|---|
| `rules.target-mismatch` | 规则文件声明的 `target` 与 profile 不同：另一个目标的成员改写没理由在本目标成立 |
| `rules.namespace-mismatch` | 规则里的 `net/minecraft/*` 引用写成了另一个命名空间（intermediary ↔ official） |
| `indices.missing` / `indices.hash-mismatch` | 目标索引缺失，或字节与冻结哈希不符：换一份 jar/mapping 会静默改变所有成员查找 |
| `indices.no-hash` | 索引没有声明哈希：这样的转换下个月无法复现 |
| `bridge.class-version` | 桥 class 的 major 高于 `target.classMajorMax`：目标运行时会拒绝加载 |
| `pipeline.bridge-abi` | 规则包面向的桥 ABI 与本构建不同：必须重新验证整套规则，不能沿用 |
| `pipeline.rule-order-empty` | 没有权威规则顺序：同一成员被多条规则命中时结果不可复现 |
| `rules.order-mismatch` | 传参顺序与 `ruleOrder` 相反：会改变哪条规则先命中 |
| `rules.metadata-missing` | 转换规则缺 `capability`/`risk`/`evidence`：无声明的能力等于猜测 |
| `rules.strip-no-reason` | 移除 mixin 却没写理由：静默降级与「把崩溃藏起来」无法区分 |
| `rules.id-missing` | 规则没有 id：无法在报告里点名、无法 `--require-hit`、无法降级 |
| `target.class-major-inconsistent` | `classMajorMax` 与 `javaMajor` 不符（如 Java 21 却声明 61） |

警告（不阻断，但会写进报告）：`rules.duplicate-id`（跨规则文件复用 id，命中计数合并）、
`rules.not-in-profile`（规则不在 `ruleOrder` 中，本次不可复现）、
`indices.unpinned-override`、`source.newer-than-target`、`target.id-convention`。

### 负例回归

[`TargetProfileValidationTest`](../java/src/test/java/top/mcbridge1201/TargetProfileValidationTest.java)
用 16 个用例覆盖上表：错目标、错命名空间、索引缺失、索引被替换、桥 class 版本过高、
规则顺序颠倒、规则缺能力声明、空规则顺序、桥 ABI 不符、class major 与 Java 不符，
以及两个正例——**真实**的 `targets/fabric-1.21.1.json` 必须接受它自己的规则包。

```powershell
$env:JAVA_HOME = "<jdk21>"
& <gradle> -p java --offline test --tests "top.mcbridge1201.TargetProfileValidationTest"
```

## 3. 本阶段没有做的事

- 没有新增目标：`targets/` 只有 `fabric-1.21.1.json`；`refusesTargets` 明确列出未接入的目标，
  1.20.4 探针属于 A06，本轮未做。
- 没有按目标隔离构建输出与缓存（A03）与缓存键失效（A04）。`pipeline.output` 只是记录了
  拟用的目录，`patch` 尚不强制写入那里——不要把它当作已经隔离。
- 没有重建桥的编译矩阵（Java 17/21/25 三档）：`build_bridges.py` 仍使用调用方 JDK，
  只新增了「目标侧 class major 检查」这一道防线。
- 没有重新执行任何游戏侧契约；`profiles/` 里的状态来自冻结之前的轮次。

## 4. 现状与缺口

`manifests/baseline.lock.json` 生成时的状态以文件内 `git` 与 `evidence` 两节为准。
已知未完成项（需要第二台机器或真实客户端）与之前轮次一致，见
[remaining-work.md](remaining-work.md) 与 [limitations.md](limitations.md)：
真实跨机多人、进世界后的玩法/渲染/多人、以及把转换后模组带进世界的验证仍为 pending。
