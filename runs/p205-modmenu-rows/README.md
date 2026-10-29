# p205 — Mod Menu 列表行终于画出来了（修 p94/p204 记下的那个缺陷）

p204 顺手发现「Mod Menu 左侧列表是全黑的」，并明确写成「独立缺陷，本轮没修」。这一轮修掉它。

## 1. 缺陷是什么

`rules/fabric-1.21.1/modmenu-list-render.json` 用 `ModMenuListRenderBridge.renderList` 顶掉了
`ModListWidget.method_25311`（原版 `EntryListWidget.renderList`）。旧桥里这一行是错的：

```java
render.invoke(entry, context, i, left, top, rowWidth, itemHeight, mouseX, mouseY, hovered, delta);
```

`Entry.render` 的参数是 **`(ctx, index, y, x, width, height, ...)`**——y 在前、x 在后。旧桥把
`left` 传给了 y、`top` 传给了 x，于是每个条目的图标和名字都被摆到了别处；而**行底色**是桥自己用
`context.fill(left, top, ...)` 画的，坐标是对的，所以「黑底上有行、行里没东西」。

三处独立证据：

1. `net.minecraft.class_350.method_44397`（原版单行绘制）字节码：
   `entry.method_25343(ctx, iload 5 /*index*/, iload 7 /*y*/, iload 6 /*x*/, iload 8 /*width*/, iload 9 /*height*/, ...)`；
2. `com.terraformersmc.modmenu.gui.widget.entries.ModListEntry.method_25343` 字节码：
   `iload 4; getXOffset; iadd; istore 4`（第 4 个参数加偏移当 **x**）、`iload 5; getXOffset; isub`
   （第 5 个参数减偏移当 **width**）、`iload 3` 直接当 **y** 用；
3. 修前截图（`before/rows-before.png`）：列表区**零**个亮像素、零个彩色像素。

## 2. 修成什么样

桥现在按原版 `renderList` + `method_44397` 逐条对照：

| 量 | 旧桥 | 现在（原版口径） |
|---|---|---|
| 条目参数 | `(…, left, top, …)` | `(…, top, left, …)` |
| 行宽 | `getWidth() - 8` | `method_25322()` = **294**（ModListWidget 覆写过） |
| 行高 | `itemHeight` | `itemHeight - 4` |
| 可见性 | `bottom < 0 \|\| top > height` | `bottom < getY() \|\| top > getBottom()`（`method_46427`/`method_55443`） |
| hovered | 自己算矩形 | `method_25308(mouseX, mouseY) == entry`（`getEntryAtPosition`） |
| 边框 | 没调 | 先 `method_49568`（`Entry.drawBorder`），再 `method_25343` |

调试输出用 `-Dmcbridge.listrender.debug=true` 打开（默认关，发布 jar 不打印）。带上它的实际输出：

```text
P205_LIST class=DescriptionListWidget count=0 left=7 rowWidth=302 itemHeight=10 rows=108..324 mouse=0,0 firstEntry=none
P205_LIST class=ModListWidget count=11 left=6 rowWidth=294 itemHeight=36 rows=67..324 mouse=0,0 firstEntry=com.terraformersmc.modmenu.gui.widget.entries.IndependentEntry
```

`count=11` 与探针 `entries=11` 一致，`itemHeight=36` 与 p204 的滚动阶梯一致。

## 3. 两次运行，只差一个桥

`run.py` 复用 p204 的 Win32 链路（抬窗 + 前台 + `SendInput`），同一套模组、同一窗口（1280×720，
guiScale 2）、同一个光标点（列表中心，`underIsGame=True`）；只有 `modmenu.jar` 不同：

| | jar sha256 | 列表区亮像素 | 彩色像素 | 图标条带 | 滚动前后位移 |
|---|---|---|---|---|---|
| `before/`（旧桥） | `9989cf3c…` | **0** | **0** | **0** | 无行可动 |
| `after/`（新桥） | `9cb27e54…` | **11147** | **20211** | **6** | **−36 px** |

- 位移 −36 是两格滚轮理论上限里的实测：`scroll 0 → 18`（两格被 OS 合并成一条消息），
  ×guiScale 2 = 36 设备像素，`verify_rows.py` 在 ±90 px 里做互相关，最优点 `-36`，
  次优点与 0 位移都明显更差（见 `rows-check.json` 的 `shift`）。
- 图标条带按行内左侧 32 px 的彩色像素切：6 条，高度 51/44/11/67/63/74 px。11 px 那条是一个
  状态小徽章，不是行——所以判据写成「高度 30–90 px 的条带 ≥ 5 条」，不是「每条都正好 64」。
- 内容条带（整行亮像素）只有 4 条：36 px 行距里塞 32 px 图标，相邻行会连成一片。这个数只记录，
  不作为判据。

`verify_rows.py` 的 8 条判据全过（`rows-check.json.passed=true`）。

## 4. 顺带修的一个启动器缺陷

这条调试输出需要给 JVM 传 `-D`，于是发现 `launcher/mclaunch.py:build_command` 的 `extra_jvm`
**参数声明了但从来没被用过**（只有形参，没进命令行）。已修：两条组装路径（fabric 与
forge/neoforge backend）都在 `-Xmx` 之后插入 `extra_jvm`，`launch()` 也把它透传下去。
回归里有一条直接调 `build_command` 断言「标志紧跟 -Xmx」。

不修它的话，这轮证据会变成「以为开了调试、其实没开」——第一次跑就是这个结果（`P205 missing`）。

## 5. 怎么重建

```text
python runs/p205-modmenu-rows/build.py                     # javac 单桥 + inject_bridges 注入
python runs/p205-modmenu-rows/run.py --modmenu work/client/modmenu-patched.jar --out runs/p205-modmenu-rows/before
python runs/p205-modmenu-rows/run.py --modmenu work/client/modmenu-rows.jar     --out runs/p205-modmenu-rows/after
python runs/p205-modmenu-rows/verify_rows.py               # 写 rows-check.json
```

`build.py` 只编译并替换 `ModMenuListRenderBridge` 一个类（`tools/inject_bridges.py` 是支持的
独立路径）：`tools/build_bridges.py` 编全部 36 个桥需要 Fabric API / brigadier 在 classpath 上，
而这个桥只碰 `class_332`。全量重打包时仍应走 `patch --bridge-dir`。

产物：`work/client/modmenu-rows.jar`（sha256 `9cb27e5455a2a01eb6a653111a91790184be1cd9f91367cd4ff23d51e65d9b0c`）。
`work/client/modmenu-patched.jar` 保持修前状态，p204 的证据仍然可复现；正式分发要用 `modmenu-rows.jar`。

## 6. 边界

- 单机单显示器、窗口 1280×720、guiScale 2；只验证了 Mod Menu 的**模组列表**；
- 描述面板走同一个桥（日志里 `DescriptionListWidget count=0`），但这一轮没有选中模组，
  所以它的行渲染**没有验证**；
- 原来的纹理背景没有恢复：行底色仍是桥画的 `0x80000000` 平色，这是显式降级，不是「还原」；
- 高 guiScale、超长模组名截断、选中高亮（`method_44398` 没调用）都没测；
- Cloth Config 界面依旧打不开（p204 的 `class_437.field_44669` 栈），与本轮无关。
