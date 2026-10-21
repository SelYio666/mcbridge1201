# 构建与复现（干净目录）

## 需要什么

| 依赖 | 版本 / 说明 |
|---|---|
| JDK | 21（桥源码与 Java 工具链都按 21 编） |
| Gradle | 9.x（仓库**不带 wrapper**：wrapper 需要提交 `gradle-wrapper.jar`，与“仓库不放 jar”的策略冲突，所以用系统 Gradle） |
| Python | 3.10+（工具、启动器、回归脚本只依赖标准库 + 启动器可选的 `minecraft-launcher-lib`） |
| 网络 | 首次构建需要 Gradle 依赖；依赖进缓存后可 `--offline` |

## Java 工具链

```text
cd java
gradle test installDist        # 单测 + 可执行分发（java/build/install/mcbridge1201）
```

**已实测（2026-10-21）**：把 `java/` 整个复制到一个空目录，用同一个 Gradle 缓存执行
`gradle --offline test installDist`，构建成功。这验证了“干净目录”可复现，但不等于“全新机器
无缓存可复现”（缓存来自本机）。

## 桥编译

```text
python tools/build_bridges.py --stub work/cb/data/jars/client-1.21.1-intermediary.jar \
  --lib ...gson --lib ...datafixerupper --lib ...fabric-networking-api-v1 \
  --lib ...fabric-item-api-v1 --lib ...fabric-api-base --lib ...netty-transport \
  --lib ...fastutil --lib ...brigadier --lib ...netty-buffer --lib ...netty-common \
  --lib ...balm --out work/bridges
```

依赖清单与桥源码实际 import 对齐（`ItemTooltipCallback`、`ClientPlayNetworking`、
`PayloadTypeRegistry` 等）。`tools/rebuild_ironchests_client.py` 会按 glob 自动找这些 jar，
不再写死 `processedMods` 的版本/哈希。

## 回归

```text
python tools/test_review_fixes.py     # 外部问题汇总 20 项检查
python tools/verify_evidence.py       # 证据/测试/哈希
python tools/check_hashes.py          # 哈希清单
python launcher/mclaunch.py verify 1.21.1 <root>
```

## 边界

- 基础版本转换由外部 CenturyBridge 完成，本项目只有 `patch`；`patch` 输入必须是转换后的 jar。
- CenturyBridge 锁定的提交仍需本地 no-op `MixinCheck` 补丁才能编译，这道上游 mixin 检查没有实现。
- ISSUE-01（桥失败显式抛错）只做了编译级验证，游戏内失败传播仍需一次真实存档/同步回归。
