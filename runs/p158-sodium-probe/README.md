# p158 — Sodium 1.20.1 转换可行性探针（结论：blocked_static）

日期：2026-10-22。目标：不靠猜，用 `mcbridge1201 analyze` 对 Sodium 0.5.13（1.20.1）做静态
伤害矩阵，判断“把 Sodium 当被转换模组”现在是否可行。

## 样本

- `sodium-fabric-0.5.13+mc1.20.1.jar`（Modrinth，SHA-1 `bcdbf37d9494e405cba210d7a80ed58e756297b5`，
  SHA-256 `688c2602…`，971,552 bytes，511 classes）；
- 目标：1.21.1 / fabric；client jar 用 `work/cb/data/jars/client-1.21.1-intermediary.jar`；
- API：Fabric API 0.102.0 + Fabric Loader 0.19.5（补上 loader 后 `apiMissing` 从 35 → 0，
  说明之前的 API 缺失主要是夹具没给全）。

## 结果（静态）

```text
sodium-fabric-0.5.13+mc1.20.1.jar  blocked_static
missingClass=13  missingMember=15  mismatch=16  apiMissing=0  external=9
mixin classes=103  injections=104  unresolved injections=2
```

主要阻塞类别（来自 `plan.json`）：

| 类别 | 例子 |
|---|---|
| 缺失类 | `class_4585`（含 `<init>`/`method_22919/22920`）、`class_287$class_7433`、`class_6491` 的 `method_24895`、`class_761.field_4055`、`class_630$class_628.field_3649` |
| 缺失成员 | `class_289.method_1349/1328/1326/1350`、`class_287.method_22901/35666`、`class_290.field_1578/1579/1581/1583/1587/20886` |
| 描述符不匹配 | `class_2960.<init>(String)`（1.21.1 变 private 工厂）、`class_1058.method_4570/4580 (D)F → (F)F`、`class_437.method_25420(DrawContext) → (DrawContext,int,int,float)`、`class_446` 构造器、`class_4583` 构造器、`class_1294.field_5918` 类型变化 |
| 嵌套 jar 的 yarn 命名 | Fabric API 的 nested jars（block-view/resource-loader 等）里还有 `net/minecraft/block/BlockState` 这类 yarn 名字（10 处） |

另外 Sodium 自带 103 个 mixin 类、104 个注入点，其中 2 个注入目标在 1.21.1 索引里解析不到。

## 结论

- **静态阶段就 blocked**，没有进入运行时/启动验证；
- 这 13+15+16 个点不是加几条规则能糊过去的：Sodium 直接改 BufferBuilder/VertexFormat/
  CloudRenderer 等渲染内核，1.21.1 的 BufferBuilder 已换成 ByteBufferBuilder+MeshData 体系；
- 要真正转换 Sodium，需要为它的渲染内核单独做 1.20.1→1.21.1 的适配层/移植，工作量和
  “重写一个 Sodium”同量级；本轮明确**不做**，也**不宣称**它可用。

## 证据

`analyze.log`、`plan.json`、`plan.md`（静态分析，不代表运行时通过）。
