# 状态总览（2026-10-20）

这是整个项目的“一页看完”：当前能做什么、验证到什么程度、还缺什么。细节见各 `docs/*.md` 与
`runs/` 下的证据。

## 一句话

1.20.1 → 1.21.1 Fabric 的**保体积重映射 + 规则修补 + javac 桥**工具链可用：三个原样本（Lithium、
IronChests、TrashSlot）功能级通过，6 个扩模样本完成转换，其中 AppleSkin / Mod Menu / Clumps /
FallingTree / ShulkerBoxTooltip 的核心功能有实测证据，FerriteCore 只到启动 + 性能降级。

## 当前门禁（2026-10-20 23:20 全绿）

| 门禁 | 命令 | 结果 |
|---|---|---|
| 单测 + 安装 | `gradle --no-daemon test installDist` | 23/23 |
| 证据一致性 | `python tools/verify_evidence.py` | `passed: true` |
| 哈希清单 | `python tools/check_hashes.py` | 615 项，0 mismatch / 0 missing |
| 桥版本一致 | `python tools/check_bridge_consistency.py --bridge-dir work/bridges ...` | 6 个 jar，`problems = 0` |
| mixin 完整性 | `python tools/audit_mixins.py --allow-inert ...` | `problems = 0`（惰性 mixin 已知且记录） |
| 多模组回归 | quickplay + 探针（`runs/p109-combined-regression/`） | `COMBINED_SMOKE in-world`，无崩溃 |

## 模组矩阵

| 模组 | 验证到哪 | 证据 | 缺口 |
|---|---|---|---|
| Lithium | 81 区块放置/破坏、60s TPS 20.03、4 分钟空载、40 僵尸、红石时钟、168 区块综合 | `p73/p84/p99/p103/p105/p108` | 多小时长跑、大型红石 |
| IronChests | 容器放置/插入/NBT/重启、重建后桥一致 + 联测 | `p14/p26/p68-p70/p98` | 仅基础箱子交互 |
| TrashSlot | 启动、Balm 网络、真实 GUI 点击、S2C 内容、provider 级清空 | `p17/p59/p63/p64/p65` | 物理 Delete 键/真实 UI 动作 |
| AppleSkin | 初始化/同步、HUD 食物路径、真实悬停 tooltip（`FoodOverlayTextComponent`） | `p89/p95/p101` | 数字因缺 `icons.png` 不可读；逐效果截图 |
| Mod Menu | 主菜单、列表、滚动、搜索、配置界面（10 行选项） | `p94/p97` | 真实滚轮/键盘输入（注入限制，`p104`） |
| Clumps | 经验球合并 companion：3+7→10 | `p93` | 仅 2 格半径、无配置读取 |
| FallingTree | 真实砍标准橡树整棵倒下（20→16），3 个桥 | `p90/p102` | 需主手斧；其他木材/巨型树 |
| FerriteCore | 启动/200 tick/正常停服 | `p106` | `fastmap`/`mrl` 两个 mixin 被剥离，性能降级 |
| ShulkerBoxTooltip | 真实悬停摘要 tooltip（`Diamond x5`）；网格预览伴生 mixin 已写但未打通 | `p100/p110` | 客户端容器组件读取为空，网格仍不可用 |

## 工具链

- `mcbridge1201 patch`：规则修补（field/method/body/superclass/constructor/rename/mixin 等），
  桥类 javac 后内嵌，同 bridge-dir 对齐。基础转换由外部 CenturyBridge 完成，`patch` 的输入必须是
  转换后的 jar（没有 `convert` 子命令）。
- `patch` 校验：规则 `schemaVersion` 白名单、多规则包 `target` 必须一致（`--target` 可再核对）、
  `--require-hit <rule-id>` 要求关键规则至少命中一次；未命中退出 3，疑似已修补的输入退出 4。
- `tools/build_bridges.py`：编译桥 + shim，需要 gson/dfu/fabric-api/netty/brigadier/fastutil 等 library。
- `tools/check_bridge_consistency.py`：校验多补丁 jar 内嵌桥版本一致。
- `tools/audit_mixins.py`：抓“配置列了但类缺失”与“@Mixin 类未被任何配置引用”的惰性 mixin；配置 JSON 解析失败现在计入 problems 并以非零退出（不再跳过）。
- `tools/verify_evidence.py` / `tools/check_hashes.py` / `tools/hash_evidence.py`：证据与哈希门禁。
- `tools/rebuild_ironchests_client.py`、`tools/build_clumps_companion.py` 等：多阶段/伴随模组构建。
- `tools/test_review_fixes.py`：外部问题汇总的 13 项回归（patch 校验、审计、日志路径、版本过滤、NeoForge 检测、缺 Java）。
- `launcher/`：本地 GUI 启动器（网页界面），从官方源/BMCLAPI 下载原版与 Fabric，离线启动。

## 诚实边界

- 转换会剥离目标已死的 mixin（AppleSkin tooltip、Shulker 网格、FerriteCore 两项优化）；恢复需重写。
- 热门模组抽样（`p111`，Modrinth 下载榜 1.20.1 Fabric）：VeinMiner 转换后服务端启动通过但功能未验；
  EntityCulling 启动并进服，但转换报告标明剥离了 load-bearing `EntityRendererMixin`，不算功能通过；
  ImmediatelyFast 在 `@Overwrite` 目标签名变化处 mixin apply 崩溃。渲染类模组的门槛是 mixin，不是普通调用点。
- 本机缺 GUI 材质（洋红棋盘、`icons.png`），部分视觉/数字无法像素级验收。
- 真实鼠标滚轮与部分键盘事件在本环境注入不到游戏；程序化状态验证可替代一部分。
- 未做：多小时长跑、大型红石机器、Shulker 网格渲染替代实现、nested mixin 的 ordinal/slice 级校验。
- 不分发任何游戏 jar / 模组 jar / 转换件；证据只含日志、截图、规则与源码。

## 发布

v0.1.6 … v0.1.29 见 GitHub Releases（每条对应一轮证据）。本文件对应 **v0.2.0** 里程碑。
