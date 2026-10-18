# P0 基线：环境、上游、样本与首轮实测

执行日期：2026-10-18（Asia/Shanghai）。本文件只记录实际执行过的命令、实际产物和实际失败，不把方案里的拟议接口写成已实现能力。

## 0. 一句话结论

- **可执行的**：环境锁定、上游提交/许可锁定、10 份 1.20.1 样本（sha512 校验通过）、自研静态损伤分析器（10/10 跑通）、CenturyBridge 引擎编译、7 节版本分段、ironchests 真实转换（`ok_partial`）。
- **被环境阻塞的**：Fabric 1.21.1 专用服务端在本机启动失败。原因是 Java 进程在本会话工作区里 `Files.isWritable` 恒为 false（受限令牌 ACL），Fabric Loader 据此把 remap 目标判定为只读并拒绝写出。已保留完整日志与两个绕过尝试的结果。
- **未完成的**：任何 `BOOTED` 及以上证据；图形客户端；Forge→NeoForge 成员级分析（只做到命名空间/类级）。

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
| 专用服务端 | 已下载 Fabric server launcher（loader 0.19.5 / 0.16.14），未能启动，见 §7 | `runs/p0-server-baseline/` | **是** |

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

### 5.2 结果（`runs/p0-fabric-target/plan.json`，SHA-256 `edfcf09b...44c88`）

| 样本 | 判定 | MISSING_CLASS | MISSING_MEMBER | DESC_MISMATCH | FABRIC_API 缺失 | 源索引确认 | 备注 |
|---|---|---|---|---|---|---|---|
| ironchests | blocked_static | 1 | 15 | 19 | 7+5 | **47/47** | NBT/组件墙、BlockEntity NBT、Item.appendTooltip、Explosion 构造器、Fabric API model/networking 删除 |
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
- 未分析 Mixin 注入点 ordinal/slice/local capture 的匹配质量（只解析了 `@Mixin` 目标类是否存在）。
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

## 7. 目标 1.21.1 专用服务端：真实尝试与阻塞

### 7.1 做了什么

1. `tools/setup_server.py` 用 Fabric meta 生成隔离实例（launcher + `eula=true` + `server.properties` + Fabric API 0.102.0）。
2. `tools/run_server.py` 启动 JVM、抓日志、在出现 `Done (` 后发送 `stop`，并输出 JSON 结果。
3. loader 0.19.5、0.16.14 各尝试多次；也在 `C:\mcrun`（ASCII 路径、干净 ACL）复现。

### 7.2 结果

全部停在 `BOOTED` 之前，日志：`runs/p0-server-baseline/server.log`、`server-l016.log`、`server-outside.log`。

```text
Caused by: java.io.IOException: the jar file .\.fabric\remappedJars\minecraft-1.21.1-0.19.5\server-intermediary.jar.tmp can't be written
  at ...tinyremapper.OutputConsumerPath.<init>(OutputConsumerPath.java:102)
```

根因（已定位到具体判据）：`OutputConsumerPath` 用 `FileSystemReference.isReadOnly()`，而 zipfs 的只读判定依赖 `Files.isWritable`；在本会话里工作区内 `Files.isWritable` **恒为 false**（探针：`parent writable=false`、`created exists=true writable=false`，但 `Files.writeString` 实际成功）。这是受限令牌 ACL 的结果，不是磁盘权限问题。

尝试过的绕过与结果：

| 尝试 | 结果 |
|---|---|
| 手动创建 `.fabric/remappedJars/...` 目录 | 无效（问题在文件可写性判定） |
| 删除残留 `.tmp` 后重跑 | 首次仍失败；`icacls` 显示 ACL 正常 |
| 换 ASCII 路径 `C:\mcrun` | 失败更早：Java 创建 `.fabric` 本身 `AccessDeniedException`；同一路径 `pwsh`/`python` 可写 |
| `-Djava.io.tmpdir` 指向工作区内 | 修好了 ImageIO/temp 类错误（0.16.14 因此能走得更远），但不解决 zipfs 只读判定 |
| 用 CenturyBridge `remap-jar` **预生成** `server-intermediary.jar`（6 148 类） | 跳过 remap，但 Loader 在 `EntrypointPatch` 处失败：`Could not find game constructor in net.minecraft.server.Main!`（本地 remap 不等价于 Loader 自己的 remap+patch 流程） |

### 7.3 复现步骤（在可写环境下应当可复现）

```powershell
python tools/setup_server.py --instance work/instances/fabric-1.21.1-server
$env:JAVA_HOME='...\.toolchain\jdk'
python tools/run_server.py --instance work/instances/fabric-1.21.1-server `
  --log runs/p0-server-baseline/server.log --timeout 300
```

在正常 Windows 用户会话（非受限令牌）里，这条命令应当到达 `Done (` 并自动 `stop`。本会话的失败与代码无关，日志已保留。

## 8. 未验证项与下一步

1. **BOOTED 及以上**：需要可写 `Files.isWritable` 的环境，或改用不依赖 zipfs 可写判定的启动路径。
2. **图形客户端**：无客户端实例、无已确认显示环境；`WORLD_LOADED`/渲染截图全部 pending。
3. **Forge 成员级分析**：需要 SRG→Mojang 索引（`mcp_config` joined.tsrg + 1.21.1 Mojang 映射）。本轮只给出命名空间级结论。
4. **CenturyBridge 桥 jar**：需上游补 `MixinCheck`，或接受 `build.sh` 门禁不可验证。
5. **BytecodeVerify**：未编译；转换产物尚未做数据流校验。
6. 分析器缺 `Mixin` 注入点级别的匹配质量评估（ordinal/slice/局部变量）。
