# mcbridge1201 独立测试报告

测试日期：2026-10-19（Asia/Shanghai）。测试提交：`d9e88a1610fee06e09a10be503185adde206ddf6`。

**结论：三个样本已有可运行的适配结果；这次重新验证了服务端读档、双客户端抢物品和 TrashSlot 网络往返。但公开的“从原始模组直接转换”流程不能按文档复现，测试脚本也存在两处会误报成功的问题。现阶段适合作为研发原型，不宜宣传为保留全部功能的通用转换器。**

## 本次实测结果

| 检查 | 结果 | 本次证据 |
|---|---|---|
| 工具从源码构建、安装 CLI | 通过 | Gradle `clean test installDist`，`BUILD SUCCESSFUL` |
| Java 单元测试 | **22/22 通过** | 7 个测试套件，0 failures、0 errors |
| 仓库证据检查脚本 | 18 项通过 | 混合了本次单元测试与仓库归档结果，不能视为重新执行全部游戏测试 |
| 缓存原始模组校验 | 10/10 SHA-256 与清单一致 | 本次复用缓存，未重新联网下载十个模组 |
| IronChests 后半段重建流水线 | 通过 | 重新编译 14 个桥源码及 ResourcefulLib 网络类；依赖已有转换中间件 |
| IronChests 放置、存入、NBT、真实进程重启、读回 | **5/5 通过** | 存入 5 钻石，重启后仍为 5 |
| 三模组同服、225 区块保存重启 | 通过 | 两个服务端进程退出码均为 0；排除命令回显后仍有真实 `STRESS_OK_A/B` 服务端响应 |
| IronChests 双客户端同时抢取 | **通过** | 两端在世界 tick **2500** 点击；最终箱子 0、HostA 0、GuestB 7；HostA 客户端被纠正为空 |
| TrashSlot 移入、取回、再次移入、清空 | **通过，provider 调用范围** | 客户端与专用服务端分别观察到 `(trash, cursor)` 从 `(5,0)` → `(0,5)` → `(5,0)` → `(0,0)` |
| Lithium TPS 样本 | **20.02 TPS** | 起始加载 289/289 区块；1200 ticks / 59.95 秒；服务端正常停止 |

本次实际运行 Minecraft 客户端和专用服务端，并非只读取作者日志。双客户端测试通过 `clickSlot` 发包操作真实菜单；TrashSlot 测试打开背包后调用真实删除 provider，经过真实客户端/服务端网络收发。没有执行物理鼠标和键盘输入验收。

IronChests 重建 SHA-256：

```text
7e9d341f143e54c508b148bed30803fd60dddc040654853a04c3342fff4d75aa
```

与仓库 P75 中记录的服务端安全重建版本一致。Lithium 和 TrashSlot 运行件来自已有本地开发缓存，本次未从原始模组重新完成它们的整条转换链。

## 发现的问题

### 1. [P1] 发布文档把补丁步骤写成原始模组转换步骤

位置：[docs/distribution.md](https://github.com/SelYio666/mcbridge1201/blob/d9e88a1610fee06e09a10be503185adde206ddf6/docs/distribution.md)，第 3 节；[重建脚本第 128 行](https://github.com/SelYio666/mcbridge1201/blob/d9e88a1610fee06e09a10be503185adde206ddf6/tools/rebuild_ironchests_client.py#L128)。

按文档对原始 `ironchests-5.0.2-fabric.jar` 执行 NBT + draw 规则，CLI 返回成功并写出 jar。把这个 jar 放进独立 Fabric 1.21.1 服务端后，实际启动失败：

```text
NoSuchMethodError:
com.google.gson.JsonElement net.minecraft.class_2073.method_8971()
```

改走文档的“一键流水线”，干净 Git 副本直接报：

```text
input jar not found: .../work/client/ironchests-modelbridge2.jar
```

该文件是提前经过转换和模型适配的中间件，既不在仓库中，也不是用户下载到的原始模组。脚本还默认依赖 `work/cb/data/jars`、服务端 `processedMods`、Balm 与 Netty 的具体缓存路径。已有开发环境能重建，不代表普通用户按发布文档可以从零生成。

建议：把“原始 jar → CenturyBridge 转换 → 基础规则/模型适配 → 当前重建脚本”的过程纳入一个入口，或在发布文档中明确列全准备命令、输入阶段和校验值。单件 `patch` 示例应明确要求已转换输入。

证据：`logs/raw-patch.log`、`logs/controls/raw-patch-boot.log`、`logs/clean-repro.log`。

### 2. [P1] 区块测试把命令回显当成断言成功

位置：[tools/run_chunk_stress.py:98](https://github.com/SelYio666/mcbridge1201/blob/d9e88a1610fee06e09a10be503185adde206ddf6/tools/run_chunk_stress.py#L98)。

当前判定是 `"STRESS_OK_A" in log2`。但是 `run_server.py` 会先把发送的命令写进同一个日志：

```text
# > execute if block ... run say STRESS_OK_A
```

因此，即使 `execute if block` 的条件不满足，也会被认作成功。本次对实际存在箱子的坐标断言“应为空气”，服务端没有输出成功消息，但原判定的 A/B 均为 true：

```json
{"originalMarkerA": true, "originalMarkerB": true,
 "actualMarkerA": false, "actualMarkerB": false}
```

建议：只匹配 JVM 输出中的真实服务端响应，或将发送命令记录到独立文件；增加“故意破坏保存结果后必须失败”的负向测试。

本次正常 225 区块测试另行检查了服务端实际响应，确实通过；该问题不能用来否定这次正常运行的结果。

证据：`logs/controls/false-marker.log`、`false-marker-verdict.json`。

### 3. [P1] 启动脚本吞掉启动后的 JVM 错误退出码

位置：[tools/run_server.py:117](https://github.com/SelYio666/mcbridge1201/blob/d9e88a1610fee06e09a10be503185adde206ddf6/tools/run_server.py#L117)。

脚本记录了 JVM `exitCode`，但只要看到过 `Done`，最后就返回 0。负向测试用一个受控 Java 程序模拟“启动后失败”：先输出 Done，收到停止命令后退出 7。实际结果：

```text
JVM exitCode = 7
run_server.py exitCode = 0
```

`run_chunk_stress.py` 又用外层脚本退出码判断 `step1Exit0/step2Exit0`，会进一步掩盖异常。

建议：成功必须同时要求出现 Done、JVM 正常退出及没有超时；失败应传播非零退出码。容器契约脚本也应检查运行器返回码。

证据：`logs/controls/crash-server-result.json`、`crash-server.log`；复现源码在压缩包中。

### 4. [P2] “功能不删、原样保留”与 Lithium 实际范围不符

位置：[lithium-degraded.json](https://github.com/SelYio666/mcbridge1201/blob/d9e88a1610fee06e09a10be503185adde206ddf6/rules/fabric-1.21.1/lithium-degraded.json)；[区块访问替代实现](https://github.com/SelYio666/mcbridge1201/blob/d9e88a1610fee06e09a10be503185adde206ddf6/java/src/mixin/java/me/jellysquid/mods/lithium/mixin/world/chunk_access/ServerChunkManagerMixin.java)。

规则明确禁用 `entity.collisions.movement.EntityMixin` 和 `block.flatten_states.FluidStateMixin`。新的区块访问实现委托原版接口，注释明确写了旧多入口缓存和异线程快速路径没有重写。对于优化模组，这属于功能/性能范围缩减，不能只用“能启动”替代验证。

仓库在研发文档里已有说明，问题主要在对外介绍过于绝对。建议改成“保留已验证玩法，部分优化显式降级”，并把降级列表放到用户可见的支持矩阵中。

### 5. [P2] 双客户端探针对地形和菜单状态有隐含依赖

直接复用 P80 探针，在本次新世界中：菜单初次成功打开，随后玩家位置变化使菜单关闭；探针仍访问第 54 槽，造成：

```text
IndexOutOfBoundsException: Index 54 out of bounds for length 46
```

这是探针的未检查访问，不能记成 IronChests 自身崩溃。本次只修改隔离的测试夹具：固定箱子坐标、铺设平台、清理头顶空间，然后重编探针再跑；并发和物品守恒通过。项目受版本控制的文件未修改。

建议：测试自行建立安全地形，并在读槽位前验证菜单类型、槽位数量和玩家距离。失败时输出明确断言，避免探针把服务端打崩。

证据：`logs/runtime/multiplayer/` 为原探针失败；`logs/runtime/multiplayer-platform/` 为固定平台后的成功结果。

### 6. [P2] 哈希清单未随最新工具代码更新

`runs/SHA256SUMS.txt` 中 `tools/verify_evidence.py` 的哈希仍对应前一提交的内容，而最新提交修改了该工具。本次通过 Git 历史确认旧文件 SHA-256 恰好等于清单值。

此外，Windows Git 检出会转换换行，原日志还存在混合换行；不能把所有原始字节哈希不符都解释成内容被修改。建议明确对 Git blob 或标准化归档计算哈希，并在发布前生成、随后真正校验清单。当前 `verify_evidence.py` 不验证此清单。

## 测试环境与边界

- Windows，JDK Zulu 21.0.12.1，Gradle 9.8.1；Minecraft 1.21.1、Fabric Loader 0.19.5、Fabric API 0.102.0+1.21.1、Balm 21.0.66。
- 从已有本地 Git 仓库克隆指定提交；其 commit/tree 与 GitHub API 返回值一致：tree 为 `114a3edc9d3ef6b5d08ac915e02ebe801206159c`。受测副本的受版本控制文件保持不变。
- GitHub 直接克隆/归档下载缓慢，因此复用本机既有源码对象、依赖、原始模组缓存和转换中间件。测试运行于新的隔离目录和新世界，未使用用户原存档。
- 原 Java 21 路径在当前目录遭遇写入限制；复制 JDK 到本次工作区后同一写入探针及构建通过。该环境问题没有算作项目代码缺陷。
- 服务器仅绑定 `127.0.0.1`，客户端为测试用离线身份。客户端在取得断言后由测试程序终止，因此日志中的客户端退出码 1 是清理结果；不能当成自然退出成功。
- TPS 样本开始前的区块加载出现一次 `Can't keep up ... 8856ms or 177 ticks behind`。随后 1200 tick 窗口平均为 20.02 TPS。这不支持“全程无卡顿”或“性能优于原版”的结论；探针只在窗口开始报告 289 个区块，没有逐 tick 验证持续驻留。
- 物理 Delete/ESC、完整 GUI 视觉对照、长时间存档运行、生物 AI、红石、全部箱子种类/升级/掉落、恶意数据包，以及其他模组的转换均未在本次验收。

## 交付文件

- `test-results.json`：本次运行件哈希、运行结果与环境。
- `test-evidence.zip`：本次构建日志、JUnit XML、真实游戏日志、负向对照与测试源码，内含独立 SHA256SUMS。
- 压缩包不包含 Minecraft、第三方模组或转换模组 jar。复现脚本依赖本机缓存路径；不是修复后的公开安装器。

建议先修正文档转换入口和两处假阳性，再扩大玩法覆盖；现有游戏结果可以继续保留，但应在报告中标清验证范围和降级项。
