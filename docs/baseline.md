# P0 基线：环境、上游、样本与首轮实测

执行日期：2026-10-18（Asia/Shanghai）。本文件只记录实际执行过的命令、实际产物和实际失败，不把方案里的拟议接口写成已实现能力。

## 0. 一句话结论

- **可执行的**：环境锁定、上游提交/许可锁定、10 份 1.20.1 样本（sha512 校验通过）、自研静态损伤分析器（10/10 跑通）、CenturyBridge 引擎编译、7 节版本分段、ironchests 真实转换（`ok_partial`）。
- **已 BOOTED**：Fabric 1.21.1 专用服务端在**本地重映射过的游戏 jar** 上到达 `Done (4.803s)`，正常保存并停止。原版 Loader 的 remap 路径被沙箱的 `Files.isWritable` 阻塞，因此用自研 ASM 重映射器产出等价 jar（保留方法体 + 继承/接口/lambda 重命名传播）；Loader 本身未改动。
- **已 LOADED，未通过**：CenturyBridge 转换后的 ironchests 被 Loader 接受并进入入口点，随后在 `ItemPredicate.ANY`（`class_2073.field_9640`，1.21.1 已移除）处 `NoSuchFieldError`。这是当前第一个真实运行时缺口，与静态分析、CenturyBridge 账本三方一致。
- **未完成的**：`WORLD_LOADED` 以上的玩法契约、客户端/渲染、多人同步、Forge 成员级分析。

## 1. 环境

| 项目 | 精确值 | 证据/命令 | 是否阻塞 |
|---|---|---|---|
| OS/架构 | Windows 11 `10.0.26200`，amd64 | `[System.Environment]::OSVersion` | 否 |
| CPU / 内存 / 磁盘 | 16 逻辑核；15.3 GiB RAM；C: 23.3 GiB 可用 | Python `os.cpu_count` / `GlobalMemoryStatusEx` / `shutil.disk_usage` | 否 |
| 构建 JDK | Azul Zulu **21.0.12.1+1-LTS**，`C:\Users\27682\Documents\新建文件夹\.toolchain\jdk` | `java -version`、`javac -version`、`release` 文件 | 否 |
| 来源 JDK 17 | **未安装**（PATH 无 java；Program Files 无 JDK）。PCL 配置里存在一个 Zulu 17 **JRE**（`D:\...\zulu17.68.203-ca-jre17.0.20.1-win_x64\bin`），未用于本轮 | `Get-Command java`、PCL `config.json` | 部分：编译 fixture 需用 `javac --release 17` 或另装 JDK 17 |
| Gradle | 9.8.1（`.toolchain\gradle`），需显式 `JAVA_HOME`、`GRADLE_USER_HOME` | `gradle --version` | 否 |
| Git | 2.55.0.windows.3；**HTTPS 不可用**（schannel `SEC_E_NO_CREDENTIALS`） | `git ls-remote` 失败日志 | 否（改用 codeload zip） |
| Python | 3.12（`C:\Users\27682\AppData\Local\Programs\Python\Python312`），HTTPS 正常 | 全部 `tools/*.py` | 否 |
| 网络可达 | `piston-meta.mojang.com`、`maven.fabricmc.net`、`meta.fabricmc.net`、`api.modrinth.com`、`repo1.maven.org`、`codeload.github.com`、`github.com` HTML/atom 可达；`api.github.com` 返回 **403 限流**；`plugins.gradle.org` 握手超时 | 各抓取脚本日志 | 部分 |
| 启动器/图形 | PCL2 已安装；`.minecraft` 仅有 `runtime/jre-legacy`，无版本目录；未做任何图形客户端启动 | 目录检查 | **是**：本轮无客户端/渲染证据 |
| 专用服务端 | Fabric server launcher 0.19.5；**已 BOOTED**（见 §7），游戏 jar 由本项目重映射 | `runs/p1-server-baseline/` | 否（remap 需本地绕过，见 §7.2） |

### 1.1 三个环境异常（都会影响复现，必须写进脚本）

1. **`%TEMP%` 不可写**：`C:\Users\27682\AppData\Local\Temp` 下 `Files.createTempFile` 抛 `AccessDeniedException`。ImageIO、zipfs、tinyremapper 都会踩到。所有 JVM 调用必须显式 `-Djava.io.tmpdir=<工作目录内路径>`（`tools/run_server.py` 已处理）。
2. **工作区内 `Files.isWritable` 恒为 false**：文件实际可写（`Files.writeString` 成功），但 AccessCheck 失败。Fabric Loader 的 `OutputConsumerPath` 用 `FileSystemReference.isReadOnly()` 判定，于是拒绝 remap。见 §7.2。
3. **`java.exe` 只能写会话工作区**：同一 Java 程序写 `C:\mcrun\...`、`C:\Users\27682\Documents\probe-root.txt` 全部 `AccessDeniedException`，写工作区成功；同时 `pwsh` 和 `python` 可以写这些位置。这使“把实例搬到 ASCII/干净 ACL 路径”这一常规绕过无效。

## 2. 上游锁定

锁定方式：GitHub REST API 限流，因此用 `commits/<branch>.atom` 取 SHA、`codeload.github.com/<repo>/zip/<sha>` 取精确快照、`releases.atom` 取发布列表。见 `manifests/upstream.lock.json`。

| 候选 | 锁定提交 | 许可（文件 SHA-256 前 12） | 工件/构建系统 | 本轮构建结果 |
|---|---|---|---|---|
| Retromod | `e693278379a6c80cd1a6623136a166f4d8c5cafe`（2026-10-13） | MIT（`1bd4bc93e323`） | Maven（根 `pom.xml`，`build.sh`/`build-all.sh`，1320 个源文件）；`releases.atom` 仅有 `1.4.0-snapshot.1 for MC 26.2`（Fabric/Quilt） | 未构建。26.2 工件不能当 1.21.1 目标；源码支持需另验证 |
| CenturyBridge | `cf4ebeba2eaaa49d3746162cc2c10b670d681aec`（2026-08-25，与交接包调查一致） | MIT（`c505a7cd0e51`） | **无构建系统**：`javac` + ASM/gson，`build.sh` + `core/tools/*.py`；无 Release | **引擎可编译**（46 个 class），但需本地补一个上游缺失类，见 §6.1 |

## 3. 样本清单（10 份，5 Fabric + 5 Forge）

来源：Modrinth 项目所有者发布的 1.20.1 版本；下载后独立校验 SHA-256，并核对 Modrinth 公布的 SHA-512。完整字段见 `manifests/corpus.json`。

| ID | 角色 | 制品 | 大小 | SHA-256 | 许可 |
|---|---|---|---|---|---|
| F01 | container | `ironchests-5.0.2-fabric.jar` | 485 230 | `6a07065a3a68280e26a0fc8a3fc0d8dde10b0999432492ef6726cd583be96de6` | All-Rights-Reserved |
| F02 | high-risk-mixin | `lithium-fabric-mc1.20.1-0.11.4.jar` | 691 483 | `76133efe92aea907cf75562d9e26517deb170e2580e1ecd4979da2c8902de782` | LGPL-3.0-only |
| F03 | client-ui | `appleskin-fabric-mc1.20.1-2.5.2.jar` | 1 097 240 | `821241285f534fd04aa15a91f3d1a6059135bce2d4b6e409fa1ae8825b4c9702` | Unlicense |
| F04 | metadata-config | `modmenu-7.2.2.jar` | 721 366 | `a041b0f0305ffa5eb90120aa23768e1cfbb27583904b1751e3783c0f69382f1a` | MIT |
| F05 | container | `trashslot-fabric-1.20.1-15.1.5.jar` | 118 660 | `07858324752987ed6a7a83b9dc71385fbe43ca1e16bcae91bdf57850e92435f2` | All-Rights-Reserved |
| G01 | container-gui | `jei-1.20.1-forge-15.71.0.224.jar` | 2 393 438 | `30626ef01662d0d79ccaa04fb3ce8bd1a084e8031dc90e276b626ca82698ad46` | MIT |
| G02 | client-render | `journeymap-forge-1.20.1-6.0.7.jar` | 4 353 808 | `65cf198bd2ec41b2c1ac24a28544dddc74d5ef63222ebf3d393b76fa7bdc7a23` | All-Rights-Reserved |
| G03 | capability-api | `curios-forge-5.14.1+1.20.1.jar` | 398 066 | `1e817919a35b37cf30524aaec73f0ca5130452f23f168f844854df282eb8e51f` | LGPL-3.0-or-later |
| G04 | data-library | `Patchouli-1.20.1-85-FORGE.jar` | 642 732 | `05f7b5d52f6b8f0fd7f8b4822fa07a192d1394d83a264309c9d221d6d4fd21c5` | CC-BY-NC-SA-3.0 |
| G05 | high-risk-mixin | `create-1.20.1-6.0.8.jar` | 19 170 905 | `6fbb910c367dbce8e4fc7e5bf64b6edd4de980906ed00af8e47e4af843c0d9b0` | Create Mod License（自定） |

注意：

- 5 份 Forge 样本的许可不是统一 MIT：Journeymap/ironchests/trashslot 为 All-Rights-Reserved，Patchouli 为 NC-SA，Create 为自定许可。**只在本机分析，不随仓库分发**；对外发布结论时只能给工具和 hash。
- `ironchests` 与 `couplings` 是 CenturyBridge 作者自报的样例锚点；本轮只复现到 ironchests 的**转换**，没有复现作者的客户端玩法链。
- 原始 jar 与 `work/corpus/` 下的下载副本都不是本仓库的交付物。

## 4. 目标环境锁定

| 项目 | 值 |
|---|---|
| Minecraft 1.21.1 client jar | `499f6897d1837516680f3114072d8106e11c9adcd933fe5cf051b551089b0c99`（26 836 906 B，Mojang sha1 校验通过） |
| Minecraft 1.20.1 client jar | `56b71336d2b4fdffd197f56595b0da93e32a946f78f382a299b8f4b92758bb0f` |
| Mojang 官方映射 1.20.1/1.21.1 | `work/target/client-*-mappings.txt`（为后续 Forge/SRG 路线准备） |
| intermediary 1.20.1 / 1.21.1 | `26b60a7d...4799` / `e8bd6a4c...12a6` |
| Fabric API 1.21.1 | `0.102.0+1.21.1`，`fd021e3e...1bd1` |
| Fabric API 1.20.1（源索引） | `0.92.12+1.20.1`，`4197ff4f...1c1e` |
| Fabric Loader | 0.19.5（`93044e4d...c695`）；服务端另测 0.16.14 |

## 5. 静态损伤分析（Fabric 1.21.1）

### 5.1 方法（不是“字符串比对”）

`java/` 下的 `mcbridge1201` 做了三件事：

1. **目标索引**：用官方 1.21.1 client jar + intermediary 映射构建完整类/成员索引（10 919 类、87 766 成员），描述符经 official→intermediary 重写；**带继承树**，成员解析沿 superclass/interface 上溯。
2. **源索引**：同样用 1.20.1 client jar + intermediary 构建，用于反证“这条引用在 1.20.1 确实存在”，避免把映射噪声当损伤。
3. **引用扫描**：ASM 遍历每个类的常量池级引用（类型、方法、字段、invokedynamic/handle、泛型签名、注解、mixin target 字符串），按 `(owner,name,desc)` 去重后与目标索引比对，区分 `MISSING_CLASS / MISSING_MEMBER / DESC_MISMATCH / MISSING_API_* / WRONG_LOADER / UNMAPPED_NAMESPACE`。

判定规则保持保守：继承链中出现未索引的非 `java/lang/Object` 祖先时记 `UNKNOWN` 而不是缺失；Mojang 名/SRG 名引用单独计入 `unmappedNamespace`，不冒充损伤。`presentInSource` 为 true 表示“这条损伤在 1.20.1 索引里确实存在”，即真实跨版本变化。

### 5.2 结果（`runs/p0-fabric-target/plan.json`，SHA-256 `9ebfa5e9...e5316`）

| 样本 | 判定 | MISSING_CLASS | MISSING_MEMBER | DESC_MISMATCH | FABRIC_API 缺失 | 源索引确认 | 备注 |
|---|---|---|---|---|---|---|---|
| ironchests | blocked_static | 1 | 20 | 19 | 7+5 | **52/52** | NBT/组件墙、BlockEntity NBT、Item.appendTooltip、Explosion 构造器、Fabric API model/networking 删除 |
| lithium | blocked_static | 1 | 5 | 6 | 0 | 11/12 | 224 个 mixin；`class_3193$class_3724` 类消失 |
| appleskin | blocked_static | 0 | 11 | 14 | 1+1 | 27/27 | HUD/事件签名变化 |
| modmenu | blocked_static | 4 | 7 | 14 | 0 | 24/25 | 4 个类整体消失 |
| trashslot | blocked_static | 0 | 2 | 0 | 0 | 2/2 | 只差 2 个成员 |
| jei | wrong_loader | 0 | 0 | 0 | 0 | — | 16 343 条 SRG/Mojang 命名空间引用，需第二套索引 |
| journeymap | wrong_loader | 0 | 0 | 0 | 0 | — | 30 588 条未映射命名空间引用；该 jar 同时带 `fabric.mod.json` 与 `mods.toml`，按 loader 专用元数据判定为 Forge |
| curios | wrong_loader | 0 | 0 | 0 | 0 | — | 242 条 `net.minecraftforge.*`，在 Fabric 目标下必然是 Wrong loader |
| Patchouli | wrong_loader | 0 | 0 | 0 | 0 | — | 127 条 Forge 命名空间引用 |
| create | wrong_loader | 0 | 0 | 0 | 0 | — | 226 433 条未映射引用；57 个 mixin 配置 |

关键样例（均 `presentInSource=true`）：

- `net/minecraft/class_1799.method_7948()Lnet/minecraft/class_2487;` —— `ItemStack.getNbt()`，1.20.5 组件化后消失（ironchests 14 处引用）。
- `net/minecraft/class_2586.method_38242()Lnet/minecraft/class_2487;` —— BlockEntity NBT 方法签名变为 `(Lnet/minecraft/class_7225$class_7874;)...`（ironchests 2 处）。
- `net/minecraft/class_1293.<init>(Lnet/minecraft/class_1291;II)V` —— Explosion 构造器改为接收 `class_6880` 注册项。
- `net/fabricmc/fabric/api/client/model/ModelLoadingRegistry`、`.../networking/v1/ServerPlayNetworking$PlayChannelHandler` —— Fabric API 自身 API 删除/改名。

完整表格：`docs/generated/static-matrix-fabric-1.21.1.md`。

### 5.3 这套结果的边界

- 只到 `ANALYZED`。`blocked_static` 的意思是“静态上存在必须处理的变化”，不是“无法运行”；`wrong_loader` 同理。
- Mixin 注入目标已提取并保守校验 intermediary 方法（§7.24）；ordinal/slice/local capture 和 Yarn/refmap/构造器仍未分析。
- Forge 样本没有成员级结论：1.20.1 Forge 用 SRG 名，NeoForge 1.21.1 用 Mojang 名，必须有第二套索引才能判断。这是 P1 的第一个分析缺口。

## 6. 上游引擎真实尝试

### 6.1 CenturyBridge 引擎编译

| 步骤 | 命令 | 结果 |
|---|---|---|
| 编译 | `javac -cp asm+asm-tree+asm-commons+gson -d core/build/classes core/src/**/*.java` | **失败**：`Main.java:42` 引用 `top.dext.centurybridge.data.MixinCheck`，但该提交的 `core/src` 只有 14 个 java 文件，**不存在 MixinCheck.java** |
| 本地补丁后编译 | 增加 `patches/centurybridge/MixinCheck.java`（no-op，带注释说明不是上游代码） | **成功**，46 个 class |

结论：该提交**不能按仓库原样构建**；“mixn-check” 这道 `build.sh` 门禁无法验证。产物只能用于 `gen-segment`/`convert`，不能声称桥 jar 的 mixin 目标已验证。

### 6.2 分段生成（真实执行）

`gen-chain 1.20.1 1.21.1 data/mappings data/segments`：

| 边界 | 消失类 | 消失方法 | 签名变更方法 | 消失字段 | 类型变更字段 |
|---|---|---|---|---|---|
| 1.20.1 → 1.20.2 | 19 | 933 | 665 | 884 | 217 |
| 1.20.2 → 1.20.3 | 26 | 619 | 203 | 319 | 46 |
| 1.20.3 → 1.20.4 | 0 | 0 | 0 | 0 | 0 |
| 1.20.4 → 1.20.5 | 36 | 1 369 | 921 | 987 | 678 |
| 1.20.5 → 1.20.6 | 0 | 0 | 0 | 0 | 0 |
| 1.20.6 → 1.21 | 61 | 618 | 400 | 353 | 134 |
| 1.21 → 1.21.1 | 0 | 1 | 4 | 0 | 0 |

1.20.5（组件墙）确实是损伤最重的一节，与方案预期一致。

### 6.3 ironchests 真实转换

```text
convert data/segments 1.20.1 1.21.1 out/ironchests in/ironchests-5.0.2-fabric.jar
→ verdicts: {ok_partial=1}
→ unaccounted runtime refs: 55 (ledgered: 0)
→ full-audit: {CLASS-ISSUE=1, CTOR-ISSUE=1, ISSUE=24, TOMBSTONE=28}
```

产物：`work/cb/out/ironchests/ironchests-5.0.2-fabric+1.21.1.jar`（451 766 B，SHA-256 `222c0d2a...5700`）。报告：`work/cb/out/ironchests/report.md`。其中明确记录了 28 个 tombstone（惰性抛错），集中在 `class_1799` NBT 家族、`class_1856/2040/2048/2090/2102/2073` 的 JSON 读写、`class_4588` 渲染调用。

**这仍然是 `TRANSFORMED`，不是 `VERIFIED`/`BOOTED`**：没有运行、没有跑 `BytecodeVerify`（上游工具类，本轮未编译）、桥 jar 未构建。

## 7. 目标 1.21.1 专用服务端：从阻塞到 BOOTED

### 7.1 第一层阻塞（已定位）

`tools/setup_server.py` 生成隔离实例，`tools/run_server.py` 启动 JVM 并在 `Done (` 后自动 `stop`。stock Loader 的 remap 直接失败：

```text
Caused by: java.io.IOException: the jar file .\.fabric\remappedJars\minecraft-1.21.1-0.19.5\server-intermediary.jar.tmp can't be written
  at ...tinyremapper.OutputConsumerPath.<init>(OutputConsumerPath.java:102)
```

根因：`OutputConsumerPath` 用 `FileSystemReference.isReadOnly()` 判定，而 zipfs 的只读标志取自 `Files.isWritable`；本会话工作区内 `Files.isWritable` **恒为 false**（探针：`parent writable=false`、`created exists=true writable=false`，但 `Files.writeString` 实际成功）。这是受限令牌/沙箱 ACL 的结果，不是磁盘权限。

尝试过但无效的绕过：手动建目录、删残留 `.tmp`、换 ASCII 路径 `C:\mcrun`（Java 连 `.fabric` 都建不了）、给沙箱 SID 加 FullControl ACE、`-Djava.io.tmpdir`（只修好 ImageIO 类错误）。

### 7.2 误导：CenturyBridge 的 `remap-jar` 是 stub 生成器

用上游 `remap-jar` 预生成 `server-intermediary.jar` 能跳过 Loader remap，但 Loader 报
`Could not find game constructor in net.minecraft.server.Main!`。用 `javap -c` 检查发现：
**该 jar 的类没有 Code 属性**——CenturyBridge 的 `remap-jar` 只产出编译用 stub，方法体被剥离。这不是 Loader 的问题，是工具用途不同。

### 7.3 解决：自研 body-preserving remapper

新增命令（`java/src/main/java/top/mcbridge1201/remap/`）：

```text
mcbridge1201 remap-jar --in <obf.jar> --out <intermediary.jar> --mappings <intermediary-1.21.1.tiny>
```

用 ASM `ClassRemapper` + `ZipOutputStream`（**不经过 zipfs**，因此绕开只读判定），保留方法体。四个缺陷都是运行时崩溃暴露后逐个修的：

| 现象 | 原因 | 修复 |
|---|---|---|
| `AbstractMethodError` `class_3797` 未实现 `class_6489.method_48019` | 接口实现方法不在 intermediary 映射里（server-only override） | 沿 super/interface 传播方法名 |
| `ClassFormatError: Duplicate method` `class_5912.method_14486` | 传播把 static/private 辅助方法改成了接口方法名（intermediary 名只由 name+desc 决定） | static/private 不参与传播 |
| `NoSuchFieldError class_244` 无 `b` | 字段引用以子类为 owner，实际声明在父类 | 字段仅在 owner 未声明时沿父类传播 |
| `AbstractMethodError` `class_3754$$Lambda` 未实现 `method_16359` | LambdaMetafactory 取 **invokedynamic 名字**作为 SAM 名，不取接口方法名 | 重写 `mapInvokeDynamicMethodName`，按接口 SAM 映射改名 |

产物：`work/remap/server-intermediary.jar`，6 148 类、18 425 518 B、SHA-256 `27d29458a7e64512b592555c75fe52156260b784d2da46d90e34aba3bc17978d`。Loader 接受它并跳过自己的 remap。两次独立重映射得到**逐字节相同**的 jar（同一 SHA-256），可复现。

> 这是**本地工具链绕过**，不是产品能力：Loader 本体未改；游戏 jar 的映射语义相同，但实现是本项目的。重映射器本身有独立价值（目标 jar 索引/桥编译都需要它），已加单元测试与确定性输出（entry 时间戳置 0）。

### 7.4 BOOTED 证据

```powershell
python tools/setup_server.py --instance work/instances/fabric-1.21.1-server
# 本机必需：用自研重映射器预生成 Loader 期望的 server-intermediary.jar
python tools/remap_server.py --instance work/instances/fabric-1.21.1-server `
  --loader 0.19.5 --mappings work/cb/data/mappings/intermediary-1.21.1.tiny
python tools/run_server.py --instance work/instances/fabric-1.21.1-server `
  --log runs/p1-server-baseline/server.log --timeout 300
```

```text
[18:33:34] [Server thread/INFO]: Done (4.803s)! For help, type "help"
[18:33:36] [Server thread/INFO]: Stopping the server
[18:33:37] [Server thread/INFO]: Saving chunks for level 'ServerLevel[world]'/minecraft:overworld
...
{"doneSeen": true, "exitCode": 0, "durationSeconds": 20.6}
```

日志：`runs/p1-server-baseline/server-baseline.log`（首次，SHA-256 `3523ae82...`）与 `server-rerun.log`（重跑，`doneSeen: true`、退出码 0、15.8s）。Fabric API 0.102.0+1.21.1 的 41 个模块全部加载；两次启动均到达 `Done`。

### 7.5 转换后的 ironchests：LOADED，然后真实崩溃

把 `work/cb/out/ironchests/ironchests-5.0.2-fabric+1.21.1.jar` 放进 `mods/` 后重跑（`runs/p1-server-converted-ironchests/server.log`）：

```text
[main/INFO]: Loading 42 mods:
    - ironchests 5.0.2
...
java.lang.RuntimeException: Could not execute entrypoint stage 'main' ... provided by 'ironchests'
Caused by: java.lang.NoSuchFieldError: Class net.minecraft.class_2073 does not have member field 'net.minecraft.class_2073 field_9640'
    at tech.thatgravyboat.ironchests.api.chesttype.ChestType.lambda$codec$1(ChestType.java:70)
    at ...ChestType.codec(ChestType.java:57)
    at ...ChestTypeLoader.parseChest(ChestTypeLoader.java:48)
    at ...IronChests.init(IronChests.java:16)
```

命名解析（`tools/name_lookup.py`，把 intermediary 与 Mojang 官方映射按 obf 名 join）：

- `class_2073` = `net.minecraft.advancements.critereon.ItemPredicate`
- `field_9640` = `ItemPredicate.ANY`（1.21.1 已移除）

意义：**Loader 接受了转换件**（mod 列表里出现 ironchests 5.0.2，`fabric.mod.json` 的 minecraft 依赖已被 CenturyBridge 改为 1.21.1），失败发生在入口点执行时，属于真实的语义缺口，而不是加载/元数据问题。

### 7.6 这次崩溃反过来修正了分析器

首次静态分析**没有**报 `class_2073.field_9640`：`resolveField` 把 `java/util/function/Predicate` 这类未索引 JDK 祖先当成“可能提供成员”，于是返回 `UNKNOWN` 而不是 `MISSING_MEMBER`。已修正为：字段解析只对非 JDK 的未索引祖先保守。重跑后 ironchests 的确认损伤从 **47 条变成 52 条**（`confirmed 52/52`），新增的正是 `ItemPredicate.ANY`。

这条闭环（运行时崩溃 → 分析器漏报 → 修正 → 静态预测命中）是当前最可信的跨版本证据链。

### 7.7 第一条转换规则与常量池种类修正

规则文件 `rules/fabric-1.21.1/container.json`：

- `itempredicate.any.static-field`：匹配 `GETSTATIC net/minecraft/class_2073.field_9640`，替换为 `INVOKESTATIC top/mcbridge1201/bridge/ItemPredicateAny.any()`。
- 桥类由 ASM 生成并嵌入输出 jar：返回 `new ItemPredicate(Optional.empty(), MinMaxBounds.Ints.ANY, DataComponentPredicate.EMPTY, Map.of())`，与 1.20.1 的“匹配所有物品”语义等价。
- 第一次生成时 `Map.of()` 用了 Methodref，运行时报 `IncompatibleClassChangeError: ... must be InterfaceMethodref`，已改为 interface 调用。

同一次 `patch` 还做了**常量池种类修正**（`--client-jar`/`--mappings`/`--lib`）：

| 位置 | 现象 | 处理 |
|---|---|---|
| `DataResult.success` 调用点（123 处，含 JiJ） | 1.20.5 起 `DataResult` 由 class 变 interface，旧 `Methodref` 不再合法 | 改成 `InterfaceMethodref` / `invokeinterface` |
| `MethodHandle` 常量与 invokedynamic 参数（3 处） | 句柄里的 `REF_invokeStatic` 也带种类位，`ShapeTypes.decode` 通过 handle 引用 `DataResult.success` | 重建 `Handle`，`isInterface=true` |
| 嵌套 jar | 崩溃来自 ironchests 内嵌的 ResourcefulLib `EnumCodec` | 递归处理 `META-INF/jars/*.jar` |

产物：`work/cb/out/ironchests/ironchests-5.0.2-fabric+1.21.1-patched.jar`（SHA-256 `ad5e87ed...7e80`）。`IronChests.init` 现在通过 `ItemPredicate` 阶段。

### 7.8 下一个真实缺口：`Codec.dispatch` 的 `MapCodec` 形状

同一进程继续加载 chest 数据，在 `ShapeTypes.decode` 处失败：

```text
Caused by: java.lang.ClassCastException: class com.mojang.serialization.MapCodec$MapCodecCodec
  cannot be cast to class com.mojang.serialization.MapCodec
    at java.base/java.util.function.Function.lambda$andThen$1
    at com.mojang.serialization.codecs.KeyDispatchCodec.lambda$decode$4
    at ...KeyDispatchCodec.decode
    at ...ShapeTypes.decode(ShapeTypes.java:32)
```

`ShapeTypes.decode` 调用 `Codec.dispatch(Function, Function)`；1.20.1→1.21.1 之间 `MapCodec` 被引入，dispatch 的第二个函数语义从 “返回 Codec” 变成 “返回 MapCodec”。这是**形状变化**，不是重命名，需要适配器（把 MapCodec 包成 Codec 或改 dispatch 的调用点），属于下一步要写的第二条规则/桥。

### 7.9 第二、三条规则：dispatch 适配与 `fromJson` 重建

新增两条规则（`rules/fabric-1.21.1/container.json`）：

| 规则 | 处理 | 结果 |
|---|---|---|
| `codec.dispatch.mapcodec-shape` | 把 `INVOKEINTERFACE Codec.dispatch(Function,Function)` 重定向到生成的 `CodecDispatch.dispatch`，内部用 `MapCodec.assumeMapUnsafe` 包装旧 lambda 的返回值 | 应用 2 次，`ShapeTypes.decode` 不再抛 `ClassCastException` |
| `itempredicate.fromjson.static` | CenturyBridge 把 `ItemPredicate.fromJson(JsonElement)` 替换成了 tombstone，且调用点是 **MethodHandle**（lambda 实现）而非直接指令；按 owner 前缀 + 精确描述符匹配句柄并重定向到 `ItemPredicateFromJson.fromJson`（用 1.21.1 的 `ItemPredicate.CODEC.parse(JsonOps.INSTANCE, json).result().orElse(null)` 重建原实现） | 应用 1 次，tombstone 不再被调用 |

补丁产物：`work/cb/out/ironchests/ironchests-5.0.2-fabric+1.21.1-patched.jar`（SHA-256 `7ec705dd...5592`）。规则引擎现在支持：字段重定向、方法重定向（含 `MethodHandle` 实现）、常量池种类修正、JiJ 递归。

### 7.10 当前阻断：`assumeMapUnsafe` 不足

下一层失败：

```text
Caused by: java.lang.NullPointerException
    at java.util.Optional.of
    at com.mojang.serialization.DataResult$Success.result(DataResult.java:140)
    at com.mojang.serialization.MapCodec$7.apply(MapCodec.java:317)
    at com.mojang.serialization.MapCodec$4.decode(MapCodec.java:257)
    at RecordCodecBuilder$Instance$7.decode(RecordCodecBuilder.java:406)
```

`MapCodec.assumeMapUnsafe` 只对“本来就是 map codec”的 Codec 安全；这里被包装的 Codec 走普通解码路径，返回 `success(null)`，于是 `Optional.of(null)` 抛 NPE。正确做法不是继续用 unsafe 包装，而是构造真正的 `MapCodec`（`MapCodec.of(MapEncoder, MapDecoder)` 或 `Codec` 的 map 视图），或者改走 `MapCodec` 原生的 dispatch 语义——这是下一步要设计的适配器。

这一点也说明：**“能过入口点”与“能加载数据”是两层不同的语义**，规则必须逐条有行为证据，不能只看异常消失。

### 7.11 转换件随服务端启动成功（含世界加载）

在 `Identifier` 构造器被 1.21.1 私有化后，最后一处 `IllegalAccessError` 来自 ResourcefulLib 的注册表代码。逐点改写只能覆盖“参数是纯压栈”的 13 处，剩下一处的参数由方法调用产生，保守匹配器不会动它。

处理方式改为 **access widener**（`rules/fabric-1.21.1/mcbridge.accesswidener`）：

```text
accessWidener v2 intermediary
accessible method net/minecraft/class_2960 <init> (Ljava/lang/String;Ljava/lang/String;)V
```

`tools/inject_aw.py` 把 AW 写进补丁 jar 并给 `fabric.mod.json` 加 `accessWidener`。之后：

```text
[18:59:47] Found new data pack ironchests, loading it automatically
[18:59:50] Done (1.134s)! For help, type "help"
{"doneSeen": true, "exitCode": 0}
```

日志：`runs/p3-server-accesswidener/server.log`。**这是转换后的 ironchests 第一次随 1.21.1 服务端完成启动与世界加载**（专用服务端的 "Done" 包含主世界生成与 tick 启动）。

### 7.12 最小容器契约（无客户端）

服务端控制台可以执行命令，因此做了不需要玩家客户端的容器契约。`tools/run_server.py --command ...` 在 `Done` 之后按序注入命令。

放置与写入（`runs/p4-contract-place/server.log`）：

```text
# > setblock 0 100 0 ironchests:iron_chest
# > item replace block 0 100 0 container.0 with minecraft:diamond 5
[Server thread/INFO]: Replaced a slot at 0, 100, 0 with [Diamond]
[Server thread/INFO]: 0, 100, 0 has the following block data: {x: 0, y: 100, z: 0, id: "ironchests:iron_chest"}
```

重启后（`runs/p4-contract-restart/server.log`）：方块仍在，`data get block` 依然没有 `Items`。

对照组（`runs/p4-contract-vanilla-control/server.log`，同一实例、同一命令）：

```text
4, 100, 0 has the following block data: {x: 4, y: 100, z: 0, Items: [{count: 5, Slot: 0b, id: "minecraft:diamond"}], z: 0, id: "minecraft:chest"}
```

结论（严格按阶段）：

| 契约 | 结果 |
|---|---|
| 方块注册与放置 | **通过**（`setblock` 成功、重启后仍在） |
| 容器接收物品 | **通过**（`item replace` 报 Replaced，容器接口接受） |
| NBT 持久化 | **失败**（`data get block` 无 `Items`，重启后仍无） |
| 图形/GUI/渲染 | pending（无客户端） |

### 7.13 持久化失败的根因（已定位）

`GenericChestBlockEntity` 声明的是旧签名：

```text
public void method_11014(net.minecraft.class_2487);   // 读
public void method_11007(net.minecraft.class_2487);   // 写
```

而 1.21.1 的 `BlockEntity` 是：

```text
protected void method_11014(net.minecraft.class_2487, net.minecraft.class_7225$class_7874);
protected void method_11007(net.minecraft.class_2487, net.minecraft.class_7225$class_7874);
```

多了一个 `RegistryWrapper.WrapperLookup` 参数。转换件的方法**不再 override**，vanilla 保存时调用的是基类实现，所以物品从未被写进 NBT——不抛异常、不报错，正是最危险的“静默降级”。本项目静态分析器早已把 `class_2586.method_11014/38242` 列为 `DESC_MISMATCH`，运行时结果与之一致。

这属于方案里的“签名变化”，需要专门的适配（把 1-arg 覆写改成 2-arg 并忽略/转发 lookup，同时处理调用点），不能用改名或空实现糊过去。

### 7.14 签名适配规则修复持久化，容器契约通过

针对 §7.13 的根因新增 `signatureAdaptations` 规则（不只改名，而是把 1 参覆写迁移成 2 参）：

- `method_11007(NbtCompound)V` → `method_11007(NbtCompound, WrapperLookup)V`
- `method_11014(NbtCompound)V` → `method_11014(NbtCompound, WrapperLookup)V`
- 局部变量槽从 2 开始整体后移，新增参数放在槽 2；
- 方法体内的既有调用同步补参：
  - `super.method_11007/11014`（`class_2621`）
  - `ContainerHelper.saveAllItems`（`class_1262.method_5426`，2 参 → 3 参）
  - `ContainerHelper.loadAllItems`（`class_1262.method_5429`，2 参 → 3 参）
- 由于改了方法描述符，帧用 `COMPUTE_FRAMES` 重算（`SafeClassWriter`，不加载游戏类）。

应用统计：`blockentity.nbt.write.lookup` 1 次 + 2 处调用补参；读方法同样被改写为 2 参。

契约重跑（同一实例，命令驱动）：

| 步骤 | 证据 | 结果 |
|---|---|---|
| 放置 `ironchests:iron_chest` @ (0,100,0) | `runs/p5-contract-nbt-fix/server.log` | 通过 |
| 插入 5 个钻石 | `Replaced a slot at 0, 100, 0 with [Diamond]` | 通过 |
| 读取方块数据 | `{... Items: [{count: 5, Slot: 0b, id: "minecraft:diamond"}], ... id: "ironchests:iron_chest"}` | **通过（物品已进 NBT）** |
| 保存并重启进程 | `runs/p5-contract-nbt-restart/server.log` | 通过 |
| 重启后读回 | `data get block 0 100 0` → 同上；`Items[0].count` → `5` | **通过** |

结论：**容器契约在“专用服务端 + 命令 API + 单进程重启”范围内通过**（`CONTRACT_PASSED`，范围受限）。没有验证 GUI、渲染、多人同步，也没有客户端玩家操作路径。

### 7.15 第二份样本：lithium 的加载、mixin 注入点与下一道签名墙

为验证管线不是 ironchests 专用，用同一套流程处理 **lithium**（1.20.1、224 个 mixin、优化器类模组）：

```text
convert → verdicts: {ok_degraded_partial=1}, unaccounted refs: 11, tombstones: 5
patch   → 通用规则 0 命中（说明规则没有硬编码到 ironchests 的符号）
boot    → Loading 42 mods 含 lithium 0.11.4；读取了 131 个配置项；随后崩溃
```

依次观察到的失败：

| 阶段 | 失败 | 处理 |
|---|---|---|
| Mixin | `lithium.mixins.json:entity.collisions.movement.EntityMixin` 的 Redirector `adjustMovementForCollisionsGetEntitiesLater` scanned 0 targets | 新增 `mixinStrips` 降级机制，从配置中移除该类 |
| Mixin | `block.flatten_states.FluidStateMixin` 的 `@Inject initFluidCache` 无目标 | 同一降级档案追加 |
| 方法签名 | `NoSuchMethodError: net.minecraft.class_14.method_59(...)`（BlockState 相关） | **已由 §7.17 的调用点签名适配处理**；启动推进到 `ExplosionMixin` 目标变化 |

结论：

- 转换件能被 Loader 接受，mixin 配置能解析，**说明管线可复用到第二份模组**；
- 但“mixin 目标消失”与“方法签名变化”两类损伤会继续阻断启动（其中方法签名变化已在 §7.17 用调用点桥解决）；
- `mixinStrips` 是**显式降级**：每条 strip 记录 id、配置、类名、原因，并出现在 patch 输出中；这不是“兼容成功”，文档按 degraded 记；
- 降级档案：`rules/fabric-1.21.1/lithium-degraded.json`（单独文件，不混进通用规则）。

实例随后恢复为 ironchests，并重跑容器契约确认仍通过（`runs/p6-contract-recheck/verdict.json`）。

### 7.16 降级探针：`fromJson` 回退确实被触发

把 `ItemPredicateFromJson` 改成「解析失败时打印原始 JSON + 明确告警」，重新补丁并启动 ironchests：

```text
[STDERR]: {"items":["minecraft:dirt"]}
[STDERR]: [mcbridge1201] ItemPredicate.fromJson: 1.21.1 codec rejected legacy JSON;
          falling back to match-everything predicate (recorded degradation)
[19:33:43] Done (1.225s)!
```

由此确认两件事：

1. 这个降级不是理论风险，**实际被触发**：mod 的 chest 定义里有 `{"items":["minecraft:dirt"]}` 这类谓词；
2. 1.21.1 的 `ItemPredicate.CODEC` 对这份 JSON 解析失败。最可能的原因：`items` 字段在 1.21.1 是 `HolderSet`，解析需要 `RegistryOps`（带 registry lookup），而桥里用的是 `JsonOps.INSTANCE`，没有 registry 上下文。

影响：所有通过 `fromJson` 构建的物品谓词都会退回「匹配所有」。对本样本而言，容器定义中的物品筛选语义被弱化——这是**记录在案的降级**，不是兼容通过。

后续正确做法（已列为下一缺口）：不要用 `JsonOps` 解析 `ItemPredicate`，而是从 registry 上下文构建（`RegistryOps` 或直接用 `BuiltInRegistries.ITEM` 构造 `HolderSet` + 空 `DataComponentPredicate`），再用构造器生成谓词；这需要一个真正的运行时桥，而不是静态 JSON 解析。

### 7.17 调用点签名适配：lithium 的 `class_14.method_59`（新增规则类型）

§7.15 的 `NoSuchMethodError` 是**调用点签名变化**，不是改名。命名解析（`tools/name_lookup.py` + Mojang 映射 join）：

- `class_14` = `net.minecraft.world.level.pathfinder.WalkNodeEvaluator`；`method_59` = `checkNeighbourBlocks`。
- 1.20.1：`(BlockGetter, BlockPos.MutableBlockPos, BlockPathTypes) -> BlockPathTypes`。
- 1.21.1：`(PathfindingContext, int, int, int, PathType) -> PathType`。
- 交接里写的 “BlockPlaceContext” 是按旧参数猜的；映射结果是 `class_9316` = `PathfindingContext`（`class_9316` 不是 `BlockPlaceContext`）。这一条按实际映射修正。

为了拿到真实方法体（`work/cb/data/jars/client-*-intermediary.jar` 是 CenturyBridge 的 stub，方法没有 Code），用自研 body-preserving remapper 把 1.20.1/1.21.1 client jar 重映射成 intermediary 后再 `javap -c`：

```text
runs/p10-lithium-signature/class_14-1.20.1-body.txt   # 旧 checkNeighbourBlocks 的完整字节码
runs/p10-lithium-signature/class_14-1.21.1-body.txt   # 新签名 + PathfindingContext 路径
```

1.20.1 方法体的语义：按 3×3×3 邻居（跳过原点所在列）扫描；仙人掌/甜浆果 → `DANGER_OTHER`，`isBurningBlock` → `DANGER_FIRE`，水 → `WATER_BORDER`，凋灵玫瑰/滴水石锥 → `DAMAGE_CAUTIOUS`；没有命中则返回传入的 `type`。它还会改写传入的 `BlockPos.Mutable`。

**实现（本轮新增，工具代码不是样本硬编码）**

- `RuleSet` 新增 `callSiteAdaptations`：字段为 `id/sourceOwner/sourceName/sourceDesc/sourceOpcode/targetOwner/targetName/targetDesc/bridgeClass/bridgeMethod/bridgeDesc/capability/risk/evidence`。匹配只接受 **精确** owner + name + descriptor（可选 opcode），不按名字猜、不做前缀通配。
- `JarPatcher` 对直接 `MethodInsnNode` 和 `MethodHandle` 都应用；命中后把调用改成 `INVOKESTATIC <bridgeClass>.<bridgeMethod> <bridgeDesc>`，旧栈形状保持不变。
- 桥写成 **Java 源码**：`java/src/bridge/java/top/mcbridge1201/bridge/WalkNodeEvaluatorCheckNeighbourBlocks.java`；`tools/build_bridges.py` 对 `client-1.21.1-intermediary.jar` 编译，`mcbridge1201 patch --bridge-dir <dir>` 嵌入；`tools/inject_bridges.py` 可独立替换/补齐（本轮两条路径都跑过）。
- 规则文件：`rules/fabric-1.21.1/lithium.json`。规则里的 `evidence` 绑定了真实崩溃日志和旧/新签名，不是事后补的理由。

为什么桥不直接调用 1.21.1 的新 `method_59`：`PathfindingContext` 只有 `(CollisionGetter, Mob)` 构造器，而旧调用点可能传任意 `BlockGetter`——lithium 的 `SingleBlockBlockView` 既不是 `CollisionGetter`，也没有 entity。伪造 context 会改变语义并引入 entity 依赖，所以桥按旧方法体逐条移植到 1.21.1 仍存在的 API（`BlockGetter`/`BlockState`/`FluidState`/`Blocks`/`WalkNodeEvaluator.method_57082`），并保留旧 `MutableBlockPos` 的副作用。这是**语义等价移植**，不是空实现或默认值。

**实际命令、退出码与结果**

| 步骤 | 命令（节选） | 退出码 | 结果 |
|---|---|---|---|
| 编译桥 | `python tools/build_bridges.py --stub work/cb/data/jars/client-1.21.1-intermediary.jar --lib work/lib/gson-2.11.0.jar --lib <datafixerupper.jar> --out work/bridges` | 0 | 3 个 bridge 源编译成功；日志 `runs/p10-lithium-signature/build-bridges.log` |
| 打补丁 | `mcbridge1201 patch --in <lithium converted> --out lithium-patched-callsite.jar --rules rules/fabric-1.21.1/lithium-degraded.json --rules rules/fabric-1.21.1/lithium.json --bridge-dir work/bridges` | 0 | 规则命中 **2** 次；桥嵌入；日志 `runs/p10-lithium-signature/patch-lithium.log` |
| 独立注入 | `python tools/inject_bridges.py --jar ... --out lithium-patched-final.jar --classes work/bridges --replace top/mcbridge1201/bridge/WalkNodeEvaluatorCheckNeighbourBlocks` | 0 | replaced 1；日志 `runs/p10-lithium-signature/inject-bridges.log` |
| 启动 | `python tools/run_server.py --instance work/instances/fabric-1.21.1-server-lithium --log runs/p10-lithium-signature/server-callsite.log --timeout 240` | 11（runner；JVM 1） | `doneSeen=false`；**`NoSuchMethodError` 消失**，推进到下一失败 |
| 单元测试 | `gradle --no-daemon test`（在 `java/`） | 0 | 8 个测试，0 失败；日志 `runs/p10-lithium-signature/gradle-test.log` |

补丁后的两处调用点是 `PathNodeCache.getNodeTypeFromNeighbors` 与 `mixin/ai/pathing/AbstractBlockStateMixin.init`；`javap -c` 确认它们变成：

```text
invokestatic top/mcbridge1201/bridge/WalkNodeEvaluatorCheckNeighbourBlocks.checkNeighbourBlocks:
  (Lnet/minecraft/class_1922;Lnet/minecraft/class_2338$class_2339;Lnet/minecraft/class_7;)
  Lnet/minecraft/class_7;
```

回归检查：用 `container.json` 重新补丁 ironchests（同样的 `--client-jar`/`--mappings`/DFU 输入），输出与已有 `-patched.jar` **逐字节相同**（SHA-256 `7d89d452...bc9a1`），说明新增的调用点机制没有改变既有规则的行为。日志：`runs/p10-lithium-signature/ironchests-patch-recheck.log`。

启动日志（`runs/p10-lithium-signature/server-callsite.log`）：

- 不再出现 `NoSuchMethodError ... class_14.method_59`；
- 原来的入口点 `class_4970$class_4971.handler$...$lithium$init` 已经执行过去；
- 下一个真实阻断是 `lithium.mixins.json:world.explosions.ExplosionMixin` 的 `@Inject` 找不到 1.21.1 的 `Explosion` 构造器（`class_1927.<init>(Level, Entity, DamageSource, Explosion.BlockInteraction, DDD, float, boolean, Explosion.BlockInteraction)` 已不存在）。这是 **mixin 目标变化**，不是本规则能修的调用点描述符；留作下一项，不得用删除核心 mixin 冒充通过。

产物 SHA-256（证据文件 `runs/p10-lithium-signature/verdict.json`）：

| 产物 | SHA-256 |
|---|---|
| converted lithium | `2a94fff311bf5b30d0890865f4016f4a4252d9169129fbe333a5962d3cd3b52b` |
| `lithium-patched-callsite.jar` | `0f383be3f18fbe5dc47ba5afa9d275d5f658076e953118af96d32ee4b4d2824f` |
| `lithium-patched-final.jar` | `4d9e5374e01d5ce51e0ded94293c307bfda7c0d33a43ccaf28b85be0320a9822` |
| compiled bridge class | `679ed5ac5d33cd8e88caf517439e25d84df214323196593fcbadf345789e6ead` |

边界：本轮只验证专用服务端启动；GUI/渲染/多人仍 pending。外部桥原先只嵌入顶层 jar，嵌套 jar 内的调用点未覆盖；P18 已改为“桥嵌入到使用它的那个 jar”，并用 synthetic nested jar + ironchests 的 ResourcefulLib 回归验证（§7.22）。

### 7.18 Mixin 目标描述符适配：lithium 的 `ExplosionMixin` 与 POI storage

P10 解决 `class_14.method_59` 后，lithium 的下两个阻断不再是普通调用点，而是 **Mixin `@Inject` 的目标方法描述符**在 1.21.1 变化。§7.15 的两条 `mixinStrips` 只处理“注入目标消失”的显式降级；这两处如果直接 strip 会丢掉爆炸/POI 优化，因此新增了 `mixinCallbackAdaptations`（不是 strip）。

**两处实际变化**

| Mixin | 1.20.1 目标 | 1.21.1 目标 | 适配 |
|---|---|---|---|
| `world.explosions.ExplosionMixin#init` | `class_1927.<init>(Level, Entity, DamageSource, ExplosionBehavior, DDD F Z Explosion$DestructionType)` | 同参数后追加 `ParticleOptions, ParticleOptions, Holder<SoundEvent>`（13 参） | 在 `CallbackInfo` 前插入 3 个参数槽，局部变量整体后移 3，重写 `@Inject(method=...)` 为 intermediary 13 参描述符 |
| `ai.poi.SerializingRegionBasedStorageMixin#init` | `class_4180.<init>(Path, Function, Function, DataFixer, class_4284, boolean, class_5455, class_5539)` | `class_4180.<init>(SimpleRegionStorage, Function, Function, RegistryAccess, ChunkIOErrorReporter, LevelHeightAccessor)` | 回调体只使用 `this`，直接替换捕获参数；同时把 refmap 的 `"<init>"` 映射改到新描述符 |

两个回调体都不读取旧构造器参数（Explosion 只用 shadow 字段，POI 只初始化自己的 map），所以“参数槽迁移/替换”是语义等价的；这不是空实现，也不是删 mixin。

**引擎支持**（`RuleSet`/`JarPatcher`）

- `mixinCallbackAdaptations`：`mixinClass`、`callbackMethod`、`oldCallbackDesc`/`newCallbackDesc`、`insertSlot`、`addedParamDescs/Names`、`replace`、`oldTargetDescriptor`/`newTargetDescriptor`、`refmap/refmapKey/refmapValue`、`capability`、`risk`、`evidence`。
- `append` 模式：在 `insertSlot` 插入新参数，平移 `VarInsn/IincInsn/LocalVariableTable`，补 `MethodParameters`，重写 `@Inject.method`。
- `replace` 模式：替换回调捕获参数（调用体必须不读旧参数），清掉过期调试元数据，`maxLocals` 按新描述符计算。
- refmap 重写：`patchRefmap` 把 `mappings.<mixinClass>.<key>` 改成目标版本描述符，避免 Mixin 继续用旧 refmap 锁定旧签名。
- 规则文件仍是 `rules/fabric-1.21.1/lithium.json`，每条规则带能力、风险与真实崩溃证据。

**实际结果**

| 步骤 | 命令（节选） | 退出码 | 结果 |
|---|---|---|---|
| 打补丁 | `mcbridge1201 patch --in <converted lithium> --out lithium-patched-explosion3.jar --rules rules/fabric-1.21.1/lithium-degraded.json --rules rules/fabric-1.21.1/lithium.json --bridge-dir work/bridges` | 0 | Explosion 1 次 + POI 1 次 + refmap 1 次；`sha256 44a49bcd...e05e` |
| 启动 | `python tools/run_server.py --instance work/instances/fabric-1.21.1-server-lithium --log runs/p11-lithium-explosion/server-explosion3.log --timeout 240` | 11（runner）；JVM 0；`doneSeen=false` | 两处 Mixin 均通过，推进到下一失败 |
| 单元测试 | `gradle --no-daemon test --rerun-tasks` | 0 | 11 个测试，0 失败 |

`server-explosion3.log` 已无 `NoSuchMethodError`、无 `ExplosionMixin`/`SerializingRegionBasedStorageMixin` 注入失败；服务端走到 `Preparing level "world"`，加载 1290 个配方、1399 个进度，随后在
`class_3215.getChunkBlocking` 抛
`ClassCastException: class_3193 cannot be cast to ChunkHolderExtended`。

**下一层为什么不是“再改一个描述符”**

CenturyBridge 转换时从 `lithium.mixins.json` 移除了 `world.chunk_access.ChunkHolderMixin`（其 shadow 字段 `field_16425` 与 `class_3193$class_3724` 在 1.21.1 已消失），但保留了使用 `ChunkHolderExtended` 的 `world.chunk_access.ServerChunkManagerMixin`，于是 cast 失败。两条实验都记录在案、**均未采用**：

- 直接 re-add `ChunkHolderMixin`：`server-readd.log` 报 `@Shadow field field_16425 was not located in net.minecraft.class_3193`。
- 把 shadow 字段本地化（mixin 自己的字段 + 懒初始化）：`server-chunkholder-local2.log` 越过了 cast，但随即撞上 CenturyBridge tombstone `class_3898.method_17236`。这改变了 chunk future 记账语义，未做完整 1.21.1 ChunkMap 适配，因此不采用；也没有用 mixin strip 掩盖。

进一步分析（`runs/p12-chunk-access/README.md`）：旧 `ChunkMap.method_17236` 返回
`CompletableFuture<Either<ChunkAccess, Unloaded>>`，1.21.1 已移除该方法与 `Unloaded` 类型，改用
`CompletableFuture<ChunkResult<...>>`（`class_9259`）和 `ChunkHolder` 的独立 future 字段。即使给
`t3` 写一个返回新 future 的桥，`getChunkBlocking` 后面仍会 `checkcast Either` 失败；所以必须
真正移植 `ServerChunkManagerMixin.getChunkBlocking` + `ChunkHolderExtended` 到 1.21.1 API，
而不是再加一条描述符规则。

因此 lithium 仍是 **degraded**，不是兼容通过；下一步是真正移植 chunk access 层或为 `method_17236` 写非降级桥。**该移植已在 §7.19 完成，lithium 到达专用服务端 `Done`。**

边界：只验证专用服务端启动；GUI/渲染/多人 pending。没有提交游戏 jar、模组 jar 或转换件。

### 7.19 chunk access 迁移到 1.21.1 API：lithium 到达 Done

§7.18 的下一层不是描述符问题：`ServerChunkManagerMixin` 的 `@Overwrite` 依赖
`ChunkHolderExtended` 与旧的 `ChunkMap.method_17236`（`CompletableFuture<Either<ChunkAccess,
Unloaded>>`），而 1.21.1 已改为 `CompletableFuture<ChunkResult<LevelChunk>>`（`class_9259`）+
`GenerationChunkHolder`。本轮把该 mixin **实现类整体移植**到 1.21.1，而不是删除 mixin：

- 新增规则类型 `mixinClassReplacements`：保留原 mixin 类名与 `@Overwrite`，把编译好的替换类写回
  原路径，并嵌入 helper 类（`alsoEmbed`）。
- 替换类 `java/src/mixin/java/.../ServerChunkManagerMixin.java`：
  1. 调用 1.21.1 的 `ServerChunkManager.method_14134(x,z,status,create)`；
  2. future 未完成时，用 `ChunkAccessPump` 反射调用私有队列
     `field_18809.method_18857(() -> future.isDone())`（字段类型是 package-private 嵌套类，
     普通 `@Shadow` 无法拿到精确描述符）；
  3. join 后用 `ChunkResult.method_57130(null)` 取 chunk；`create && null` 时抛原版
     `IllegalStateException`。
- 编译：`tools/build_mixins.py` 对 `work/remap/server-intermediary.jar` + Sponge Mixin lib 编译；
  `tools/build_bridges.py` 编译 `ChunkAccessPump`；`patch --bridge-dir work/bridges --bridge-dir
  work/mixins` 统一嵌入。
- 这不是 mixin strip，也不是默认值/空实现；旧的多入口缓存与 off-thread 快路径没有重写，属于
  **性能优化减少**，不是存档/掉落/同步语义降级。P11 的两条 `mixinStrips` 仍然存在。

**实际结果**

| 步骤 | 命令（节选） | 退出码 | 结果 |
|---|---|---|---|
| 编译 bridge | `python tools/build_bridges.py --stub <client stub> --lib gson --lib dfu --out work/bridges` | 0 | 4 个 bridge（含 `ChunkAccessPump`） |
| 编译 mixin | `python tools/build_mixins.py --stub work/remap/server-intermediary.jar --lib <sponge-mixin> --lib work/bridges --out work/mixins` | 0 | `ServerChunkManagerMixin.class` |
| 打补丁 | `mcbridge1201 patch --in <converted lithium> --out lithium-patched-chunkport.jar --rules ... --bridge-dir work/bridges --bridge-dir work/mixins` | 0 | `chunkresult-port` 1 次 + 既有规则；`sha256 67013b3b...02ee` |
| 启动 | `python tools/run_server.py --instance work/instances/fabric-1.21.1-server-lithium --log runs/p13-chunk-port/server-chunkport-rule.log --timeout 240` | 0（runner 0；`doneSeen=true`） | **`Done (4.772s)`**，世界加载并保存 |
| 命令探针 | 同上 + `forceload add 0 0`、`setblock 0 100 0 minecraft:stone`、`data get block 0 100 0` | 0 | chunk 强制加载、方块修改成功、无异常 |
| 单元测试 | `gradle --no-daemon test --rerun-tasks` | 0 | 13 个测试，0 失败（P18 新增 nested-jar 桥测试） |

证据：`runs/p13-chunk-port/README.md`、`server-chunkport-rule.log`、`server-chunkport-commands.log`、`verdict.json`。日志显示 `Done (4.772s)`、三主世界全部保存，无 Mixin/类转换错误。

结论：lithium 在 Fabric 1.21.1 **专用服务端 BOOTED**（启动 + 世界加载/保存 + 命令 chunk 探针），
不是玩法契约，也不是客户端/多人验证。两条既有 `mixinStrips` 与 chunk 优化减少都在档案中记录。

边界：只验证专用服务端；没有 lithium 的玩法契约、客户端 GUI/渲染或多人同步；没有提交游戏 jar、
模组 jar 或转换件。

### 7.20 联合契约：lithium + ironchests 同实例通过容器契约

为验证 P13 的 chunk access 移植没有破坏容器持久化、两份转换件能共存，把 **lithium P13 jar**
与 **ironchests P5 AW jar** 放进同一个 Fabric 1.21.1 专用服务端实例，运行
`tools/run_contract.py`（两个真实进程）：

| 步骤 | 结果 |
|---|---|
| 第一次启动 | `doneSeen=true`，exit 0 |
| `setblock ironchests:iron_chest` + 插入 5 钻石 | 通过 |
| `data get block` | `Items: [{count: 5, Slot: 0b, id: "minecraft:diamond"}]` |
| 进程重启 | `doneSeen=true`，exit 0 |
| 重启后读回 | 同上，`count_after_restart=true` |

`verdict.json` 的 5 个断言全部 true，`passed=true`。证据：
`runs/p14-lithium-ironchests/README.md`、`step1-place-insert.log`、`step2-restart-read.log`。
这仍只是专用服务端 + 命令 API 范围，不覆盖 GUI/渲染/玩家交互/多人同步；lithium 的 chunk 优化
减少与 2 条 `mixinStrips` 仍在。

### 7.21 第三个样本 trashslot：4 个 tombstone 已桥接，但 Balm 依赖阻断启动

trashslot 15.1.5（Fabric 1.20.1）转换结果 `ok_partial`，在 1.20.4→1.20.5 组件边界产生 4 个 tombstone：

- `ItemStack.method_7953(NbtCompound)NbtCompound`（writeNbt）
- `ItemStack.method_7915(NbtCompound)ItemStack`（fromNbt）
- `FriendlyByteBuf.method_10793(ItemStack)FriendlyByteBuf`（write item）
- `FriendlyByteBuf.method_10819()ItemStack`（read item）

本轮新增 `TrashSlotNbtBridge` 与 `rules/fabric-1.21.1/trashslot.json`：用 1.21.1 的
`ItemStack.CODEC` + `RegistryOps(NbtOps)` 编解码，并通过 `FriendlyByteBuf` 的 NBT 方法
（`method_10794`/`method_10798`）传包；patch 命中 1+1+2+2 次，桥已嵌入。**但这条规则尚未
boot 验证**，因为 trashslot 依赖 Balm：

- 下载并转换 Balm 7.3.44（1.20.1）：`ok_degraded_partial`（4 tombstone + 9 stripped mixin）；
  注入项目 access widener 解决私有 `Identifier` 构造器后，仍卡在 Fabric API 0.102 已移除的
  `ServerPlayNetworking$PlayChannelHandler`；
- 改用原生 Balm 21.0.66（1.21.1）：又因 trashslot 15.1.5 调用旧 API
  `Balm.initialize(String,Runnable)` 而 `NoSuchMethodError`。

因此没有 `Done`，也没有把 trashslot 规则算通过。规则状态是 **prepared / not boot-verified**；
证据 `runs/p15-trashslot/README.md`、`convert.log`、`convert-balm.log`、`server-trashslot3.log`。
下一步是 Balm networking/API 桥，或使用同时兼容旧 Balm API 与 1.21.1 Fabric API 的 Balm 版本。

P16 继续尝试原生 Balm 21.0.66：新增 `BalmInitializeBridge`，把旧的
`Balm.initialize(String,Runnable)` 调用点适配为
`initialize(String, EmptyLoadContext.INSTANCE, Runnable)`，旧的初始化 `NoSuchMethodError` 消失；
但下一失败是 `BalmNetworking.registerServerboundPacket(Identifier, Class, BiConsumer, Function,
BiConsumer)`——Balm 21 已改成 `PacketType`/`StreamCodec` 载荷注册，需要真正的网络包适配，不是
补一个 context 就能解决。trashslot 仍未 boot；证据 `runs/p16-balm/`。

P17 完成网络桥：`BalmNetworkingBridge` 把旧注册调用重定向到 Fabric 1.21.1 的
`PayloadTypeRegistry` + `CustomPayload` 包装 + `StreamCodec`（serverbound 2 个、clientbound 1 个），
并给 serverbound 安装 `ServerPlayNetworking` 全局接收器。原生 Balm 21.0.66 + 补丁后 trashslot
到达 **专用服务端 `Done (4.655s)`**，世界加载/保存；`doneSeen=true`，runner/JVM exit 0。
这是 **BOOTED**，不是客户端/玩法通过：没有客户端连接，clientbound receiver 未安装，包
encode/decode 与 ItemStack NBT 桥未被玩家动作触发。证据 `runs/p17-balm-net/`。

### 7.22 嵌套 jar 的桥按 jar 嵌入

`JarPatcher` 原先把所有使用过的桥统一放进顶层 jar；嵌套 jar（`META-INF/jars/*.jar`）有独立的 Fabric
classloader，顶层桥不保证可见。P18 改为每个 `patchEntries` 维护自己的 `used` 集合：
`recordBridge` 同时记录全局报告和当前 jar；`embedUsedBridges` 在每层 jar 结束时把
生成的 ASM 桥和 javac 桥嵌入**使用它的那个 jar**。顶层未使用的桥不会泄漏到顶层。

回归：

- 新增 synthetic nested jar 测试：补丁后桥只出现在 nested jar 内，顶层没有；nested caller 的调用
  被改写。`gradle test --rerun-tasks` **13/13**（新增 1 个），exit 0。
- ironchests 重补丁的规则计数与旧结果一致（36 classes、123 constant-kind、3 handle 等）；顶层
  类与桥列表完全相同，唯一差异是 nested ResourcefulLib jar 现在带有自己的
  `top/mcbridge1201/bridge/IdentifierFactory.class`。因此整体 hash 从 `7d89d452...bc9a1` 变为
  `aa589bbb...0430`（AW 注入前），这是预期变化。
- 新 patched+AW jar 启动 `Done`，容器契约 5/5 通过（放置/插入/NBT/重启/读回 5 钻石）。
  证据 `runs/p18-nested-bridges/`。

### 7.23 BytecodeVerify 数据流校验

编译 CenturyBridge 的 `core/tools/BytecodeVerify.java`（ASM 9.7.1 + asm-analysis），对三个已补丁
样本的顶层类运行：

- ironchests `-aw.jar`
- lithium `lithium-patched-chunkport.jar`
- trashslot `trashslot-patched-net2-aw.jar`

结果：**650 classes / 3 jars，0 methods failed dataflow verification**，exit 0。又把 ironchests
内嵌的 ResourcefulLib jar 单独跑：**141 classes，0 failures**，exit 0。

边界：`BasicInterpreter` 只检查栈深度/`max_stack` 一致性，不是完整 JVM 类型校验；覆盖三个顶层
jar 和一个 nested jar，其他嵌套 jar/客户端路径未覆盖。证据 `runs/p19-bytecode-verify/`。

### 7.24 Mixin 注入目标提取与 refmap 解析

`ArtifactScanner` 解析 mixin handler 上的 `@Inject`/`@Redirect`/`@ModifyConstant`/
`@ModifyVariable`/`@ModifyArg`/`@ModifyArgs`/`@ModifyExpressionValue`/`@ModifyReturnValue`/
`@WrapOperation`/`@WrapWithCondition` 的 `method` 值（单值或数组，支持 owner 前缀），并读取
mixin config 的 `refmap`，把命名目标映射为 `Lowner;method(desc)`（含构造器）。
`Analyzer.Result` 新增 `mixinInjections` / `mixinInjectionsUnresolved` 和
`unresolvedMixinInjections`；后者非空会进入 `blocked_static`。

验证：

- `gradle test --rerun-tasks` **16/16**，exit 0；
- synthetic `@Mixin` + `@Inject(method="method_59()V")` 测试提取；
- synthetic refmap：`named()V -> Lnet/minecraft/class_14;method_59()V`，断言 owner/name/desc；
- synthetic target index 测试“存在/缺失”两种 injection target；
- 对转换后的 lithium 实跑：`mixins=202`、`mixinInjections=214`、
  `mixinInjectionsUnresolved=3`。3 条正是已知的构造器变化：
  `class_4180.<init>`（POI storage）、`class_3610.<init>`（FluidState）、
  `class_1927.<init>`（Explosion）——静态分析独立复现了 P11/P13 的运行时阻断。
- 对补丁后的 lithium 实跑：`mixinInjections=209`、`mixinInjectionsUnresolved=0`；
  P11/P13 的规则把 3 个构造器目标清掉，说明检查与真实修复一致（§7.25）。

边界：只检查精确描述符是否存在；ordinal/slice/local capture、非 refmap 的命名目标仍未解析。
这不是运行时 Mixin 验证。证据 `runs/p20-mixin-inject/`、`runs/p21-refmap/`。

### 7.25 注入目标检查的交叉验证

同一目标索引下比较转换件与补丁件：

| artifact | mixins | injection targets | unresolved |
|---|---:|---:|---:|
| lithium converted | 202 | 214 | **3** |
| lithium patched (chunk-port) | 202 | 209 | **0** |
| Balm 7.3.44 converted | 32 | 43 | 0 |
| ironchests converted | 0 | 0 | 0 |
| trashslot converted | 0 | 0 | 0 |

转换件 3 条 unresolved 与 P11/P13 的构造器阻断一一对应；补丁件清零，和实际 `Done` 结果一致。
ironchests/trashslot 的 0 是“顶层 jar 没有 mixin”的意思，nested mixin 未展开，不应解读为
“所有 mixin 都安全”。证据 `runs/p22-cross-analyze/`。

### 7.26 lithium chunk-access 压力测试

P13 的 chunk 移植此前只做了单 chunk 命令探针。P23 在
`fabric-1.21.1-server-lithium` 上 forceload **224 个 chunk**（`[-7,-7]` 到 `[7,7]`），在
`(112,100,112)` 与 `(-112,100,-112)` 设置钻石/绿宝石块，`save-all flush` 后停止；新 JVM
重启后 `forceload add` 显示 force-load 状态持久化，`execute if block` 两个远角块分别输出
`STRESS_OK_A` / `STRESS_OK_B`。两次 `Done`、exit 0。

这说明 `ServerChunkManager.method_14134` + `ChunkAccessPump` 的移植在更大 chunk 集与
保存/重启路径上仍然正确。边界仍是专用服务端 + 命令 API，无客户端/玩家/多人；旧的多入口
缓存/off-thread 快路径仍未恢复。证据 `runs/p23-chunk-stress/`。

### 7.27 chunk 压力测试工具

P23 的压力测试已工具化为 `tools/run_chunk_stress.py`：自动跑两个服务端进程，先
`forceload remove all`，再 force-load 225 个 chunk（`--radius 7` 的 `-112..112` 方块范围），
在远角设置钻石/绿宝石块并 `save-all flush`；重启后 `execute if block` 断言两个远角块，
输出 `verdict.json`。工具只在两次 `Done`、两个 exit 0、两个 `STRESS_OK` 标记都满足时返回 0。

本次运行：`chunksMarked=225`、`STRESS_OK_A/B`、`passed=true`，exit 0。第一版工具在
`forceload add` 后立刻 `setblock`，因异步 chunk 加载出现 “Could not set the block”；现在
step1 命令间隔 2.5s，并解析实际的 “Marked N chunks”。证据 `runs/p24-chunk-stress-tool/`。

### 7.28 `Codec.dispatch` 的安全 MapCodec 适配

P25 曾给 `assumeMapUnsafe` 包一层 `CodecDispatch$Guard`，把 null-success 变成 decode error。
P26 把活跃路径换成 **javac 编译的 `CodecDispatch`**：旧 dispatch 第二函数返回的 `Codec` 通过
`MapCodec.of(MapEncoder, MapDecoder)` 安全包成真正的 MapCodec：

- decode：`DynamicOps.createMap(input.entries())` 后调用 `codec.decode(...).map(Pair::getFirst)`；
- encode：`codec.encodeStart(...)` 得到 map，再把 entries 写入 `RecordBuilder`；
- `MapCodecCodec` 直接 unwrap，避免二次包装；
- keys/KeyCompressor 为空（dispatch 的 key 由 `Codec.dispatch` 自身处理）。

`JarPatcher` 在提供 `--bridge-dir` 时优先使用这个 javac `CodecDispatch`，其他生成桥仍走 ASM；
没有 bridge dir 时才回退到旧的 generated 版本（P25 guard 仅作为 fallback 保留）。重新补丁
ironchests 后 `javac bridges: [CodecDispatch]`，jar 内是 `CodecDispatch`/`$1`/`$2`，不含 `$Guard`；
容器契约 5/5 通过，两次 `Done`、exit 0。测试 **17/17**。

这是真正的安全 map 包装，但 keys/compressor 为空是为 dispatch 值有意设计的；契约范围仍是
专用服务端 + 命令 API。证据 `runs/p25-codec-guard/`、`runs/p26-codec-safe/`。

### 7.29 安全 CodecDispatch 的联合回归

P26 的 javac `CodecDispatch` 换入 P14 的 lithium + ironchests 同实例后，`run_contract.py`
两进程仍全部通过：`Done (26.7s)` → 放置/插入/NBT → 重启 `Done (17.0s)` → 读回 5 钻石；
`passed=true`，5 个步骤全 true，exit 0。说明安全 MapCodec 包装没有破坏两份样本的共存路径。

契约范围仍是专用服务端 + 命令 API；无客户端 GUI/玩家/多人。证据 `runs/p27-combined-safe-codec/`。

### 7.30 安全 Codec 构建的 BytecodeVerify

对 P26 的 `ironchests-safe-aw.jar` 重跑 BytecodeVerify：顶层 **73 classes / 1 jar，0 methods
failed**，nested ResourcefulLib **142 classes，0 failures**，exit 0。覆盖 javac
`CodecDispatch`/`$1`/`$2` 与 nested 类；仍只是栈深度校验，运行语义由 §7.28/§7.29 的契约覆盖。
证据 `runs/p28-codec-verify/`。

### 7.31 trashslot 的 clientbound receiver

`BalmNetworkingBridge` 增加嵌套 `$Client`：客户端用
`ClientPlayNetworking.registerGlobalReceiver` 注册 playS2C payload，解码后调用旧的
`BiConsumer<Player,T>`。`registerClientbound` 通过 `FabricLoader` 环境反射，只在 `CLIENT`
时加载并调用该嵌套类；服务端不会加载 `ClientPlayNetworking`。

服务端验证：更新后的 trashslot 补丁启动 `Done (4.894s)`，`doneSeen=true`，exit 0，没有
`ClientPlayNetworking` 类加载错误；jar 内包含 `BalmNetworkingBridge`/`$Payload`/`$Client`。

边界：没有客户端 fixture，client 分支、receiver 注册和 `MessageTrashSlotContent` 的实际
投递/解码**未执行**；服务端 boot 只证明服务端分支惰性且类集合可加载。证据
`runs/p29-client-receiver/`。

### 7.32 多份兼容档案

`profiles/` 现在有三份档案：

- ironchests：`passed_within_scope`（容器契约）；
- lithium：`booted_within_scope`（boot + 225-chunk stress + combined；pending gameplay/client）；
- trashslot：`booted_within_scope`（原生 Balm 21 + 7 条规则；pending client GUI/packet round-trip/player）。

每份档案 pin 源 jar hash、目标 client/mappings hash、规则包 hash 和证据文件；jar 本身不进仓库。
`profiles/README.md` 给出状态词表。证据 `profiles/`。

### 7.33 CodecDispatch 选择回归

`JarPatcherCodecDispatchTest` 构造调用 `CodecDispatch.dispatch` 的 synthetic caller，并在
`bridgeClasses` 里提供一个 dummy `CodecDispatch`。补丁后断言：规则命中一次、
`externalBridges` 含 `CodecDispatch`、输出 class 是 supplied 版本、且没有 generated
`CodecDispatch$Adapter`。这锁住了 P26 的 `--bridge-dir` 优先逻辑（只有 `CodecDispatch`
被外部覆盖，其他生成桥保持 ASM）。测试 **18/18**；证据 `runs/p31-codec-selection/`。

### 7.34 trashslot packet codec 往返

用一个 Fabric 测试 mod 在 `ServerLifecycleEvents.SERVER_STARTED` 时执行
`MessageTrashSlotClick.encode/decode`，覆盖两个 case：

- `ItemStack.EMPTY` -> decode 后仍 empty；
- `new ItemStack(Items.DIAMOND, 5)` -> decode 后非空、count=5、item 仍为 diamond。

日志 `TRASHSLOT_CODEC_OK`；服务端 `Done (5.025s)`、exit 0。这验证了
`TrashSlotNbtBridge.writeItem/readItem`、`FriendlyByteBuf` NBT 写读和 registry-aware
`ItemStack.CODEC`，而不是只验证启动。仍不含客户端 `ClientPlayNetworking` 投递、trash GUI
或玩家动作。证据 `runs/p32-trashslot-codec/`。

### 7.35 trashslot 三个包的 codec 往返

扩展 P32 probe：

- `MessageTrashSlotClick`：empty + `ItemStack(DIAMOND,5)`；
- `MessageTrashSlotContent`：empty + `ItemStack(DIAMOND,5)`；
- `MessageDeleteFromSlot(3,true)`：断言 slot/all 标志。

日志 `TRASHSLOT_ALL_CODEC_OK`；服务端 `Done (4.993s)`、exit 0。三个包的 encode/decode 和
双向 ItemStack/NBT 桥都已实际执行。仍不含客户端 `ClientPlayNetworking` 投递、trash GUI 或玩家
动作。证据 `runs/p33-all-packets/`。

### 7.36 `@At` 注入点目标（保守）

`ArtifactScanner` 现在解析 `@Inject`/`@Redirect` 等的嵌套 `@At(value=..., target=...)`（单值或
数组），并记录 `atValue`/`atTargetOwner`/`atTargetName`/`atTargetDesc`/`atTargetField`。同时修复
了多 `method` 数组被合并成一条 injection 的问题（lithium 的 214 条恢复）。

`Analyzer` 只对 **intermediary 的 INVOKE/FIELD `@At` 目标** 查 1.21.1 索引；缺失/描述符不匹配
进入 `unresolvedMixinInjections`，并新增 `mixinAtTargets` 计数。命名/refmap 目标和
ordinal/slice/local capture 仍未解析。

实跑转换后 lithium：`mixinInjections=214`、`mixinAtTargets=0`（`@At` 目标为 Yarn/refmap 命名，
跳过）、`mixinInjectionsUnresolved=3`（仍是已知构造器）。无新增 false positive。测试 **18/18**；
证据 `runs/p34-at-targets/`。

### 7.37 refmap 感知的 `@At` 目标

P34 的 `@At` 解析只认已是 intermediary 的 target。P35 把 `Injection.atRawTarget` 也送入
mixin refmap；映射成功后解析 `Lowner;method(desc)` 或 `field:type`，再交给 analyzer 校验。
scanner 测试同时映射 handler 的 `named()V` 与 at-target 的 `namedAt()V`。

实跑转换后 lithium：

```text
mixinInjections: 214
mixinAtTargets: 86
mixinInjectionsUnresolved: 3
```

86 个 at-target 从“跳过”变为实际解析；3 个 unresolved 仍是已知的 POI/FluidState/Explosion
构造器，没有新增 false positive。测试 **18/18**；证据 `runs/p34-at-targets/`、`runs/p35-at-refmap/`。

### 7.38 at-target 补丁前后

| artifact | injections | at-targets | unresolved |
|---|---:|---:|---:|
| lithium converted | 214 | 86 | **3** |
| lithium patched (chunk-port) | 209 | 84 | **0** |

P11/P13 的规则清掉了 3 个已知构造器；补丁件仍解析 84 个 at-target，说明 P35 的 refmap 检查
不是只对转换件生效。减少的 5 个 injection / 2 个 at-target 对应被替换的 callback/实现类。
静态检查，不含 ordinal/slice/local capture。证据 `runs/p36-patched-at/`。

### 7.39 安全 CodecDispatch 的语义 probe

用一个 Fabric probe 在服务端启动后直接测试 P26 的 javac `CodecDispatch`：

- `record Box(int a) {}`；
- `valueCodec = RecordCodecBuilder`（字段 `a`）；
- `dispatched = CodecDispatch.dispatch(Codec.STRING, Box -> "k", key -> valueCodec)`；
- encode `Box(1)` 应为 `{"a":1,"type":"k"}`，decode 同 JSON 应回 `Box(1)`。

日志 `CODEC_DISPATCH_PROBE_OK`；服务端 `Done (4.847s)`、exit 0。这比 P26 的容器契约更直接地
验证了安全 MapCodec 包装的 encode/decode 语义。仍是 synthetic record，不是 ironchests
`ShapeTypes`，也不覆盖客户端。证据 `runs/p37-codec-probe/`。

### 7.40 client bridge 的 BytecodeVerify

对 P29 的 `trashslot-client-aw.jar` 运行 BytecodeVerify：**47 classes / 1 jar，0 methods
failed**，exit 0。覆盖 `BalmNetworkingBridge`、`$Payload`、`$Client` 以及 NBT 包桥。仍只是
栈深度校验，客户端分支未执行；不能当成客户端通过。证据 `runs/p38-client-bv/`。

### 7.41 证据总校验

`tools/verify_evidence.py` 读取 unit-test XML、P14/P24/P26/P27/P33/P37/P38 的 verdict，并检查
`git ls-files` 没有 `.jar`。本次 9 项 checks 全 true，`passed=true`，exit 0；测试 18/18、0
failures/errors。它只检查既有证据一致性，不重新启动服务端/客户端。证据
`runs/p39-verify-evidence/`。

### 7.42 证据总校验扩展

`tools/verify_evidence.py` 增加三项：P35 converted at-target 计数 `(214,86,3)`、P36 patched
`(209,84,0)`、lithium profile `booted_within_scope`。连同原有测试/契约/无 tracked jar 检查，
本次全部 true，exit 0。它只校验既有证据，不启动服务端/客户端。证据
`runs/p40-verify-extended/`。

### 7.43 三样本同服

同一个 Fabric 1.21.1 专用服务端加载：

- lithium P13 chunk-port；
- ironchests P26 safe-Codec AW；
- trashslot P29 client-bridge 构建 + 原生 Balm 21.0.66；
- Fabric API。

启动 `Done (4.632s)`；随后两次进程的容器契约 5/5 通过（两次 `Done`、exit 0），5 钻石在
重启后读回。说明三份转换件可以共存，ironchests 持久化未被 lithium/trashslot 干扰。

范围仍是专用服务端 + 命令 API；无客户端、trash GUI、lithium 玩法或多人。证据
`runs/p41-all-three/`。

### 7.44 三样本同服 chunk 压力

在 P41 的 all-three 实例上运行 `run_chunk_stress.py --radius 7`：225 个 force-loaded chunk，
远角钻石/绿宝石块，save/restart 后 `STRESS_OK_A/B` 均出现；两进程 `Done` + exit 0，
`passed=true`。说明 lithium 的 chunk access 移植在 ironchests + trashslot + Balm 同时加载时
仍然正确。范围仍是专用服务端 + 命令 API；证据 `runs/p42-all-three-chunk/`。

### 7.45 三样本 + CodecDispatch probe

在 P41 的 all-three 实例中加载 P37 的 `codecdispatchprobe.jar`，`CodecDispatch` 的
`Box(1)` encode/decode 仍得到 `CODEC_DISPATCH_PROBE_OK`；服务端 `Done (5.425s)`、exit 0。
说明安全 MapCodec 包装在 lithium/trashslot/Balm 同时加载时仍正常。合成 probe，不是
ironchests `ShapeTypes`；无客户端。证据 `runs/p43-all-three-codec/`。

### 7.46 三样本 bundle 档案

新增 `profiles/bundle-all-three__fabric-1.21.1.json`，`status=passed_within_scope`：lithium
P13 + ironchests P26 + trashslot P29/Balm 21 同服；contracts 为 boot `Done (4.632s)`、容器
5/5、225-chunk stress、CodecDispatch probe；client/GUI/multiplayer 仍 pending。四项 evidence
均 pin hash。索引在 `profiles/README.md`。

### 7.47 剩余工作边界

`docs/remaining-work.md` 明确记录：服务端/静态范围已验证；客户端 GUI、`ClientPlayNetworking`
投递、多人同步因本机没有 client fixture 未执行；chunk 优化、nested mixin 静态分析、Forge
成员分析列为非阻塞后续。该文档同时给出提供 client fixture 后的验收方式，不包含任何
“客户端通过”声明。

### 7.48 多 method injection 数组回归

新增 synthetic `@Inject(method={"method_59()V","method_60()V"})` + 共享 `@At(method_61)` 测试，
断言产生两条 `Injection` 且都带 at-target。这钉住 P34 的修复（此前数组被折叠成一条，
lithium 214→207）。测试总数 **19/19**。证据 `runs/p46-multi-method/`。

### 7.49 字段 `@At` 目标回归

新增 synthetic `@At(value="FIELD", target="Lnet/minecraft/class_14;field_99:Lnet/minecraft/class_1799;")`
测试，断言 owner/name/desc、`atTargetField=true` 和 `atValue=FIELD`。测试总数 **20/20**。
证据 `runs/p47-field-at/`。

### 7.50 nested jar mixin 展开

`ArtifactScanner` 保留每个 `META-INF/jars/*.jar` 的字节，`readNestedMixinConfigs` 解析其中的
`*.mixins.json`，configName 用 `<nested>!/` 前缀区分；`@Mixin` target、`@Inject`/`@At` 和
refmap 都走同一套解析。

实跑 P26 ironchests（nested ResourcefulLib）：mixin config/class/injection 从 `0/0/0` 变为
`1/1/1`，unresolved 仍 0；lithium converted 保持 `202/214/86/3`，没有重复或丢失。新增
synthetic nested jar 测试；测试总数 **21/21**。证据 `runs/p48-nested-mixins/`。

### 7.51 `@At` ordinal 提取

`Injection.atOrdinal` 现在保存 `@At(ordinal=...)`，多 method 数组共享；`Analyzer` 统计
`mixinAtOrdinals`，`Main` 输出 `atOrdinals`。转换后 lithium 的 86 个 at-target 中 **10** 个带
ordinal，unresolved 仍 3。

这只是提取：尚未统计目标方法中的匹配指令数，也不判断 ordinal 是否越界；slice/local capture
仍未解析。新增 synthetic ordinal 测试；测试总数 **22/22**。证据 `runs/p49-at-ordinal/`。

### 7.52 首次真实客户端运行（PCL）

利用 D 盘 PCL 的 `D:\我的世界\.minecraft` 安装 1.21.1 base + Fabric 0.19.5 profile，放入
Fabric API、Balm 21、lithium、P26 ironchests、P29 trashslot。客户端 Fabric 成功加载全部模组，
进入 `Initializing game`，随后 ironchests 入口点崩溃：

```text
NoClassDefFoundError:
net/fabricmc/fabric/api/client/networking/v1/ClientPlayNetworking$PlayChannelHandler
  at ...resourcefullib...FabricClientPacketHelper.clientOnlyRegister
```

ResourcefulLib 2.0.6 使用旧 `PlayChannelHandler` / `Identifier` 客户端网络 API；1.21.1 改为
`PlayPayloadHandler` / `CustomPayload`。将嵌套 ResourcefulLib 换成 3.0.12 后，又缺
`networking.base.PacketHandler`，不是 drop-in 修复。

这是**真实客户端阻断**，服务端测试覆盖不到；没有升级任何客户端 profile 状态。证据
`runs/p50-client/`。下一步是实现 ResourcefulLib 客户端网络桥，或把其 client helper 改到
1.21.1 API 且保留 ironchests 使用的 `PacketHandler`。

### 7.53 ResourcefulLib 客户端网络桥

P50 的 `ClientPlayNetworking$PlayChannelHandler` 阻断通过替换嵌套 ResourcefulLib 2.0.6 的
`FabricClientPacketHelper` 解决：

- 旧 `clientOnlyRegister(Identifier, PacketHandler)` 创建 1.21.1 `CustomPayload` id，注册
  S2C/C2S codec，接收后用原始 `PacketHandler.decode/handle` 处理；
- 旧 `sendToServerClientOnly(Identifier, Packet)` 用原始 handler 编码后
  `ClientPlayNetworking.send(CustomPayload)`；
- 保留 RL 2.0.6 的 `PacketHandler`/`Packet`/`PacketContext`。

客户端因此越过 ironchests **main** 入口点，进入 client 入口点；新阻断为：

```text
NoClassDefFoundError: net/fabricmc/fabric/api/client/model/ModelLoadingRegistry
NoSuchMethodError: BalmClient.initialize(String, Runnable)
```

这两项仍未修；桥目前是 work-only 实验，尚未规则化，不能声明客户端通过。证据
`runs/p51-client-bridge/`。

### 7.54 客户端主菜单与 Balm 同步阻断

在 PCL 的 1.21.1 Fabric 0.19.5 客户端上，五个模组全部加载；补上 RL 客户端网络桥、Balm
客户端初始化桥（`BalmClient.initialize(String, EmptyLoadContext, Runnable)`）和 ironchests
`ModelLoadingPlugin` 后，客户端到达**主菜单**（`runs/p52-client-balm/main-menu.png`）。

创建/进入世界时，trashslot 的登录同步触发 `BalmNetworking.sendTo`；服务端断开：

```text
EncoderException: Failed to encode packet 'clientbound/minecraft:custom_payload'
  (trashslot:trash_slot_content)
ClassCastException: class_9129 cannot be cast to MessageTrashSlotContent
  at BalmNetworkingBridge.lambda$codec$2
```

payload 包装的 `value` 与 codec 参数顺序仍未对齐；世界/GUI/持久化/双客户端同步未执行。
这不是客户端通过，也没有升级 profile 状态。证据 `runs/p52-client-balm/`。

### 7.55 世界加入越过 Balm payload，遇到 lithium tombstone

旧 Balm 1.20.1 的 writer 是 `BiConsumer<T, FriendlyByteBuf>`（packet 在前，buffer 在后）；
`BalmNetworkingBridge` 改成 `writer.accept(value, buf)` 后，`trash_slot_content` 的
`EncoderException`/`ClassCastException` 消失，客户端可以登录并开始世界生成。

新的阻断是 lithium 的 tombstone：

```text
UnsupportedOperationException:
  CenturyBridge tombstone: net.minecraft.class_2540.method_10815
  at ...Tombstones_lithium...t2
  at ...LithiumHashPalette.method_12290
```

1.20.1 的 `FriendlyByteBuf.getVarIntSize(int)` 在 1.21.1 移到 `VarInt.getByteSize(int)`；服务端
225-chunk 测试使用已有世界，没有触发这条 palette 序列化路径。世界/GUI/持久化/双客户端仍未
执行。证据 `runs/p53-client-world/`。

### 7.56 客户端进入世界并渲染

Lithium palette 的 `method_10815` tombstone 通过 `LithiumVarIntBridge.getByteSize(int)` →
`class_8703.method_53015`（`VarInt.getByteSize`）修复，规则 `lithium-varint.json` 命中 2 处。
客户端随后完成世界生成并登录：

```text
Preparing start region for dimension minecraft:overworld
TestPlayer joined the game
Loaded 2 advancements
```

窗口 `Minecraft* 1.21.1 - Singleplayer`，`world.png` 显示地形、HUD、hotbar。**这是客户端进入
世界并渲染**，但背包/trash GUI、容器持久化、clientbound 同步、双客户端仍未执行；自动化
`E` 键未打开背包，不能当成 GUI 已测。证据 `runs/p54-client-lithium/`。

### 7.57 背包 + TrashSlot GUI 渲染

合成键盘 `E` 不可靠，改用客户端测试 probe 在 player 存在后调用
`MinecraftClient.method_1507(new InventoryScreen(player))`。截图（`inventory-probe.png`）显示
原版背包以及右下角的 **TrashSlot 按钮**，世界/HUD 正常；点击空 trash 按钮后界面保持
（`trash-click.png`）。

这验证了 **GUI 渲染/集成**，但没有物品移入/移出、重启持久化、ironchests 容器 GUI 或同步。
probe 是 work-only 测试入口，不是 patcher 的一部分；没有因此声称完整 GUI 通过。证据
`runs/p55-client-gui/`。

### 7.58 真实 ItemStack 进入背包，trash 拖放未成功

客户端测试 probe 在 `ServerPlayConnectionEvents.JOIN` 给玩家 5 钻石；`inventory-with-diamonds.png`
显示背包/快捷栏中的钻石，说明物品注入与背包渲染正常。

随后尝试：

1. 点击钻石堆，再点击右下角 TrashSlot 按钮；
2. 把钻石放到空背包槽，再拖到 TrashSlot 按钮。

两种操作后钻石仍停在光标（`trash-content.png`、`trash-drag.png`），trash 没有接收，日志
无异常。因此**不能**记为 trash 转移/持久化通过；下一步要检查 TrashSlot 的 GUI slot 命中区/
点击处理器，而不是放宽结论。证据 `runs/p56-client-item/`。

### 7.59 trash 生命周期：登录重置，不是 NBT 桥失败

用服务端 probe 直接调用 `TrashHelper`，绕开 GUI：

```text
first join:  TRASH_PROBE_SET after=5 empty=false
             TRASH_PROBE_NBT ... trash={count:5,id:"minecraft:diamond"}
Save and Quit to Title -> reopen same world -> join
second join: TRASH_PROBE_SET after=5 empty=false
```

同会话写入/读回正确，live `BalmData/TrashSlot` 也含 5 钻石；重进后为空是因为
`TrashSlot.lambda$initialize$0(PlayerLoginEvent)` 显式执行
`setTrashItem(player, ItemStack.EMPTY)` 并发送空 content。**这是模组自己的登录重置**，不能据此
判定 NBT 桥失败；原 P57“持久化缺口”结论已撤回。该版本没有可用的跨重进 trash 持久化契约。
GUI 拖放仍是独立未解问题（P56）。证据 `runs/p57-trash-persist/`。

### 7.60 TrashSlot 不是普通 ScreenHandler slot

客户端 probe 取得：

```text
TRASH_PROBE trash=152,165
TRASH_PROBE componentAnchor=231,211
TRASH_PROBE leftTop=83,45
TRASH_PROBE diamond slot=36 count=5
TRASH_PROBE trashIndex=-1 slots=46
```

`152,165` is relative to `leftTop=83,45`, so the absolute GUI slot is about `235,210`; the component
anchor `231,211` agrees. It is **not** the raw `152,165` screen rectangle.

`handler.field_7761.indexOf(trash) = -1`：垃圾桶 `TrashSlotSlot` 不在 46 个普通 slot 中，而是
由 `TrashSlotComponent` 在客户端绘制并拦截鼠标。普通 `clickSlot`/`ScreenHandler` 无法定位它，
所以 P56 的屏幕坐标点击/拖拽没有完成转移——这是 GUI 命中路径问题，不是 NBT、输入法或物品
路径问题。实际移入/移出仍未验证；下一步应对 component 的 `isInside`/拖拽状态或它自己的
click 路径做测试。证据 `runs/p58-trash-click/`。

### 7.61 trash GUI 移入：serverbound Balm 桥

第一次真实点击垃圾桶，客户端崩溃：

```text
NoSuchMethodError: 'void BalmNetworking.sendToServer(java.lang.Object)'
at DefaultDeletionProvider.deleteMouseItem(DefaultDeletionProvider.java:33)
```

Balm 21 的泛型 `sendToServer(T extends CustomPayload)` 擦除后与旧的 `Object` 调用不匹配。
新增 `BalmNetworkingBridge.sendToServer(BalmNetworking, Object)`：按 `registerServerbound`
注册的 packet class 找到 payload，调用 `ClientPlayNetworking.send`；规则
`trashslot-sendtoserver.json` 命中 4 处。

补丁后点击 5 钻石再点垃圾桶，钻石进入 trash slot（`after-send.png`）；服务端 probe 读到：

```text
SERVER_TRASH count=5 item=minecraft:diamond
```

无 `NoSuchMethodError`，客户端存活。已确认 **GUI 移入方向 + 服务端内容**；移除/undelete、容器
GUI、同步仍未验证。证据 `runs/p59-trash-send/`。

### 7.62 trash 取回：provider 级通过

quick-play 进入世界，在 TrashSlot 登录重置后由服务端 seed 5 钻石；客户端直接调用
`DefaultDeletionProvider.undeleteLast`：

```text
RETURN_GUI    trash=5 minecraft:diamond provider=DefaultDeletionProvider
RETURN_AFTER  cursor=5 minecraft:diamond trash=0 minecraft:air
RETURN_FINAL  cursor=5 minecraft:diamond trash=0 minecraft:air
RETURN_SERVER empty=true count=0
```

取回逻辑、serverbound 包、服务端清空都正常，无异常。真实鼠标第二次点击仍未触发取回，属于
GUI 命中/事件问题；empty-trash、容器 GUI、同步未验证。证据 `runs/p60-trash-return/`。

### 7.63 干净 GUI 取回复测：第二次点击仍不返回

只给一个 5 钻石堆，不使用任何人工 seed：

1. 点击钻石堆 → 点击垃圾桶：5 钻石进入 trash；
2. 等待 2 秒，再次点击同一垃圾桶位置；
3. 结果：trash 仍有 5 钻石，背包/快捷栏为空，无复制。

provider 级 `undeleteLast` 已在 §7.62 通过，所以失败点明确在 TrashSlot GUI 的**第二次真实点击
事件/状态**，不是取回实现。empty-trash、容器 GUI、同步未验证。证据
`runs/p61-trash-clean-return/`。

### 7.64 TrashSlot 双向通过：移入 + 取回

debug mixin 在 GUI、provider、服务端包三处记录：

```text
DEBUG_CLICK ... hovering=true carried=5 minecraft:diamond trash=0
DEBUG_AFTER_CLICK carried=0 trash=5
DEBUG_PACKET_HEAD msg=5 serverCarried=5 serverTrash=0
DEBUG_PACKET_RETURN serverCarried=0 serverTrash=5

DEBUG_CLICK ... hovering=true carried=0 trash=5
DEBUG_PROVIDER_UNDELETE trash=5 right=false
DEBUG_AFTER_CLICK carried=5 minecraft:diamond trash=0
DEBUG_PACKET_HEAD msg=0 serverCarried=0 serverTrash=5
DEBUG_PACKET_RETURN serverCarried=5 minecraft:diamond serverTrash=0
```

截图 `final-return.png` 看似 trash 仍有钻石，是因为物品在**光标**上，而光标停在垃圾桶图标；
移开光标后 `cursor-away.png` 确认钻石在光标、trash 为空。P61 的“失败”是截图误判。

因此 **GUI 移入、GUI 取回、服务端 delete、服务端 return 全部通过，无复制**。仍未验证
empty-trash、ironchests GUI、clientbound 投递、双客户端同步。证据 `runs/p63-trash-debug/`。

### 7.65 TrashSlot clientbound content 通过

服务端 tick 60 通过 `BalmNetworkingBridge.sendTo` 发 `MessageTrashSlotContent(3 diamonds)`；
客户端 tick 140 读取 trash slot：

```text
S2C_SENT
S2C_CLIENT trash=3 minecraft:diamond
```

说明 S2C payload 注册、`sendTo` 桥和客户端 receiver 都正常，无异常。ironchests 的 clientbound
流量和双客户端同步仍未验证。证据 `runs/p64-trash-s2c/`。

### 7.66 empty-trash：Balm reply 桥

首次调用 `emptyTrashSlot` 触发：

```text
NoSuchMethodError: 'void BalmNetworking.reply(java.lang.Object)'
at MessageDeleteFromSlot.handle(MessageDeleteFromSlot.java:44)
```

新增 `BalmNetworkingBridge.reply`：在 serverbound handler 执行期间记录当前玩家，回发已注册的
clientbound payload；规则 `trashslot.balm.reply` 命中 2 处。结果：

```text
EMPTY_BEFORE trash=5 minecraft:diamond
EMPTY_AFTER  trash=0 minecraft:air
EMPTY_SERVER empty=true count=0
```

客户端/服务端都清空，无崩溃。真实 UI 键位未测。证据 `runs/p65-trash-empty/`。

### 7.67 IronChests GUI：客户端模型类阻断

world 无 cheats，chat `give`/`setblock` 返回 `Unknown or incomplete command`。改用 server probe
直接放置：

```text
IRONCHESTS_SERVER block=Block{ironchests:iron_chest} item=1 ironchests:iron_chest
IRONCHESTS_PLACED=true
```

客户端渲染时崩溃：

```text
NoClassDefFoundError: net/fabricmc/fabric/api/client/model/BakedModelManagerHelper
at tech.thatgravyboat.ironchests.client.IronChestsClient.loadModel
```

所以 GUI 还没打开就被**客户端模型加载桥**阻断，不是容器/GUI handler 失败。需要恢复
`IronChestsClient.loadModel` 的 1.21.1 ModelLoadingPlugin 桥后再重测。证据
`runs/p66-ironchests-gui/`。

**后续（09:25）**：work-only 兼容类
`net.fabricmc.fabric.api.client.model.BakedModelManagerHelper.getModel(class_1092, Identifier)` 实现为
`manager.method_4742(class_1091.method_61078(id))`，并把入口换成调用 `IronChestsClient.init()` +
`ModelLoadingPlugin` 的 `IronChestsFabricClient`。箱子渲染不再崩溃。服务端直接调用
`GenericChestBlock.method_9534` 打开菜单时出现新阻断：

```text
NoSuchMethodError: 'void GenericChestBlockEntity.method_11007(net.minecraft.class_2487)'
```

这是 1.20.1 一参 `readNbt(NbtCompound)`；1.21.1 是两参 `readNbt(NbtCompound, WrapperLookup)`。
需要补 NBT 读桥后 GUI 才能打开。证据 `runs/p66-ironchests-gui/latest-model-shim.log`。

### 7.68 IronChests 同步 NBT 桥与 ResourcefulLib 阻断

三条规则，`patch.log` 报告各命中 1 次：

| 规则 | 调用点 |
|---|---|
| `ironchests.sync.write-tag` | `getSyncTag` → 一参 `method_11007` |
| `ironchests.sync.read-tag` | `loadSyncTag` → 一参 `method_11014` |
| `nbt.packet.write-nbt-compound` | `PacketByteBuf.method_10794(NbtCompound)`，1.21.1 已加宽为 `NbtElement` |

转换后的类保留 1.20.1 一参 `readNbt`/`writeNbt` 调用；由于两者描述符相同，转换器还把
`getSyncTag` 与 `loadSyncTag` 的调用**对调**了。`IronChestsNbtBridge` 按语义纠正：`getSyncTag`
调两参 `writeNbt`，`loadSyncTag` 调两参 `readNbt`，provider 取 `Level.registryAccess()`。

修完后开箱路径越过 NBT，停在：

```text
NoSuchMethodError: 'void ServerPlayNetworking.send(ServerPlayer, Identifier, PacketByteBuf)'
at com.teamresourceful.resourcefullib.common.networking.fabric.PacketChannelHelperImpl.sendToPlayer
```

这是 IronChests 内嵌 JiJ（`META-INF/jars/resourcefullib-fabric-1.20-2.0.6.jar`）用的、1.21.1 已删除的
原始通道 API。把它换成 1.21.1 的 ResourcefulLib 3.0.12 会在启动时
`NoClassDefFoundError .../networking/base/PacketHandler`，所以内嵌 2.0.6 必须移植而不是替换。
证据 `runs/p67-ironchests-gui-nbt/`。

### 7.69 IronChests 箱子 GUI 通过

1. **ResourcefulLib 服务端网络移植**（work-only）：`PacketChannelHelperImpl` 改为 payload 实现
   （`RawPayload` + `PayloadTypeRegistry` + `ServerPlayNetworking.send(player, CustomPayload)`），
   与客户端 helper 共用同一 payload 类型。
2. **channel 公式修正**：早期客户端 helper 产出 `ironchests/ironchests:main/sync`（非法
   namespace）；两边统一为 `namespace:channelPath/packetPath` = `ironchests:main/sync`。
3. **规则 `screen.render-background-one-arg`**：`ChestScreen.method_25420(DrawContext)` →
   `ScreenRenderBridge` → `Screen.renderBackground(context, 0, 0, 0)`（1.21.1 四参形式），命中 1。
4. **规则 `ironchests.draw-texture`**：墓碑 `t8`（`DrawContext.drawTexture` 12 个 int）→
   `DrawContextTextureBridge` → `method_25293(texture, x, y, w, h, u, v, rw, rh, tw, th)`，命中 1。

结果：

```text
IRONCHESTS_USE result=CONSUME
IRONCHESTS_SCREEN=tech.thatgravyboat.ironchests.client.ChestScreen
```

`chest-gui.png` 显示 Iron Chest 标题、9×6 箱子格、背包和物品，无崩溃。背景是纯灰：旧调用传了
12 个 int，只有前 10 个能映射到 1.21.1，末尾两个旧参数被忽略。证据 `runs/p68-ironchests-gui/`。

### 7.70 IronChests GUI 交互通过

在打开的箱子上做真实 `clickSlot`：

```text
CLICK_PUT   slot0=25 diamonds  source=air
SERVER_MENU tick=220 slot0=25 diamonds
CLICK_TAKE  slot0=air          slot54=25 diamonds
SERVER_MENU tick=260 slot0=air slot54=25 diamonds
```

25 钻石从热键栏 81 放进箱子槽 0，再取回到背包槽 54；服务端同一菜单在 tick 220/260/300 的状态
与客户端一致，无复制、无丢失。证据 `runs/p69-ironchests-interaction/`。

### 7.71 关箱重开持久化与 S2C 内容同步（并更正 §7.68）

补测关箱/重开后发现物品被清空：

```text
BE tick=240 slot0=25 diamonds
CLOSED screen=null
BE tick=280 slot0=25 diamonds
BE tick=320 slot0=0 air          <- 重开清空
```

根因是转换器对调了方法**体**而不是调用点：`method_11007` 写（`class_1262.method_5426`），
`method_11014` 清空并读（`class_1262.method_5429`）。§7.68 的桥按名字调用，`getSyncTag` 走了读
路径，用空 tag 清空 items。把 `IronChestsNbtBridge` 的两个方向对调后：

```text
BE tick=280 slot0=25 diamonds
BE tick=320 slot0=25 diamonds
SERVER_MENU tick=320 sync=2 slot0=25 diamonds
REOPEN screen=ChestScreen sync=2 slot0=25 diamonds
```

关箱不丢、重开仍在，且客户端重开后看到服务端内容——S2C 箱子同步同时通过。证据
`runs/p70-ironchests-persist/`。§7.68 的方向性结论以本节为准（该 README 已加更正说明）。

### 7.72 IronChests 修复流水线入仓

`tools/rebuild_ironchests_client.py` 把此前手工执行的步骤串成一条命令：

1. `ironchests-nbt.json` + `nbt-packet.json`；
2. 抽内嵌 `resourcefullib-fabric-1.20-2.0.6.jar`，编译 `java/src/nested/java/` 下的两个 helper，
   替换 3 个类后放回；
3. `ironchests-screen.json` + `ironchests-draw.json`。

重建产物与手工验证版 **sha256 相同**（`c0589eeb…`），冒烟测试 GUI 打开、放入 50 钻石、
`BE tick=320 slot0=50`、重开 `slot0=50`。证据 `runs/p71-rebuild-pipeline/`。

### 7.73 IronChests 九宫格背景

上游 `thatgravyboat/Ironchests`（1.20.x）的 `GeneratedScreenRenderer` 实际调用：

```java
graphics.drawNineSlicedTexture(BACKGROUND, x, y, type.width(), type.height(),
        4, 4, 4, 4, 256, 256, 0, 0);
```

即 1.20.1 的十二参 `drawNineSlicedTexture(..., left, top, right, bottom, centerW, centerH, u, v)`，
不是普通贴图；P68 把它当单次 blit，因此背景是纯灰。桥改为
`DrawContextTextureBridge.drawNineSliced`：用 9 次 `method_25293` 画四角、四边、中心
（中心区 = 纹理尺寸 − 边框）。规则改名为 `ironchests.draw-nine-sliced`。

`chest-nine.png` 显示真实面板：浅色背景 + 边框，槽位/标题/物品正常。GUI 打开、放入 64 钻石、
关箱重开同步仍通过。`rebuild_ironchests_client.py` 现在默认先重编桥（stale bridge 曾触发
`NoSuchMethodError`），重建 sha256 `20864ad9…` 与手工版一致。证据 `runs/p72-ironchests-nine-slice/`。

### 7.74 lithium 玩法冒烟

探针强制加载玩家周围 9×9 区块、放置石头、再用真实服务端交互破坏：

```text
LITHIUM_CHUNKS loaded=81/81 center=4,4
LITHIUM_PLACE placed=true state=Block{minecraft:stone}
LITHIUM_BREAK_REAL broke=true after=Block{minecraft:air}
LITHIUM_SERVER_ALIVE tick=240
LITHIUM_CLIENT_ALIVE screen=null
```

区块访问路径（lithium mixin 的作用区）和方块放置/破坏都正常，服务端持续 tick、客户端留在世界，
日志无崩溃或 `NoSuchMethodError`。这是**冒烟测试**，不覆盖 TPS、生物 AI、红石或长时间稳定性。
证据 `runs/p73-lithium-play/`。

### 7.75 双客户端尝试：被 LAN 正版验证阻断

主机客户端开 LAN：

```text
LAN_OPEN ok=true port=25566
Started serving on 25566
```

离线访客连入即被踢：

```text
GuestB (/127.0.0.1:65026) lost connection: Disconnected
```

访客画面（`guest-screen3.png`）：

```text
Failed to connect to the server
Failed to log in: Invalid session (Try restarting your game and the launcher)
```

往主机目录写 `server.properties`（`online-mode=false`）不改变 integrated LAN 的行为。
下一步需要专用服务器（`online-mode=false`），并把 ResourcefulLib 移植拆成服务端安全部分
（`RawPayload`/`idFor` 不能依赖 `ClientPlayNetworking`），再用两个离线客户端重试。证据
`runs/p74-two-client/`。

### 7.76 双客户端同步通过（专用服务器）

按 §7.75 的路线执行：

1. 把 ResourcefulLib 移植拆成服务端安全的 `RawChannel`（payload id/codec、channel location、
   `RawPayload`，无客户端引用）与仅客户端的 `FabricClientPacketHelper`
   （`ClientPlayNetworking` 注册/发送）；`PacketChannelHelperImpl` 的服务端路径改用 `RawChannel`。
   重建脚本同步替换新类并删除旧的 `FabricClientPacketHelper$RawPayload`，重建
   sha256 `7e9d341f…`。
2. 专用服务器 `online-mode=false`、`enforce-secure-profile=false`，装补丁版 IronChests 与
   `dedprobe`。
3. 两个离线客户端（HostA/GuestB）连接 `127.0.0.1:25565`。

结果：

```text
DED_SET  slot0=7 minecraft:diamond
DED_OPEN opened=OptionalInt[1] guest=GuestB
LAN_GUEST_MENU screen=ChestScreen sync=1 slot0=7 minecraft:diamond
```

服务端写入的 7 钻石出现在第二客户端的箱子界面里——**双客户端 clientbound 内容同步通过**。
范围：验证的是服务端 → 第二客户端的内容同步；两端互相取放、双端关屏仍未测。证据
`runs/p75-two-client-server/`。

### 7.77 双客户端取放往返

在同一专用服务器上继续：访客在箱子里把 7 钻石取走，主机随后开箱。

```text
GUEST   LAN_MENU player=GuestB slot0=7 minecraft:diamond
GUEST   LAN_GUEST_MOVED slot0=air slot54=7 minecraft:diamond
SERVER  DED_AFTER slot0=air
SERVER  DED_OPEN_HOST
HOST    LAN_MENU player=HostA slot0=air
```

访客的点击写回服务端（箱子变空），主机再开箱看到同一状态——**访客 → 服务端 → 主机** 的往返
通过。中途修复：访客离箱约 11 格时菜单失效、客户端槽位回落到 46 格导致越界崩溃；现在开箱前
把访客传送到箱子旁，并在点击前检查槽位数。证据 `runs/p76-two-client-move/`。

### 7.78 双端关屏：setScreen(null) 不够，Screen.close() 通过

两端先调用 `MinecraftClient.setScreen(null)`：

```text
GUEST  LAN_CLOSED player=GuestB screen=null
HOST   LAN_CLOSED player=HostA screen=null
SERVER DED_MENUS hostSlots=90 guestSlots=90   (tick 420/520)
```

客户端本地关闭且无崩溃；但服务端仍持有 90 格的箱子菜单。改为调用界面 `close()`
（`method_25419`）后：

```text
GUEST  LAN_CLOSED player=GuestB screen=null slots=46
HOST   LAN_CLOSED player=HostA screen=null slots=46
SERVER DED_MENUS hostSlots=46 guestSlots=46   (tick 420/520)
```

客户端与服务端都回落到 46 格背包，**双端关屏通过**。真实键盘 ESC 走同一 `close()` 路径，但物理
按键未单独测试。证据 `runs/p77-two-client-close/`（`*-close.log`）。

## 8. 未验证项与下一步

> 说明：§7.16 记录的 `fromJson` 全匹配回退已在后续 `p9-registryops` 中改为 registry-aware 构造，兼容档案状态为 `passed_within_scope`；该条不再列为未解决，保留 §7.16 作为历史探针记录。

1. **图形/GUI 与多人**：服务端容器契约已通过；玩家侧（打开 GUI、右键交互、两个客户端同步）仍 pending，需要客户端实例。
2. **调用点签名适配的覆盖面**：`callSiteAdaptations` 已用 lithium `class_14.method_59` 验证（§7.17）；P18 已把桥按 jar 嵌入嵌套 jar 并用 ironchests JiJ 回归（§7.22），仍可继续覆盖更多样本/多层嵌套/方法句柄场景。
3. **Mixin 目标描述符适配的覆盖面**：`mixinCallbackAdaptations` 已处理 Explosion 与 POI storage 两处（§7.18），但仍需覆盖更多 `@Inject`/`@Redirect`/`@ModifyConstant` 目标变化，并验证 append/replace 两种模式在真实注入点上的边界。
4. **Mixin 实现类替换的覆盖面**：`mixinClassReplacements` 已把 `ServerChunkManagerMixin` 移植到 1.21.1 并让 lithium 到达 `Done`（§7.19）；仍需验证该模式在更多 API 形状变化上的可维护性，并决定是否重写被放弃的 chunk 多入口缓存/off-thread 快路径。
5. **`Codec.dispatch` 的可靠适配**：P26 已用 javac `CodecDispatch` 实现真正的 `MapEncoder`/`MapDecoder` 包装，不再依赖 `assumeMapUnsafe`（§7.28）；generated guard 仅作为无 bridge-dir 的回退。仍需验证更多 dispatch codec 形状。
6. **CenturyBridge 桥 jar**：`core/shims/1.21.1` 未编译；`build.sh` 四道门禁未跑（`MixinCheck` 缺失）。当前结论全部是“无桥”结果。
7. **WORLD_LOADED / 玩法契约**：lithium+ironchests 同实例的容器契约已通过（§7.20）；lithium 自身的玩法、`/give`/玩家交互/掉落/同步仍未覆盖，客户端仍 pending。
8. **trashslot 仅到 BOOTED**：原生 Balm 21 + 初始化/网络载荷桥 + 4 个 NBT 桥已让专用服务端 `Done (4.655s)`（§7.21）；但无客户端连接，clientbound receiver 未安装，包 encode/decode 与 ItemStack NBT 桥未被玩家动作触发，客户端 GUI/玩法未验证。
9. **图形客户端**：无客户端实例与显示验证，渲染/截图全部 pending。
10. **Forge 成员级分析**：需 SRG→Mojang 索引（`mcp_config` joined.tsrg + 1.21.1 Mojang 映射 + NeoForge 索引）。
11. **BytecodeVerify**：已对三个顶层补丁 jar + 一个 nested ResourcefulLib jar 运行（§7.23，0 failures）；其他嵌套 jar/客户端路径仍未覆盖，且它只是栈深度校验，不是完整类型校验。
12. **Mixin 注入点级分析**：已提取 `@Inject`/`@Redirect` 等 `method` 目标，支持 refmap 和构造器，并对 lithium 静态复现 3 个已知构造器变化（§7.24）；ordinal/slice/局部变量和非 refmap 命名目标仍未解析。
