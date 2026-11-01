# 移交提示词（复制整段给 ZCode / 其他 agent）

```text
你是接手 mcbridge1201 仓库的维护者。先读完这份提示，再动任何文件。

一、项目是什么
- 仓库：https://github.com/SelYio666/mcbridge1201（master，MIT）
- 本地：C:\Users\27682\Documents\新建文件夹\mcbridge1201
- 定位：Minecraft 1.20.1 模组 → Fabric 1.21.1 的兼容工具箱（CenturyBridge 转换 + 规则 + javac 桥），
  外加一个本地网页启动器，以及给 PCL2/HMCL 的“一键安装”工具。
- 当前 HEAD：a181e02；最新发布 v0.5.10（启动器 zip）、v0.5.9（安装器/面板 zip）。
- 文档阅读顺序：README.md → docs/FINAL-STATUS.md → docs/report-2026-10-30.md →
  docs/remaining-work.md。runs/ 下每个 pNNN-* 是一轮证据（README + 脚本 + 日志/截图）。

二、当前状态（2026-11-01）
- 引擎：CenturyBridge 分段转换 + 规则修补；ImmediatelyFast 1.21.1 移植已验证（HUD/物品/地图 atlas/
  VertexBuffer/Iris/专用服务器）；Shulker 网格与服务端物品恢复；TrashSlot UI 全链路；
  Cloth Config 配置界面可开可改值；Forge/NeoForge 专用服务器与客户端加入；mrpack 真实 files。
- 启动器：launcher/server.py + launcher/web（原生 HTML/JS），921 版本浏览/安装/启动，
  下载源可选 + 源健康缓存；“安装到 PCL2”可一键装进 PCL（p223/p227）。
- 最近结案：p215 的“创建世界按钮不吃点击”其实是坐标偏了 20px（p226）；
  `Not a string` 是原版 1.20.4 单人 level.dat 空 Player 模板导致的无害日志（p230）。
- 门禁（作者机）：check_hashes 1609 ok / 0 mismatch / 0 missing；verify_evidence passed；
  test_review_fixes 467/467；java test 32/32；干净 clone 460/460 且有 3 项 artifact skip。
- 真正没做的只剩：多客户端 / 跨机器延迟（需要第二台机器或真实双开）。
- 用户已明确：HMCL 不用太投入（HMCL 有自己的下载路径）；不要为 HMCL 再排计划。

三、环境
- JDK 21：C:\Users\27682\Documents\新建文件夹\.toolchain\jdk
- Gradle 9.8.1：C:\Users\27682\Documents\新建文件夹\.toolchain\gradle\bin\gradle.bat
  （离线构建时设 GRADLE_USER_HOME=C:\Users\27682\Documents\新建文件夹\mcbridge1201\.toolchain\gradle-home）
- Python：系统 3.12（C:\Users\27682\AppData\Local\Programs\Python\Python312\python.exe，
  带 PyInstaller/tkinter/Pillow）；另有 DSH 运行时 python。
- PCL2 2.99.0.0：D:\浏览器所下载文件\我的世界PCL2启动器_2.12.8.2，其 gameDir 是 %APPDATA%\.minecraft。
- HMCL 3.17.0.363 测试目录：work/tmp/hmcl-test（jar 在里面；按用户要求别继续投入）。
- 旧路径 D:\我的世界\.minecraft 已不存在，配置里可能还残留，改目录前先测存在性。
- 本地启动器：python launcher/server.py → http://127.0.0.1:8765/

四、红线（违反即返工）
- 仓库里 0 个 jar；游戏/模组 jar 只能放 work/（已 gitignore）。不要分发游戏或模组。
- 不空实现、不返回默认值糊弄、不删 mixin 冒充通过；核心逻辑（存档/掉落/同步）不许降级。
- 不伪造证据；没验证的就说没验证；失败要贴具体错误。
- 不改玩家存档；测试写盘前先备份或写副本。
- 中文短句回答；先结论再证据路径。

五、每次改动后的门禁
  python tools/hash_evidence.py
  python tools/check_hashes.py          # 期望 ok=N mismatch=0 missing=0
  python tools/verify_evidence.py       # 期望 "passed": true
  python tools/test_review_fixes.py     # 期望 467/467（或新增后的总数）
  gradle -p java test                   # 32/32
全绿再提交。提交前确认 git status 没有意外文件。

六、提交与推送（最容易翻车）
- git push 经常失败（Recv failure / 443 timeout）：重试；仍不行用 work/tmp/push_via_api5.py，
  它会打印 MATCH（对比本地树与远端树）。
- 远端可能被 API 影子提交顶开：先 git fetch，再 git rebase origin/master，然后 push。
- 文件名用 ASCII。中文文件名会让 p201 的 checkout 校验失败。
- 写文件不要 CRLF（.gitattributes 是 * -text，按字节校验哈希）；Python 写文件用 newline="\n"。
  不要 BOM（javac 会报“非法字符: '\ufeff'”）。
- argparse 的 help 文案里不要出现裸 %。

七、踩过的坑（runs/ 里有完整记录）
- 打包启动器必须带 tools/from_source_install.py，否则发布包 /api/pcl 报
  No module named 'from_source_install'（p223）。
- PyInstaller 只能 --onedir；--onefile 会触发安全检查失败。
- runs/p208 的 clean-host 脚本取“最新包”要按版本号自然排序（0.5.10 > 0.5.7）。
- 混淆后的 MC 类都在默认包：写 javaagent 必须放进包名，否则签名信息冲突启动即崩。
- JFR：jcmd JFR.stop 常写出 0 字节，先 jcmd JFR.dump 再 stop。
- HMCL 便携版配置里游戏目录是相对 .minecraft（自动检测拿不到），且用户说不用太管。
- p215 的创建世界按钮坐标（含窗口边框的截图坐标）：y≈470，不是 437；按钮实际 y 457–488。
- 服务端生成的 1.20.4 世界 level.dat 里 Player 是空模板 → 单人首次/每次加入都会打
  “Not a string”，属原版无害日志（p230）。

八、下一步（按优先级）
1. 多客户端 / 跨机器延迟验证（唯一真缺口；需要第二台机器或两个独立 gameDir 的双开）。
2. 维护性工作：发新版本时重建 dist/mcbridge-launcher-<label>.zip，跑
   runs/p208-cross-platform/run_clean_host.py 与 runs/p227-shipped-launcher-pcl/drive.py 验收，
   更新 README / docs/FINAL-STATUS.md（版本号、门禁数字）。
3. 不要主动做：HMCL 面板、HMCL 便携自动检测、Sodium 渲染核心移植（已判定不可行）。

九、交付格式
- 每轮改动放在 runs/pNNN-短名/：README.md（结论/证据/边界）+ 可复现脚本 + 结果 JSON/截图；
  新增文件要加进 tools/hash_evidence.py 的清单。
- commit message 说清“改了什么 + 为什么”；用户面前先给结论，再给证据路径，最后列没做完的。
```
