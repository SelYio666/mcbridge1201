# 工作区约定（给在这棵树里干活的 agent）

你是 **ZCode**，这是分给你的独立工作区。

- 路径：`C:\Users\27682\Documents\新建文件夹\mcbridge1201-zcode`
- 分支：`zcode`（从 master `de36c5a` 分出）
- 主仓库：`C:\Users\27682\Documents\新建文件夹\mcbridge1201`（**另一个人/agent 在用，不要读写它**）

## 硬规则

1. **只在本目录读写、提交**。不要 `cd` 到主仓库去改动它的工作区、索引或分支。
2. 不要在别的目录里 `git worktree add` 套娃。
3. 提交前跑完门禁；不要 force-push。
4. 编号（`runs/pNNN-*`）先查 `git log --oneline -5` 和 `ls ../mcbridge1201/runs`（只读），
   避开已经在用的编号；拿不准就用 `p300+` 段并说明。
5. 证据目录格式照旧：`runs/pNNN-短名/`，含 `README.md`（结论/证据/边界）+ 可复现脚本 + `result.json`/截图；
   新文件必须加进 `tools/hash_evidence.py` 的清单。

## 门禁（在本目录跑）

```text
python tools/hash_evidence.py
python tools/check_hashes.py
python tools/check_manifest_coverage.py
python tools/verify_evidence.py
gradle -p java test
```

Java 环境：

```text
JAVA_HOME=C:\Users\27682\Documents\新建文件夹\.toolchain\jdk
GRADLE_USER_HOME=C:\Users\27682\Documents\新建文件夹\mcbridge1201\.toolchain\gradle-home
```

## 共享资源

- 主仓库的 `work/`（游戏、assets、服务器实例、测试 world）**不在本工作区**，且被 gitignore。
- 需要跑客户端/服务器实验时，先只读引用主仓库里的路径，或问用户要一份拷贝；
  不要往主仓库的 `work/` 里写新东西。

## 提交与推送

- 小步提交，message 说清“改了什么 + 为什么”；
- 推送前先 `git fetch origin`，需要时 `git rebase origin/master`；
- 网络经常抽风（`Recv failure` / `443 timeout`）：重试即可，**别 force-push**；
- 远端主分支是 `master`；你在这个分支上工作，推送时用 `git push origin zcode`，
  由主工作区的人合并，或按用户指示推 `HEAD:master`。

## 接管

主仓库里可能还留着你上一轮未提交的 `fixtures/` 和 `tools/build_source_fixture.py`；
如果需要，把它们复制到本工作区继续，然后**不要再动主仓库**。
