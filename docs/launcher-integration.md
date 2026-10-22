# 接入其他启动器：PCL / HMCL / Prism / 官方启动器

本文说明怎么把 **mcbridge1201 的产物**（转换后的模组 jar + 桥 jar）放进大家常用的启动器，
以及反过来怎么用本工具检查别的启动器里的实例。

> 前提：本仓库**不分发**任何游戏/模组 jar。你需要先用自己的 mod 文件，通过本工具链完成转换，
> 产物是**标准 Fabric 1.21.1 模组**，任何支持 Fabric 的启动器都能加载。

## 0. 产物长什么样

转换/修补后，通常得到：

```text
mods/
  你的模组-1.21.1.jar        # 转换后的模组
  mcbridge1201-bridge.jar    # 本项目提供的桥（若规则要求）
config/                      # 如转换产生，随实例带走
```

关键要求：

- **游戏版本 1.21.1 + Fabric**（不是 Forge/NeoForge）；
- **Java 21**；
- 模组 jar 与桥 jar 必须**同时**放进去；
- 不要和 1.20.1 的原版 jar 混放（类名不同，会崩）。

## 1. PCL（Plain Craft Launcher 2）

1. 启动 PCL →「版本管理」→ 安装 **1.21.1 + Fabric**；
2. 选中该版本 →「版本设置」→「Mod 管理」→「添加」→ 选择转换后的 jar（以及桥 jar）；
   - 也可以直接把文件放进 `<PCL 目录>/versions/<版本>/mods/` 或全局 `mods/`；
3. 「设置」→「Java」确认是 **21**；
4. 启动，进游戏后看 `logs/latest.log` 有无 `mcbridge` 相关报错。

PCL 也认标准 `launcher_profiles.json`：本工具生成的实例目录可以直接被 PCL 打开。

## 2. HMCL

1. HMCL →「版本列表」→「安装新游戏版本」→ 选 1.21.1 → 勾选 **Fabric**；
2. 选中实例 →「游戏设置」→「模组管理」→「添加模组」→ 选择转换产物；
   - 或直接放进 `.minecraft/mods`；
3. 「设置」→「Java 路径」选 Java 21；
4. 启动并检查日志。

## 3. Prism Launcher

1. 「Add Instance」→ 版本选 1.21.1 → Loader 选 Fabric → 创建；
2. 右键实例 →「Edit」→「Mods」→「Add」→ 选择 jar（桥 jar 一起）；
3. 「Edit」→「Settings」→「Java」确认 21；
4. Launch，看日志。

## 4. 官方启动器

1. 安装 1.21.1，再用 Fabric Installer 装 Fabric（或用本项目的 `install_fabric`）；
2. 打开游戏目录 → `mods/` 放入产物；
3. 启动器里创建/选择该 Fabric 配置，Java 选 21（1.21.1 官方运行时可自动下载）。

## 5. 反向：用本工具检查别的启动器实例

把实例目录当成本工具的游戏目录即可（只读检查，不改文件）：

```text
python launcher/mclaunch.py verify 1.21.1 "D:\你的实例目录"

# 也可以在任意空目录里装一份 1.21.1 + Fabric，用来对照
python launcher/mclaunch.py install 1.21.1 "D:\tmp\compare" fabric
```

`verify` 会检查 version json / client jar / libraries / natives / assets 是否齐全；
返回码非 0 表示缺文件。

如果要迁移/转换该实例里的 1.20.1 模组，把 jar 复制到 `work/` 下再走转换流程（见 `docs/build.md`）。

## 6. 常见问题

| 现象 | 原因 | 处理 |
|---|---|---|
| 启动即崩 `NoSuchMethodError`/`ClassNotFound` | 模组没转换或桥没放 | 确认 jar 是 1.21.1 产物，桥 jar 同时存在 |
| 游戏版本对不上 | 实例不是 1.21.1 | 新建 1.21.1 Fabric 实例 |
| `UnsupportedClassVersionError` | Java 不是 21 | 切换 Java 21（delta） |
| 资源/语言缺失 | 资源没下全 | `mclaunch verify` 看 `assets n/n`，必要时重装 |
| 两个启动器互相覆盖配置 | 共用同一个 `.minecraft` | 给每个实例独立游戏目录，或先备份 |

## 7. 目录速查

| 启动器 | 默认实例根 |
|---|---|
| PCL | `<PCL 目录>/versions/<版本>` 或全局 `.minecraft` |
| HMCL | `.minecraft`（可自定义） |
| Prism | `%APPDATA%/PrismLauncher/instances/<实例>` |
| 官方 | `%APPDATA%\.minecraft` |

> 提醒：不同启动器的“全局 mods”和“实例 mods”优先级不同；排查时先确认到底加载了哪一份。
