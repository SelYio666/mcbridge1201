# p247 — 冻结 1.21.4 环境与差异分类（B01）

日期：2026-11-03。对应路线计划阶段 B 的 **B01**：冻结精确 1.21.4 环境，生成差异分类。
本回合**只做静态**：没有转换任何 jar，没有启动 1.21.4 游戏，也没有 1.21.4 规则包。

## 1. 环境冻结

```powershell
python tools\fetch_target_1214.py      # 下载并按 hash 钉住（幂等，已存在且 hash 对就跳过）
```

| 工件 | 版本 | sha256（前缀） |
|---|---|---|
| client jar | 1.21.4（java-runtime-delta，Java 21） | `c17c450c6e72cc51…` |
| official client mappings | 1.21.4 | `48b502ccc5e855b4…` |
| intermediary | 1.21.4-v2 | `2ca8d753e5338f78…` |
| fabric api | 0.119.4+1.21.4 | `d183bacb845167f0…` |
| fabric loader | 0.16.14 | `9ed7b7f4197153ad…` |
| **桥编译 stub** | 本项目 `remap-jar` 生成，**8857 个 class，全 major 65** | `6c421c2c3583b414…` |

锁文件 `manifests/target-fabric-1.21.4.lock.json`；目标身份 `targets/fabric-1.21.4.json`
（`status: planned`，`ruleOrder` 为空）。piston 提供的 sha1 在下载时逐项校验。

## 2. 三条防线实测

| 用例 | 期望 | 实测 |
|---|---|---|
| 用 1.21.4 profile 转换 | 拒绝 | rc 3，`pipeline.rule-order-empty` |
| 把 1.21.1 规则包指到 1.21.4 | 拒绝 | rc 3，`pipeline.rule-order-empty` + `rules.target-mismatch` |
| 1.21.4 stub 的 class 版本 | 全 65 | 8857/8857 major 65 |

## 3. 实测差异（同一输入，两个索引）

同一份 1.20.1 输入分别对 1.21.1 与 1.21.4 索引做静态分析，再按
"新增断裂 / 消失 / 两版共通"分类：

| 输入 | 1.21.1 断裂 | 1.21.4 断裂 | **新增** | 消失 | 共通 |
|---|---:|---:|---:|---:|---:|
| `fixtures/source-fabric-1.20.1` | 1 | 1 | **0** | 0 | 1 |
| `ironchests-5.0.2`（真实样本） | 76 | 97 | **21** | 0 | 76 |

两条结论：

- **fixture 在 1.21.4 上没有新增断裂。** 它唯一的问题 `class_1799.method_7969`（ItemStack NBT 读取）
  在 1.21.1 就已经存在——那是 1.20.5 的 `WrapperLookup` 签名变化，不是 1.21.4 引入的。
  也就是说 fixture 覆盖的 API 恰好落在 intermediary 稳定的区间里，**它无法代表全部增量**。
- **真实样本多出 21 个断裂点**，性质分布：
  - `missingClass`：`class_2753`、`class_3270`、`class_6395`——1.21.4 里整个类不见了；
  - `descMismatch`：`class_1269` 的字段描述符变化（`field_21466/field_5811/field_5812`），
    以及 `class_2741.field_12481/field_12525` 的类型改成了 `class_2753`；
  - `missingMember`：`class_2464.field_11456`、`class_1269.method_29236`、
    `class_1936.method_39281`、`class_2237.method_9559` 等方法/字段消失。

  完整清单在 `result.json` 的 `delta.*.newIn1214`（各列前 25 条）。

**两个输入必须各自成目录**：`analyze` 会扫描整个 `--mods` 目录，第一次把两个 jar 放进同一目录
时两边结果完全相同（76/97/21）。已修正为每个输入一个目录，脚本里留了注释说明这个坑。

## 4. 官方变化清单（数据，不是实测）

来源（2026-11-03 读取）：

- [Fabric for Minecraft 1.21.2 & 1.21.3](https://fabricmc.net/2024/10/14/1212.html)
- [Fabric for Minecraft 1.21.4](https://fabricmc.net/2024/12/02/1214.html)

共 21 条，按领域：注册 3、API 形态 8、渲染 3、数据 3、数据生成 1、资源 2、网络 1。
每条都标注 `staticDetectable`：

| 可检出性 | 条数 | 含义 |
|---|---:|---|
| `yes` | 15 | 成员/描述符/类型变化，字节码差异能看见 |
| `partial` | 5 | 只有部分形态可见（例如"缺一个从未发出的调用"看不见） |
| `no` | 1 | 纯资源路径/运行时协议，引用层面看不见（`1214.equipment-path`） |

**这个标注是本轮的判断，不是测量结果**；`result.json` 里明确写着这句。
真正被测量的是第 3 节的两个数字。

代表性条目：

- `1212.registry-key-settings`：Block/Item settings 必须带 `RegistryKey`，否则
  `NullPointerException: Item id not set`。**静态 `partial`**——`Settings#registryKey` 的调用可见，
  但"少了一个调用"在字节码里没有痕迹。这是 1.21.4 路线最容易漏的一类。
- `1212.entity-render-state`：`EntityRenderer` 增加 `S extends EntityRenderState` 类型参数，
  `createRenderState`/`updateRenderState` 拆分渲染数据。**静态 `yes`**，但"移植后的渲染是否还正确"看不见。
- `1214.block-model-render-type`：`BlockEntity#getRenderType` 移除。**静态 `yes`**（覆写目标消失）。
- `1214.equipment-path`：equipment 资源从 `models/equipment` 移到 `assets/<ns>/equipment`。**静态 `no`**。

## 5. 附带的可重现性验证

本工作区的 fixture jar 是构建产物（不入库）。按 `tools/build_source_fixture.py` 重建后
sha256 为 `1f210e26c471a261…`，与 `fixtures/source-fabric-1.20.1/manifest.json` 记录的**完全一致**——
说明 fixture 的构建在固定依赖下是确定性的，不是"本机能跑就算"。

## 6. 边界（哪些没有验证）

- **没有 1.21.4 规则包**：profile 的 `ruleOrder` 为空，门禁拒绝用它转换任何东西。
- **没有启动 1.21.4 游戏**，也没有渲染/协议/资源层面的任何运行时证据。
- **没有 fabric-api 索引**：`analyze` 只把 loader 当作 `--api`，所以 76 项里包含"未提供 API 索引"
  造成的缺失（`missingApiClass`）。两版用的是同一套 classpath 假设，**相对差（+21）可信，
  绝对数不可当作全部损伤**。
- **没有桥编译闭包**：`indices.libs` 为空，1.21.4 的桥还没法编译（B02/B03 才需要）。
- 没有验证 1.21.4 的 `dataVersion` / 资源包格式，profile 里留 `null` 而不是猜。
