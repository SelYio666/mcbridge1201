# p220 — `pcl2_game_dir` 返回“配置了但不存在”的目录

日期：2026-10-31。类型：真 bug 修复。

## 缺陷

`pcl2_game_dir()` 读 `PCL/Setup.ini` 的 `LaunchFolderSelect` 时，只要配置里有值就直接返回
`exe_dir / rel` 或绝对路径，**不检查目录是否存在**。

后果：如果 PCL2 配置里写的目录还没创建（换机器、删过目录、首次运行），`--pcl` 会 `mkdir`
并把整个游戏装到那个陌生路径（例如启动器目录下的 `missing/`），而不是退回 PCL2 自带的
`.minecraft`，也不会提示。

## 修复

- 解析出的候选目录**必须是已存在的目录**才返回；
- 不存在时退回 `exe_dir/.minecraft`（便携版标准位置）；
- 两者都没有则返回 `None`，让调用方报错，不再静默造目录。

## 验证

`runs/p220-pcl2-dir-check/verify.py`（4/4）：

```text
PASS missing configured folder -> None (no stray path)
PASS portable .minecraft is the fallback
PASS existing relative folder is used
PASS absolute existing folder is used
```

覆盖：缺失的相对目录、便携 `.minecraft` 回退、存在的相对目录、存在的绝对目录。
