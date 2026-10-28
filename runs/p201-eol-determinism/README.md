# p201 — 让哈希清单在干净克隆里还能对得上

日期：2026-10-28
对象：`runs/SHA256SUMS.txt`（`tools/hash_evidence.py` 生成、`tools/check_hashes.py` 校验）
结论：p200 那次提交在**别人机器上根本验不过**——全新 clone 得到 `ok=646 mismatch=623 missing=20`，而本机打印的是 1289/1289。已修：`.gitattributes` 钉死 `* -text`、工作区归一到 blob 字节、20 条指向 gitignored `work/` 的条目删除。修完 clone 出来 `ok=1269 mismatch=0 missing=0`（清单 1289→1269 是因为删了 20 条 `work/`；本目录的 6 个文件随后也进了清单，所以今天看 HEAD 是 1275 条，`check_hashes` 在同一棵树上给 1275/1275）。

## 缺陷是怎么暴露的

用户清单的第 8 条是"干净机器交付"。写这条之前先做了一个最小实验：`git clone` 自己，跑同一条命令。

`clone-before.log`（clone 出 `82e4e9f`，即 p200 那版）：

```text
ok=646 mismatch=623 missing=20
```

三个数各有各的原因：

- **623 mismatch**：`core.autocrlf=true` 且仓库没有 `.gitattributes`，git 提交时把文本归一成 LF 存 blob，检出时又改写成 CRLF。本机工作区的真实状态是 **1224 个纯 LF、422 个纯 CRLF、264 个混合**——哈希就是按这堆混合字节算的。凡是本机存成 CRLF 的文件，清单里记的是**别人永远拿不到的字节**。
- **20 missing**：清单里有 20 条指向 `work/` 下的构建产物（patched jar、remap 输出）。`work/` 是 gitignored 的，只有造它的那台机器上有，干净 clone 里必然"missing"，永远无法验证。
- **646 ok**：剩下那些本来两边一致的——所以本机看是"全绿"。

诊断脚本 `audit_eol.py` 用的是更干净的比较：对清单里每个路径，比较**工作区字节**和**`git checkout` 真会写出的字节**（`git cat-file blob :<path>`）。修复前 1289 条里 737 条一致、532 条不一致（都是 `index=lf worktree=crlf`）。这个 532 与 clone 的 623 不是同一口径（前者比的是"本机工作区 vs blob"，后者比的是"清单里的哈希 vs clone 拿到的字节"），所以两个数都写出来，不混用。

## 修了什么

1. **`.gitattributes` 钉 `* -text`**：不再做任何 CRLF↔LF 转换，"提交进去什么，落地就是什么"。
   - 为什么不用 `* text=auto eol=lf`：`launcher/run.bat` 在清单里、且是 LF 提交的；一旦给它 `eol=crlf`，干净 clone 拿到 CRLF，哈希就对不上了。`run.bat` 里没有 `goto`/标签（纯顺序命令），LF 可用，现状也一直是 LF。
2. **工作区归一到 blob 字节**：`git checkout-index -a -f`（1224 LF / 456 二进制 / 67 空文件）。注意这一步在 `* -text` 生效前后看到的"686 个文件被修改"是**纯行尾差异**（394940 insertions = 394940 deletions），没有任何内容变化。
3. **删掉 20 条 `work/` 条目**，并在 `hash_evidence.py` 里加警告：清单里出现未跟踪路径就打印出来（不 fail，因为新产物总是先写哈希再 `git add`）。
4. **顺手修的第二个洞**：`hash_evidence.py` 用 `git ls-files` 做"是否跟踪"判断，而 git 默认给非 ASCII 路径加引号转义（`share/from-source/\344\273\216...`），于是 3 个已跟踪的 `share/` 交付物被误报成"未跟踪"。改成 `git ls-files -z` 后清零。这个如果没发现，会诱导人去"补提交"三个本来就在库里的文件。

## 怎么防止再坏

- `runs/p201-eol-determinism/audit_eol.py`：逐条比较工作区 vs checkout 字节，列出未跟踪条目；`--json` 给回归用。
- `test_eol_determinism()`（6 条）：`.gitattributes` 存在且钉了 `-text`；审计脚本存在；审计读全了清单（>1000 条）；**已提交**文件零漂移；清单里没有未跟踪路径。
  - 允许"未提交的改动"漂移：哈希是对**已提交字节**的声明，作者正在改文件时不该判红。判据是 `git status --porcelain -z`。

## 证据

同一台机器、同一条命令、只差一个提交：

| | clone `82e4e9f`（p200） | clone `2e34a9a`（p201） |
|---|---|---|
| `check_hashes` | `ok=646 mismatch=623 missing=20` | `ok=1269 mismatch=0 missing=0` |
| `audit_eol` 漂移 | —（该提交还没有这个脚本） | `reproducible 1269/1269, drifted 0` |
| `check_text_encoding` | — | `226 markdown, 226 clean`（本报告加入后为 227） |
| `test_review_fixes` | — | 未在该次 clone 里跑（见 `clone-head.log`：HEAD 上 125/125，ISSUE-02 skip） |

文件：`clone-before.log`、`clone-after.log`、`audit_eol.py`、`gate-review-fixes.log`（130/130）、`gate-verify.log`（`verify_evidence` passed）。

两个 clone 日志各自带 `git log --oneline -1` 头，数字只对那一个提交成立；清单一旦把这几个文件本身也收进去，clone 的计数就会比 HEAD 少 6 条——"清单包含自己的日志"必然落后一步。这里不重跑，宁可让数字少 6，也不写一个对不上的数。


## 第三个基线：HEAD 自己的 clone

`clone-head.log`：clone 上面两个提交之后的 HEAD（`1c9cd48`），得到

```text
check_hashes        ok=1275 mismatch=0 missing=0
audit_eol           1275/1275 reproducible, drifted 0
check_text_encoding 227 markdown, 227 clean
test_review_fixes   125/125 checks passed, skipped: ISSUE-02
```

清单此时是 1275 条（1289 − 20 个 `work/` + 6 个 p201 文件），clone 出来的和本机一模一样。`clone-head.log` **故意不进清单**：清单要是把"证明清单可验证"的日志也收进去，每跑一次就得重算一次，永远自证不完。

## 边界（如实）

- **`test_review_fixes.py` 在 clone 里能跑，但少 5 条**：裸 clone 跑出 `125/125 checks passed, skipped: ISSUE-02`（ISSUE-02 那组要已构建的 Java CLI / 网络）。作者机上是 130/130。第一版这里写的是"clone 里没跑"，那是被一次 120 秒超时误导的结论，实跑之后改掉（`clone-head.log`）。
- **只在 Windows + Git for Windows 上验证**：`core.autocrlf` 是这台机器的全局配置，`* -text` 在 Linux/macOS 上是无操作（本来就不转换），但没有在那边实跑过。
- 这次没有改动任何 mod/launcher 代码，release 仍是 `v0.5.6`。
- `share/` 下三个交付物（`一键装到PCL.bat`、`从零下载.pdf`、`从零下载长图.png`）本来就在库里，只是被 `ls-files` 的引号转义误判；我没有"补提交"它们，只修了判断。
