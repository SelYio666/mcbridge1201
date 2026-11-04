# p271 — 推送被 GitHub 拒绝（远端故障），改用 bundle 交付

> **后续（2026-11-04 稍晚）**：远端故障恢复，推送**成功了**。
> `refs/heads/zcode` = `b5b7dfc`，与本地 HEAD 完全一致；`git fetch origin zcode` 之后
> `origin/zcode` 也指向同一个提交。下面记录的「被拒绝」是当时的事实，不是最终状态——
> bundle 方案因此不再需要，但保留下来作为「远端不可用时怎么交付」的做法。


日期：2026-11-04。本会话所有提交都还在本地；尝试推到 `origin`（`github.com/SelYio666/mcbridge1201`）
时被远端拒绝。本回合记录证据，并准备好**可离线交付**的替代方案。

## 1. 三次尝试，三种不同的远端错误

| 次数 | 远端返回 |
|---|---|
| 1 | `remote: Internal Server Error` / `! [remote rejected] zcode -> zcode` |
| 2 | 同上，Request ID 不同（`F6E4:22EF92…`）|
| 3 | `remote: fatal error in commit_refs` / `! [remote rejected] zcode -> zcode (failure)` |

三种不同错误、本地仓库完整（`git bundle verify` 通过、`check_hashes` 全绿）→ **不是本地数据问题，
也不是网络中断**（网络是通的，请求到达了 GitHub 并被拒绝）。

已排除的可能：

- **不是体积**：`.git` 只有 0.3 MB（对象在共享库），完整 bundle 67.4 MB，远低于 GitHub 的单次推送上限；
- **不是权限**：错误是 `remote rejected` + 服务器内部错误，不是 `403`/`denied`；
- **不是 force 冲突**：没有用 `--force`，且远端根本没有 `zcode` 分支（`origin/zcode` 不存在）。

**没有用 force-push，也不会用。**

## 2. 可离线交付的替代方案

既然远端暂时不可用，把分支打成 bundle——这是 git 原生的、可放在任意介质上的交付物：

```powershell
# 完整历史（自包含，67.4 MB）
git bundle create work\tmp\zcode-2026-11-04.bundle zcode

# 增量（只需 31 个提交，0.29 MB；接收方需要已有 origin/master = 51cea8d）
git bundle create work\tmp\zcode-incremental.bundle origin/master..zcode
```

接收方用法：

```powershell
git bundle verify <file>
git fetch <file> zcode:zcode            # 完整包
git fetch <file> zcode:zcode            # 增量包（基于 origin/master）
```

两个文件都在 `work/`（不入库）。`git bundle verify` 对完整包返回 "The bundle records a complete
history"。

**0.29 MB 的增量包**是实际可用的那个：本会话的 31 个提交全是文本改动（规则 JSON、Java 源码、
证据文档），没有二进制。

## 3. 恢复推送时该做什么

1. 先 `git fetch origin`，确认 `origin/master` 是否前进了（可能有别的会话在推）；
2. 如果前进了 → 在 `zcode` 上 `git rebase origin/master`（本会话一直这么做，`1e4d14f` 那次就是这么对齐的）；
3. 再 `git push origin zcode`（**不带 --force**）；
4. 推送成功后，跑一遍干净 checkout 的三件套确认远端内容与本地一致。

## 4. 边界

- 本回合**当时没有**推送到任何地方（三次尝试都被远端拒绝）；随后远端恢复，`zcode` 已推送成功。
- 没有尝试换协议（SSH）、换镜像或改 remote——那属于用户的账号/基础设施决定。
- bundle 文件是派生数据，不纳入版本库（且完整包 67 MB 不适合入库）。
