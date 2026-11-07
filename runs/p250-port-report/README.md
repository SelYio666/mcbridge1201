# p250 — 移植辅助：给一包模组做“分诊”

日期：2026-11-07。回答“做不了自动兼容，那能不能辅助移植”。

## 工具

`tools/port_report.py`：只读 jar 结构与元数据，不启动游戏，输出 Markdown + JSON 分诊表。

```text
python tools/port_report.py --mods <mods 目录> --out report.md --json report.json
```

每个 jar 记录：加载器（Forge `mods.toml` / Fabric `fabric.mod.json`）、mod id、mixin 数、
access transformer、Kotlin 依赖、原生库、内嵌 jar、Forge/NeoForge/Fabric API 引用数，
最后给一个粗判：

| 判定 | 含义 |
|---|---|
| BLOCKED | 渲染/优化内核、原生库、coremod、加载器级 hack（如 Connector）——不是“改几个名字”能过的 |
| HARD | access transformer、重度 Forge API、≥2 个 mixin |
| MEDIUM | 有 mixin 或 Fabric API 引用 |
| EASY | 纯数据/资源/无 mixin，最接近“换个入口点就能跑” |

## 对「缆车末日」替换包的实测（12 个 jar）

```text
BLOCKED=2 · HARD=6 · MEDIUM=1 · EASY=3
```

- BLOCKED：`pmshaders`（渲染内核）、`Connector`（加载器级 jar）；
- HARD：CreativeCore、GlitchCore、ToughAsNails、pmweather、memoryleakfix、zombiegame；
- EASY：bookwyrms、dcrapi（Kotlin）、syals_delight。

完整表格见 [port-report.md](port-report.md)，机器可读版 [port-report.json](port-report.json)。

## 结论（如实）

- 这 12 个 jar **都是 Forge**；把它们搬到 1.21.1 要 NeoForge，属于“逐模组移植”，
  这份表能告诉你从哪个开始、哪些别碰，但不能替你做；
- 本仓库真正能“往下做”的是 **Fabric 目标**：`Main analyze` 会给出符号级损伤
  （missingClass / missingMember / descMismatch），再配规则与桥；
- 所以“移植辅助”分三层：**分诊（本工具，任意加载器）→ 符号级分析（Fabric 目标）→
  规则修补/桥（Fabric→Fabric）**。Forge→NeoForge 目前只到第一层。

## 边界

- 结构级判断，不是兼容性证明：判 EASY 也可能启动就崩（入口点、注册表差异）；
- 不读 Minecraft 版本兼容元数据之外的运行期行为；
- 不修改任何 jar。

## 复现

```text
py -3.12 tools/port_report.py --mods "D:\浏览器所下载文件\缆车末日整合包\2.拖入minecraft文件夹中替换\overrides\mods" \
    --out runs/p250-port-report/port-report.md --json runs/p250-port-report/port-report.json
```
