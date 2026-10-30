# p210：让 Cloth Config 的配置界面在 1.21.1 上打开、画出来、并且点得动

AppleSkin 的配置界面不是 AppleSkin 画的，是 **Cloth Config 11.1.136**（1.20.1 的版本）画的，
而它作为 jar-in-jar 塞在 `META-INF/jars/cloth-config-fabric-11.1.136.jar` 里。所以 p210 要修的不是
一个模组，而是"把 1.20.1 的 Cloth 拖到 1.21.1 上"这件事的 5 层断点。

结论（全部有本轮 `runs/p210-cloth-config/` 下的日志与截图支撑）：

| 事项 | 结果 | 证据 |
|---|---|---|
| 配置界面能打开（`ModsScreen` 的初始化路径，不是手工 new 一个 Screen） | ✅ `config.ok=true`，`screen=me.shedaniel.clothconfig2.gui.ClothConfigScreen` | `after3/result.json`，`after3/client.log:147` |
| 能画出 13 行 | ✅ `rows=13 kinds={BooleanToggleBuilder$1=9, EmptyEntry=2, FloatListEntry=1, SearchFieldEntry=1}` | `after3/client.log:147`，`after3/config.png` |
| 客户端日志里没有模组错误 | ✅ `client_errors=[]`、`NoSuchFieldError=0`、`NoSuchMethodError=0` | `after3/result.json` |
| 点一下 ON 按钮，值真的翻成 OFF | ✅ `handled=true`（走 `Screen.mouseClicked`）→ `before=true after=false` | `after3/client.log:153-156`，`after3/toggle.png`（第 1 行变 OFF，其余 8 行仍是 ON） |
| 不修就真的打不开 | ✅ 对照组 `config.ok=false`，`NoSuchFieldError: class_437 … field_44669`，栈在 `ConfigBuilderImpl.<init>` | `before/result.json`，`before/client.log:183,203` |

判定脚本 31/31 通过：

```bash
py -3.12 runs/p210-cloth-config/verify_cloth.py     # 输出 runs/p210-cloth-config/cloth-check.json
```

## 复现

```bash
export JAVA_HOME="/c/Users/27682/Documents/新建文件夹/.toolchain/jdk"
cd "/c/Users/27682/Documents/新建文件夹/mcbridge1201"

py -3.12 runs/p210-cloth-config/build_probe.py      # 探针 → work/tmp/p210probe.jar
py -3.12 runs/p210-cloth-config/build.py            # → work/client/appleskin-cloth.jar（会断言每条规则命中数）
py -3.12 runs/p210-cloth-config/run.py --appleskin work/client/appleskin-cloth.jar \
    --out runs/p210-cloth-config/after3
py -3.12 runs/p210-cloth-config/verify_cloth.py
```

对照组（证明"不修就打不开"）：

```bash
py -3.12 runs/p210-cloth-config/run.py --appleskin work/client/appleskin-patched.jar \
    --out runs/p210-cloth-config/before
```

`run.py` 必须带 `--appleskin`，否则 argparse 直接退出。一次真实启动 3–5 分钟。
`work/client/*.jar` 不入库，所以别人复现要先跑 `build.py`。

## 5 层根因链

Cloth Config 是嵌套 jar，每层都要「抽出来 → 打 → 塞回去」，`build.py` 干的就是这件事。

| 层 | 症状（日志原文） | 根因 | 处理 | 规则 |
|---|---|---|---|---|
| 1 | `NoSuchFieldError: class_437 does not have member field class_2960 field_44669` @ `ConfigBuilderImpl.<init>` | 1.21.1 删了 `Screen.OPTIONS_BACKGROUND_TEXTURE` | 桥返回 `minecraft:textures/gui/menu_background.png`（= 1.21.1 自己的 `field_49511`，运行期由探针打印并比对） | `cloth-config.screen-background` |
| 2 | `IncompatibleClassChangeError: TextFieldListEntry$1 overrides final method class_339.method_25394` | 1.21.1 把 `ClickableWidget.render` 变 final，覆盖点挪到 `method_48579` | 通用改名规则 + **必须** `onlyIfExtends: net/minecraft/class_339` | `fabric.legacy.render-widget-override`（6 次） |
| 3 | `NoSuchMethodError: void class_342.method_1870()` / `method_1883(I)` | 1.21.1 两个 setter 都多了一个 `boolean shiftKeyPressed` | 桥补 `false` | `cloth-config.textfield.cursor-to-start` / `.set-cursor` |
| 4 | `NoSuchMethodError: ClothConfigScreen.method_25434(class_332)` | 1.20.1 `renderBackground(ctx)` → 1.21.1 `renderBackground(ctx,int,int,float)` | 桥转发，指针给 0（背景不读指针） | `cloth-config.screen.render-background.*` |
| 5 | `UnsupportedOperationException: CenturyBridge tombstone: class_289.method_1349`（每帧崩） | **整代渲染模型被换掉**：`Immediate.getBuffer` / `BufferBuilder.begin` / 顶点链终点 / `Immediate.draw` 全部消失 | 6 条 bodyRedirect（装饰改 no-op）+ 3 条 stub 重定向 | `cloth-config-render.json` |
| 6 | 修完 5 层后，点开模组列表仍报 `Error from mod 'cloth-config'` | Cloth **自己的 demo 屏**用 `ItemStack.setCustomName`（1.20.4→1.20.5 删） | 桥换成空实现（`keepStackName`） | `cloth-config.render.demo-item-name` |
| 7 | 同一 lambda 紧接着读 `class_1893.field_9131` | 1.21.1 把附魔字段类型改成 `RegistryKey<Enchantment>`；同一处 `addEnchantment(Enchantment,int)` 也变成 `RegistryEntry` 版 | 桥返回 null + 调用点改到空实现（详见下面的退化说明） | `cloth-config.render.demo-enchantment` / `.demo-add-enchantment` |

层 6/7 是这一轮新发现的尾巴：层 6 修掉后，同一个 lambda 的下一条指令才暴露层 7。
`scan_refs.py` 一次就列全了（`refs-after.json`），不用再一轮启动一个成员。

### 第 5 层为什么是架构问题，不是改名

1.20.1 的立即模式链在 1.21.1 全部消失：

| tombstone | 被删的 API | 1.20.1 语义 | 1.21.1 |
|---|---|---|---|
| `t0` | `class_289.method_1349` | `Immediate.getBuffer()` | → `method_60827(RenderLayer)` |
| `t1` | `class_287.method_1328` | `BufferBuilder.begin(DrawMode, VertexFormat)` | 无此概念 |
| `t2` | `class_4588.method_1344` | 顶点链终点 | 无 |
| `t3` | `class_289.method_1350` | `Immediate.draw()` | `method_60828()`（唯一 1:1） |
| `t4` | `class_1799.method_7977` | `ItemStack.setCustomName` | 组件系统 |
| `t5` | `class_342.method_1865` | `TextFieldWidget.tick` | 无 per-tick 钩子 |

**救命的结构事实**（整轮的关键发现）：

```
DynamicEntryListWidget.renderList(DrawContext, int, int, int, int, float)
  0-10:   vcp = Immediate.getInstance(); bb = t0(vcp)     ← 死代码：slot 8 全程从未被 aload
  49-281: for (entry : visibleChildren()) {
              ctx.method_25294(...)                        ← 选中条，用 DrawContext
              renderItem(ctx, entry, row, ...)             ← 13 行真正的绘制，签名无 BufferBuilder
          }
```

「13 行构造好了但一个像素都没有」的唯一拦路者，就是开头那 4 条死指令。
`ClothRenderBridge.buffer()` 返回 `null` 即可，下游没有任何人读它。

而 `after/`（只有层 1–4）留下的崩溃报告证明了这条链是活的：
`class_289.method_1349` 从 `DynamicEntryListWidget.method_25394:298` 抛出，
一路 `DynamicSmoothScrollingEntryListWidget → ClothConfigScreen.method_25394:235`
（`after/client.log:207`，"Rendering overlay" 崩溃报告）。

## 规则与退化（`rules/fabric-1.21.1/cloth-config.json` + `cloth-config-render.json`）

`build.py` 对每条规则断言 `applied N time(s)`，命中数一变就说明有人的类结构被改了。

| 规则 | 类型 | 命中 | 作用 | 退化 / 代价 |
|---|---|---|---|---|
| `cloth-config.screen-background` | fieldRedirect | 1 | `field_44669` → `ClothConfigBridge.defaultBackground()` | 无 |
| `cloth-config.textfield.cursor-to-start` | callSite | 1 | `setCursorToStart()` → 补 `false` | 无 |
| `cloth-config.textfield.set-cursor` | callSite | 1 | `setCursor(int)` → 补 `false` | 无 |
| `cloth-config.screen.render-background.*` | methodRedirect ×2 | 各 1 | `renderBackground(ctx)` → 转发 4 参版，指针给 0 | 无（背景不读指针） |
| `fabric.legacy.render-widget-override` | methodRename | 6 | `method_25394` → `method_48579`，**只对 `class_339` 子树** | 无 |
| `fabric.legacy.clickable-text-override` | methodRename | 8 | `getClickableText` → `method_48597` | 无（**不能**加 `onlyIfExtends`，实测会丢光 8 处命中） |
| `cloth-config.render.buffer-accessor` | methodRedirect | 5 | `t0` → `buffer()` 返回 null | 只有死前导码能这样处理；3 处活的 t0 在 `GlobalizedClothConfigScreen.method_25394` 里，见"已知限制" |
| `cloth-config.render.textfield-tick` | methodRedirect | 1 | `t5` → 空方法 | 1.21.1 文本域的闪烁在它自己的 render 里，空体即正确翻译 |
| `cloth-config.render.demo-item-name` | methodRedirect | 1 | `t4` → `keepStackName`（原样返回 stack） | **退化**：Cloth demo 的样例物品没有自定义名字 |
| `cloth-config.render.demo-enchantment` | fieldRedirect | 1 | `class_1893.field_9131` → `demoEnchantment()` 返回 null | **退化**：样例物品没有附魔。1.21.1 的 `class_7923` 里 75 个 `class_2378` 字段没有任何一个是附魔注册表，附魔只能从 per-world 的 `DynamicRegistryManager` 拿，而这个 lambda 里没有 world |
| `cloth-config.render.demo-add-enchantment` | callSite | 1 | `addEnchantment(Enchantment,int)` → 空实现 | 同上（两个规则成对，构建断言各 1 次） |
| `cloth-config.render.list-backdrop` | bodyRedirect | 1 | 铺贴图背景 → no-op | **退化**：列表后面的平铺 `menu_background` 不画；`class_362.drawBackground` 仍铺底，行可读 |
| `cloth-config.render.list-vignette` | bodyRedirect | 1 | 上下边缘渐变 → no-op | **退化**：没有边缘渐隐 |
| `cloth-config.render.screen-overlay` | bodyRedirect | 1 | 屏幕 dim 层 → no-op | **退化**：没有 Cloth 自己的压暗层（仍有 vanilla backdrop） |
| `cloth-config.render.tab-shades` | bodyRedirect | 1 | tab 下方渐变 → no-op | **退化**：没有 tab 阴影（AppleSkin 只有一个分类，本来就是一个 tab） |
| `cloth-config.render.fill-gradient` | bodyRedirect | 1 | 行渐变（hover/选中 fallback）→ no-op | **退化**：行渐变不画；选中条仍由 `method_25294` 画 |
| `cloth-config.render.dropdown-shadow` | bodyRedirect | 1 | 下拉阴影 → no-op | **退化**：没有阴影；AppleSkin 配置里没有下拉，现路径不经过它 |

`build.py` 打印的完整命中表（本版）：`buffer-accessor 5`、其余 14 条各 1、`clickable-text-override 8`、
`render-widget-override 6`。`applyBodyRedirects` 在 `patchClass` 里最先执行，所以被 bodyRedirect 掉的方法里的
stub 不再计入 `methodRedirect` 的命中数——`buffer-accessor` 是 5 而不是 8，原因就在这里。

## 证据表

| 目录 | AppleSkin jar sha256（size） | 这次加了什么 | 结果 | 关键行 |
|---|---|---|---|---|
| `before/` | `b415bfc28ccb4de405adc3ef3647ad4f88c1ca896d0f1db90ea59ea19a6a8112`（1104012） | 什么都没改（对照组） | `config.ok=false`，`no_such_field=6`，5 个模组报错 | `client.log:183`（trashslot）、`:203`（appleskin），栈在 `result.json:51`（`ConfigBuilderImpl.<init>`） |
| `after/` | `294482f71b8f37577644e4782008590103e4e4e2f756d68cb3d6952b3bbdbece`（1105374） | 层 1–4（field + textfield + renderBackground） | 界面**能建出来**（`ok=true`），但第一帧崩：`t0` 从 `DynamicEntryListWidget.method_25394:298` 抛出 | `client.log:138`（demo 的 t4）、`:207`（"Rendering overlay" 崩溃报告） |
| `after2/` | `c4f1b70d391352b81f44acc8c14a2fc6c281905a53eaead39b4a0e166bd053b0`（1101379） | 层 5（渲染规则全 8 条） | **13 行画出来了**，`kinds` 已是 9 个 toggle | `config.png`（318440 B）、`client.log:179`（rows=13）、`:138`（残留的 t4 错误） |
| `attempt2-demo-enchantment/` | `6203d4a420b7fe5ad3317d25c5ed726ae79e4d1426a9d563068145068ef81a35`（1101379） | 层 6（`t4` → `keepStackName`） | 13 行仍在，但 `no_such_field=1`：`class_1893.field_9131` | `client.log:129`（新错误）、`:170`（rows=13） |
| `after3/` | `af9cdc3ac28a8c60d09064f0156e5d687598bc1cb95e346c717ca67bc5ef20ff`（1101433） | 层 7（`field_9131` + `method_7978`） | **`client_errors=[]`、`no_such_field=0`、`no_such_method=0`、`done.tick=182`、rows=13、点得动** | `client.log:147`（rows=13）、`:153-156`（click / toggle / 截图）、`config.png`+`toggle.png` |

`attempt2-*` 与 `after/` 是中间尝试，保留是为了"这条尾巴是怎么找到的"能被复核；
判定只认 `before/` 与 `after3/`。`work/client/*.jar` 不入库，所以 `after/`、`after2/`、
`attempt2-*` 的 sha 只能与本机 `work/client/` 下的 jar 对照（`after3` 的 sha 与
`work/client/appleskin-cloth.jar` 由 `verify_cloth.py` 现场比对）。

## 交互验证（P1）

`probes/p210-cloth-config/src/p210probe/ClothProbe.java` 在界面切过去 60 tick 后：

1. 找屏幕列表里第一条布尔行（`BooleanToggleBuilder$1`），读 `getValue()`；
2. 取它的 ON/OFF `class_4185` 的 `x/y/width/height`，算中心点；
3. 用 **`Screen.method_25402`（mouseClicked）** 发一次真实点击——走 Cloth 自己的命中测试；
4. 再读 `getValue()`：`before=true after=false flipped=true`，且 `direct_press=false`
   表示**不是**靠直接调 `ButtonWidget.method_25306` 兜底翻的；
5. 打 `P210_TOGGLE_SHOT`，`run.py` 抓第二张图 `toggle.png`。

`toggle.png` 与 `config.png` 同屏对比：第一行按钮由 ON 变 OFF，其余 8 个 ON 不动——
值、按钮文字、渲染三者一致，不是只改了内部字段。

## 已知限制（**没有**在本轮修，且不要顺手"修"）

1. **`GlobalizedClothConfigScreen.method_25394` 仍会崩**：它有 27 处 tombstone（Ctrl+滚轮全局设置屏），
   需要重建整条 tab 栏，不是桥能解决的。AppleSkin 永远不打开它，所以本轮不覆盖；
   `cloth-config-render.json` 的 `note` 里已写明。若将来要修，方向是 bodyRedirect 到"只画内容区、
   不画 tab"，而不是继续加 stub。`refs-after.json` 里剩下的 2 个缺失成员
   （`class_287.method_22912`、`class_4597.method_22991`）都只在它里面。
2. **6 处装饰降级为 no-op**：列表平铺背景、列表上下边缘渐变、screen dim 层、tab 阴影、
   行渐变、下拉阴影。行本身、选中条、文字、按钮都在（见上表逐条 `evidence`）。
3. **Cloth demo 屏的样例物品**没有自定义名字、没有附魔（层 6/7 的退化）。这只影响
   Cloth 自己在 Mod Menu 里的展示屏，不影响 AppleSkin 的配置界面；不处理又会每次进模组列表
   都报 `Error from mod 'cloth-config'`。
4. **`DynamicElementListWidget$ElementEntry.method_25401(DDD)` 未覆盖**：1.21.1 的 `class_4069`
   已经没有 3 参 `isMouseOver`，`refs-after.json` 里还剩这一条。AppleSkin 的屏幕不经过这个包装类
   （13 行是 `DynamicEntryListWidget` 的滚动条目，点击与悬停都已实测无报错），所以本轮不动它；
   如果将来某个动态元素列表被打开并悬停，会在这里抛 `NoSuchMethodError`。
5. **单机**：本轮所有证据都是本机 `work/launcher-e2e` 上的真实客户端，跨机器仍未做（属任务 4）。

## 本轮新增/修改的文件

**新增**
- `java/src/bridge/java/top/mcbridge1201/bridge/ClothConfigBridge.java` — 层 1
- `java/src/bridge/java/top/mcbridge1201/bridge/ClothTextFieldBridge.java` — 层 3
- `java/src/bridge/java/top/mcbridge1201/bridge/ClothConfigScreenBridge.java` — 层 4
- `java/src/bridge/java/top/mcbridge1201/bridge/ClothRenderBridge.java` — 层 5–7（11 个方法）
- `rules/fabric-1.21.1/cloth-config.json` — 层 1/3/4（1 fieldRedirect + 2 callSite + 2 methodRedirect）
- `rules/fabric-1.21.1/cloth-config-render.json` — 层 5–7（1 fieldRedirect + 1 callSite + 3 methodRedirect + 6 bodyRedirect）
- `probes/p210-cloth-config/` — 探针（反射调 `ModMenu.getConfigScreen`，打印 `P210_*`，含点击验证）
- `runs/p210-cloth-config/{build.py,run.py,build_probe.py,scan_refs.py,scan_tombstones.py,verify_cloth.py}`
- `java/src/test/java/top/mcbridge1201/JarPatcherMethodRenameTest.java` — `onlyIfExtends` 的 4 个回归用例

**修改**
- `java/src/main/java/top/mcbridge1201/rules/RuleSet.java` — `MethodRename` 加 `onlyIfExtends`
- `java/src/main/java/top/mcbridge1201/rules/JarPatcher.java` — `superNames()` / `extendsType()`（解析不出祖先就**中止**，不是"当作没有"），`applyMethodRenames` 里加 gate
- `rules/fabric-1.21.1/render-widget-override.json` — 加 `onlyIfExtends: net/minecraft/class_339`

## 踩过的坑

1. `javap` 是 Windows 程序：`-cp` + **类名**，不要传 `.class` 路径，不认 MSYS 的 `/tmp`。
2. Mojang 混淆 jar 的 `javap -c` 没有 `Code:`；查 1.20.1 语义用 `work/cb/data/jars/client-1.20.1-intermediary.jar`。
3. `build.py` 里搜 field 名必须解压后再搜：`zipfile.read()` 拿到的是 deflate 后的字节。
4. 后台 run 结束后 java 进程可能还活着，占着 `png`，重跑前先 `taskkill`。
5. `applyBodyRedirects` 在 `patchClass` 里最先执行，被 bodyRedirect 掉的 stub 不再计入 methodRedirect 命中数。
6. 别用 `Screen.children().size()==3` 判断"界面非空"——Cloth 里这个数恒定是 3，行都在 `ListWidget` 里。要看 `kinds={}`。
7. `BooleanListEntry.getValue()` 才是值的真相；只截一张图不能证明"点了会变"。
