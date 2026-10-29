# p206 — 选中行的可见高亮，以及描述面板为什么是空的

p205 修好了列表行，留下两件没交代的事：**选中行没有任何视觉反馈**，**描述面板一条文字都没有**。
这一轮把第一件做完，把第二件查到底——但没修，原因是它比"补一行绘制"大得多。

两次运行只换 `modmenu.jar`，其余全部相同：同一客户端、同样 11 个模组、1280×720 / guiScale 2、
同一个光标点 `(632,626)` 设备坐标、同样"真实左键点第 3 行"。

| 运行 | jar | 说明 |
|---|---|---|
| `no-highlight/` | `modmenu-rows.jar`（p205 的构建，sha256 `9cb27e54…`） | 点得中、选得中，但**不画任何高亮** |
| `highlight/` | `modmenu-selected.jar`（本轮，sha256 `8cbb82df…`） | 同样的点击，画出高亮 |

## 做了什么

原版 `EntryListWidget.method_44398` 负责画选中行，路径是两次 `fill`：

```
fill(x1, y-2, x2, y+rowHeight+2, 选中色)   // 上下各溢出 2 px 的条
fill(x1+1, y-1, x2-1, y+rowHeight+1, 黑)   // 内缩 1 px 的芯
```

也就是说**原版的"选中"是一条 1 px 描边**，里面是黑的（`method_44397` 里 `method_25332(i)` 为真时调用，
颜色 `hasFocus() ? -1 : -8355712`，边框 `-16777216`）。桥接不了这个方法（redirect 只换被替换方法的
方法体，`method_44398` 仍是 protected 的成员），所以照字节码重写了一份。

**这里我做了一处有意的偏离**：1 px 白边压在近黑的平色行底上几乎看不见（本轮第一次运行的截图就是
这样）。所以在描边之后又铺了一层半透明底（聚焦 `0x40FFFFFF`、未聚焦 `0x24FFFFFF`），让"选中"真的
读得出来。这不是原版行为，写在代码注释里，也写在这里。

## 证据

`verify_rows.py` 不看桥自己怎么宣称，只看像素：对 `sel-before.png` / `sel-after.png` 做**有符号**差分
（变亮 / 变暗分开统计），在列表矩形内按行统计变化像素数，超过行宽 40% 的行合并成条带。

```
control: changed=92    gained=[]             lost=[]
fix:     changed=47602 gained=[[378, 463]]   lost=[[165, 244]]
         gained centre=420.5 (预测 413.0), height=86 (预测 72)
         lost   centre=204.5 (预测 197.0)
```

- 旧 jar 点完只变了 **92** 个像素（行内文字与 hover），**没有任何条带**——选中确实没画；
- 新 jar 变了 **47602** 个像素：**多出一条** 86 px 高的条带在 `378..463`，**少了一条**在 `165..244`；
- 两条条带的位置和"选中从第 0 行移到第 3 行"对得上：第 0 行预测中心 197、实测 204.5；第 3 行预测
  413、实测 420.5（整幅截图相对客户区有 +8 px 的标题栏偏差，两条一起偏，间距是对的）。
- 桥自己的记录同向：`P205_SELECT class=ModListWidget selected=0 … focused=false` →
  `selected=3 … focused=true`，真实左键让列表拿到了焦点。

`ring-compare.png` 是 2×2 拼图（左列=打开时，右列=点完；上排=旧 jar，下排=新 jar）：上排两格都没有
高亮，下排左格第 1 行有亮带、右格第 4 行有亮带。

## 描述面板：不是"没测"，是我们的 redirect 把它掏空了

p205 记的是"描述面板 `count=0`，未验证"。这一轮查清了原因，而且**没有修**：

- `DescriptionListWidget.method_48579`（1.21.1 的 render）被规则整段替换成一次
  `ModMenuListRenderBridge.renderList(...)` 调用（`bytecode/render-redirected.txt`，方法体只有 12 行字节码）；
- 但在**替换之前**的那个方法体里，前 1397 个字节码干的是"**建行**"：读 `parent.getSelectedEntry()`、
  和 `lastSelected` 比、`method_25339()` 清空、`method_25307(-MAX)` 回顶、把
  `mod.getTranslatedDescription()` 按宽度换行、逐行 `new DescriptionEntry(...)` 塞进列表——之后才是
  1.20.1 的 `BufferBuilder` 管线（17 处 tombstone 调用，`bytecode/render-original.txt`，851 行）；
- 换句话说：**建行的副作用和崩溃的绘制在同一方法里**。我们为了让绘制不崩，把整个方法体换掉，于是
  行永远不会有——`count` 在每一帧都是 0，面板只剩 ModsScreen 自己画的那部分（图标、名字、两个按钮），
  正文区是空的（`sel-after.png` 可直接看到）。

修它要么把"建行"那段逻辑按 1.21.1 重写在桥里（描述、更新状态、Modrinth、链接、来源、许可证、致谢
共 24 处 `DescriptionEntry` 构造），要么只替换尾部那段 tombstone 管线、保留前半段。两条都不是一行
改动，所以本轮**不动**，只在 `verify_rows.py` 里把它记成一个显式的检查项
（`description_panel_is_empty_in_both_runs`），避免下次又被写成"未验证"。

## 判据（10/10，rc=0）

```
PASS control_draws_no_selection            旧 jar 的点击不产生条带
PASS fix_changes_more_than_control         47602 > 3 × 92
PASS fix_gains_exactly_one_band            变亮只有一条
PASS fix_loses_exactly_one_band            变暗只有一条
PASS gained_band_height_matches_the_row    86 vs 72，±16
PASS gained_band_sits_on_the_clicked_row   420.5 vs 413，±12
PASS lost_band_sits_on_the_previously_selected_row  204.5 vs 197，±12
PASS fix_selection_moved_to_the_clicked_row 0 → 3
PASS fix_list_took_focus                   false → true
PASS description_panel_is_empty_in_both_runs
```

## 复现

```
python runs/p206-modmenu-select/build.py
python runs/p206-modmenu-select/run.py --modmenu work/client/modmenu-rows.jar \
    --out runs/p206-modmenu-select/no-highlight --row 3
python runs/p206-modmenu-select/run.py --modmenu work/client/modmenu-selected.jar \
    --out runs/p206-modmenu-select/highlight --row 3
python runs/p206-modmenu-select/verify_rows.py
```

`build.py` 只编 `ModMenuListRenderBridge` 一个类，用 `tools/inject_bridges.py` 换进去；产出
`work/client/modmenu-selected.jar`，不动 p205 那份 `modmenu-rows.jar`（那一轮的 sha256 还要对得上）。

## 边界

- 单机单显示器、guiScale 2、窗口 1280×720；只点了一个行号（第 3 行），没有测键盘选择、没有测多行框选；
- 半透明底是**有意偏离原版**；描边+黑芯那两层是按 `method_44398` 字节码逐条复刻的；
- 截图相对客户区有 +8 px 的竖直偏差（标题栏），判据里用两条条带的相对间距校验，绝对值只做 ±12 的粗校验；
- 描述面板**仍然是空的**，本轮只给出原因与证据；
- 窗口置顶偶尔会被系统忽略（本轮第一次跑就撞上了 `underIsGame=False`），`run.py` 现在会重试三次，
  三次都不行才退出——不是"重试到通过"，是记录每次都失败后如实报错。
