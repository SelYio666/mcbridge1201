# p199 — Sodium 迁移可行性评估的证据

日期：2026-10-28。性质：**调研/方案，不是移植**。没有转换成功、没有启动游戏、没有写任何转换规则，
不宣称支持 Sodium。

产出：`docs/sodium-plan.md`（方案正文）。本目录是它的证据与复算脚本。

## 为什么要单独做这一层

p158 的静态矩阵只说“这里对不上”：13 个类解析不到、15 个成员解析不到、16 个描述符对不上。
它不回答“每个到底变成了什么”，所以没法判断工作量。本轮把每条落回命名空间：

- 输入：`runs/p158-sodium-probe/plan.json`；`work/target/intermediary-{1.20.1,1.21.1}-v2.jar`；
  `work/target/client-{1.20.1,1.21.1}-mappings.txt`（仓库工作集已有，不下载任何东西）。
- 连接方式：intermediary 描述符里的 obf 类名改写成官方名（`L` 描述符里点号换斜杠），
  与 Mojang 映射按 `(obf 类, obf 成员, 官方描述符)` 三元组连接；Mojang 文件把返回类型写成前缀，
  要折回描述符里；构造器在 intermediary 里不出现，单独按描述符从 Mojang 侧比对。
  这样 `a`/`b` 这类重载 obf 名不会张冠李戴（第一版就是因为按名字连而错配，已废弃）。
- 判定：`removed` / `re-signed` / `re-ID` / `moved` / `unresolved`。`unresolved` 一律列出，
  不静默丢弃。

## 结果（44 条）

| 桶 | 总数 | Sodium 侧 | Fabric API（内嵌）侧 |
|---|---|---|---|
| missingClass | 13 | 12（re-ID 7、re-signed 2、removed 3） | 1（removed） |
| missingMember | 15 | 14（removed 13、unresolved 1） | 1（unresolved） |
| descMismatch | 16 | 12（re-signed 11、removed 1） | 4（re-signed 3、unresolved 1） |
| **合计** | **44** | **38**（re-ID 7、re-signed 13、removed 17、unresolved 1） | **6**（re-signed 3、removed 1、unresolved 2） |

三条 `unresolved`（全部列出，各有原因）：

- `net.minecraft.world.level.block.entity.BlockEntity#getRenderData` —— Fabric API 接口注入的方法，
  vanilla 映射里不存在，Sodium 侧调用了它；
- `net.minecraft.server.packs.repository.Pack$ResourcesSupplier#open` —— Fabric API 接口方法；
- `net.minecraft.nbt.ListTag#add` —— 继承自集合基类，1.20.1 侧也不在本类声明。

## 两个纠正 p158 印象的发现

1. **6 条不是 Sodium 的代码。** 它们来自 Sodium `META-INF/jars/` 里内嵌的 1.20.1 版 Fabric API 模块
   （block-view、resource-loader）。真机上 1.21.1 的 API 按版本胜出，这些引用大概率不会阻塞。
   **但本轮没有验证这一点**，只在表里按“来源”标注，不计入 Sodium 工作量。
2. **阻塞集中在即时模式顶点管线。** 13 条成员删除全部落在 `BufferBuilder` / `Tesselator` /
   `DefaultVertexFormat`；Sodium 的 `SodiumBufferBuilder` 直接继承 `BufferBuilder`，3 个 mixin 也注入
   在它上面。这不是“改名类”问题，是 1.21.1 换掉了整个模型（`ByteBufferBuilder` + `MeshData`）。

## 边界（不夸大的部分）

- 全是**静态**结论：只回答“名字还在不在、签名变没变”，不回答“行为是否等价”。
  `ANALYZED` ≠ `VERIFIED` ≠ `BOOTED`。
- 判定依赖官方映射与 Fabric intermediary；映射里本来就没有的成员（如 Fabric API 注入的方法）
  只能标 `unresolved`，不能猜。
- 工作量只有“量级”判断（规则级 / 适配层级 / 内核级），没有排期承诺。
- 没有写规则、没有生成端口 jar、没有启动客户端；本目录不含任何游戏或模组 jar。

## 门禁

`runs/p199-sodium-plan/gate.log`（本次）：`check_text_encoding` 225 个跟踪 `*.md` 全绿；
`test_review_fixes` **105/105**；`verify_evidence` passed；`check_hashes` **1270/1270**。
本轮没有改 Java、没有改转换规则，所以不涉及 `gradle test installDist`。

## 复现

```text
python runs/p199-sodium-plan/resolve.py            # 三张表 + 汇总 + unresolved 清单
python runs/p199-sodium-plan/resolve.py --json     # 逐条机器可读
```

## 证据

`README.md`、`resolve.py`、`resolve-table.log`（表格原文）、`resolve.json`（逐条）。
方案正文见 `docs/sodium-plan.md`。
