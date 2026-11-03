# p245 — 按目标隔离的桥构建与转换缓存键

日期：2026-11-03。对应路线计划阶段 A 的 **A03**（按目标隔离桥源码和输出）与
**A04**（转换缓存键与陈旧桥防护）。本回合不转换任何模组、不启动游戏：验的是构建与缓存契约。

## 改动

| 文件 | 作用 |
|---|---|
| `tools/build_bridges.py` | 新增 `--profile` 目标模式：stub、`--release`、classpath、输出目录全部来自 profile；旧 `--stub/--lib/--out` 入口保留且行为不变 |
| `targets/fabric-1.21.1.json` | 新增 `indices.bridgeStub`（桥编译用的 intermediary stub 及其 SHA-256）与 12 项 `indices.libs`（桥编译的完整 classpath 闭包，逐项带 hash） |
| `tools/conversion_cache.py` | 新增：`key` / `store` / `lookup` 三个子命令，缓存键覆盖 ABI、profile、源 jar、索引、规则顺序、桥字节、引擎提交与额外配置 |
| `tools/run_isolation_cache.py` | 本目录证据：13 个用例 |
| `docs/multi-target-baseline.md` | 补 A03/A04 两节并改写"本阶段没有做的事" |

## A03：目标模式与拒绝条件

```powershell
$env:JAVA_HOME = "<jdk21>"
python tools\build_bridges.py --profile targets\fabric-1.21.1.json
```

输出落在 `pipeline.output.bridgeClasses`（本目标为 `work/targets/fabric-1.21.1/bridges`），
与旧默认目录 `work/bridges` 不同；`--out` 可显式覆盖并打印提示。目标模式在编译前后各设一道闸：

| 情况 | 行为 | 实测 |
|---|---|---|
| 目标 Java 高于本地 javac | 拒绝：`needs Java 25 but javac is 21` | rc 2 |
| stub 缺失或字节与 profile 不符 | 拒绝：`has sha256 2cbf8e4a… but the profile froze 000000000000` | rc 2 |
| stub 的 class major 高于目标 | 拒绝：`carries class major 65, above the target's 61`（`javac --release 17` 不会读更新的 classpath class） | rc 2 |
| profile 的桥 ABI 与本构建不同 | 拒绝：`bridge ABI 'mcbridge-bridge-0' but this build embeds 'mcbridge-bridge-1'` | rc 2 |
| `classMajorMax` 与 `javaMajor` 不一致 | 拒绝（推导值不符） | — |
| 编译产物 class major 与目标不符 | 拒绝：逐 class 检查后报 `not at major N` | — |

正例实测：34 个桥源编译出 **41 个 class，全部 major 65**，同时嵌入两个 fabric legacy shim。
旧入口 `--stub/--lib/--out` 以 12 项 classpath 重跑同样 rc 0——**旧目标不退化**。

## A04：缓存键与"为什么不命中"

```powershell
python tools\conversion_cache.py key    --profile targets\fabric-1.21.1.json --source <原始jar> --bridge-dir work\targets\fabric-1.21.1\bridges --rules-from-profile
python tools\conversion_cache.py store  ... --artifact <转换产物>
python tools\conversion_cache.py lookup ...          # 命中 rc 0，未命中 rc 1 并列出变化的组件
```

键 = SHA-256(规范化 JSON)，组件包括：`bridgeAbi`、profile（路径/哈希/目标身份）、
`pipeline.engine`、源 jar 字节、profile 里每个索引的哈希、**按顺序**的规则文件哈希、
桥目录里每个 class 的哈希、调用方追加的 `--config key=value`。

实测：

| 用例 | 结果 |
|---|---|
| 同输入两次 | 键相同 `1c21a387349aa28a…`（`store` 后再 `lookup` 为 HIT） |
| 换目标（profile 副本改成 1.21.4） | MISS，原因逐项列出：`profile.minecraft / profile.path / profile.sha256 / profile.targetId` |
| 换桥（复制桥目录后改一个 class 字节） | MISS，原因：`bridges.sha256: f1778096b1ab8d38 → 407e87e65f9b309c` |
| 换规则包（只传 `container.json`） | 键变为 `929993c90733b90c…` |
| jar 内嵌同名不同字节的桥 | `check_bridge_consistency.py` 报 `MISMATCH top/mcbridge1201/bridge/AppleSkinFoodBridge.class`，rc 1 |

最后一条是 A04 要求的"同目标桥冲突被发现"：现有 `check_bridge_consistency.py` 已经能做这件事，
本轮用合成 jar 证明它确实会失败，而不是假定它有效。

## 这次没有证明的事

- 没有真实转换任何模组：`conversion_cache.py` 是键与记录的契约，`patch` 本身尚未读写缓存。
  **接进 `patch` 属于后续工作**，本轮不宣称"转换已带缓存"。
- 没有跑 Java 17/25 的真实桥编译矩阵：`--release` 与 class major 校验已就位，但唯一被验证的
  目标是 21；17 档被"stub 版本更高"挡住，25 档被"javac 版本不足"挡住——这两条是拒绝路径，不是支持。
- `indices.libs` 指向 `work/instances/…/libraries`（本机服务端库），是**被 pin 的本地闭包**，
  不是可下载工件；干净机器需要先准备同版本服务端库，否则 `profile-check` 会报 `indices.missing`。
- 没有重新执行任何游戏侧契约。
