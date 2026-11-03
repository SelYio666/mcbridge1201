# p254 — ironchests 三处绘制全部改写（B03 第三刀）

日期：2026-11-03。p252 接了九宫格那一处；本回合把另外两个 plain blit 也接上。
ironchests 的绘制路径现在在**原始 1.20.1 jar** 上被完整改写，不经过 CenturyBridge。

仍然没有启动 1.21.4 游戏，所以渲染是否正确未验证。

## 1. 两条新规则

| 规则 | 1.20.1 调用 | 1.21.4 目标 |
|---|---|---|
| `ironchests.blit-region-1214` | `method_25290(tex, x, y, u, v, w, h, regionW, regionH)`（9 参） | 多加 `Function` 首参，其余顺序不变 |
| `ironchests.blit-simple-1214` | `method_25302(tex, x, y, w, h, u, v)`（7 参） | 12 参：resolver + `region` + `texture` 尺寸 |

`blitSimple` 复现的是 1.20.1 便利重载的转发约定：**region = 目标尺寸，texture = 256×256**，
与 `method_25302` 在 1.20.1 内部分发到完整重载时的取值一致。
`blit` 只是补 resolver，参数一一对应。

## 2. 实测（`tools/run_1214_draw_rules.py`，7 项全过）

| 检查 | 期望 | 实测 |
|---|---|---|
| 桥编译 class major | 全 65 | 全 65 |
| 三条规则命中 | 1 / 2 / 3 | 1 / 2 / 3 |
| 改动类数 | 3 | 3 |
| 两个桥嵌入 | 2 | 2 |
| 外层旧调用残留 | 0 | 0 |
| 外层桥调用 | 5 | 5 |
| **嵌套 jar 也被改写** | 是 | 是 |

**6 次命中里有一次在嵌套 jar 里**：`resourcefullib-fabric-1.20-2.0.6.jar!` 的
`com/teamresourceful/resourcefullib/client/components/ImageButton` 也调用 `method_25290`。
补丁把它改写成桥调用，并把 `DrawContextBlitBridge1214` **嵌进了那个嵌套 jar 本身**
（而不是只放外层）——这条路径以前在 `runs/p18-nested-bridges` 建立过，本轮在 1.21.4 上再次验证。

## 3. 一个差点被误报的坑

第一版检查把嵌套 jar 里的"旧方法名出现次数"直接当残留，得到 2 并判 FAIL。
实际是：**桥类自己的常量池里就含 `method_25290`**（它要调用 1.21.4 的新签名）。
排除 `top/mcbridge1201/bridge/` 包之后，残留为 0。

如果没查这一层，就会把一个正确的产物判成坏的——反之，如果只信任"规则命中数"而不看字节码，
也可能漏掉真正的残留。两边都得看。

## 4. 边界

- **256×256 是约定，不是测量**：`blitSimple` 的 texture 尺寸取自 1.20.1 便利重载的转发值。
  如果某个图集大于 256，取样会错；只有游戏能证伪。这条已写进规则 evidence 和 result.json 的
  `openAssumption`。
- **没有启动 1.21.4**：三处绘制都只做到"调用被正确重定向"，画面正确性未验证。
- `class_2769.method_11898`（返回 `List`）、`class_4309.<init>`（换 `Codec` 重载）、
  `BlockStateProperties` 两个字段、6 个类删除，都还没动。
- 桥只覆盖 ironchests 用到的三种形态；别的模组会需要别的重载。
