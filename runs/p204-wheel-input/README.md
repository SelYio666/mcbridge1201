# p204 — 真实滚轮与真实键盘打进 Mod Menu

日期：2026-10-28
结论：**任务 5 的滚轮/键盘半条关了。** 一次真实 OS 滚轮刻度让 Mod Menu 列表精确走 18 px（= itemHeight/2），九格走到上限 147 停住；一次真实鼠标点击把焦点给到搜索框，四个真实字符把列表从 11 项过滤到 1 项。**Cloth Config 半条关不了**，原因不是没测，是它在这个环境里根本建不出来——见第四节。

## 结果

```text
P204_SCROLL_STATE tick=41  scroll=0.0   max=147 entries=11 text=""     scrollEvents=0
P204_SCROLL_STATE tick=173 scroll=18.0  max=147 entries=11 text=""     scrollEvents=3
P204_SCROLL_STATE tick=212 scroll=36.0  max=147 entries=11 text=""     scrollEvents=4
P204_SCROLL_STATE tick=231 scroll=54.0  max=147 entries=11 text=""     scrollEvents=5
P204_SCROLL_STATE tick=249 scroll=72.0  max=147 entries=11 text=""     scrollEvents=6
P204_SCROLL_STATE tick=268 scroll=90.0  max=147 entries=11 text=""     scrollEvents=7
P204_SCROLL_STATE tick=286 scroll=108.0 max=147 entries=11 text=""     scrollEvents=8
P204_SCROLL_STATE tick=304 scroll=126.0 max=147 entries=11 text=""     scrollEvents=9
P204_SCROLL_STATE tick=323 scroll=144.0 max=147 entries=11 text=""     scrollEvents=10
P204_SCROLL_STATE tick=341 scroll=147.0 max=147 entries=11 text=""     scrollEvents=11
P204_SCROLL_STATE tick=390 scroll=0.0   max=0   entries=1  text="menu" scrollEvents=11 charEvents=4
P204_DONE tick=490 scroll=0.0 max=0 entries=1 text="menu" scrollEvents=11 charEvents=4 keyEvents=8
```

`result.json`：`wheel_staircase=true wheel_reached_max=true keyboard_text=true keyboard_filter=true`。
`scroll-check.json`：`track=514 thumb=328 free=186 predicted(1格)=23 measured=22 full=184 checks 全 true`。

## 一、为什么 p104 那次一格都没动，这次动了

p104 的结论是"这台机器收不到滚轮"，理由是三种注入方式（`mouse_event` 绝对移动、`SetCursorPos`、`PostMessage`）之后 scroll 一直是 `0.0`。p202 已经证明那句归因是错的：**当时压着光标的是终端，不是游戏窗口**。p204 沿用 p202 的修法（`ShowWindow(SW_RESTORE)` + `SetWindowPos(HWND_TOPMOST)` + `BringWindowToTop`），并且把"光标底下是不是游戏窗口"当成每次移动都要记的证据：

```text
CONTROL_A outside=(1660,600) underIsGame=False accepted=9 scroll 0.0 -> 0.0 eventsDelta=0
CONTROL_B pane=(1240,391)    accepted=9               scroll 0.0 -> 0.0 eventsDelta=2
MOVE listCenter requested=(632,631) cursorNow=(632,631) underIsGame=True
MOVE listCenter-again requested=(632,631) cursorNow=(632,631) underIsGame=True
FOREGROUND hwnd=9832030 foreground=9832030 ok=True
```

滚轮消息在 Windows 上跟着**光标底下的窗口**走（"悬停滚动非活动窗口"），键盘消息跟着**焦点窗口**走。这两条不同，所以两个通道的修法也不同：

- 鼠标：只要窗口在最上面、光标在窗口里就够了（p202 已验证）；
- 键盘：必须真的抢到前台。测试前显式检查 `GetForegroundWindow()==hwnd`，抢不到就用 `AttachThreadInput` 借前台线程的权限再 `SetForegroundWindow`——日志里 `FOREGROUND hwnd=857604 foreground=857604 ok=True` 就是这个检查，不是假设。

## 二、探针没碰过滚动量

`probes/p204-wheel-input/` 里只有 getter：

| 探针动作 | 用的接口 |
|---|---|
| 读滚动量 | `class_350.method_25341()`（返回 `field_22749`） |
| 读上限 | `class_350.method_25331()` |
| 读条目数 | `class_350.method_25396().size()` |
| 读行高 | `ListAccessor` 的 `field_22741`（只有 getter） |
| 读控件矩形 | `WidgetAccessor` 的四个 `field_2276x`（只有 getter） |
| 读搜索框文本 | `class_342.method_1882()` |

`setScrollAmount`（`method_60321` / `method_25307`）在探针里一次都没被调用——回归测试会直接在源码里找这两个名字，找到就红。

三个"事件确实来自窗口"的钩子：

1. `ScrollProbeMixin` 打在 `class_312.method_1598`（GLFW scroll 回调落地处）的 HEAD，记 `dx/dy`。九格滚轮在日志里就是九条 `dy=-1.0`；
2. `TextFieldMixin` 打在 `class_342.method_25400/25404`（**只有拿到焦点的控件才会被派发**），记每个字符；
3. 探针每 25 tick 记一次 `focus=` 与 `searchFocused=`，所以"焦点在哪"是日志里的字段，不是旁白。

## 三、阶梯为什么正好是 18

原版 `EntryListWidget.method_25401` 是 `scroll -= amount * itemHeight / 2`：

```text
public boolean method_25401(double, double, double, double);
   1: invokevirtual  method_25341   // getScrollAmount
   8: getfield       field_22741    // itemHeight
  12: dmul
  13: ldc2_w 2.0
  18: dsub
  18: invokevirtual  method_25307   // setScrollAmount
```

探针报 `itemHeight=36`，所以一格 = 18。实测就是 18/36/54/72/90/108/126/144，第九格 `144+18=162` 被 `method_60321` 的 `clamp(0, max)` 夹到 `147`。**这个数字是原版算出来的，探针连夹取都插不上手。**

### 两个对照

| 对照 | 光标在哪 | 滚轮刻度 | 事件 | 列表 |
|---|---|---|---|---|
| A | 游戏窗口外（`underIsGame=False`） | 9 | **0** | 不动 |
| B | 窗口内、列表外（右侧面板） | 9 | 2（`dy=-1` 和 `dy=-8`，合计 −9，OS 把 8 格合并成一条） | **不动** |
| 主测 | 列表中心（`underIsGame=True`） | 9 | 9（`dy=-1` 各一条） | 18→…→147 |

A 证明这套注入不是"不管光标在哪都能滚"；B 证明**事件到了、列表没动**——位置命中测试是真的在起作用，不是"窗口收到滚轮就全局滚动"。B 那两条还顺带说明刻度没有被注入器放大或缩小：9 格就是 9 个单位，只是分成了两条消息。

### 键盘

先真实左键点搜索框（`P204_HEART` 里 `searchFocused=true`），再 `SendInput` 发 `KEYEVENTF_UNICODE` 的 `m/e/n/u`：

```text
P204_KEY  n=1 code=-1 scan=0      ← VK_PACKET，GLFW 报 GLFW_KEY_UNKNOWN
P204_CHAR n=1 c=m  code=109
…（每个字符一对 KEY + 一条 CHAR）
P204_SCROLL_STATE tick=390 scroll=0.0 max=0 entries=1 text="menu" charEvents=4
```

`code=-1` 恰好说明了为什么"按键数"不能当证据：`KEYEVENTF_UNICODE` 走的是 `VK_PACKET`，GLFW 认不出键码，字符是从 **char 回调**进来的。真正说明问题的是 `text="menu"` 和 `entries 11 → 1`：文本进到了控件里，过滤器照它重算了列表，`max` 从 147 掉到 0。

## 四、Cloth Config：不是没测，是建不出来

任务 5 的另一半是 Cloth Config 界面。这个环境里有 Cloth Config，但它是 **1.20.1 的 JiJ 捆绑包**（`cloth-config-fabric-11.1.136`，藏在 AppleSkin / ShulkerBoxTooltip 的 `META-INF/jars/` 里），Fabric 照样把它加载进了 1.21.1（资源包列表里能看到 `cloth-config`）。它一被真正使用就死：

```text
Error from mod 'appleskin'
java.lang.NoSuchFieldError: Class net.minecraft.class_437 does not have member field
    'net.minecraft.class_2960 field_44669'
  at me.shedaniel.clothconfig2.impl.ConfigBuilderImpl.<init>(ConfigBuilderImpl.java:53)
  at me.shedaniel.clothconfig2.api.ConfigBuilder.create(ConfigBuilder.java:36)
  at net.blay09.mods.balm.fabric.compat.ClothConfigUtils.lambda$getConfigScreen$1(...)
  at com.terraformersmc.modmenu.ModMenu.getConfigScreen(ModMenu.java:61)
  at com.terraformersmc.modmenu.gui.ModsScreen.method_25426(ModsScreen.java:114)
```

同一条栈在 `trashslot`、`fallingtree`、`shulkerboxtooltip` 各打了一次——因为 Mod Menu 的 `ModsScreen` 初始化时会替每个模组问一遍"你有没有配置界面"，四家都是 Cloth 路线，四次全炸（`field_44669` 是 1.20.1 `Screen` 的背景文理字段，1.21.1 已移除）。

所以：**Cloth Config 的界面在这个产物里根本打不开**，谈不上滚轮。这不是跳过，是一个带栈的结论：要让 Cloth Config 界面能用，得先把它按 1.21.1 转换（它是个大库，属于单独一轮的工作量）。`docs/remaining-work.md` 里原来那句"其他模组的 Cloth-Config 界面未测"已改成"不可用 + 原因"。

## 五、顺手纠正一句旧话

p94 的 README 写着"截图里能看到列表行（图标、名称、描述、滚动条）"，但 `runs/p94-modmenu-list/modmenu-list.png` 和 `modmenu-scrolled.png` 里左边列表是**全黑**的，只有滚动条。p204 的四张截图也一样：列表行不画，滚动条画。

所以 p204 的视觉校验做在**滚动条**上，因为它是控件自己按滚动量算出来的：

```text
thumb_top = list_top + scroll / max_scroll * (track - thumb_height)
```

`verify_visual.py` 不用固定阈值：先在列表右侧条带里找"整列中位亮度最高"的那一列（轨道暗、滑杆是一条约 100 的灰条），再用"轨道最暗值与该列中位数的中点"切出滑杆的上下沿，然后对两个预测：

| 量 | 预测 | 实测 |
|---|---|---|
| 一格（scroll 18 / max 147）的滑杆位移 | `18/147 × (514−328) = 23` | **22** |
| 满格（scroll 147）的滑杆位移 | `514−328 = 186` | **184** |
| 过滤后（max=0） | 不画滑杆 | **不画** |

滑动 22 vs 23 的 1 px 差是滑杆抗锯齿边界取整；判定容差 ±3。

## 边界（如实）

- 只在**单机单显示器**、窗口 1280×720、guiScale 2 上跑过；DPI 未变。
- 测的是 **Mod Menu 的列表**与它的搜索框；Cloth Config 界面不可用（见第四节）；Mod Menu 自己的选项界面（p97）没在本轮重复。
- **方向键/PageDown 没测**：`KEYEVENTF_UNICODE` 只能送字符，方向键要真实扫描码；本轮只证明了"字符 + 点击"这条键盘通道。
- 列表行不画（第五节）是一个**独立缺陷**，本轮没有修，也没有假装它不存在；滚动与过滤的证据不依赖行是否可见。
- 只有两次运行（主跑 + `repeat/`），不是多次重复的统计。

## 复现

```text
python runs/p204-wheel-input/build.py                     # 编译探针到 work/tmp/p204probe.jar
python runs/p204-wheel-input/run.py --notches 9 --timeout 300
python runs/p204-wheel-input/verify_visual.py             # 滚动条量测 → scroll-check.json
```

`run.py` 需要带 Pillow 的解释器（本机是 `%LOCALAPPDATA%\Programs\Python\Python312\python.exe`）；
`python` 3.13 那份没有 Pillow，截图会跳过。

## 证据

| 文件 | 内容 |
|---|---|
| `client.log` | 探针全部输出（`P204_*`），含 11 条 `P204_SCROLL`、4 条 `P204_CHAR`、八条 `P204_KEY`、Cloth 栈 |
| `harness.log` | 每次 OS 输入：机制、请求坐标、回读、`underIsGame`、每格之后的滚动量 |
| `result.json` | 阶梯、对照、键盘与判据 |
| `scroll-check.json` | 滑杆列/上下沿/预测 vs 实测 |
| `list-before.png`、`list-scrolled.png`、`list-scrolled-max.png`、`list-filtered.png` | 四帧（滚动前 / 一格 / 满格 / 过滤后） |
| `build.py`、`run.py`、`verify_visual.py` | 构建 / 驱动 / 量测 |
| `repeat/` | 第二次独立运行的关键行 |
| `probes/p204-wheel-input/` | 探针源码（`WheelProbe`、`ScrollProbeMixin`、`TextFieldMixin`、`WidgetAccessor`、`ListAccessor`） |

无新 release（p204 只加探针与证据，没有 mod 代码改动）。
