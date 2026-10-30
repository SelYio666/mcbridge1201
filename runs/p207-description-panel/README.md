# p207 — 描述面板真的有字了：只换尾部，保留建行

p206 把"面板为什么是空的"查到了底，但没修，理由是"建行的副作用和崩溃的绘制在同一个方法体里"。
这一轮把它修了：给 redirect 加一种**保留前缀**的模式，只把尾部那段 1.20.1 `BufferBuilder` 管线换掉。

两次运行只换 `modmenu.jar`，其余全部相同：同一客户端、同样 11 个模组、1280×720 / guiScale 2、
同一光标点 `(156,193)` GUI / `(632,626)` 设备、同样"真实左键点第 3 行"。

| 运行 | jar | 说明 |
|---|---|---|
| `before/` | `modmenu-selected.jar`（p206 的构建，sha256 `8cbb82df…`） | 点得中、高亮画得出，**面板 `count=0`** |
| `after/` | `modmenu-description.jar`（本轮，sha256 `6a6a14ea…`） | 同样的点击，**面板 `count=13`** |

## 做了什么

### 1. 新的 redirect 模式：`keepPrefixBeforeTombstones`

`RuleSet.BodyRedirect` 多一个布尔字段；`JarPatcher.applyBodyRedirects` 里先于整段替换判断它，
走独立的 `keepPrefixThenCall()`：

1. 从方法头往下找到**第一条引用 tombstone 桩的指令**（`centurybridge/gen/Tombstones_*`），尾部从它开始；
2. 从它往前找**块入口 label**——**优先取被某条跳转或异常表引用的 label**，找不到才退回最近的普通 label；
3. 保留 label 之前的一切，之后全部删掉，换成 `INVOKESTATIC bridge` + `RETURN`。

第 2 步是本轮踩到的真 bug：第一次实现取"最近的 label"，而 1397 是块入口、1402 是块内部的行号 label，
结果产物尾部残留了 `class_289.method_1348()` 和一次 `astore 6`（一条没人读的死语句）。改成优先取
被引用的 label 之后，切点从 1402 提前到 1397，残留消失。

切错了不会报错，会变成运行期 `VerifyError`，所以三条前置检查是**抛异常**而不是假设：

```
": kept code jumps past the cut to " + target + ", which would land inside the replaced tail"
": kept code still references centurybridge/gen/*"
": the replaced tail writes <owner>.<field>, so cutting it would drop a state change; move the cut or keep the body"
```

第三条正是 p206 那个缺陷的另一种形状——如果被丢掉的尾部在写本类的字段，那就是在丢状态变化。
还有一条：找不到 tombstone 就拒绝（"no reference to centurybridge/gen/*, so the boundary between kept
and replaced code is undefined"），而不是"什么都没做也报成功"。

`java/src/test/java/top/mcbridge1201/JarPatcherKeepPrefixTest.java` 是它的回归测试（3 个用例）：
成功一条断言前缀的两次字段写入存活、桥被调用、0 处 tombstone、最后一条指令是 `RETURN`；另外两条
分别断言两种拒绝的消息。

### 2. 规则：一条拆成两条，名字不同、动作相同

`rules/fabric-1.21.1/modmenu-list-render.json` 里原来的 `modmenu.description.render-body`
（整段替换）没了，换成两条都带 `"keepPrefixBeforeTombstones": true` 的：

- `modmenu.description.render-tail` → `method_25394`（转换后的 jar 还带着老名字）
- `modmenu.description.render-tail-renamed` → `method_48579`（经过 `render-widget-override.json`
  改名之后的 jar 只有这个名字）

一个 jar 最多命中其中一条，`build.log` 里能看到命中就是 `applied 1 time(s)`。

### 3. 顺手修掉的真 bug：面板画在 x=0

p206 的截图里"面板区域"其实一直没有背景，因为 `DescriptionListWidget.method_46426()`（1.21.1 的
`getX()`）返回 **0**——Mod Menu 用的是 1.20.1 的 `EntryListWidget.setLeftPos()`，1.21.1 删掉了它，
`LegacyParentWidget` 把它复刻成写 `field_19088`，但**从来没同步过 `ClickableWidget.x`**。

于是：画到 `x=0`（盖在模组列表上），而且**面板区域里所有的点击和滚轮都落到 ModListWidget 上**。

修法是两头都改：

- `LegacyParentWidget.method_25333` 在写 `field_19088/19087` 之后补一次 `method_46421(left)`
  （1.21.1 的 `setX`）；
- 桥在读几何时**优先读 legacy 字段**（`field_19088/19087/19085/19086`），没有才退回
  `method_46426/method_46427/method_55443`；`fieldOrNull` 让"没有这个字段"是个正常答案而不是异常。

同一行日志把前后对比说得很清楚：

```
before  P205_LIST class=DescriptionListWidget count=0  left=7   … box=0,108,312,216              firstEntry=none
after   P205_LIST class=DescriptionListWidget count=13 left=335 … box=328,108,312,216 legacy=true getX=328 firstEntry=…DescriptionListWidget$DescriptionEntry
after   P207_PANEL class=DescriptionListWidget box=328,108,312,216 count=10 legacy=true rowLeft=335
```

`P207_PANEL` 只打一次（首帧，那一刻 `count=10`，随后涨到 13），所以它和 `P205_LIST` 的 13 不矛盾。

### 4. 面板画成"一块底"，不是一个行一个条带

p205/p206 的列表是逐行画 `0x80000000` 条带的。描述面板如果照做，文字会变成斑马纹，所以 `panel`
分支改成一个整块底 `PANEL_BACKDROP = 0x80000000`，行条带只在 `if (!panel)` 时画。

顺带补了 `drawScrollBar()`：被删掉的尾部原本也画滚动条，几何按原版（右内缩 2 px、宽 6 px、上下各让 2 px），
颜色是平色（贴图 sprite 没了），**只在有东西可滚时画**（`maxScroll <= 0` 直接返回）。

## 证据

`verify_description.py` 用三类互不依赖的证据，不看桥自己怎么宣称：

### 字节码（5 条）

- `method_48579` 在产物里 **550 行 javap**；
- 里面**还有** `method_25396`（`getEntryList`）和 `DescriptionEntry`——建行的代码活着；
- 里面有 `ModMenuListRenderBridge.renderDescription`；
- 里面**一处 `Tombstones` 都没有**——被删的 API 一个不剩；
- 被切的那个方法体和 p206 记录的 `render-original.txt` **逐行相同**（记录是前缀：843 行 vs 846 行，
  p206 的 dump 停在最后一个 tombstone，真实方法后面还有 `renderScrollBar` / `disableBlend` / `return`）。

产物相对 p206 的 jar **只有 3 个 class 变了**：

```
com/terraformersmc/modmenu/gui/widget/DescriptionListWidget.class   9045 -> 13335
top/mcbridge1201/bridge/ModMenuListRenderBridge.class               7278 ->  9275
top/mcbridge1201/bridge/LegacyParentWidget.class                     790 ->   824
```

### 日志（8 条）

`count=0` → `count=13`；两次都选中第 3 行（`3 / 3`）；ModListWidget 几何未变（11 条、36 px）；
`P207_PANEL box=328,108,312,216`；`legacy=true`；产物三个类没有 `NoSuchMethodError` /
`NoSuchFieldError` / `VerifyError`。

### 像素（3 条）

在面板内部矩形（窗口位图像素 `668,251`–`1284,675`）统计文字灰（亮度 46–110）的逐行像素数，≥8 像素的行合并成条带：

```
control  1 band(s),  204 px
fix      7 band(s), 2920 px   条带 y: 260-267, 279-289, 301-308, 399-425, 459-468, 480-490, 497-508
```

2920 > 204 × 5。control 的那 1 条 204 px 是 ModsScreen 自己的图标/文字漏进矩形边缘，不是面板正文。

## 判据（17/17，rc=0）

```
PASS description_method_exists                       550 lines of javap
PASS description_method_keeps_row_building           getEntryList + DescriptionEntry 还在
PASS description_method_calls_the_bridge
PASS description_method_has_no_tombstone_call        0 处 Tombstones
PASS pre_redirect_body_matches_the_p206_record       843 行是 846 行的前缀
PASS only_the_three_rebuilt_classes_changed
PASS control_panel_has_no_rows                       count=0
PASS fix_panel_has_rows                              count=13
PASS both_runs_selected_the_same_row                 3 / 3
PASS mod_list_geometry_unchanged
PASS panel_reports_its_real_position                 box=328,108,312,216
PASS panel_sits_in_the_right_half
PASS panel_read_its_layout_from_the_legacy_fields    legacy=true
PASS no_linkage_error_in_the_patched_classes
PASS control_panel_has_no_text_bands                 1 band, 204 px
PASS fix_panel_has_text_bands                        7 bands, 2920 px
PASS fix_panel_ink_dominates_the_control             2920 vs 204
```

**滚动条分支本轮没有被执行**：29 个模组的描述最长的那条也没有超过面板高度，`maxScroll=0`，
`drawScrollBar()` 第一行就返回了。`verify_description.py` 把它如实打印成
"scrollbar not drawn in this run (maxScroll=0: no description long enough to scroll)"，
`description-check.json` 里 `scrollbar_lines` 是空数组——它**没有被算成一条通过的检查**。

## 复现

```
python runs/p207-description-panel/build.py
python runs/p207-description-panel/run.py --modmenu work/client/modmenu-selected.jar \
    --out runs/p207-description-panel/before --row 3
python runs/p207-description-panel/run.py --modmenu work/client/modmenu-description.jar \
    --out runs/p207-description-panel/after --row 3
python runs/p207-description-panel/verify_description.py
```

`build.py` 做三件事：编 `ModMenuListRenderBridge` + `LegacyParentWidget`；把
`modmenu-instrumented.jar` 里**原始**的 `DescriptionListWidget.class`（`16051` 字节、含 tombstone、
不含 `println`）换回 p206 那份 jar，得到一个干净的 `restored.jar`；再跑 `patch` 并按名替换
`LegacyParentWidget`。它拒绝把"带 println"或"没有 tombstone"的类当原始件：

```
the pristine DescriptionListWidget carries a println; refusing to ship it
the pristine DescriptionListWidget has no tombstone reference; ...
```

两次 `run.py` 的 `--out` 不同，产出 `before/` `after/`；`work/client/modmenu-selected.jar` 不被覆盖
（p206 的 sha256 还要对得上）。

`run.py` 需要 Pillow（`py -3.12` 有，`python` 没有），缺了会直接给出解释而不是跳过截图：

```
Pillow is not installed for this interpreter (...); run with one that has it, e.g. `py -3.12`
```

## 边界

- 只点了一个行号（第 3 行）、一种描述长度（29 个模组里第 4 个）；没测键盘切换、没测多行框选；
- **滚动条分支未被执行**（见上）：代码路径存在、几何按原版算，但这一轮的 `maxScroll=0`；
- 单机单显示器、guiScale 2、窗口 1280×720；截图相对客户区有 +8 px 的左偏与 +31 px 的顶偏，
  像素判据用的是面板内部矩形，不依赖绝对值精确到 1 px；
- 面板底与滚动条是**平色**，原版的贴图 sprite 没有复刻，是记录在案的视觉退化；
- `legacy=true` 只对**转换来的 1.20.1 子类**成立；原生 1.21.1 的列表走 `method_46426` 那一支，
  这一轮没有轨迹覆盖到它（`panel=false` 的 ModListWidget 一直在走另一支）。
