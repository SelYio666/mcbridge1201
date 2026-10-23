# p173 — 回滚地图 atlas 尝试后的启动 sanity

日期：2026-10-23。p172 重新登记 `MixinMapRenderer` 失败（`method_32601` 参数变成 `class_9209`），
回滚后确认端口仍可启动。

## 状态

- jar sha256 `3043c978...`；
- 审计 `listed=34 inert=5`（`MixinMapRenderer`、`MixinMapRenderer_MapTexture` 均未启用）；
- p173：单人 `ColdWorld`，`{"joined": true, "crash": null}`。

## 证据

`launch.log`、`result.json`、`world.png`。
