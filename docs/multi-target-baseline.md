# 多目标基线与目标身份（阶段 A）

本文件记录路线计划 `MCBridge-多版本兼容规划-2026-11-03` 里 **阶段 A** 的落地结果：
A01（冻结 1.21.1 基线）、A02（`TargetProfile` 与计划身份）、A03（按目标隔离桥构建）、
A04（转换缓存键与陈旧桥防护）。

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

## 3. A03：按目标隔离的桥构建

`tools/build_bridges.py` 增加 `--profile` 目标模式；旧的 `--stub/--lib/--out` 入口保留且行为不变。

```powershell
python tools\build_bridges.py --profile targets\fabric-1.21.1.json
```

目标模式下 stub、`--release`、classpath 与输出目录全部来自 profile：

| 来自 profile | 字段 |
|---|---|
| 编译用的 stub | `indices.bridgeStub`（intermediary 化的客户端 jar，带 SHA-256） |
| classpath | `indices.libs`（12 项：gson、datafixerupper、netty×3、fastutil、brigadier、loader、fabric 三个模块、Balm） |
| `javac --release` | `target.javaMajor` |
| 输出目录 | `pipeline.output.bridgeClasses` → `work/targets/fabric-1.21.1/bridges` |

编译前后的拒绝条件（全部实测 rc 2）：目标 Java 高于本地 javac、stub 缺失或哈希不符、
stub 的 class major 高于目标、profile 的桥 ABI 与本构建不同、`classMajorMax` 与 `javaMajor`
不一致、产物 class major 与目标不符。正例：34 个桥源 → 41 个 class，全部 major 65。

**输出隔离的含义**：不同目标不会共用 `work/bridges`。但 `indices.libs` 指向本机
`work/instances/…/libraries` 下的服务端库，是**被 pin 的本地闭包**而非可下载工件；
干净机器必须准备同版本库，否则 `profile-check` 会报 `indices.missing`。

## 4. A04：转换缓存键与陈旧桥防护

`tools/conversion_cache.py` 把"这次转换的输入"命名成一个键，并在未命中时说出**是哪个输入变了**：

```powershell
python tools\conversion_cache.py key    --profile targets\fabric-1.21.1.json --source <原始jar> \
    --bridge-dir work\targets\fabric-1.21.1\bridges --rules-from-profile
python tools\conversion_cache.py store  ... --artifact <转换产物>
python tools\conversion_cache.py lookup ...
```

| 键组件 | 防的是什么 |
|---|---|
| `bridgeAbi` | 规则包面向旧桥 ABI 时仍命中旧缓存 |
| `profile`（路径+哈希+目标身份） | 换目标却复用另一目标的产物 |
| `pipeline.engine.commit` | 上游引擎换了分段语义 |
| `source.sha256` | 同名的不同构建被当成同一来源 |
| `indices.*`（stub/client/mappings/loader/api/libs） | 换索引或换 mapping |
| `rules`（按 `ruleOrder` 顺序） | 换规则或换顺序 |
| `bridges.*`（每个 class 的哈希） | **陈旧桥**：桥重编了但产物还是旧的 |
| `config` | 调用方追加的 patch 选项 |

`lookup` 命中 rc 0；未命中 rc 1，并与"同一源 jar 的最近一次记录"逐组件比对，输出
`bridges.sha256: f1778096… -> 407e87e6…` 这类原因。**`patch` 尚未读写缓存**——本轮交付的是
键与记录的契约，接进 `patch` 是后续工作，不宣称"转换已带缓存"。

## 5. A05：来源端固定 fixture

真实样本都是别人的制品，改转换器时无法确定输入形态。`fixtures/source-fabric-1.20.1/` 是自建的
1.20.1 Fabric 源，**编译一次、按 hash 固定**，每个目标转换同一份字节：

```powershell
python tools\build_source_fixture.py
```

| 覆盖 | 载体 |
|---|---|
| 注册 + `new Identifier(ns,path)` 构造器 | `FixtureRegistry` |
| ItemStack NBT 读取（1.20.5 的 `WrapperLookup` 断裂点） | `FixtureData` |
| Screen 渲染钩子（1.21.6 的提取/绘制拆分） | `FixtureScreen` |
| `@Inject` 到真实 intermediary 成员的四参回调 | `mixin/FixtureMixin` |
| lambda／方法引用／字符串拼接／stream（indy） | `FixtureIndy` |

产物 6 个 class 全部 major 61，jar 由 `fixtures/source-fabric-1.20.1/manifest.json` 按 SHA-256 定位，
`.gitignore` 只让源码与 manifest 入库。对 1.20.1 自身索引静态自检 `missingClass=0 /
missingMember=0 / descMismatch=0`。

**运行基线 pending**：本机没有 1.20.1 Fabric 实例，"来源原生环境通过"这条没有做。

## 6. A06：1.20.4 架构探针

`targets/fabric-1.20.4.json`（`status: probe_only`）把 1.20.4 环境 pin 下来：client jar、
intermediary、由本项目 `remap-jar` 生成的 stub（7787 class，全部 major 61）、loader 0.15.11、
fabric api 0.97.3。它**故意没有规则包**，所以门禁拒绝用它转换任何东西。

三条实测结论：

1. **目标切换有防线**：`profile-check` 报 `pipeline.rule-order-empty`；把 1.21.1 规则指过去再叠加
   `rules.target-mismatch`。不是靠别名蒙混。
2. **静态断裂为 0，但不等于能跑**：fixture 对 1.20.4 索引 `missingClass=0 / missingMember=0 /
   descMismatch=0`——intermediary 名在这段区间对 fixture 覆盖的 API 稳定。1.20.4 的真实风险是
   1.20.2 引入的 configuration 网络阶段、注册时机与渲染管线，**字节码引用层面看不出来**。
   因此本轮只记录"静态无断裂"。
3. **桥是目标资产**：`build_bridges.py --profile targets/fabric-1.20.4.json` 产出 103 个编译错误、
   0 个 class。1.21.1 的桥源码不能复用给 1.20.4，每个目标需要自己的桥。

**未验证**：没有启动 1.20.4 客户端/服务端，构造器/注册/容器/收发包/GUI 五项只做到静态定位。

## 7. 本阶段没有做的事

- 没有把任何目标标记为"已支持"：`targets/` 里 1.20.4 只有 `probe_only`，且没有规则包。
- 没有跑 Java 25 的真实桥编译：`--release` 与 class major 校验已就位，但 25 档被
  "javac 版本不足"挡住——那是**拒绝路径**，不是支持。
- 没有把缓存接进 `patch`（见 §4）。
- 没有重新执行任何游戏侧契约；`profiles/` 里的状态来自冻结之前的轮次。
- 没有 1.20.1 / 1.20.4 的运行时基线，也没有 configuration 阶段的任何验证。

## 8. 现状与缺口

`manifests/baseline.lock.json` 生成时的状态以文件内 `git` 与 `evidence` 两节为准。
已知未完成项（需要第二台机器或真实客户端）与之前轮次一致，见
[remaining-work.md](remaining-work.md) 与 [limitations.md](limitations.md)：
真实跨机多人、进世界后的玩法/渲染/多人、以及把转换后模组带进世界的验证仍为 pending。
