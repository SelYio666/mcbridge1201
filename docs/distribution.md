# 分发与发布

最后更新：2026-10-19。本文回答两件事：**GitHub 上能发布什么**，以及**别人拿到后怎么复现**。

## 1. 能发布什么

可以发布（都在本仓库内，`work/` 已被 gitignore）：

- 工具源码：`java/`、`tools/`；
- 转换规则：`rules/fabric-1.21.1/*.json`；
- 桥源码：`java/src/bridge/`；
- 文档与证据：`docs/`、`runs/`（日志、源码、我们的探针 jar）；
- hash 清单：`runs/SHA256SUMS.txt`。

**不能发布**：

- 游戏 jar（`client-*.jar`、`server-*.jar`）；
- 模组 jar（1.20.1 原版或任何 `fabric-api`/Balm 等）；
- 转换件（`*-rebuilt.jar`、`*-final.jar`、`*-patched.jar`）。

原因：转换件是原模组的衍生作品，分发需要原作者的许可；Minecraft 本体更不能分发。仓库
`README.md` 的“边界”与 `tools/verify_evidence.py` 的 `no_tracked_jars` 检查都据此设置。

`runs/` 下的探针 jar（`dedprobe.jar`、`escprobe.jar` 等）是本项目自己写的测试代码，旁边有
`.java` 源码，属于“工具”而非“游戏内容”，允许入库。

## 2. 发布到 GitHub

```powershell
cd mcbridge1201
git remote add origin https://github.com/<你的账号>/mcbridge1201.git
git push -u origin master
```

发布一个 Release 时，只上传：

- 源码压缩包（GitHub 自动生成）；
- 可选的 CLI 构建产物（`java/build/install/mcbridge1201/`，本项目自己的代码）；
- `runs/SHA256SUMS.txt`。

**不要**上传任何 `.jar` 游戏/模组/转换件。

## 3. 别人怎么用

对方需要：

1. JDK 21；
2. 自己的 1.20.1 模组 jar（从 Modrinth/CurseForge 下载，不随仓库分发）；
3. `fabric-api-0.102.0+1.21.1.jar` 与 Fabric Loader 1.21.1。

步骤：

```powershell
git clone https://github.com/<你的账号>/mcbridge1201.git
cd mcbridge1201
$env:JAVA_HOME='<JDK 21>'
cd java; gradle --no-daemon installDist; cd ..

# 单件转换（示例：IronChests）
java\build\install\mcbridge1201\bin\mcbridge1201.bat patch `
  --in <自己的 ironchests 1.20.1.jar> `
  --out <输出目录>\ironchests-rebuilt.jar `
  --rules rules\fabric-1.21.1\ironchests-nbt.json `
  --rules rules\fabric-1.21.1\ironchests-draw.json `
  --bridge-dir work\bridges
```

IronChests 一键流水线（会编译桥、处理嵌套 ResourcefulLib）：

```powershell
python tools\rebuild_ironchests_client.py `
  --fabric-api "<fabric-api-0.102.0+1.21.1.jar>" `
  --out work\client\ironchests-rebuilt.jar
```

## 4. 精确版本

| 组件 | 版本 |
|---|---|
| Minecraft | 1.21.1 |
| Fabric Loader | 0.19.5 |
| Fabric API | 0.102.0+1.21.1 |
| Balm | 21.0.66（fabric 构建） |
| Java | 21 |

客户端和服务端要放同一套转换件；1.20.1 原版同名模组必须移除。

## 5. 支持范围（发布时必须一起说明）

已验证：

- IronChests：模型、NBT 同步、GUI、取放、关箱持久化、九宫格背景、双客户端同步与并发；
- TrashSlot：移入/取回/clientbound/empty（provider 级）；
- Lithium：加载、玩法冒烟、289 区块 60 秒 20.03 TPS。

未验证 / 已知边角：

- empty-trash 物理按键：合成按键未进入 Balm 屏幕按键事件；
- Lithium 生物 AI、红石、长时间 soak；
- 其他任何模组。

完整证据见 `docs/baseline.md`、`docs/progress.md`、`docs/remaining-work.md`。
