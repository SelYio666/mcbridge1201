# p216 UI 美术优化 · 独立验收（2026-10-31）

验收对象：`fabca29 feat(ui): polish the three user-facing pages ... (p216)`。
结论：**美术与可用性通过（PASS）**，但有 2 个交付项要补、1 个 UI 文案小问题。

## 一、独立复跑（不是照抄它的日志）

| 项 | 结果 |
|---|---|
| `gradle -p java test installDist` | BUILD SUCCESSFUL（6 tasks up-to-date） |
| `tools/test_review_fixes.py` | **463/463** |
| `tools/check_hashes.py` | **1559/1559**（mismatch 0 / missing 0） |
| `tools/verify_evidence.py` | passed |
| `tools/check_text_encoding.py` | 244 markdown clean |
| git | `master...origin/master` 同步（验收前 HEAD `fabca29`） |

## 二、页面复现

### 启动器（launcher/web）

- 起真实后端 `launcher/server.py`（8765）+ Edge headless CDP；
- 重跑 `interact_check.mjs`：真实交互全过，`console errors = []`；
  - 选中/键盘 Enter/模式切换/搜索过滤；
  - 加载器版本 **256** 个选项，原版时禁用加载器；
  - 高级设置展开，JVM/模组/整合包下拉各有内容；
  - 900px / 480px 宽度 `scrollWidth` 不溢出（885/480）；
- 重拍截图 `redo-launcher-after.png`，与提交的 `launcher-after.png` 视觉一致（实时版本列表时间不同）。

### PCL 面板（tools/pcl_panel.py）

- 重跑 `capture_panel.py`：真实 Tk 事件循环，**921** 个版本加载完成，安装按钮可用；
- 重拍 `redo-panel-after.png`，与提交的 `panel-after.png` 一致；
- 深色卡片、三步布局、状态色、等宽日志都正常，无控件裁剪。

### 下载源页（share/download-sources/index.html）

- 用 CDP 模拟 `prefers-color-scheme: dark` 重拍 `redo-download-dark.png`：深色可读、层级正常；
- 链接对比（`HEAD^` vs `HEAD`）：外部链接 **0 丢失**，只新增 6 个页内锚点（#official/#loaders/#mirror/#status/#verify/#faq）；
- `focus-visible` 与 `prefers-color-scheme` 样式确实存在。

## 三、发现的问题（按优先级）

1. **列表截断与文案不一致（小，但真实）**：
   `app.js` 用 `items.slice(0, 400)` 渲染列表，但计数文案写“当前列出 921 个”
   （`vercount` 取下拉选项数）。实测 `#mcver` 有 921 项、`#verlist` 只有 401 行。
   建议二选一：改成“显示前 400 个（可用下拉/搜索定位）”，或做虚拟列表/分页。
2. **发布包未重建**：`launcher/web/*` 与 `tools/pcl_panel.py` 会进便携包，但最新 release 仍是
   v0.5.6 的旧 UI；需要重新打包并发版（建议 v0.5.7），否则用户下载到的还是旧界面。
3. **面板安装流程未端到端重跑**：本次只验证了真实窗口渲染与既有契约回归；
   美术验收可以，但不要据此宣称“安装流程重新验证过”。
4. **下载页移动端只验了 CSS/宽度，没有移动端截图**；启动器窄屏有数字验证。
5. 工作区仍有未跟踪噪声：`.workbuddy/`、`runs/p210-cloth-config/attempt1-field-only/`
   与 p215 旧截图——不属于 p216，建议清理或单独归档。

## 四、美术评价

- 三处页面已统一到同一套深色视觉语言：启动器双栏（版本库 + 主操作）、面板三步卡片、下载页吸顶导航 + 卡片表格；
- 信息层级、留白、hover/disabled/error、焦点态、窄屏保护都在；没有发现刺眼或不可读的配色；
- 结论：**作为“美术优化”这次交付合格**；上述 1/2 两项属于产品收尾，不是美术返工。

## 五、证据

- `redo-launcher-after.png`、`redo-panel-after.png`、`redo-download-dark.png`（本次独立重拍）；
- 交互输出见运行记录（本文数值）；门禁由验收者本机重跑。
