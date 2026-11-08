# p254 — Forge 1.20.1 包的符号级损伤分析（compat 方向 D，只声称分析）

日期：2026-11-08。新增 `tools/forge_symbol_damage.py`：对一目录 Forge 1.20.1 mod jar 输出
**逐符号**损伤（missingClass / missingMember / descMismatch），替代 p250 `port_report.py`
的结构分诊。**只声称分析，不声称 NeoForge 能跑**。

## 原理

Forge 1.20.1 生产 jar 的引用面 = official 类名 + SRG 成员名（`m_/f_XXXXX_`），描述符也是
official 空间。所以整条联接不需要启动任何东西：

```text
srg 成员 --(mcp_config joined.tsrg, obf<->srg)--> obf 成员
        --(Mojang official 1.20.1 mappings)--> official 成员名
        --(对照 client-1.21.1-mappings.txt 的 official 成员集 + 描述符)--> 损伤判定
```

映射输入：`mcp_config-1.20.1-20230612.114412.zip`（仅 `config/joined.tsrg` 用到，
sha256 `f46d1050d8bed9046886b90a0d2fb80b4c6b5120fc35d32e5d37498dbe0a6d2a`，只落 work/）+
仓库已有的两份 Mojang official mappings。

扫描器解析每个 class 文件常量池的 Methodref/Fieldref/InterfaceMethodref（自写解析器，
不依赖外部库），只统计指向 `net/minecraft/**`、`com/mojang/**` 的引用；Forge/NeoForge/cpw
API 引用单独计数（那是 NeoForge 移植的工作量，不是符号损伤）。

## 实现中修掉的三个真误报（都记进代码注释）

1. tsrg2 的行格式按列数区分：方法行是 `obf desc srg id`（4 列），字段行是 `obf srg id`
   （3 列）——最初按固定列读，字段全部错位；
2. mod 用**接收者类型**引用继承成员（`Player.m_21120_` 声明在 LivingEntity）——tsrg 的
   srg id 全局唯一，用全局反查索引定位真实声明类，否则 2715 条里绝大多数是层级误报；
3. 同一 obf 名可被同类的 static 与实例成员共用——official 名必须按描述符消歧
   （`Style.m_131144_` 曾被解析成另一个成员）。

修完：zombiegame 的 srg 解析失败从 98/1110 降到 7/1110，missingMember 从 386 → 51
（剩下的是真损伤：`ItemStack.getTag/getOrCreateTag/setHoverName` 等 1.20.5 NBT→组件
移除项全部命中，与本仓库 Fabric 侧 analyzer 的结论互相印证）。

## 实测：「缆车末日」替换包 12 个 jar（与 p250 同一批）

| jar | classes | MC 引用 | missingClass | missingMember | descMismatch | forge/NeoForge API |
|---|---|---|---|---|---|---|
| ToughAsNails 9.2.0.171 | 152 | 1185 | 7 | 52 | 258 | 30 |
| bookwyrms 1.2.0 | 20 | 186 | 0 | 20 | 75 | 53 |
| CreativeCore 2.12.37 | 642 | 1738 | 9 | 62 | 331 | 96 |
| dcrapi 0.1.1 | 69 | 125 | 0 | 1 | 31 | 41 |
| ftb-library 2001.2.12 | 318 | 1426 | 13 | 70 | 297 | 11 |
| GlitchCore 0.0.1.1 | 76 | 54 | 1 | 3 | 14 | 77 |
| pmshaders 1.0.2 | 7 | 24 | 0 | 1 | 5 | 0 |
| pmweather 0.16.4-alpha | 198 | 2703 | 11 | 54 | 473 | 249 |
| syals_delight 1.0.0 | 6 | 34 | 5 | 1 | 11 | 25 |
| zombiegame 1.2 | 135 | 1110 | 8 | 51 | 273 | 138 |
| Connector 1.0.0-beta.48 | 1111 | 308 | 16 | 0 | 0 | 275 |
| memoryleakfix 1.1.5 | 132 | 2 | 0 | 0 | 1 | 3 |

合计 missingMember 183 条、descMismatch 1399 条、missingClass 70 条——每条符号都带
（接收者, official 名, srg id, 1.20.1 描述符 → 1.21.1 描述符），在
`forge-damage.json` 里可机读、可排序、可直接喂给移植工单。

## 边界（如实）

- **分析≠能跑**：本工具不检测 Forge API 语义、coremod/ASM 行为、mixin 目标存活、
  事件总线差异，更不声称这些 mod 能在 NeoForge 上启动。
- 构造器引用（`<init>`）未参与成员存在性检查（SRG 名不存在于构造器）；indy/MethodHandle
  常量未扫描——这两类损伤会低估。
- 7/1110 级别的 srg id 在 tsrg 里找不到（合成/动态成员），如实计数为 srgUnresolved。
- descMismatch 里含"同名重载改变"与"参数类型迁移"两种，未再细分语义等价性。
- joined.tsrg 与 mappings 都不入库（work/ 落盘 + 哈希记录，符合仓库 0 数据红线）。

## 复现

```text
curl -o work/tmp/mcp-config-1.20.1.zip https://maven.minecraftforge.net/de/oceanlabs/mcp/mcp_config/1.20.1-20230612.114412/mcp_config-1.20.1-20230612.114412.zip
py -3.12 tools/forge_symbol_damage.py --mods "D:\浏览器所下载文件\缆车末日整合包\2.拖入minecraft文件夹中替换\overrides\mods" --out runs/p254-forge-symbol-damage/forge-damage.json --markdown runs/p254-forge-symbol-damage/forge-damage.md
```
