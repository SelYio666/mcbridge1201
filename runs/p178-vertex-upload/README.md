# p178 — MixinVertexBuffer：动态顶点上传 fast path 的压力/A-B 验证

日期：2026-10-23。p169 认为 `fast_buffer_upload.MixinVertexBuffer` “目标在、但会改 GL 上传路径，
需要顶点上传压力/视觉测试才能启用”。本轮补上这个测试，并把 1.21.1 新增的
`method_60829` 入口一起接上。

## 1.21.1 签名

| 目标 | 1.20.4 | 1.21.1 |
|---|---|---|
| 顶点上传 | `method_43442` | 存在（`RenderSystem.glBufferData` 仍在） |
| 索引上传 | `method_43443` | 存在 |
| 新索引入口 | — | `method_60829(class_9799$class_9800)` |

替换类 `MixinVertexBuffer` 同时 redirect 三个入口；逻辑保持上游：

- `usage == 35044`（STATIC）或 `!fast_buffer_upload` 或数据比上次大 → `glBufferData`（重新分配）；
- 否则 → `glBufferSubData(target, 0, data)` 复用更大的 dynamic buffer；
- 加了一个低频证据计数器 `[mcbridge-port] fast-buffer-upload subdata count=…`（1/2/3/每 1000 次）。

## 压力场景

`ColdWorldVertex`：80 个 `NoAI/NoGravity/Invulnerable/Silent` 盔甲架，5×4×4 网格，位于出生点前方；
数据包 `p178-vertex`：

- `gamerule doDaylightCycle false`、`time set 6000`、`doWeatherCycle false`、`weather clear`、
  `randomTickSpeed 0`、`sendCommandFeedback false`；
- 每 tick `tp @a 17.5 66.0 70.5 0.0 0.0` 锁定相机（否则鼠标焦点会让 A/B 画面旋转，像素对比无意义）；
- 挖空前方 box，盔甲架悬空可见。

截图通过 `PrintWindow(PW_RENDERFULLCONTENT)` + 进程 PID 匹配窗口（此前按标题匹配会误抓浏览器；
p175 runner 也同步了 PID/PrintWindow/客户区截图）。

## 结果

四阶段：`off1`、`off2`（同 off jar 对照）、`on1`、`on2`（同 on jar 稳定性）。每阶段都是全新世界、
同一相机、截图后 terminate。

| 指标 | 结果 |
|---|---|
| off 侧 fast 标记 | 0 / 0 |
| on 侧 fast 标记 | 60 / 79 行；最高 `subdata count=57000` / `76000` |
| off/off 对照像素差 | `0.002142`（2107 px，mean 0.0750） |
| on/on 稳定性像素差 | `0.002077`（2043 px，mean 0.0747） |
| off/on 像素差 | **`0.0000874`**（86 px，mean 0.00304） |
| GL/mixin 错误 | 无（`GL_INVALID` / `OpenGL error` / Mixin apply / crash 均为空） |

off/off 与 on/on 的残差来自十字准星处的一个盔甲架（基线 run-to-run 变化）；`compare-off-off2.png`
和 `compare-on-on2.png` 是同形状残差，而 `off1` vs `on1` 只有 86 个像素不同。因此 on/off 的差异
**没有超过 off/off 基线**，不是 fast path 引入的新视觉回归。

最终 on jar（与 A/B on jar 字节一致）：
`ImmediatelyFast-ported.jar` sha256 `fdde23e1…e3e2d`；off jar `f0f7fa8e…a8`。

审计：`listed=37 inert=2 problems=2`（剩余 `MixinBufferBuilder`、`MixinFontManager`），
`--allow-inert` → `problems=0`；桥一致性 `problems=0`（19 个 canonical class）。

## 规则

`rules/fabric-1.21.1/immediatelyfast-batching-port.json` 新增：

- `mixinConfigAdditions`：`fast_buffer_upload.MixinVertexBuffer`；
- `mixinClassReplacements`：上述类的 1.21.1 替换（`alsoEmbed` 空）。

## 未验证 / 诚实限制

- **不宣称性能收益**：本测试只证明 fast path 执行且没有视觉/GL 回归；没有帧率基准；
- 场景是 80 个盔甲架的合成压力，不是完整整合包/真实地形流式加载；
- 只测了 NVIDIA RTX 5050 一台机器；shader pack（Iris）下未重跑；
- 长时间 soak、GL 驱动差异、`fast_buffer_upload=false` 的运行期切换未测；
- 截图 helper 的 PrintWindow/PID 改动是本轮为了证据可靠性做的工具修复，已在代码中。

## 复现

```text
python runs/p178-vertex-upload/make_world.py
python runs/p178-vertex-upload/run_ab.py
```

`run_ab.py` 默认使用：

- `.build/ImmediatelyFast-port-off.jar`：主规则**去掉**两条
  `immediatelyfast/vertex-buffer-*` 记录后的补丁 jar（p178 前状态，sha256 `f0f7fa8e…`）；
- `.build/ImmediatelyFast-vertex-on.jar`：含 VertexBuffer mixin 的 jar；p178 当时的 A/B 用它跑
  （sha256 `fdde23e1…`）。p181 之后主规则产物加了 map 生命周期证据标记和 closed 守卫，当前
  `ImmediatelyFast-ported.jar` 是 `7141abdc…`，但 `fast_buffer_upload` 逻辑未变，p178 的 A/B
  结论仍适用。

补丁命令与 p175 README 相同；把 off 规则 JSON 的 `mixinConfigAdditions` /
`mixinClassReplacements` 中 `immediatelyfast/vertex-buffer-config` 和
`immediatelyfast/vertex-buffer-mixin` 两条删掉即可得到 off jar。
