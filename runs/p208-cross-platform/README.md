# p208 交付验证：干净主机 + 跨平台审计（2026-10-28）

关 p195 留下的 "clean-host portable remain open" 和 p201 结尾的 "Verified on Windows /
Git for Windows only"。这一轮只做两件事，都不涉及新功能：**把一个别人拿到的包放到一个干净的
环境里跑**，以及**把"非 Windows 会死在哪"变成可执行的清单**。

结论先说，证据在后面：

| 项 | 结果 |
|---|---|
| 干净环境跑便携包（照发原件） | **8/8**，`clean-host-shipped.json` |
| 干净环境跑便携包（叠加当前源码） | **8/8**，`clean-host-current.json` |
| 平台探针 | 修前 **2/6** → 修后 **6/6**，两份 JSON 都在 |
| 交付路径的静态命中 | **28 处 / 5 文件** → **22 处 / 4 文件**；未加保护的 **24 → 4** |
| POSIX 模拟下能导入的交付模块 | **4/4**（修前修后都是，说明没有 Windows-only 导入依赖） |
| 依赖缺失时重新打包 | **rc=1 拒绝出包**，`build-blocked.log` |

## 1. 干净环境：把"环境"这个变量真的剥掉

`tools/test_portable.py` 第 78 行是 `env = dict(os.environ, ...)`，**继承**调用者的环境。所以它只能
证明"在造它的这台机器上能跑"。p195 那次也是同样的问题：换了个目录，但 PATH 里的 Python、JDK、
已有的 `.minecraft` 都还在。

`run_clean_host.py` 换成构造环境：

```text
PATH            = C:\Windows\System32;C:\Windows      ← 没有 Python，没有 JDK
PYTHON*         = 全部移除
JAVA_HOME/MC_JAVA = 移除
HOME / USERPROFILE / TEMP / APPDATA / LOCALAPPDATA
                = 全新空目录（看不到任何用户配置、任何已装运行时、任何 .minecraft）
```

**第一件要证明的事是"剥干净了"**，否则后面全是空话：

```text
PASS no_system_python      shutil.which("python") == None
PASS no_system_java        shutil.which("java")   == None
PASS bundled_python        pkg/python/python.exe 存在
PASS no_jars_shipped       231 个条目里 0 个 .jar
PASS interpreter_is_bundled  sys.prefix 落在解压目录内
PASS hostile_pythonhome_ignored  注入 PYTHONHOME/PYTHONPATH 后 prefix 不变
PASS api_status            /api/status 200
PASS guide_page            /guide 200 且含"使用说明"
```

`hostile_pythonhome_ignored` 是这轮新加的：嵌入式 Python 有 `python312._pth`，按 CPython 的行为
`PYTHONHOME`/`PYTHONPATH` 会被忽略。这是**测出来的**，不是假设——而 `dict(os.environ)` 那种写法
恰好会把这两个变量原样传给子进程，所以以前既不会失败也测不出。

干净环境里 `/api/status` 的原文：

```json
{"root": "...\\p208-clean-host\\home\\.mcbridge\\mc", "versions": 0,
 "java": null, "java_error": "Java not found: set JAVA_HOME or MC_JAVA"}
```

三件事同时成立：默认游戏目录落在**新的 HOME** 下（不是相对路径，不是作者机器上的路径）；没有 JDK
时接口仍返回 **200 + 错误字段**，而不是崩掉；`versions: 0` 说明它真的看不到任何已装版本。启动器
本身有 `backend.install_jvm_runtime` 这条自动装运行时的路（`backend.py:205`），但下载本身要联网，
本轮**没有跑**。

### 一个必须说清的缺口

`dist/mcbridge-launcher-0.5.6.zip` 是**改动之前**打的包。要验证"改过的启动器在包内能不能跑"，
就得重新打包——而这台机器上没有任何解释器装了 `minecraft_launcher_lib` / `requests`：

```text
missing dependency, skipped: minecraft_launcher_lib
missing dependency, skipped: requests
...
package: dist/mcbridge-launcher-0.5.7-p208.zip  11204821 bytes   ← 比 0.5.6 少 755 KB
```

那个包是残的（少了 vendored 依赖），已经删掉。所以改成**叠加**：把当前 `launcher/*.py` 覆盖进
0.5.6 解压出来的包，依赖沿用包内已有的，两件事分开记录——`launcher_sources` 字段写明这一份是
"current worktree over mcbridge-launcher-0.5.6.zip"。真正的完整重打包仍然要在装了依赖的机器上做，
这一点写在边界里，不假装做过了。

## 2. 打包脚本的"假成功"（真缺陷，已修）

上面那个残包不是意外：`vendor_deps()` 把 import 不到的依赖打印一行 `missing dependency, skipped`
然后**继续**，调用处连返回值都没接，最后照样 `done`、退出码 0。也就是说，任何一台没装依赖的机器
都能产出"能启动、一按下载就报错"的包，而构建过程会告诉你成功了。

改成显式拒绝（`require_vendored`），保留一个故意的开关 `--allow-missing-deps`：

```text
$ python tools/build_portable.py --label 0.5.7-blocked
RuntimeError: refusing to build: minecraft_launcher_lib (and its deps) were not importable by
...\python.exe, so the package would ship without them. Install them
(pip install minecraft-launcher-lib requests) or pass --allow-missing-deps ...
rc=1                                     ← 且 dist/ 下没有新产物
```

## 3. 跨平台：审计而不是假装跑过

WSL 在这台机器上是有的，但被安全策略拦住（`wsl.exe` 在 Program Blacklist 里），**Linux 没有
被执行**。这个不绕过，直接写进边界。能做的是两遍独立检查：

**静态**：tracked `*.py`（第一次跑时 108 个；三个新工具提交后是 111 个，新增的三个都归 harness，不改变交付路径的数字）里挑出"收件人会跑的那部分"（`launcher/` 三个文件 +
`build_portable.py` + `test_portable.py`），扫 `os.name` / `sys.platform` 分支、`winreg`、
`msvcrt`、`os.startfile`、`java.exe`、盘符、`%APPDATA%`、`chcp`、`taskkill` 等。

只看命中数会误导：`os.startfile` 写在 `if platform.startswith("win")` 里是**对的**。所以每条命中
都带两个上下文判定——20 行内最近的平台守卫、是否在 docstring 里——再分三类报：

| | 命中 | docstring | 已按平台分支 | **未保护** |
|---|---|---|---|---|
| 修前 | 28（5 文件） | 1 | 3 | **24** |
| 修后 | 22（4 文件） | 6 | 12 | **4** |

修后那 4 条全是已知的、故意的：3 条在 `build_portable.py` / `test_portable.py`（便携包按构造就是
Windows-only：`python-embed-amd64` + `run.bat`），1 条是 `server.py` 里紧跟 `if appdata:` 的那次
`getenv`。

**动态**：把 `sys.platform` 翻成 `linux`、把 Windows-only 模块（`winreg`/`msvcrt`/`_winapi`…）设为
不可导入，再逐个 `import` 交付模块。结果 **4/4 全部导入成功**（`server`、`mclaunch`、`backend`、
`fetch`）——说明启动器**没有 Windows-only 的导入依赖**，它在 Linux 上是"能加载"的。

## 4. 四个真缺陷（修前有失败记录，修后有通过记录）

`probe_behaviour.py` 对活代码断言可观测结果，同一个脚本跑出 before / after：

| 探针 | 修前 | 修后 |
|---|---|---|
| `default_root_no_appdata` | `'.minecraft'`（**相对路径**） | `$HOME/.mcbridge/mc`（绝对） |
| `find_java_home_posix` | 官方 `windows-x64` 运行时（**JAVA_HOME 被忽略**） | `$JAVA_HOME/bin/java` |
| `open_folder_darwin` | `xdg-open` | `open` |
| `open_folder_linux` / `open_folder_win32` | 通过 | 通过（对照组，防止"修好一个弄坏一个"） |
| `java_fallback_unused` | 定义了从未使用的 `C:\Program Files\Java\...` | 已删 |

修前 2/6。逐条说清：

1. **`default_root()` 会认领当前目录**。`Path(os.environ.get("APPDATA", ""))` 在 `APPDATA` 未设置时
   是 `Path("")` == `Path(".")`，于是候选列表第一项是相对路径 `.minecraft`，只要启动器的 CWD 里
   正好有个 `.minecraft/versions`，它就把 CWD 当游戏目录。这条**不需要任何模拟**就能在 Windows 上
   复现：探针把 `APPDATA` 删掉、`USERPROFILE` 指到空目录、CWD 放个诱饵 `.minecraft/versions`，
   返回值就是 `'.minecraft'`。
2. **POSIX 下 `JAVA_HOME` 被无视**。`find_java()` 只找 `bin/java.exe`，Linux 上文件叫 `java`；
   探针给一个 `bin/java`（无 `.exe`）的假 JDK、PATH 清空，修前它返回的是**另一个** JDK（官方
   启动器的 `windows-x64` 运行时）。现在按 `sys.platform` 取二进制名，并且 `MC_JAVA` 指向文件时
   用 `is_file()` 判断（原来是 `suffix == ".exe"` + `exists()`，对**目录**也会返回——那是更糟的
   一种：会把 JAVA_HOME 目录本身当作 java 可执行文件）。
3. **macOS 被当成 Linux**。`open_in_explorer()` 只有 `nt` 和"其它"两支，macOS 走 `xdg-open`（通常
   没有这个命令），而且没有异常保护——`Popen` 抛 `FileNotFoundError` 会把请求打成 500。现在按
   `win` / `darwin` / 其它三分支，并返回 `bool`，找不到打开器就返回 `False`。
4. **死代码常量** `JAVA_FALLBACK` 定义了从未引用，值是作者机器上的 `C:\Program Files\Java\...`。

顺带把 `LOCALAPPDATA` 的回退从写死的 `~/AppData/Local` 换成按平台取（Windows 有 `LOCALAPPDATA`
时行为完全不变；POSIX 走 `XDG_DATA_HOME` 或 `~/.local/share`），`backend.pick_java` 的
`windows-x64` 目录名也不再写死。

**Windows 侧没有变化**，这条是回归重点，实测：

```text
local_app_data()  C:\Users\27682\AppData\Local
java_binary()     java.exe
find_java()       ...\Microsoft.4297127D64EC6_...\java-runtime-epsilon\windows-x64\...\bin\java.exe
default_root()    C:\Users\27682\AppData\Roaming\.minecraft
```

## 5. 这一轮踩到的四个坑（都是"测量工具坏了"，不是被测代码坏了）

做这类验证最容易把工具的问题当成产品的缺陷，记下来：

1. **先翻 `sys.platform` 再 import `subprocess`** → Windows 版 CPython 会去 `import _posixsubprocess`
   然后失败。修法：驱动里先把要用的 stdlib（`subprocess`/`json`/`shutil`/`zipfile`/`http.server`）
   用 Windows 语义导入，再翻平台。
2. **把 `os.name` 也翻成 `posix`** → `pathlib` 会去构造 `PosixPath`，Windows 上直接
   `UnsupportedOperation: cannot instantiate 'PosixPath' on your system`。这一条我第一版当成
   "`server` 模块在 Linux 上加载失败"报了，是假的，已改掉：`os.name` 不动，只翻 `sys.platform`，
   并把这条局限写进 audit 的 `caveats`。
3. **内嵌 Python 在含中文的路径下用 cp936 写 stdout**，父进程按 UTF-8 解就 `UnicodeDecodeError`。
   修法：子进程加 `-X utf8`，父进程显式 `encoding="utf-8"`。仓库路径里有"新建文件夹"，
   这个坑在这台机器上必然触发。
4. **误报要逐条核对**：`drive-letter` 正则把 `https://` 里的 `s:/` 当成盘符，`percent-env` 把
   `strftime` 的 `%Y%m%d` 当成环境变量，一次性贡献了 30 多条假命中。收紧成"盘符后必须跟字母或
   中文"、"百分号里只能是大写+数字"之后，命中数才从 58 掉到 28。

## 5.5 克隆验证：收件人自己也能验

交付验证的最后一步是"别人拿到能不能自己跑"。在 `f89f0b2` 上做了一次真克隆：

```text
== check_hashes ==          ok=1337 mismatch=0 missing=0
== audit_portability ==     tracked *.py: 111 | delivery hits: 22 in 4 files
                            (docstring 6, guarded 12, bare 4) | 4/4 可导入
== probe_behaviour ==       6/6
```

原始输出在 `clone-check.log`。这里写 `ok=1337` 是因为克隆的是 `f89f0b2`——那份清单有 1337 项；
`clone-check.log` 本身是在这次验证之后才加入清单的，所以当前清单是 1338 项。

这一步同时反证了 p201 的成果：`.gitattributes` 的 `* -text` 加上 `git ls-files -z` 之后，克隆出来的
字节和清单一致，不需要 `core.autocrlf` 配合。

## 6. 门禁与边界

- `test_review_fixes` **188/188**（新增 `test_cross_platform_delivery()`，从四份 JSON 与两份日志
  **重算**，见 `gate-review-fixes.log`）；
- `check_hashes` **1324 → 1349**，`verify_evidence` passed，`audit_eol` 一致；
- 无新 release：v0.5.6 不变，`dist/` 不进仓库（那个残的 0.5.7 包已删除）。

边界，按重要性排：

1. **同一台机器，不同的环境**——不是另一台电脑。Windows 本身、网络、以及"这台机器上正好装了
   什么"仍然在影响结果。
2. **没有 POSIX 内核参与**。动态检查只证明"导入图里没有 Windows-only 依赖"，不证明路径语义
   （分隔符、大小写敏感、文件锁、信号）在 Linux 上正确。WSL 被安全策略拦住，没有绕过。
3. **便携包按构造就是 Windows-only**：内嵌 `python-embed-amd64` + 只有 `run.bat`（没有 `.sh`）。
   要出 Linux/macOS 的包，需要另一套嵌入式运行时与另一份启动脚本，本轮没做，也没有说能做。
4. **Java 的自动下载没验**：干净环境里 `/api/status` 返回 `java: null` + `java_error`，UI 不会崩，
   但 `install_jvm_runtime` 的实际下载要联网，没跑。
5. **完整重打包没做成**：`minecraft_launcher_lib` 在这台机器上没有，所以用叠加源码的方式验了
   改动，而不是新包。这正是新加的 `require_vendored` 存在的理由——下次它会直接拦住。

## 7. 文件

```text
runs/p208-cross-platform/
  README.md                    本文件
  probe_behaviour.py           六个行为探针（before/after 同一个脚本）
  behaviour-before.json        修前：2/6
  behaviour-after.json         修后：6/6
  run_clean_host.py            剥离环境跑包（--overlay-launcher / --out）
  clean-host-shipped.json      照发原件：8/8
  clean-host-current.json      叠加当前源码：8/8
  build-blocked.log            依赖缺失时拒绝出包（rc=1）
tools/audit_portability.py     静态 + 动态平台审计（本目录的两份 audit JSON）
runs/p208-cross-platform/audit-before.json   28 处 / 未保护 24
runs/p208-cross-platform/audit.json          22 处 / 未保护 4
```
