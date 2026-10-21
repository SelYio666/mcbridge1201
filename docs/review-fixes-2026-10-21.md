# 外部问题汇总（2026-10-21）修复记录

对应报告：`mcbridge1201-问题汇总-2026-10-21.md`（8 项 + 3 项交付缺口）。逐条处理如下。

| 编号 | 问题 | 处理 | 验证 |
|---|---|---|---|
| ISSUE-01 | 桥接失败被替换成默认结果 | `ItemPredicateFromJson` 解析失败改抛 `IllegalStateException`（带 codec 错误）；`TrashSlotNbtBridge` 的 save/writeItem/load 失败改抛错，空标签仍视为合法空物品；并拒绝字符串类型的 `count`/`Slot`（原版 codec 会静默转 1） | **运行期已验证**（p113：VALID/EMPTY/INVALID/TYPED 四个探针全部符合预期）；完整 UI 流程未重跑 |
| ISSUE-02 | 补丁入口缺少校验 | `RuleSet.load` 校验 `schemaVersion`（白名单 `0.1-draft`）与 `target`；`patch` 校验多规则包 target 一致、`--target` 可选核对；新增 `--require-hit`：零命中退出 3，疑似已修补退出 4，规则非法退出 2 | 用 CLI 实测 5 种输入：schema 2 / target 2 / 空命中 3 / 已修补 4 / 正常 0 |
| ISSUE-03 | mixin 配置损坏仍成功 | `audit_mixins` 把配置解析错误计入 `problems` 并输出 `config_errors` | 坏配置退出 1，合法配置退出 0 |
| ISSUE-04 | 重建脚本依赖不同步 | `rebuild_ironchests_client.py` 改为用 `--stub/--processed-mods` 参数贯穿；依赖改为 glob 解析（networking、item-api、api-base、netty-transport、fastutil、brigadier、dfu），不再写死 processedMods 版本/哈希 | `build_bridges` 用新依赖集编译 30 个桥源码成功 |
| ISSUE-05 | 日志路径 URL 编码 404 | 服务端 `unquote` 后再解析路径；前端改 `encodeURIComponent` | 含中文、空格、反斜杠的日志路径请求返回 200，offset 正常 |
| ISSUE-06 | NeoForge 检测忽略 MC 版本 | `installed()` 读取候选 profile 的 `inheritsFrom`，只复用游戏版本匹配（且 loader 版本匹配）的目录 | 1.21.1 返回 neoforge-21.1.172，1.20.4 返回 neoforge-20.4.123 |
| ISSUE-07 | 快照/远古版本被过滤 | `is_mc_version` 改为“官方 manifest 命中 或 命名规则命中”（含 24w14a、b1.7.3、alpha/beta、pre/rc 等） | 1.21.1、24w14a、b1.7.3、loader profile 均列出；整合包实例仍被隐藏 |
| ISSUE-08 | 缺 Java 时 config 断开 | `/api/config` 与 `/api/status` 捕获 Java 查找异常，返回 `java: null` + `java_error` | 模拟 Java 缺失：HTTP 200 + JSON 错误字段 |

## 交付缺口

- STATUS.md 里 `mcbridge1201 convert|patch` 已改为只写 `patch`，并注明基础转换由外部 CenturyBridge 完成；新增 patch 校验说明。
- README 中 trashslot 的“clientbound 未在客户端执行”改为指向后续 p29/p64 的客户端执行记录。
- 启动器文档补充校验工具与退出码说明。

## 尚未完成（如实记录）

- ISSUE-01 已用客户端探针做运行期回归（p113），但完整 TrashSlot UI 流程（开面板→移物品→关箱→重进）仍未重跑。
- ISSUE-04 的“干净目录”已验证（复制 java/ 到空目录 + `gradle --offline test installDist` 成功），但没在无缓存的干净机器上验证。
- 报告提到的 Gradle Wrapper 缺失、CenturyBridge 的 no-op `MixinCheck` 仍未处理。
- 已固化为 `tools/test_review_fixes.py`（13 项检查），但这轮仍未覆盖 ISSUE-01 的游戏内行为。
