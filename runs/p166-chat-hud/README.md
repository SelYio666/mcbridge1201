# p166 — 重登记 MixinChatHud（inert 7 → 6）

日期：2026-10-23。p165 审计发现 7 个 inert mixin，其中 `hud_batching.MixinChatHud` 是聊天 HUD 批处理；
这次把它按 1.21.1 重新登记进 config。

## 改动

- `rules/fabric-1.21.1/immediatelyfast-batching-port.json` 的 `mixinConfigAdditions` 增加：
  `hud_batching.MixinChatHud`（config `immediatelyfast-common.mixins.json`）；
- 1.21.1 的 `class_338.method_1805` 多了 `boolean` 参数，Mixin 按方法名匹配，靠 `@Inject HEAD/RETURN`
  包住聊天 HUD 渲染；begin/end 会嵌套在 `MixinInGameHud` 的 HUD 批处理里。

## 结果

```text
audit_mixins: configs=2 errors=0 listed=33 inert=6 problems=6   （inert 7 → 6）
p166: {"joined": true, "crash": null}  （单人 ColdWorld，64 石头 playerdata）
```

- 启动进世界无崩溃；
- 聊天 HUD 的 begin/end 被调用（HUD 每帧渲染聊天层），没有把既有 HUD/物品批处理打崩；
- 审计里 ChatHud 不再 inert。

## 诚实限制

- **没有实际打开聊天面板/发送消息**（此前的键盘注入对聊天输入不可靠），所以只证明“登记后能启动、
  不崩、审计不再 inert”，不证明聊天文本批处理画面完全正确；
- 嵌套 begin/end 的计数语义没有单独拆开验证（batched-draws 是聚合计数）；
- 其余 6 个 inert（BufferBuilder、MinecraftClient、VertexBuffer、FontManager、BufferRenderer、
  MapRenderer）仍未处理。

## 证据

`launch.log`、`result.json`、`world.png`、`audit.log`。
