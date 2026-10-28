# p198 — 文档双重编码修复与编码守卫

日期：2026-10-28
结论：`README.md`、`docs/FINAL-STATUS.md`、`runs/p125-final-acceptance/README.md` 三个文件已恢复为可读 UTF-8；新增 `tools/check_text_encoding.py` 作为直接门禁项接入 `tools/verify_evidence.py`，并加 6 条回归防止再次写坏。修复性质要如实说明：**只有 19.4% 的受损字符是字节级可逆还原，其余 80.6% 是按上下文重写的，不是“原样恢复”**。

## 事实链

1. 损坏方式：这三个文件曾被以 UTF-8 写入的内容按 cp936 读入、再以 UTF-8 保存（p195 期间）。表现分三类：

   - **双重编码**（可逆）：UTF-8 字节被两两配对成 GBK 字，如 `鏂版墜` `鐜嬪`；
   - **用户区私用字**（可逆）：GBK 落到 `U+E000..F8FF`，显示成方框；
   - **字节丢失**（不可逆）：配对失败处被写成 `?`，原字节已不存在，无法反推。

2. 三个文件在 HEAD 版本上的判定，用新增的守卫直接扫描原始 blob（`.build/p198-before/`，见 `encoding-scan-before.log`）：

   ```text
   checked 3 markdown file(s): 0 clean, 892 finding(s)     # exit=1
   ```

3. 修复后（`encoding-scan-after.log`）：

   ```text
   checked 3 markdown file(s): 3 clean, 0 finding(s)       # exit=0
   checked 223 markdown file(s): 223 clean, 0 finding(s)   # 全部 git 跟踪的 *.md
   exempt: runs/p198-text-encoding/README.md — …; 3 content finding(s) suppressed, 0 structural kept
   ```

   最后一行是本报告自己：它必须引用乱码字节当例子，所以按下面的“豁免”机制处理，且**明确打印被抑制的数量**，不让豁免变成藏问题的地方。

4. 行数完全保持（151 / 267 / 286 行），说明修复没有增删结构，只替换了乱码段。

## 还原 vs 重写（量化，不美化）

`restore_report.py` 对 HEAD blob 逐行、逐“非 ASCII 段”做损坏的逆运算（`GBK 编码 → UTF-8 解码`），能通过才算可逆：

| 文件 | 行数 | 原样未动 | 整行可逆还原 | 需重写 | 非 ASCII 段 | 其中可逆 | 受损字符 | 其中可逆 |
|---|---|---|---|---|---|---|---|---|
| `README.md` | 151 | 78 | 3 | 70 | 791 | 285 | 3911 | 971 |
| `docs/FINAL-STATUS.md` | 267 | 152 | 5 | 110 | 1323 | 281 | 5945 | 1034 |
| `runs/p125-final-acceptance/README.md` | 286 | 156 | 4 | 126 | 921 | 152 | 3529 | 594 |

- 行级：386 行未动、12 行可由逆运算整行还原、**306 行必须重写**。
- 字符级：受损 13385 字，可逆 2599 字（19.4%），**10786 字（80.6%）所在的字节已被 `?` 吞掉**。
- 重写依据：同一文件内未损坏的句子、同段落的英文/路径/数字骨架（`runs/pNNN`、版本号、统计数）、`git log` 的提交标题、以及被引用的 `runs/` 证据目录本身。示例：`# mcbridge1201锛圥0 鐮斿彂浠撳簱锛?` → `# mcbridge1201（P0 研发仓库）`，其中 `P0` 的 `P` 已丢成 `?`，是按下文“P0 的事实与证据”补回的，不是还原。
- 提交说明里逐段标注了哪三个文件属于“还原 + 重写混合”，没有把重写说成还原。

## 守卫规则（`tools/check_text_encoding.py`）

扫描 `git ls-files *.md`（也可传路径）。每条命中都算失败，退出码 1：

| 规则 | 判据 |
|---|---|
| `bad-utf8` | 文件不是合法 UTF-8 |
| `fffd` | 含 `U+FFFD` 替换符 |
| `pua` | 含 GBK 用户区私用字 `U+E000..F8FF` |
| `signature` | 含只可能由“UTF-8 字节当 cp936 解”产生的字（`锛 鈥 銆 鍦 乣 夛 坄 嶅 …`）；其余跟踪文档均不含 |
| `question` | ASCII `?` 紧邻 CJK/全角，或连续两个及以上 `?`（损坏器每个丢字节写一个 `?`） |
| `double-enc` | 连续 ≥6 个 CJK 字符重新 GBK 编码后仍是合法 UTF-8 —— 双重编码的一般形式，能抓住新写坏的内容 |

`question` 与 `double-enc` 会同时覆盖“未来用错编码另存”的新内容，不只是这三个文件的形状。

### 豁免（唯一一条，可审计）

引用乱码的文档（就是本文件）会被四条内容规则判死，所以守卫有一个 `EXEMPT` 表，键是相对路径、值是理由：

```python
EXEMPT = {
    "runs/p198-text-encoding/README.md":
        "p198 report quotes the damaged bytes to show what was repaired",
}
```

- 豁免只放行 `pua` / `signature` / `question-*` / `double-enc` 四条**内容**规则；`bad-utf8` 与 `fffd` 仍然照查，所以“坏编码”本身永远不能被豁免。
- 每次运行都会打印 `exempt: <路径> — <理由>; N content finding(s) suppressed`，抑制了多少条是显式的，不存在静默通过。
- 任何新文件要进这张表都得改源码，diff 里看得见，不是给文件打一行注释就能自己给自己开绿灯。

## 门禁接入

- `tools/verify_evidence.py` 新增 `text_encoding` 检查项：直接跑守卫，失败即 `passed=false`。**不是**只靠回归套件间接覆盖（回归套件在 CLI 未构建时会整体 skip，守卫不该跟着 skip）。
- `tools/test_review_fixes.py` 新增 `test_text_encoding_guard()`，6 条断言：守卫存在、跟踪文档全绿、干净样本通过、按 p195 同法造出的损坏样本报错、确实给出了 finding 明细、豁免表只指向真实存在的文档（防止改名/删除后留下一条过期的放行）。
- 故意弄坏验证：测试里把干净样本按“UTF-8 字节逐个 cp936 配对、配不上写 `?`”的同一手法重造，守卫报 `0 clean, 5 finding(s)`、退出码 1（见 `gate-review-fixes.log` 中 `encoding guard: corrupted sample fails`）。

## 边界（不夸大的部分）

- 重写段落是**语义等价重述**，不是原作者逐字原文；措辞可能与损坏前略有差异，凡是数字/路径/版本号都保持与 `runs/` 证据一致。
- 守卫只看 `*.md`；`.py`/`.json`/`.java` 不在扫描范围（它们历史上没被这个手法写坏，且 Python 文件本身会因非法编码直接报错）。
- `signature` 字表是人工归纳的高频字，不是完备集合；兜底靠 `pua` / `double-enc` / `question` 三条结构性规则。
- 未做：把修复往前追溯 p195 的写入路径（哪个工具/哪次操作写坏的）—— 现在只堵住“再次入库”。

## 复现

```text
python runs/p198-text-encoding/restore_report.py          # 还原/重写量化（读 HEAD blob）
python tools/check_text_encoding.py                       # 全量扫描
python tools/check_text_encoding.py README.md docs/FINAL-STATUS.md runs/p125-final-acceptance/README.md
python tools/verify_evidence.py                           # 统一门禁（含 text_encoding 项）
python tools/test_review_fixes.py                         # 回归（含 ENCODING 5 条）
```

## 证据

`runs/p198-text-encoding/`：`README.md`、`restore_report.py`、`restore-report.log`、`encoding-scan-before.log`、`encoding-scan-after.log`、`gate-verify.log`、`gate-review-fixes.log`。
