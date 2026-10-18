# mcbridge1201（P0 研发仓库）

Minecraft Java 1.20.1 模组跨版本兼容平台的第一阶段工作区。来源固定为 **1.20.1**，首个精确目标是 **Fabric 1.21.1**，同时抽样分析 Forge 1.20.1。

本仓库当前交付 P0 的事实与证据，以及 P1 的第一段运行时结果：环境锁定、上游引擎锁定、10 份真实样本、**自研静态损伤分析器**、**body-preserving 重映射器**、CenturyBridge 真实转换产物，和第一次真实启动。它不宣称任何模组“已兼容”。

## 现状（2026-10-18）

| 项目 | 状态 | 证据 |
|---|---|---|
| 环境锁定（JDK 21 / Gradle 9.8.1 / 无 JDK 17） | 已记录 | [docs/baseline.md](docs/baseline.md) |
| Retromod / CenturyBridge 精确提交、许可、工件 | 已锁定 | `manifests/upstream.lock.json` |
| 10 份 1.20.1 样本（5 Fabric + 5 Forge） | 已下载并校验 sha512 | `manifests/corpus.json` |
| 静态损伤分析（Fabric 1.21.1） | 10/10 已跑通，ironchests 52/52 源索引确认 | `runs/p0-fabric-target/plan.json`、[static-matrix](docs/generated/static-matrix-fabric-1.21.1.md) |
| CenturyBridge 引擎构建 | 可编译（需本地 1 个缺失类的 stub） | [docs/engine-selection.md](docs/engine-selection.md) |
| CenturyBridge 真实转换 ironchests | 已完成，`ok_partial`（28 tombstone） | `work/cb/out/ironchests/report.md` |
| 自研重映射器（保留方法体） | 6148 类服务端 jar 可用，修复 4 类真实缺陷 | `java/.../remap/`、[docs/baseline.md](docs/baseline.md) §7.3 |
| 1.21.1 专用服务端 | **BOOTED**：`Done (4.803s)`，正常停止 | `runs/p1-server-baseline/` |
| 转换件运行时 | **BOOTED + 世界加载**：`Done (1.134s)`，42 个模组 | `runs/p3-server-accesswidener/` |
| 第一条转换规则 + 桥 | `ItemPredicate.ANY` → 空谓词；入口点通过 | `rules/fabric-1.21.1/container.json`、[rules/README.md](rules/README.md) |
| 常量池种类修正 | 123 处 Methodref→InterfaceMethodref + 3 个 method handle（含 JiJ） | `java/.../rules/JarPatcher.java` |
| 规则数 | 3 条（`ItemPredicate.ANY`、`fromJson`、`Codec.dispatch`）+ 常量池种类修正 | `rules/fabric-1.21.1/container.json` |
| 容器契约（服务端命令） | **通过**：放置 → 插入 5 钻石 → NBT `Items` → 重启读回 5 | `runs/p5-contract-*/` |
| 兼容档案 | ironchests @ Fabric 1.21.1，`status: degraded`（契约通过；fromJson 降级；缺客户端） | [profiles/ironchests-5.0.2-fabric__fabric-1.21.1.json](profiles/ironchests-5.0.2-fabric__fabric-1.21.1.json) |
| 支持矩阵 | 10 份样本的静态结果 + 运行时阶段（未运行 ≠ 通过） | [docs/support-matrix.md](docs/support-matrix.md) |
| 签名适配规则 | BlockEntity NBT 1 参 → 2 参（带 WrapperLookup），持久化恢复 | `rules/fabric-1.21.1/container.json` §signatureAdaptations |
| 第二样本 lithium | 转换并加载成功（131 配置项）；mixin 注入失败 → 显式降级 2 条；卡在 `class_14.method_59` 签名 | `runs/p6-lithium/`、`rules/fabric-1.21.1/lithium-degraded.json` |

## 复现

所有 Python 脚本只依赖标准库（本机 PowerShell/git 的 schannel TLS 不可用，Python 的 OpenSSL 可用）。

```powershell
# 1) 锁定上游提交与许可（GitHub API 限流，改用 atom feed + codeload）
python tools/lock_upstream.py

# 2) 下载 1.21.1/1.20.1 客户端 jar、intermediary 映射、Fabric API、Fabric Loader
python tools/fetch_target_env.py

# 3) 下载 10 份 1.20.1 样本（Modrinth，记录 sha256 与 sha512 校验）
python tools/fetch_corpus.py

# 4) 构建分析器（JDK 21 + Gradle 9.8.1）
$env:JAVA_HOME='...\.toolchain\jdk'
$env:GRADLE_USER_HOME='...\.toolchain\gradle-home'
cd java; gradle --no-daemon installDist; cd ..

# 5) 静态损伤分析
java\build\install\mcbridge1201\bin\mcbridge1201.bat analyze `
  --mods work/corpus `
  --client-jar work/target/client-1.21.1.jar --mappings work/target/intermediary-1.21.1-v2.jar `
  --source-client-jar work/target/client-1.20.1.jar --source-mappings work/target/intermediary-1.20.1-v2.jar `
  --source-api "work/target/fabric-api-0.92.12+1.20.1.jar" `
  --api "work/target/fabric-api-0.102.0+1.21.1.jar" --api work/target/fabric-loader-0.19.5.jar `
  --target 1.21.1 --target-loader fabric --out runs/p0-fabric-target/plan.json
```

CenturyBridge 转换见 [docs/engine-selection.md](docs/engine-selection.md) 的“真实尝试”一节；它需要本地编译上游引擎并生成 7 节分段。

## 目录

```text
docs/            基线、引擎选择、限制、ADR、生成报表
java/            自研分析器（Gradle，ASM + Gson）
manifests/       corpus / environment / upstream 三个锁文件
tools/           抓取、校验、服务端运行、报告脚本
runs/            证据输出（plan.json、服务端日志）
work/            本地工作集：游戏 jar、样本、上游源码、实例（不入库）
third-party/     上游许可证副本与 NOTICE
patches/         对上游缺件的显式本地补丁（带说明，不是上游代码）
```

## 边界

- `work/` 下的游戏 jar、模组 jar、转换产物**只在本机**，不随仓库分发；对外只应分发工具、规则与 hash 清单。
- 静态分析只到 `ANALYZED` 阶段。`CLEAN_STATIC` 不代表能启动，更不代表玩法通过。
- 第三方作者自报（Retromod 的 26.2 工件、CenturyBridge 的 1.21.1 案例）与本仓库独立结果分开记录。
