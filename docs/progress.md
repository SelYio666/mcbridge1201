# 进度交接

最后更新：2026-10-18 18:35（Asia/Shanghai）。下一轮从这里继续，不必重读方案全文。

## 本轮做了什么

1. 建立独立研发目录 `mcbridge1201/`（未改动用户已有项目、游戏实例和 `.minecraft`）。
2. 环境核查：JDK 21 / Gradle 9.8.1 / Git / Python 3.12 可用；**无 JDK 17**；PowerShell 与 git 的 HTTPS（schannel）不可用；`%TEMP%` 与工作区 `Files.isWritable` 异常。
3. 锁定上游：Retromod `e693278...`、CenturyBridge `cf4ebeba...`，均 MIT，许可证文本与快照 hash 入 `manifests/upstream.lock.json`。
4. 建立 10 份 1.20.1 样本（5 Fabric + 5 Forge），Modrinth sha512 与自算 sha256 双校验。
5. 实现并运行自研分析器 `mcbridge1201`（Gradle + ASM）：目标/源双索引、继承解析、命名空间区分、mixin 目标存在性、JSON 计划输出、Markdown 矩阵。3 个单元测试通过。
6. 实测 CenturyBridge：引擎编译（需本地补 `MixinCheck` 空实现）、生成 1.20.1→1.21.1 的 7 节分段、转换 ironchests（`ok_partial`，28 tombstone，55 条未记账引用）。
7. 尝试 Fabric 1.21.1 专用服务端启动，定位并记录环境阻塞（zipfs 只读判定）。
8. 产出 `docs/baseline.md`、`docs/engine-selection.md`、`docs/limitations.md`、生成矩阵、`runs/SHA256SUMS.txt`。

## 证据在哪里

| 证据 | 路径 |
|---|---|
| 环境探针 | `work/evidence/doctor.json` |
| 样本锁 | `manifests/corpus.json` |
| 上游锁 | `manifests/upstream.lock.json` |
| 目标环境锁 | `manifests/environment.lock.json` |
| 静态分析计划 | `runs/p0-fabric-target/plan.json` |
| 静态矩阵 | `docs/generated/static-matrix-fabric-1.21.1.md` |
| CenturyBridge 编译日志 | `work/evidence/cb-javac.log` |
| CenturyBridge 转换报告 | `work/cb/out/ironchests/report.md`、`full-audit.tsv` |
| 转换件 | `work/cb/out/ironchests/ironchests-5.0.2-fabric+1.21.1.jar` |
| 服务端失败日志 | `runs/p0-server-baseline/server.log`、`server-l016.log`、`server-outside.log` |
| 证据 hash 清单 | `runs/SHA256SUMS.txt` |

## 未解决（按优先级）

1. **服务端启动被环境阻塞**：`Files.isWritable` 在本会话恒 false → Fabric Loader 拒绝 remap。换 ASCII 路径无效；预 remap 会卡在 `EntrypointPatch`。需要在正常令牌的 Windows 会话复跑 `tools/run_server.py`。
2. **没有任何 BOOTED/WORLD_LOADED/CONTRACT_PASSED**：因此当前所有结论都只能写 `ANALYZED`/`TRANSFORMED`。
3. **Forge 成员级分析缺失**：需要 `mcp_config` joined.tsrg（SRG）+ 1.21.1 Mojang 映射 + NeoForge 1.21.1 索引。
4. **CenturyBridge `MixinCheck` 缺失**：上游该提交不含此文件，`build.sh` 的 mixin 门禁不可验证；我们只用 no-op 让 engine 编译。
5. **桥 jar 未构建**：`core/shims/1.21.1` 未编译，`shims-1.21.1.json` 未校验。
6. **Mixin 注入点级分析**未做（只看目标类存在）。
7. **BytecodeVerify** 未编译运行，转换件未做数据流校验。
8. 客户端/图形、多人同步、存档重启全部未测。

## 下一步精确命令

```powershell
# A. 在可写环境验证基线（先做这个，否则后面都是静态推断）
python tools/setup_server.py --instance work/instances/fabric-1.21.1-server
$env:JAVA_HOME='...\.toolchain\jdk'
python tools/run_server.py --instance work/instances/fabric-1.21.1-server `
  --log runs/p1-server-baseline/server.log --timeout 300

# B. 基线通过后，把转换件放进 mods/ 再跑一次，保存真实失败栈
Copy-Item work\cb\out\ironchests\ironchests-5.0.2-fabric+1.21.1.jar `
  work\instances\fabric-1.21.1-server\mods\
python tools/run_server.py --instance work/instances/fabric-1.21.1-server `
  --log runs/p1-server-converted-ironchests/server.log --timeout 300

# C. Forge 第二套索引（P1 分析缺口）
#    下载 de.oceanlabs.mcp:mcp_config:1.20.1:joined.tsrg 与 NeoForge 1.21.1 universal jar，
#    在 index/ 下新增 MojangIndex，然后：
java\build\install\mcbridge1201\bin\mcbridge1201.bat analyze --target-loader neoforge ...
```

## 工作方式约定

- 每轮只把实际跑过的阶段写进结论；`pending` 不写成通过。
- 所有实验保留命令、退出码、日志路径；失败也保留。
- 原始 jar、游戏 jar、转换件只在 `work/`，不入库、不外发。
- 上游改动先记 ADR，再动代码。
