# p246 — 来源端固定 fixture 与 1.20.4 架构探针

日期：2026-11-03。对应路线计划阶段 A 的 **A05**（来源端固定 fixture）与 **A06**（1.20.4 探针）。
本回合**不启动任何游戏**：全部是编译与静态探针。

## A05：自建来源 fixture

真实样本（`work/corpus`）都是别人的制品，改转换器时无法确定"输入形态"是哪一个。
`fixtures/source-fabric-1.20.1/` 是本仓库自己的 1.20.1 Fabric 源，编译一次后按 hash 固定，
**每个目标转换同一份字节**。

| 文件 | 覆盖的字节码形态 |
|---|---|
| `mcbfixture/FixtureRegistry` | 注册（`class_2378.method_10230` + `class_7923.field_41178`）、`new class_2960(String,String)` 构造器 |
| `mcbfixture/FixtureData` | ItemStack NBT 读取（`method_7969`，1.20.5 在此加 `WrapperLookup` 参数） |
| `mcbfixture/FixtureScreen` | Screen 渲染钩子覆写（`method_25394` + `class_332.method_25294`，1.21.6 拆分提取/绘制） |
| `mcbfixture/mixin/FixtureMixin` | `@Inject` 到真实 intermediary 成员 `method_7852`，四参回调 |
| `mcbfixture/FixtureIndy` | lambda、方法引用、字符串拼接、stream 链（invokedynamic） |
| `mcbfixture/FixtureMod` | `ModInitializer` 入口点 |

```powershell
$env:JAVA_HOME = "<jdk21>"
python tools\build_source_fixture.py      # fixtures/source-fabric-1.20.1/out/mcbfixture-1.0.0.jar
```

实测：6 个 class，**全部 major 61**（`--release 17`），jar 4,514 字节，
sha256 `1f210e26c471a261…`，依赖 9 项逐项 hash 记录在 `fixtures/source-fabric-1.20.1/manifest.json`。
产物目录被 `.gitignore` 忽略，只提交源码与 manifest——jar 由 hash 定位，不入库。

**静态自检**：对 1.20.1 自身索引跑 `analyze`，`missingClass=0 / missingMember=0 /
descMismatch=0`，Mixin 目标与注入均解析成功（1 个注入、0 未解析）。这说明 fixture 是干净输入，
后面任何损伤都是目标侧造成的。

**运行验证：pending。** 本机没有 1.20.1 Fabric 实例（只有 1.20.1 Forge 服务端），
所以"来源原生环境通过"这一条没有做，manifest 与本文都记为未验证。

## A06：1.20.4 探针

环境（全部下载并 pin 进 `targets/fabric-1.20.4.json`）：

| 项 | 值 |
|---|---|
| client jar | 1.20.4，sha256 `9221ab46…` |
| intermediary | 1.20.4-v2，`c2df2c16…` |
| **桥编译 stub** | 用本项目 `remap-jar` 从 1.20.4 client 生成，**7787 个 class，全部 major 61**，`dcc0c3dd…` |
| fabric loader | 0.15.11（Java 17 时代构建） |
| fabric api | 0.97.3+1.20.4 |

### 三条实测结论

**1. 目标切换有防线。** `profile-check targets/fabric-1.20.4.json` 直接 rc 3：
`pipeline.rule-order-empty`——**该目标没有规则包，门禁不允许"转换但什么也没做"**。
把 1.21.1 的规则包指过去，再叠加 `rules.target-mismatch`。两个错误码都在，说明不是靠别名蒙混。

**2. 静态断裂为 0，但这不是"能跑"。** fixture 对 1.20.4 索引做 `analyze`：
`missingClass=0 / missingMember=0 / descMismatch=0`，Mixin 目标仍解析。

原因是 intermediary 名在 1.20.1→1.20.4 之间对 fixture 覆盖的 API 保持稳定。
**所以静态探针通过不能推出可运行**：1.20.4 的真实风险是 1.20.2 引入的 configuration 网络阶段、
注册流程时机、以及客户端渲染管线，这些在字节码引用层面看不出来。
据此，本轮**不**把 1.20.4 标记为"架构已通"，只标记"静态无断裂"。

**3. 桥是目标资产，不是通用资产。** `build_bridges.py --profile targets/fabric-1.20.4.json`
产出 **103 个编译错误、0 个 class**：1.21.1 的桥源码引用的成员在 1.20.4 不存在。
这是 A03 那条"目标模式 + class major 检查"之外的另一半事实——**每个目标需要自己的桥**，
不能把 1.21.1 的 `work/bridges` 复用给 1.20.4。

## 这次没有证明的事

- 没有 1.20.4 运行时探针：没有启动 1.20.4 客户端或服务端，构造器/注册/容器/收发包/GUI
  五项**只做到静态定位**，没有一项在 1.20.4 上实际执行。
- 没有 1.20.1 Fabric 运行时基线（见 A05）。
- 没有 configuration 阶段（1.20.2+）的任何验证。
- `targets/fabric-1.20.4.json` 的 `dataVersion` / `resourcePackFormat` 留空：本轮未核实，不猜。
- 1.20.4 的 fabric-api 只下载并 pin，没有解出模块做 API 索引，因此 `analyze` 的
  `missingApiClass` 为 0 不代表 API 兼容，只代表**没查**。
