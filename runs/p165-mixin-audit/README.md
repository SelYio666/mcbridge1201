# p165 — ImmediatelyFast 端口 jar 的 mixin 审计（inert=7）

日期：2026-10-23。对 v0.5.0 的端口 jar 跑仓库自带的审计工具，结果必须记账。

## 命令

```text
python tools/audit_mixins.py --jar work/cb/out/popular/immediatelyfast/ImmediatelyFast-ported.jar
python tools/check_bridge_consistency.py --bridge-dir work/tmp/if-port-classes --jar <同一个 jar>
```

## 结果

```text
configs=2  config_errors=0  listed=32  inert=7  problems=7   (audit_mixins 退出码 1)
canonical bridge classes: 17
checked 1 jar(s); problems = 0                               (bridge 一致性通过)
```

7 个 inert（在 mixin 包里、但没列进任何 mixin config，等于**不会生效**）：

- `core/MixinBufferBuilder`
- `core/MixinMinecraftClient`
- `fast_buffer_upload/MixinVertexBuffer`
- `fast_text_lookup/MixinFontManager`
- `hud_batching/MixinChatHud`
- `hud_batching/compat/MixinBufferRenderer`
- `map_atlas_generation/MixinMapRenderer`

## 解读

- 这些类存在但未在 config 中登记，说明是转换时被剥掉/未重新登记的 mixin；对应功能在本端口里
  **没有生效**（例如聊天 HUD 批处理、字体管理器、BufferBuilder/VertexBuffer 上传、地图渲染等）；
- 我们已实测通过的 HUD/物品/overlay 路径依赖的是另外的 mixin（重登的 `MixinInGameHud`、
  `MixinDrawContext`、`MixinGameRendererHud` 等），不依赖这 7 个；
- 但 v0.5.0 文档里“mixin 审计 0”的说法对**这个端口 jar** 不成立，已修正为“inert=7，见 p165”。

## 后续

- p166 已把 `hud_batching.MixinChatHud` 重新登记进 config，审计 inert 从 7 降到 6
  （`runs/p166-chat-hud/`）；其余 6 个仍未处理；
- 若要补这些功能，需要逐个按 1.21.1 移植（有的会撞 tombstone/描述符），不能只往 config 里加名字；
- 本次不硬加，避免把 v0.5.0 已稳定的 HUD 路径搞崩。

## 证据

`audit.log`、`bridge.log`。
