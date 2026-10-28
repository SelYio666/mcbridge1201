# p202 — OS 光标级悬停 + 27 格异质 NBT 抬头

日期：2026-10-28
结论：p193/p196/p197 剩下的两条都关了。**悬停这次由窗口系统送进游戏**（探针全程不写鼠标字段），**27 个格子携带 27 套不同 NBT**（服务端下发、客户端读出、渲染器逐格画、截图逐格对）。

## 结果

```text
P202_HOVER_OK tick=30 index=10 item=minecraft:shulker_box … keysSent=false
              glfw=686.0,378.0 raw=686.0,378.0 mouse=686.0,378.0 target=686.0,378.0
P202_NBT_SUM  stacks=27 distinctComponents=27 distinctItems=27 distinctNames=27
P202_DONE     hoverTick=30 fallbackTick=-1 osCursor=true glfwCursor=false keysSent=true
              nbtStacks=27 nbtDistinct=27 drawnDistinctNonAir=27 drawnItemIds=27
```

`grid-check.json`：`pitch.columns=36 pitch.rows=36 cell_size=36 distinct_cells=27 blank_cells=0 passed=true`。

## 一、悬停：这次真的是光标送进来的

p191/p193/p197 的瞄准方式是**用 accessor 写 `Mouse.field_1795/1794`**。那条路能证明渲染器没错，但证明不了"光标位置能到达游戏"。p202 换掉的是这个：

- 探针**不写任何鼠标字段**。`MouseReadAccessor`、`HandledScreenAccessor` 都只有 getter，没有 setter，所以"写进去"这条路径在编译期就不存在；
- 探针把槽位 10 的**窗口坐标**算出来打进日志（`P202_TARGET winx=686 winy=378`），然后由外部进程 `run.py` 用 `user32.SetCursorPos` / `SendInput` 把**真实光标**移过去；
- 位置要想变成悬停，只能走完这条链：

  ```text
  WM_MOUSEMOVE → GLFW cursor-pos callback → Mouse.onCursorPos → Mouse.tick
               → GameRenderer → Screen.render(DrawContext, mouseX, mouseY, delta)
               → HandledScreen.isMouseOver(slot) → focusedSlot
  ```

- `P202_CURSOR` 把**两个独立读法**并排打出来：GLFW 自己查的 `glfwGetCursorPos`，和游戏从回调算出来的 `Mouse.getX()/getY()`，再加上回调里存下来的 `raw`。三者与探针独立算的目标值**逐位相同**（`686.0,378.0`）；
- `P202_HOVER_OK` 只有在 `HandledScreen.focusedSlot`（`field_2787`）**就是槽位 10** 时才打，且这行带 `keysSent=false` —— 也就是说这时候还一个合成按键都没发过；
- 之后才有 `DRAWTOOLTIP … data=…PreviewTooltipData`（vanilla tooltip 渲染器收到 mod 的数据），以及 COMPACT/FULL。

### 一次更正：p191/p193/p197 那句"这台机器收不到 OS 光标移动"是错的

那三轮的 `MouseAccessor` 注释里写着"OS cursor moves are not picked up by the game window (RES_MOUSE pinned at the window centre)"，p202 的控制组证明这句话不成立：

| 运行 | 光标怎么动的 | 结果 |
|---|---|---|
| 第 1 轮（未提交） | 只 `SetCursorPos`，窗口**没置顶** | ❌ 无悬停，200 tick 后走 `glfwSetCursorPos` 兜底也没有 |
| 第 2/3 轮（提交） | `SetCursorPos` + `SendInput`，窗口 `SWP_TOPMOST` 置顶 | ✅ tick 28–30 悬停 |
| 控制组（`repeat/run3-control-warp.log`） | **只** `SetCursorPos`，窗口置顶 | ✅ tick 26 悬停 |

控制组是关键：**只做指针 warp 也能悬停**。所以第 1 轮失败的原因不是"warp 不产生消息"，而是**那个点上压着的窗口不是游戏窗口**（自动化跑的时候终端在最上面）。修法是 `_focus()` 里 `ShowWindow(SW_RESTORE)` + `SetWindowPos(HWND_TOPMOST)` + `SetForegroundWindow`，并在每次移动后查 `WindowFromPoint` 记进 `harness.log`（`underCursor=… underIsGame=True`）——现在这条证据是显式的，不靠猜。

也就是说：机制从来不是问题，**"光标底下的窗口必须是游戏"**才是。p191/p193/p197 因为没置顶，把这件事误记成了"这台机器不支持"。三条 README 已各加一行指向这里。

## 二、27 格：27 套不同 NBT

p196 的 27 格是 27 种 item id，但**组件全空**（`distinctComponents=6`），也就是说"异质"只体现在图标上。p202 让服务端下发一套真的异质数据（`run.py:_slot_item`）：

| 每格都有的 | 部分格子额外有 |
|---|---|
| 不同 item id（27 种）、不同数量（1–3）、不同自定义名（`S00`…`S26`） | `lore`（2 行，i%3==0）、`enchantments`（sharpness 1–5，i%4==0）、`custom_model_data`（100+i，i%5==1） |

三条独立证据：

1. **服务端视图**：`/item replace … shulker_box[minecraft:container=[…]]` 被接受（`server.log` 无 `Unknown item component`），随后 `data get entity GridUser Inventory[{Slot:10b}]` 能取到 10 号槽；
2. **客户端视图**：`P202_NBT seq=0..26` 逐格打出**完整的组件映射原文**，`P202_NBT_SUM stacks=27 distinctComponents=27 distinctItems=27 distinctNames=27`；
3. **渲染器视图**：`P202_DRAWITEM index=0..26` 逐格打出 `index / item / count / 组件映射`，27 个 index 齐全、27 个组件映射互不相同（`drawnDistinctNonAir=27 drawnItemIds=27`），`type=FULL items=27`；
4. **截图视图**：`after-full.png`（FULL 预览那一帧），逐格校验见下。

### 截图怎么对

没有"目测 27 个格子"了事，`verify_grid.py` 从图里**量**：

- 面板原点由探针日志给（`x=355 y=189` GUI × scale 2），窗口边框由 PNG 尺寸与 `P202_WINDOW m4480/m4507` 之差算出（`(1296-1280)/2=8`，`759-720-8=31`）；
- **周期**用亮度剖面的自相关求：列 `36`（峰值 56817，次峰 34665）、行 `36`（11578 / 4973），正好 `18*scale`；
- **相位**取"离探针报的面板原点最近、且格线最暗"的那条：列 18、行 18 → 网格原点 `(732,423)`；
  - 这里有个必须说清的取舍：相邻两条格线一样暗，谁是"第一条"本质上差一格。所以相位搜索限制在面板原点 ±半格内（渲染器的内边距小于一格），而不是全图找最暗；
- 27 个 `32x32`（`16*scale`）图元逐个取样：**无空格、无纯色格、27 个哈希互不相同**。若两格内容相同，哈希必然相等——那正是"异质"要排除的情况。

前两个版本的校验器都写错过，记在这里免得重犯：第一版只 hash 了格子前 8 个字节（27 格全长一样）；第二版用"边框环最干净"当对齐判据，而槽位自身就有一圈描边，判据无效（区分度只有 6%）。

## 三、还有一次返工值得记

第一次跑，服务端直接回 `Unknown item component 'minecraft:'`——外层组件键写成了 `shulker_box["minecraft:container"=…]`，加引号后解析成 `minecraft:` + 空。`check_snbt.py` 就是为此写的：**不起客户端**，只起服务端，用 `item replace` 的**解析阶段**（不需要在线玩家）验证 SNBT，40 秒就能否掉一个要花 3 分钟才发现的错误。改回不带引号的 `[minecraft:container=[…]]` 后解析通过。

## 边界（如实）

- **FULL 仍靠合成按键**：`J(74)`/`K(75)` 在 `InputConstants.isKeyDown` 的轮询边界伪造按住（与 p197 同一套），因为要进 FULL 必须有 `fullPreviewKey` 按住。**悬停本身不依赖它**——`P202_HOVER_OK` 行写着 `keysSent=false`；
- 只在**单机单显示器** Windows 上跑过；DPI 未变（`GetCursorPos` 回读与请求一致，无缩放偏差）；
- 截图走 `PrintWindow`，不是屏幕抓取，所以窗口被遮挡也能拍——但**这也正是第 1 轮踩坑的原因**：能截图不等于能收到鼠标消息；
- 未做：真实双人/多客户端同屏、双手持箱、潜影盒里再放潜影盒（嵌套）、27 格全部带 `custom_model_data` 的模型差异。

## 复现

```text
python runs/p202-hover-nbt/build.py            # 编译探针到 work/tmp/p202probe.jar
python runs/p202-hover-nbt/check_snbt.py       # 可选：只验 SNBT 解析，40 s
python runs/p202-hover-nbt/run.py --timeout 420
python runs/p202-hover-nbt/verify_grid.py      # 截图逐格校验 → grid-check.json

# 控制组（只指针 warp）：
python runs/p202-hover-nbt/run.py --cursor-mechanism warp --out work/tmp/p202-control
```

## 证据

`runs/p202-hover-nbt/`：

| 文件 | 内容 |
|---|---|
| `client.log` | 探针全部输出（`P202_*`），含 27 行 `P202_NBT` 与 40 行 `P202_DRAWITEM` |
| `server.log` | 盒子下发与 `data get` 结果 |
| `harness.log` | 三次 `OSMOVE`：机制、请求坐标、`GetCursorPos` 回读、`WindowFromPoint` 是否游戏窗口 |
| `result.json` | 解析后的结果与判据 |
| `after-full.png` | FULL 预览截图（1296×759，客户端区 1280×720） |
| `grid-check.json` | 周期/相位/27 格哈希与通过项 |
| `repeat/run2-client-extract.log` | 第 2 轮（首次成功）的关键行 |
| `repeat/run2-grid-check.json`、`repeat/run2-result.json` | 同上 |
| `repeat/run3-control-warp.log` | 控制组：只 warp 也悬停 |
| `build.py`、`run.py`、`verify_grid.py`、`check_snbt.py` | 构建 / 运行 / 校验 / SNBT 预检 |
| `probes/p202-hover-nbt/` | 探针源码（`HoverNbtProbe`、`Counters`、4 个 mixin） |

无新 release（v0.5.6，p202 没有 mod 代码改动，只加探针）。
