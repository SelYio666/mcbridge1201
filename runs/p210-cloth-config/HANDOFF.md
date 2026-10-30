# p210 交接：让 Cloth Config 的配置界面在 1.21.1 上真的能打开

> **本文件已被 `runs/p210-cloth-config/README.md` 接续完成（2026-10-30）。**
> 下面第 4 节列的"剩余任务"全部做完：新 jar 已跑过真实客户端（`after3/`，`client_errors=[]`、
> `no_such_field=0`、`rows=13`、点击验证通过），`verify_cloth.py`、README、`onlyIfExtends` 的
> Java 回归测试、`test_cloth_config()`、5 处文档、`hash_evidence.py` 都已落地。
> **现状、数字与证据以 README.md 为准**；本文件保留交接当时的原样（其中 sha256 与"还没跑过客户端"
> 这类句子已经过时），不要再当作当前状态读。

> 这份文件是给下一个会话/下一个人的交接。它假设你只读这一个文件就能接上，
> 不需要翻聊天记录。项目根目录：`C:\Users\27682\Documents\新建文件夹\mcbridge1201`。

---

## 0. 一句话现状

**AppleSkin 的 Cloth Config 配置界面已经在 1.21.1 上打开并画出全部 13 行**（截图
`runs/p210-cloth-config/after2/config.png`，`rows=13 kinds={BooleanToggleBase$1=9, EmptyEntry=2,
FloatListEntry=1, SearchFieldEntry=1}`），对照组同一操作是 `NoSuchFieldError: class_437.field_44669`。

**但是**：最后又加了一条 `t4` 规则（清掉 Cloth 自己 demo 的报错），重建出的 jar **还没在真实客户端跑过**。
所以「收尾」的第一步就是验证它。

---

## 1. 不可协商的规则（沿用项目原始要求）

1. **不造假**。没有 `runs/pNNN` 下的日志/截图支撑的结论不许写进文档。
2. **不许删 mixin / 注释掉代码冒充"通过"**。降级必须显式记录（本项目用 `risk` + `evidence` 字段，
   以及 patch report 的 `applied N time(s)`）。
3. **改代码必须加回归测试**。改 `JarPatcher` / `RuleSet` 这类核心逻辑，必须进
   `java/src/test/java/top/mcbridge1201/`。
4. **不提交**：游戏 jar、模组 jar、转换产物（`work/client/*.jar`）、`work/tmp/*`。`.gitignore` 已覆盖，
   但 `git add -A` 前要 `git status` 看一眼。
5. **文档 + 哈希清单必须同步**：改了行为就要改 `docs/*`，新增证据文件就要进 `tools/hash_evidence.py`。
6. **push 前**：`git fetch` → 确认无未推送 → 跑全部门禁 → `push`（**永不 force**）。

---

## 2. 环境（每次开新 shell 都要）

```bash
export JAVA_HOME="/c/Users/27682/Documents/新建文件夹/.toolchain/jdk"
```

- `JAVA_HOME` 不设，`build.py` 会直接 `SystemExit`。
- 验证 / 构建：
  ```bash
  cd "/c/Users/27682/Documents/新建文件夹/mcbridge1201"
  py -3.12 runs/p210-cloth-config/build.py            # 产出 work/client/appleskin-cloth.jar
  py -3.12 runs/p210-cloth-config/run.py --appleskin work/client/appleskin-cloth.jar --out runs/p210-cloth-config/after3
  ```
- `run.py` **必须带 `--appleskin`**，否则 argparse 直接退出（踩过）。
- 一次真实客户端启动约 3–5 分钟，**放后台跑**，不要前台等。

---

## 3. 这一轮到底做了什么（根因链，逐层剥开）

Cloth Config 不是独立模组，是 `META-INF/jars/cloth-config-fabric-11.1.136.jar` 这个 jar-in-jar
（由 `work/client/appleskin-patched.jar` 内嵌）。所以每层都要「抽出来 → 打 → 塞回去」，
`build.py` 干的就是这件事。

| 层 | 症状（日志原文） | 根因 | 处理 | 规则 |
|---|---|---|---|---|
| 1 | `NoSuchFieldError: class_437 does not have member field class_2960 field_44669` @ `ConfigBuilderImpl.<init>` | 1.21.1 删了 `OPTIONS_BACKGROUND_TEXTURE` | 桥返回 `minecraft:textures/gui/menu_background.png`（= 1.21.1 自己的 `field_49511` 值，运行期自证一致） | `cloth-config.screen-background` |
| 2 | `IncompatibleClassChangeError: TextFieldListEntry$1 overrides final method class_339.method_25394` | 1.21.1 把 `ClickableWidget.render` 变 final，覆盖点挪到 `method_48579` | 通用改名规则；但**必须** `onlyIfExtends: net/minecraft/class_339`，否则会把 `class_362` 系的 6 处误改 | `fabric.legacy.render-widget-override`（6 次） |
| 3 | `NoSuchMethodError: void class_342.method_1870()` / `method_1883(I)` | 1.21.1 两个 setter 都多了一个 `boolean` | 桥补 `false` | `cloth-config.textfield.cursor-to-start` / `.set-cursor` |
| 4 | `NoSuchMethodError: ClothConfigScreen.method_25434(class_332)` | 1.20.1 `renderBackground(ctx)` → 1.21.1 `renderBackground(ctx,int,int,float)`（`method_25420`） | 桥转发，指针给 0 | `cloth-config.screen.render-background.*` |
| 5 | `UnsupportedOperationException: CenturyBridge tombstone: class_289.method_1349` | **整代渲染模型被换掉**，见下 | 6 条 bodyRedirect + 3 条 stub 重定向 | `cloth-config-render.json` 全 8 条 |

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

**救命的结构事实**（这是整轮的关键发现，别丢）：

```
DynamicEntryListWidget.renderList(DrawContext, int, int, int, int, float)
  0-10:   vcp = Immediate.getInstance(); bb = t0(vcp)     ← 死代码：slot 8 全程从未被 aload
  49-281: for (entry : visibleChildren()) {
              ctx.method_25294(...)                        ← 选中条，用 DrawContext
              renderItem(ctx, entry, row, ...)             ← 13 行真正的绘制，签名无 BufferBuilder
          }
```

所以「13 行构造好了但一个像素都没有」的唯一拦路者，就是开头那 4 条死指令。
`ClothRenderBridge.buffer()` 返回 `null` 即可，下游没有任何人读它。

### 新增/修改的文件

**新增**
- `java/src/bridge/java/top/mcbridge1201/bridge/ClothConfigBridge.java` — 层 1
- `java/src/bridge/java/top/mcbridge1201/bridge/ClothTextFieldBridge.java` — 层 3
- `java/src/bridge/java/top/mcbridge1201/bridge/ClothConfigScreenBridge.java` — 层 4
- `java/src/bridge/java/top/mcbridge1201/bridge/ClothRenderBridge.java` — 层 5（9 个方法）
- `rules/fabric-1.21.1/cloth-config.json` — 层 1/3/4（1 fieldRedirect + 2 callSiteAdaptation + 2 methodRedirect）
- `rules/fabric-1.21.1/cloth-config-render.json` — 层 5（3 methodRedirect + 6 bodyRedirect）
- `probes/p210-cloth-config/` — 探针（反射调 `ModMenu.getConfigScreen`，打印 `P210_*`）
- `runs/p210-cloth-config/{build.py,run.py,build_probe.py,scan_refs.py,scan_tombstones.py}`

**修改**
- `java/src/main/java/top/mcbridge1201/rules/RuleSet.java` — `MethodRename` 加 `onlyIfExtends`
- `java/src/main/java/top/mcbridge1201/rules/JarPatcher.java` — `superNames()` / `extendsType()`（解析不了祖先就**中止**，不是"当作没有"），`applyMethodRenames` 里加 gate
- `rules/fabric-1.21.1/render-widget-override.json` — 加 `onlyIfExtends`

### 精确数字（写进文档时照抄）

- 最终 jar：`work/client/appleskin-cloth.jar`
  sha256=`6203d4a420b7fe5ad3317d25c5ed726ae79e4d1426a9d563068145068ef81a35` size=1101379
  **（这个版本还没跑过客户端）**
- 有截图的那版：sha256=`c4f1b70d391352b81f44acc8c14a2fc6c281905a53eaead39b4a0e166bd053b0` size=1101379
  → `runs/p210-cloth-config/after2/`
- 对照组：`work/client/appleskin-patched.jar` sha256=`b415bfc28ccb4de405adc3ef3647ad4f88c1ca896d0f1db90ea59ea19a6a8112`
  → `runs/p210-cloth-config/before/`，`config.ok=false`，`NoSuchFieldError field_44669`
- 规则命中（最新构建，**全部必须命中，`build.py` 已断言**）：
  `buffer-accessor 5`（`method_25394`×1 + `renderList`×1 + Globalized×3），其余 13 条各 1 次，
  `clickable-text-override 8`，`render-widget-override 6`

---

## 4. 剩余任务

### P0 — 不做完这轮不算收尾

1. **验证新 jar（`6203d4a4...`）**
   ```bash
   py -3.12 runs/p210-cloth-config/run.py --appleskin work/client/appleskin-cloth.jar \
       --out runs/p210-cloth-config/after3
   ```
   验收：`client_errors == []`（`after2` 有一条 `Error from mod 'cloth-config'`，就是 `t4` 那条，
   栈在 `after2/client.log:138`，路径是 `ModsScreen.init → ModMenu.getConfigScreen →
   ClothConfigModMenuDemo → ClothConfigDemo`）、`no_such_field=0`、`no_such_method=0`、
   `done.tick≈182`、截图里 13 行仍在。
   **如果还有错，先看 `grep -n "ERROR\|Caused by" runs/p210-cloth-config/after3/client.log`，不要猜。**

2. **写 `runs/p210-cloth-config/verify_cloth.py`**（判据脚本，风格照抄 `runs/p207-*/verify_description.py`）
   必须同时读 `before/` 和 `after3/`：
   - 对照组：`config.ok is False` 且 stack 含 `field_44669`（证明"没修就真打不开"）
   - 修复组：`config.ok is True`、`screen` 结尾是 `ClothConfigScreen`、`rows>=13`、
     `kinds` 里有 9 个 `BooleanToggleBuilder$1`、`client_errors` 为空、截图文件存在且 >100KB
   - 两边 sha256 必须与 `result.json` 自洽（防止拿错 jar 对比）

3. **写 `runs/p210-cloth-config/README.md`**：5 层根因链（照上面第 3 节）+ 每条规则的退化说明 +
   证据表（before/after2/after3 的路径、sha256、关键行号）。

4. **`onlyIfExtends` 的 Java 回归测试**（当前**零覆盖**，这是上一轮改的核心逻辑）
   放 `java/src/test/java/top/mcbridge1201/JarPatcherMethodRenameTest.java`，至少 4 个用例：
   - 直接父类命中 → 改名发生
   - 三级祖先命中（`A → B → C`，gate 是 `C`）→ 改名发生
   - 无关父类 → 不改名（**这是 `class_362` 那 6 处的真实场景**）
   - 祖先解析不出来（类不在 jar 也不在 client index）→ **不改名**（`extendsType` 返回 false，
     语义是"不知道祖先 ≠ 有祖先"）
   参照 `JarPatcherKeepPrefixTest.java` 的合成 jar 写法（`ClassWriter` + `writeJar`）。

5. **`tools/test_review_fixes.py` 加 `test_cloth_config()`** 并注册进 `main()`
   检查：两个规则 JSON 可解析、`build.log` 里 14 条规则全 `applied`、
   `appleskin-cloth.jar` 存在且 sha256 与 `hash_evidence.py` 一致。

6. **文档同步**（每处都要改，别只改一处）
   - `docs/remaining-work.md:209` — 现在写的是 "**Cloth-Config screens cannot open at all**"，
     必须改写为"已能打开并画出 13 行"，并保留 `GlobalizedClothConfigScreen` 的未覆盖说明
   - `docs/FINAL-STATUS.md:363,380,423` — 三处 "Cloth 配置界面仍打不开"
   - `docs/progress.md` — 加 p210 一条
   - `docs/distribution.md` — 分发对象从 `appleskin-patched.jar` 改成 `appleskin-cloth.jar`
   - `README.md` — 状态表 + 新增规则文件说明

7. **`tools/hash_evidence.py`** 加 `runs/p210-cloth-config/` 下的：
   `build.py`、`run.py`、`build_probe.py`、`scan_refs.py`、`scan_tombstones.py`、`README.md`、
   `verify_cloth.py`、`before/result.json`、`after2/result.json`、`after3/result.json`、
   `after2/config.png`、`after3/config.png`、`before/config.png`
   （**不要**加 `client.log`，太大且逐次变化；参照 p208 的写法）

8. **门禁 + 提交**
   ```bash
   git fetch origin
   git log --oneline origin/main..HEAD        # 应为空
   py -3.12 tools/test_review_fixes.py
   py -3.12 tools/hash_evidence.py
   py -3.12 tools/check_hashes.py
   py -3.12 tools/verify_evidence.py
   py -3.12 tools/check_text_encoding.py
   # 全绿后
   git add <具体文件>            # 不要 -A
   git commit -m "feat(cloth-config): open the config screen on 1.21.1, and draw its rows (p210)"
   git push origin main          # 不 force
   ```

### P1 — 让"能用"比"能看"更有说服力

9. **交互验证**：当前探针只做到 open / describe / heartbeat / done。要证明"可用"，需要
   在 `probes/p210-cloth-config/src/p210probe/ClothProbe.java` 里加：定位第 1 行的 ON 按钮 →
   模拟点击（`Screen.mouseClicked` 或直接 `onPress`）→ 读回该 entry 的 `getValue()` → 打印
   `P210_TOGGLE before=true after=false`，并截图。验收标准是同一进程内值真的翻了。
10. **before/after 并排对比图**（可选）：`config.png` 左边"打不开/停在 ModList"，右边 13 行。

### P2 — 项目其他任务（不在 p210 范围）

11. **任务 6：PCL 面板** — 本机没有 PCL2，`tools/pcl_panel.py` 只能静态验证。要么找一台有 PCL2
    的机器，要么把这项记成"受阻：缺环境"。
12. **任务 4 尾巴：多客户端 / 跨机器** — p208 已做单机 clean-host，跨机器未做。

---

## 5. 已知限制（**不要在 p210 里顺手"修"**，要记录）

- **`GlobalizedClothConfigScreen.method_25394` 仍会崩**：它有 27 处 tombstone，需要重建整个 tab 栏
  （不是桥能解决的）。AppleSkin 永远不打开它，所以本轮不覆盖。`cloth-config-render.json` 的 note
  里已写明。若将来要修，方向是 bodyRedirect 到"只画内容区、不画 tab"，而不是继续加 stub。
- **视觉退化（已在规则 `evidence` 里逐条写明）**：列表平铺背景、列表上下边缘渐变、屏幕 dim 层、
  tab 阴影、行渐变（hover/选中 fallback）、下拉阴影，全部不画。行本身、选中条、文字、按钮都在。
- **`ClothConfigDemo`** 除 t4 外的路径没实际打开测过（只有 `t4` 被真实触发过）。

---

## 6. 踩过的坑（省时间用）

1. **`javap` 是 Windows 程序**，不认 MSYS 的 `/tmp`，也不接受文件路径参数。正确用法：
   ```bash
   W=$(cygpath -w "$PWD")
   "$JAVA_HOME/bin/javap.exe" -c -p -cp "$W" me.shedaniel.clothconfig2.gui.ClothConfigDemo
   ```
   `-cp` + **类名**，不要传 `.class` 路径。
2. **Mojang 混淆 jar 的 `javap -c` 没有 `Code:`**（`client-1.20.1-obf.jar`）。要查 1.20.1 语义，
   用 `work/cb/data/jars/client-1.20.1-intermediary.jar` 或 mappings tiny 文件。
3. **`build.py` 里搜 field 名必须解压后再搜**。`zipfile.read()` 拿到的是 deflate 后的字节，
   直接 `FIELD in bytes` 恒为 False。
4. **规则命中数是诊断主通道**。`applied N time(s)` 一变就说明有人改了类结构。
   `onlyIfExtends` 别加在 `clickable-text-override` 上 —— 实测会把 8 处命中全丢掉。
5. **后台 run 结束后 java 进程可能还活着**，占着 `config.png`，会导致 `mv`/重跑报
   `Permission denied`。先 `tasklist | grep java` → `taskkill //PID <pid> //F`。
6. **`applyBodyRedirects` 在 `patchClass` 里最先执行**，所以被 bodyRedirect 掉的方法里的 stub
   不会再计入 `methodRedirect` 的命中数。`buffer-accessor` 是 5 而不是 8，原因就在这。
7. **别用 `Screen.children().size()==3` 判断"界面打开且非空"** —— Cloth 里这个数字恒定是 3，
   行都在 `ListWidget` 里。必须打印每行类名（`kinds={}`）。
