# p197 — Shulker 预览键重绑定（配置真正生效）

日期：2026-10-26
结论：mod **确实**从 `configuration.controls` 读取预览键；把 `previewKey`/`fullPreviewKey` 重绑到 J(74)/K(75) 后，27 格预览完整走完 COMPACT → FULL → COMPACT → NO_PREVIEW。p196 记录的“config 被忽略”是**读错字段**（写进了 `preview` 分类）导致的误判，本轮用 bytecode + 运行时配置回读更正。

## 结论先行（可复算的事实链）

1. `javap` 反编译 `ShulkerBoxTooltipClient.isKeyPressed(Key)`：

   ```text
   39: getfield  Key.get:()Lnet/minecraft/class_3675$class_306;
   42: invokevirtual class_3675$class_306.method_1444:()I     // getCode()
   45: invokestatic  class_3675.method_15987:(JI)Z             // InputConstants.isKeyDown
   ```

   即轮询码来自 `config.controls.<key>.get().getCode()`；`Configuration$ControlsCategory` 的字段是 `previewKey` / `fullPreviewKey` / `lockTooltipKey`，默认值分别是 LEFT_ALT(340) / RIGHT_SHIFT(342) / LEFT_CONTROL(341)（`Key.defaultFullPreviewKey` 里 `sipush 342`）。
2. 配置反序列化只认 `controls` 分类（`ShulkerBoxTooltipConfigSerializer.fromJson` 读 `preview`/`tooltip`/`server`/`colors`/`controls`），`Key` 支持字符串或 `{code:"..."}`，所以 `"previewKey": "key.keyboard.j"` 合法。
3. p196 把 `"previewKey"` 写在 `"preview"` 里 → Jankson 忽略未知字段 → 生效的是默认 340/342。这就是“F 没反应、342 有反应”的真正原因。

## 方法

配置（`work/launcher-e2e/config/shulkerboxtooltip.json5`）：

```json
{
  "preview": { "enable": true, "alwaysOn": false },
  "controls": {
    "previewKey": "key.keyboard.j",
    "fullPreviewKey": "key.keyboard.k"
  }
}
```

- 选 **J/K** 而不是 F/G：F 是原版 `key.swapOffhand` 默认键，合成按下会真的把悬停物品换到副手（本 run 的第一次尝试就这样把 tooltip 弄没了，看起来像“预览没生效”）；J/K 在原版没有绑定，按下只影响 mod 自己的轮询。
- 单屏全流程：生存背包（`class_490`，配方书面板打开），槽位 10 是**服务端** `/item replace entity ... container.10` 放的 27 种物品 shulker box（每种 1..3 个，27 个不同 id，避免 `ContainerComponent` 合并）。
- probe 在 p191/p193 的轮询边界伪造按住状态，但**只认 74/75**（`InputPollMixin`），340/342 永远不会被判为按住 —— 因此任何 COMPACT/FULL 渲染都只能是“mod 真的去轮询了重绑定后的码”。
- `PreviewStateProbeMixin` 记录 mod 自己的 `updatePreviewKeys()` 结果与 `getCurrentPreviewType()` 的类型切换，避免再把“没渲染”误解成“配置没生效”。

## 结果

`result.json`：

```json
{
  "config_rebound": true,
  "keys_transitions": true,
  "compact_on_j": true,
  "full_on_jk": true,
  "compact_after_k": true,
  "no_preview_after_release": true,
  "real_hover_path": true
}
```

时间线（`client.log`，同一秒内按 tick 顺序）：

```text
P197_CONFIG alwaysOn=false preview=key.keyboard.j previewCode=74 full=key.keyboard.k fullCode=75
P197_TYPE NO_PREVIEW                                             # 起始（未按键）
P197_KEYS preview=true full=false  heldP=true  heldF=false      # J 按下
P197_COMPACT_REQUEST tick=53 J=74
P197_TYPE COMPACT                                                # 27 格 COMPACT
P197_KEYS preview=true full=true   heldP=true  heldF=true       # K 按下
P197_FULL_REQUEST tick=173 K=75
P197_TYPE FULL                                                   # 27 格 FULL
P197_KEYS preview=true full=false  heldP=true  heldF=false      # 只松 K
P197_TYPE COMPACT                                                # 回到 COMPACT
P197_KEYS preview=false full=false heldP=false heldF=false      # 松 J
P197_TYPE NO_PREVIEW                                             # 不再预览
P197_POLLS [32, 47, 49, ..., 74, 75, ..., 340, 341, 345]
```

- `GRID_DRAWITEMS call=1 type=COMPACT items=27 first=minecraft:iron_ingotx3`（COMPACT 与 FULL 都是 27 格；27 格 shulker 的 COMPACT 布局本来就是 9×3，所以两张截图的网格形状相同，区别由 `P197_TYPE`/`type=` 记录）。
- 截图：`after-full.png`（FULL）、`after-compact.png`（松 K 后 COMPACT）。
- `P197_POLLS` 里的 340/341/345 等是**原版启动时轮询所有 KeyBinding**造成的，不是 mod 的预览键；判据是 `P197_CONFIG` 的 74/75 与类型转移，而不是“poll 集合里没有 342”。

## 边界（不夸大的部分）

- 键状态仍是在 **`InputConstants.isKeyDown` 轮询边界**注入的（p191/p193 同一约定），不是 OS 级真实按键；本机 `keybd_event` 焦点竞争问题未变。因此本证据证明“mod 按配置的键码轮询并据此切换预览”，不证明“物理键盘按 J 一定被 GLFW 采到”。
- 只验证 27 格 icon/计数与三种预览状态；未验证 27 格各自不同 NBT/附魔/自定义名称的渲染差异（p196 已记录为剩余项）。
- 单个客户端 + 专用服务端；无多人并发。
- 无新 release（无 mod 代码改动，只更正配置用法与证据）。

## 复现

```text
python runs/p197-preview-key/build.py
python runs/p197-preview-key/run.py --timeout 300
```

## 证据

`runs/p197-preview-key/`：`result.json`、`client.log`、`server.log`、`server.properties.before`、`after-full.png`、`after-compact.png`、`build.py`、`run.py`、`fabric.mod.json`、`resources/p197.mixins.json`、`src/probe/ShulkerResidualProbe.java`、`src/probe/mixin/`（`InputPollMixin`、`PreviewStateProbeMixin`、`PreviewDrawProbeMixin`、`DrawTooltipProbeMixin`、`ModTooltipDataProbeMixin`、`MouseAccessor`、`CreativeTabInvoker`）。
