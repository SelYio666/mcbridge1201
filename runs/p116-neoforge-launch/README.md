# p116 — NeoForge 1.21.1 客户端成功启动到主菜单

日期：2026-10-21。承接 `runs/p115-neoforge-attempt`（安装成功、启动卡在
`DisplayWindow.updateModuleReads`）。本 run 把 p115 的推测替换成已验证的根因与修复。

## 根因（已验证，不是猜测）

p115 当时的推测是「classpath / `-p` 模块路径 / launch target 有问题」。**这个推测是错的。**
启动器生成的 java 命令行与官方 `version.json` 完全一致（同样 47 个库、同样 `-DignoreList`、
同样 `-p` 模块路径、同样 `--launchTarget forgeclient`）。

真正的问题是**安装不完整**：官方安装器的客户端处理器从来没有跑成功。

1. NeoForge 的 `version.json` 里**没有**游戏 jar，也没有 `net.neoforged:neoforge` 库；
   它只声明 `mainClass=cpw.mods.bootstraplauncher.BootstrapLauncher` 和 47 个 FancyModLoader 库。
2. 客户端真正的游戏代码由安装器的 10 个处理器在本地生成：
   `jarsplitter`（slim/extra）→ `AutoRenamingTool`（→ srg）→ `binarypatcher`
   （`data/client.lzma` → `libraries/net/neoforged/neoforge/21.1.264/neoforge-21.1.264-client.jar`）。
3. 这些处理器所需的库由安装器用 **Java 自带 HTTP** 下载；本机上 Java 连
   `maven.neoforged.net` 会 connect timeout，而 Python/urllib 正常。安装器于是中途失败。
4. 我们的 `install_neoforge_direct` 只看「profile json 存在」就当成安装成功，
   再补一个「把原版 1.21.1.jar 复制成 neoforge-21.1.264.jar」的 hack。
   结果 FML 的游戏层里只有 `minecraft`（且是没有 patch 的原版），没有 **`neoforge` 模块**。

反编译 `earlydisplay-4.0.45.jar` 的 `DisplayWindow.updateModuleReads` 证实：

```text
ldc_w  "neoforge"
ModuleLayer.findModule(String) -> Optional.orElseThrow()
```

即它在**游戏层**里找名叫 `neoforge` 的模块，随后从该模块加载
`net.neoforged.neoforge.client.loading.NeoForgeLoadingOverlay`。没有这个模块 → `No value present`。

FancyModLoader 4.0.45 源码（`ProductionClientProvider` / `NeoForgeClientLaunchHandler`）进一步确认
游戏层由三份文件合并而成：

- `libraries/net/minecraft/client/1.21.1-20240808.144430/client-1.21.1-20240808.144430-srg.jar`
- `libraries/net/minecraft/client/1.21.1-20240808.144430/client-1.21.1-20240808.144430-extra.jar`
- `libraries/net/neoforged/neoforge/21.1.264/neoforge-21.1.264-client.jar`

`neoforge` 模块来自 `libraries/net/neoforged/neoforge/21.1.264/neoforge-21.1.264-universal.jar`
（`PathBasedLocator[name=neoforge]`）。

## 修复（三步，都在启动器里）

1. `mclaunch.prepare_installer_libraries()`：读安装器 jar 里的 `install_profile.json` +
   `version.json`，把 70 + 47 个库用我们自己的下载器（可回退镜像、SHA1 校验）预置到
   `<root>/libraries`，让官方处理器可以离线跑。
2. `mclaunch.loader_artifacts()` + `install_neoforge()` / `backend.install_neoforge_direct()`：
   安装以「四件游戏文件齐全」为成功条件（`neoforge_client` / `neoforge_universal` /
   `minecraft_srg` / `minecraft_extra`），不再把「profile json 存在」当成功；
   `verify_install` 也会显示这些文件；`build_command` 在文件缺失时直接报错，
   不再等到 earlydisplay 抛 `No value present`。
3. 修 `_run_installer` 的真实 bug：以前用相对路径 jar + `cwd=<root>`，安装器根本找不到自己的 jar
   （`Unable to access jarfile ...`），现在两条安装路径都用绝对路径。

安装器本身仍是官方的，处理器（split/rename/patch）是官方逻辑，没有手写替代。

## 证据

| 文件 | 内容 |
|---|---|
| `installer.log` | 官方安装器完整日志（`Successfully installed client into launcher`） |
| `verify.txt` | `mclaunch verify neoforge-21.1.264`：117/117 库、四件 loader 文件 ok、assets 3911/3911 |
| `launch.log` | 启动日志：`Found mod file "client-...-srg.jar"`、`neoforge-21.1.264-universal.jar [PathBasedLocator name=neoforge]`、`Mod List: Minecraft 1.21.1 (minecraft) / NeoForge 21.1.264 (neoforge)`、`Setting user`、`Backend library`、`OpenAL initialized`、`Sound engine started`、blocks atlas 创建 |
| `neoforge-mainmenu.png` | 游戏窗口截图，标题栏 `Minecraft NeoForge* 1.21.1`，停在首启/主菜单界面 |

复现：

```text
python launcher/mclaunch.py install 1.21.1 work/launcher-e2e neoforge
python launcher/mclaunch.py verify neoforge-21.1.264 work/launcher-e2e
python tools/test_launcher_e2e.py --root work/launcher-e2e --version neoforge-21.1.264 ^
    --require "Sound engine started" ^
    --require "Created: 1024x512x4 minecraft:textures/atlas/blocks.png-atlas"
```

## 边界（如实）

- 这是**空 NeoForge**（无第三方模组）启动到主菜单；没有进世界、没有装 NeoForge 模组。
- `minecraft-1.21.1.jar`（原版复制件）仍在 classpath 末尾，这是官方 profile 的设计
  （`-DignoreList` 里含 `<id>.jar`）；真正生效的游戏代码来自上面三份安装器产物。
- 只测了 `21.1.264` / Java 21；Java 25 仍会拒绝（`pick_java` 已按 `inheritsFrom` 选 delta）。
