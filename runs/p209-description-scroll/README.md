# p209 — 滚轮真的能滚描述面板，滚动条也真的画出来了

p207 的判据最后一行是"scrollbar not drawn in this run (maxScroll=0: no description long enough to
scroll)"——那条画滚动条的代码**一次都没跑过**。这一轮让它跑起来，并且顺手发现原来那行调试输出
分不清"不需要滚"和"根本没跑到"。

两次运行只换 `modmenu.jar`，窗口、模组、光标路径、滚轮格数全部相同；与 p205/p206/p207 的唯一
区别是**窗口宽度 800** 而不是 1280。

| 运行 | jar | 说明 |
|---|---|---|
| `before/` | `modmenu-description.jar`（p207 的构建，sha256 `6a6a14ea…`） | 同一套操作，能看到面板滚动，但看不到"没滚" |
| `after/` | `modmenu-scroll.jar`（本轮，sha256 `01019f6a…`） | 同一套操作，两个列表的滚动量都被报出来 |

## 怎么让滚动条真的需要画

不去造一段假描述，也不去改模组：**把窗口压窄**。宽度 1280 → 800（guiScale 2 不变，gui 400×360），
描述面板从 312 px 宽变成 192 px，同一段文字换行明显变多。p207 在 1280 下只验证过第 3 行（13 行，
`maxScroll=0`），所以这里不是"同一行的 13 变成 78"——这一轮把 7 个可见行全部扫了一遍，第 5 行的
描述换行后是 **78 行（≈936 px）**，而面板只有 216 px 高，`maxScroll` 于是是 **568**。

哪一行值得滚是**量出来的**，不是猜的：harness 依次点可见的 7 行，每行读一次面板的行数与
`maxScroll`：

```
SCAN row=0 desc_count=11  max=0   drawn=False
SCAN row=1 desc_count=11  max=0   drawn=False
SCAN row=2 desc_count=10  max=0   drawn=False
SCAN row=3 desc_count=15  max=0   drawn=False
SCAN row=4 desc_count=6   max=0   drawn=False
SCAN row=5 desc_count=78  max=568 drawn=True  thumb=110+58
SCAN row=6 desc_count=0   max=0   drawn=False
```

只有第 5 行需要滚（78 行 × 12 px ≈ 936 px 内容，面板只放得下 216）。

## 滚轮的两个方向

光标停在面板中心（`(1168,672)` 设备坐标，`underIsGame=True`），发三格滚轮；然后把光标移到模组
列表中心，同样三格：

```
WHEEL over=panel  desc 0.0 -> 10.0      thumb 110+58 -> 113+58
WHEEL over=panel  modListScroll 0.0 -> 0.0
WHEEL over=list   modListScroll 0.0 -> 36.0
WHEEL over=list   descScroll 10.0 -> 10.0
```

**两个方向都测**才是这条结论的关键：只测"在面板上滚，面板动了"无法排除"任何位置的滚轮都同时喂给
两个列表"。这里的方向是互斥的——面板动时列表不动，列表动时面板不动。

值得一提的数字：一次滚轮格在面板上是 **5 px**、在模组列表上是 **18 px**（p204 逐格发九格量到的），
两者都等于列表 `itemHeight / 2`（10/2、36/2）。这批三格实际只落到 **2 格**（5×2=10、18×2=36）——
另一次尝试落到了 3 格（面板 15 px）。所以判据比的是**方向**，不是总数：一次 SendInput 里到底有几格
被客户端消费，这些运行里并不稳定，把它当成固定的 3 就会写出一个偶然通过的断言。

## 顺手发现的证据缺陷

p207 的那行 `P207_SCROLL` 打在"早退之后"，也就是说**只有画了才打**。于是：

- 选完第 5 行 → 打一条 `max=568 thumb=110+58`；
- 再选第 6 行（这条描述是空的，`count=0`）→ 不画、不打，**最后一条仍是第 5 行那条**。

对照组的日志里就是这个样子：

```
control scan row=6 desc_count=0 max=568    ← 568 是上一行的
```

"没有可滚的内容"和"这一帧根本没跑到那段代码"在这行里长得一模一样。这正是 p207 里"滚动条未执行"
没法从日志自证的原因。本轮把这条改成**状态变化就打一次**，并且把 `drawn=` / `view=` 一起写进去：

```
after scan row=6 desc_count=0 max=0 drawn=False thumb=none
```

同一份日志里还暴露出另一个坑：`runs/p204-wheel-input` 的探针用 `findList()` 找列表，它挑的是
`getMaxScroll()` **最大**的那个 `class_350`——描述面板一旦变得可滚动（568 > 147），探针报告的
对象就从模组列表换成了面板。本轮的 `result.json` 把它记成 `probe_state_targets=[11, 78]`
（11 = 模组列表的条目数，78 = 面板的），而不是把两个列表的数字混在一起用。所以"模组列表有没有
动"这个读数改从桥自己的 `P205_LIST` 行取（本轮给它加了 `scroll=` / `max=`）。

## 像素

面板右缘 6 px 的滚动条列（窗口位图 `x=792..798`，可见区 `y=251..675`），亮度 ≥ 35 的连续段就是滑块：

```
before  [[251, 366]]   高 116 设备像素 = 58 gui 像素
after   [[257, 372]]   高 116，起点下移 6 设备像素
```

- **高度对得上公式**：`trackHeight = view-4 = 212`，`visible = 212/(212+568)`，
  `thumb = max(16, round(212 × visible)) = 58` gui → 116 设备像素，实测 116。
- **位移对得上比例**：滑块不是在 1:1 跟随滚动，它只在 `trackHeight - thumbHeight = 154` gui 像素
  的行程里按 `scroll/max` 走，所以 10 px 的滚动只让它下移 `154 × 10/568 ≈ 3` gui 像素（6 设备）。
  实测 6，按比例算 5.4，判据给 ±2 的余量（两个位图之间还有 2 px 的取整差）。
  判据第一版按 1:1 写，于是**误判了一次正确的绘制**——这条记在 `verify_scroll.py` 的注释里。
- **正文确实往上走了**：面板内部（排除滚动条列）做有符号平移的互相关，`before` 对 `after`
  的 `best_dy = -20`，正好是 10 gui × 2 = 20 设备像素；零位移的分数是 5.69 对 1.53，差 3.7 倍。
  对照组同样自洽（10 gui → -20）。

## 判据（23/23，rc=0）

```
PASS only_the_bridge_differs_from_the_p207_jar
PASS the_shipped_bridge_reports_scroll_and_max
PASS the_p207_bridge_does_not_report_the_same_fields
PASS the_shipped_bridge_still_filters_its_debug_lines
PASS control_panel_also_scrolls_the_wheel_already_worked      0.0 -> 10.0
PASS control_line_cannot_tell_stale_from_empty               row6 count=0 max=568
PASS control_cannot_measure_the_mod_list_scroll
PASS exactly_one_row_needs_scrolling                         [5]
PASS that_row_is_long_enough_to_scroll                       max=568 rows=78
PASS every_other_row_reports_max_zero_instead_of_nothing
PASS the_empty_row_is_no_longer_a_stale_copy_of_the_previous_one
PASS the_panel_wheel_moved_the_panel                         0.0 -> 10.0
PASS the_panel_wheel_left_the_mod_list_alone                 0.0 -> 0.0
PASS the_panel_wheel_moved_the_thumb_down                    110+58 -> 113+58
PASS the_mod_list_wheel_moved_the_mod_list                   0.0 -> 36.0
PASS the_mod_list_wheel_left_the_panel_alone                 10.0 -> 10.0
PASS the_run_recorded_that_the_probe_switches_targets         [11, 78]
PASS no_linkage_error_from_the_two_new_reflective_reads
PASS one_thumb_is_drawn_at_the_panel_edge                     [251,366] -> [257,372]
PASS the_thumb_height_is_what_the_formula_predicts            116 vs 2*58
PASS the_thumb_moves_by_the_scroll_ratio                      moved 6, expected 5
PASS the_text_moves_up_by_the_scroll_amount                   -20 vs -20
PASS the_control_text_moves_by_its_own_scroll_amount          -20
```

## 复现

```
python runs/p209-description-scroll/build.py
python runs/p209-description-scroll/run.py --modmenu work/client/modmenu-description.jar \
    --out runs/p209-description-scroll/before
python runs/p209-description-scroll/run.py --modmenu work/client/modmenu-scroll.jar \
    --out runs/p209-description-scroll/after
py -3.12 runs/p209-description-scroll/verify_scroll.py
```

`build.py` 只编 `ModMenuListRenderBridge` 一个类，用 `tools/inject_bridges.py --replace` 换进
`modmenu-description.jar` 的副本；它自己断言产出相对 p207 的 jar **只有这一个 class 变了**
（`DIFF changed=…ModMenuListRenderBridge.class added=none removed=none`），否则拒绝出包。
`verify_scroll.py` 会再独立比一次两个 jar 的条目。

## 边界

- 单机单显示器、guiScale 2、窗口 800×720；**gui 宽度只有 400**，比 1280 下的排版窄得多，面板
  左右各只剩 2 px 余量，这个宽度下的换行数是这一轮特有的；
- 只测了 7 个可见行（模组列表自己也要滚，第 7 行以下的中心点在列表外，点了会落到按钮上）；
- 滚轮格数不固定落地 2~3 格（见上），判据只比方向与比例；
- 滑块颜色/宽度是 p207 的平色近似（贴图 sprite 未复刻），本轮没有重新审视它好不好看，只验证它
  在不在、对不对位置；
- 触摸板/高精度滚轮的亚格输入、Shift+滚轮的横向滚动都没有测。
