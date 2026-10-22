# p151 — 默认运行不输出周期 benchmark 日志

日期：2026-10-22。验证 p148 的采样器改成 opt-in 后，正常启动不会刷 `batched-draws`/`fps=`。

## 条件

- 同一个移植 jar；
- **不设置** `-Dmcbridge.bench=true`；
- 单人 `ColdWorld` + 64 石头 playerdata，正常进世界。

## 结果

- `IFUser joined the game`，无 crash；
- 周期日志（`batched-draws`/`fps=`）条数：**0**；
- 仍保留一次性提示 `[mcbridge-port] hud batching begin`（不影响正常使用）。

## 证据

`launch.log`、`result.json`、`world.png`。
