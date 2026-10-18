# Third-party notice

本仓库只包含自研分析器、脚本和文档；下列第三方内容以**引用/快照**方式存在，未复制其实现代码进自研模块。任何再分发前必须按各自许可重新核对。

## 1. 上游兼容引擎（源码快照，未修改地放在 `work/`，不入库）

| 项目 | 提交 | 许可 | 版权 | 本地位置 |
|---|---|---|---|---|
| [Retromod](https://github.com/Bownlux/Retromod) | `e693278379a6c80cd1a6623136a166f4d8c5cafe` | MIT | Copyright (c) 2026 Bownlux | `work/upstream/src/Retromod-*`；许可证副本 `third-party/licenses/Bownlux__Retromod__e693278379__LICENSE` |
| [CenturyBridge](https://github.com/dextawa/CenturyBridge) | `cf4ebeba2eaaa49d3746162cc2c10b670d681aec` | MIT | Copyright (c) 2026 dext | `work/upstream/src/CenturyBridge-*`；许可证副本 `third-party/licenses/dextawa__CenturyBridge__cf4ebeba2e__LICENSE` |

`patches/centurybridge/MixinCheck.java` 是本项目为编译 CenturyBridge 而写的 **no-op 补丁**，不是上游代码，也不实现上游的 mixin 门禁。

## 2. 工具与库

| 组件 | 版本 | 许可 | 用途 |
|---|---|---|---|
| Gradle | 9.8.1 | Apache-2.0 | 构建自研分析器 |
| Azul Zulu JDK | 21.0.12.1+1-LTS | GPLv2 + Classpath Exception | 编译/运行 |
| ASM | 9.7.1 | BSD-3-Clause | 字节码读取 |
| Gson | 2.11.0 | Apache-2.0 | JSON |
| Python | 3.12 | PSF | 抓取/编排脚本（仅标准库） |

## 3. 游戏数据与模组（仅本地，绝不随仓库/发布分发）

| 内容 | 来源 | 约束 |
|---|---|---|
| Minecraft 1.20.1 / 1.21.1 client jar | Mojang piston-meta | Minecraft EULA；仅本地分析，禁止再分发 |
| Mojang 官方映射（`client-*-mappings.txt`） | Mojang piston-meta | 许可条款禁止再分发“完整且未修改”的映射文件 |
| Fabric intermediary 映射、Fabric API、Fabric Loader | maven.fabricmc.net / meta.fabricmc.net | 按 FabricMC 上游许可；本仓库只记录 URL 与 SHA-256 |
| 10 份 1.20.1 模组 jar | Modrinth（项目所有者发布） | 许可逐项不同，见 `manifests/corpus.json`；本仓库不复制 jar，也不分发转换件 |
| CenturyBridge 转换产物 | 本地生成 | 受原模组许可约束；默认不分发 |

## 4. 本项目自有内容

自研部分（`java/` 下的分析器、`tools/` 下的脚本、`docs/`、`manifests/` 中的锁文件）由本项目编写。对外发布时建议采用与上游兼容的 MIT 许可；**在正式选择许可前不要把本仓库标成任何具体开源许可**。

## 5. 合规提醒

- 不得把第三方模组 jar、转换后的 jar、官方游戏 jar/资产/映射原文打包进发布物。
- 不得把 All-Rights-Reserved / NC-SA 样本的转换件作为示例分发。
- 引用作者自报结果时必须与本单位独立结果分栏，并注明未独立复测。
