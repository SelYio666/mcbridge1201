# 启动器可复用的开源项目（调研）

目标：让配套启动器支持**最全的 MC 版本**（release / snapshot / old_alpha / old_beta）、自选版本下载，
并补齐 Fabric / Forge / NeoForge / Quilt 的安装与启动。下面只列**实际核对过许可证**的项目；
未核对成功的一律标注。

## 结论

**首选：`minecraft-launcher-lib`（Python，BSD-2-Clause）**。它已经实现了我们缺的那半套：

| 能力 | 对应函数 |
|---|---|
| 版本清单 / 全部版本 | `utils.get_version_list()`、`get_latest_version()` |
| 原版安装（jar / libraries / natives / assets） | `install.install_minecraft_version()` |
| Fabric / Quilt 安装 | `fabric.install_fabric()`、`quilt.install_quilt()` |
| **Forge 安装（跑 installer + processors）** | `forge.install_forge_version()`、`list_forge_versions()`、`find_forge_version()` |
| **NeoForge 安装** | `mod_loader.get_mod_loader("neoforge")`、`mod_loader.list_mod_loader()` |
| Java 运行时（官方 JVM manifest） | `runtime.install_jvm_runtime()`、`find_system_java_versions()` |
| 启动命令拼装（含 `legacyClassPath` 等加载器差异） | `command.get_minecraft_command()` |
| Modrinth 整合包（.mrpack） | `mrpack.install_mrpack()` |
| 微软正版登录（可选，离线不需要） | `microsoft_account.*` |

许可证：**BSD 2-Clause**（已抓取仓库 LICENSE 原文核对，2019–2025 JakobDev）。可直接依赖或 vendor，
保留版权声明即可，与闭源/开源项目都兼容。

它的短板：**没有内置镜像/加速**（直连 Mojang / Fabric / Forge 官方源）。我们自己的
`launcher/mclaunch.py` 已经做了 BMCLAPI 镜像兜底，可以保留：原版资源走我们的下载器，加载器安装与
启动交给库。

## 其他可参考项目

| 项目 | 语言 | 许可证 | 可借鉴什么 | 能否直接用 |
|---|---|---|---|---|
| Prism Launcher | C++/Qt | GPL-3.0（业界已知，本次抓取超时未复核） | 实例隔离、下载器回退链、组件化版本模型 | 代码不能并入宽松许可项目；只能参考设计 |
| HMCL | Java | GPL-3.0（同上，未复核） | 下载源（BMCLAPI/镜像）选择、Java 管理、版本 JSON 合并 | 参考；GPL 代码不能直接抄 |
| MultiMC | C++/Qt | GPL-3.0（未复核） | 元数据/实例结构 | 参考 |
| MinecraftLauncher-core（Node） | JS | **MIT**（已抓 LICENSE） | 轻量下载+启动流程 | 若改 Node 技术栈可用 |
| Modrinth API / mrpack 规范 | — | 公开 API / 规范 | 整合包与模组下载 | 直接可用（遵守其 API 规则） |
| BMCLAPI | — | 公开镜像服务 | 国内资源加速 | 已在用（非代码依赖） |

## 落地计划（按优先级）

1. **接入 `minecraft-launcher-lib`**（BSD-2）作为安装/启动内核：
   - 版本列表用 `utils.get_version_list()`（含全部类型），GUI 加“显示快照/远古版本”开关；
   - 安装：原版走库（保留我们的镜像下载器作为可选项），Fabric/Forge/NeoForge/Quilt 全部交给库；
   - 启动：`command.get_minecraft_command()`，解决 Forge 的 `-p` / `legacyClassPath` 拼装问题；
   - Java：`runtime.install_jvm_runtime()`，按版本自动挑 8/17/21。
2. **GUI 扩展**：版本下拉（release/snapshot/old）、加载器版本下拉（Fabric loader 列表、Forge 版本列表、
   NeoForge 版本列表）、每个版本独立 gameDir、模组文件夹入口。
3. **镜像策略**：默认官方；国内网络自动切 BMCLAPI（我们已有）；库本身不支持镜像时，用我们的
   `download()` 预取或按 URL 前缀改写。
4. **整合包**：`mrpack.install_mrpack()` 直接支持 Modrinth 整合包，适合后续“一键装包”。

## 证伪记录

- `minecraft-launcher-lib` 的 wheel 已下载并安装到本机 Python（`8.0`），源码模块清单核对通过：
  `install / fabric / quilt / forge / mod_loader(_neoforge) / runtime / mrpack / command / java_utils`。
- 该库 `import` 需要 `requests`，本机 Python 的 `requests` 缺 `idna`，安装依赖时 PyPI/清华镜像均超时；
  这是本机网络问题，不影响结论（库本身 BSD-2、源码结构清晰）。
- Prism / HMCL / MultiMC 的 LICENSE 本次抓取失败（GitHub 连接重置/超时），许可证按业界已知标注为
  GPL-3.0，正式引入前需再核对。
