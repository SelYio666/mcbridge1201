# p216 · 页面美术优化（启动器 / PCL 面板 / 下载源页）

对三个面向用户的页面做了一次整体视觉翻新，功能与接口保持不变。

## 改了什么

| 页面 | 文件 | 改动 |
| --- | --- | --- |
| 启动器主页 | `launcher/web/index.html` `style.css` `app.js` | 深色主题重设计：侧边版本库 + 主操作区双栏；补齐缺失的 JS 函数（`loadLoaderVersions` / `loadJvm` / `installJvm` / `loadMods` / `toggleMod` / `loadMrpacks` / `installMrpacks`），此前页面加载即抛 `loadLoaderVersions is not defined`，高级设置整块是死的 |
| PCL 一键安装面板 | `tools/pcl_panel.py` | vista 默认主题 → clam 自定义深色主题；改为「选择版本 → 游戏目录 → 安装」三步卡片；状态文字带颜色（就绪/进行中/完成/失败）；日志区等宽字体 + 滚动条 |
| 下载源说明页 | `share/download-sources/index.html` `preview.png` | 吸顶页内导航；表格卡片化（斑马纹 + hover）；代码块改深色终端风；`prefers-color-scheme` 深色适配；窄屏横向滚动保护 |

## 为什么这样改

- 启动器是第一入口，但原来是默认表单样式，且脚本在加载时就抛异常——先修功能再谈美观。
- 面板是安装入口，系统默认灰白表单与启动器观感割裂，三步引导替代一屏堆控件。
- 下载源页是对外帮助页，长表格 + 纯文本代码块可读性差，且没有深色模式。

## 改前 / 改后（真实截图，非设计稿）

- `launcher-before.png` / `launcher-after.png`（Edge headless + CDP，等待版本清单加载完成）
- `panel-before.png` / `panel-after.png`（真实 Tk 事件循环，921 个版本加载后截取）
- `download-sources-before.png` / `download-sources-after.png`

## 验证

- `capture_web.mjs`：页面就绪条件 + 控制台错误收集（改后 0 错误）
- `interact_check.mjs`：真实交互——选中版本、键盘 Enter、模式切换、搜索过滤、
  加载器版本查询（256 个选项）、vanilla 禁用加载器版本、高级设置展开、
  JVM/模组/整合包下拉填充、900px/480px 宽度无横向溢出
- `capture_panel.py`：面板真实运行，版本清单加载完成、安装按钮可用
- 仓库门禁：gradle test installDist、test_review_fixes、check_hashes、
  verify_evidence、check_text_encoding（结果见 `ui-polish.json`）

## 已知取舍

- 面板深色主题依赖 ttk `clam`；极个别平台无 clam 时回退系统主题（功能不受影响）。
- 启动器仍为纯深色（`color-scheme: dark`），未做浅色切换。
