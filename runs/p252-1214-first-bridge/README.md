# p252 — 1.21.4 的第一个真实桥与第一条描述符规则（B03 第二刀）

日期：2026-11-03。这是 p250 里 9 个 `descriptor-changed` 的第一个落地：把 1.20.1 的
九宫格贴图调用接到一个 **1.21.4 专属桥**上。没有启动游戏，所以渲染是否正确仍未验证。

## 1. 这条路的两个新东西

**（一）直接匹配原始 jar，不经过 CenturyBridge。**
1.21.1 的那条规则匹配的是引擎生成的 tombstone（`centurybridge/gen/Tombstones_*`）。本轮改为
直接匹配原始调用：

```
invokevirtual net/minecraft/class_332.method_48587 (Lnet/minecraft/class_2960;IIIIIIIIIIII)V
```

这意味着**不需要先跑引擎**也能对原始 1.20.1 jar 生效——对已经有原始 jar 的调用方是实质差别。

**（二）桥按目标隔离。**
`targets/fabric-1.21.4.json` 新增 `pipeline.bridgeSources`，
`build_bridges.py` 只编该目标声明的源码目录（这里是 `java/src/bridge-1214/java`），
不再无脑编译 1.21.1 的 34 个桥源。

## 2. 桥为什么必须重写

| | 1.21.1 | 1.21.4 |
|---|---|---|
| `class_332.method_25293` | `(id, x, y, width, height, u, v, regionW, regionH, texW, texH)` | `(Function, id, x, y, u, v, width, height, regionW, regionH, texW, texH, color)` |

两处变化：第一个参数多了 `Function<Identifier, RenderType>`，且 **`u`/`v` 移到了
`width`/`height` 前面**。后者是容易搞错的地方——照抄参数顺序会得到一个能编译、但贴图错位的桥。

解析器用 `class_1921.method_62277` = 1.21.4 的 `RenderType.guiTextured(Identifier)`
（`javap` 实测：`public static class_1921 method_62277(class_2960)`），最后那个 int 传 `-1`
（无染色）。

## 3. 实测（`tools/run_1214_first_bridge.py`）

| 检查 | 期望 | 实测 |
|---|---|---|
| 桥编译产物 class major | 全 65 | 全 65 |
| 规则在**原始 jar**上命中 | 1 次 | 1 次 |
| 桥类被嵌入产物 | 是 | 是 |
| 源侧调用 `method_48587` | 是 | 是 |
| 补丁后调用桥 | 是 | 是 |
| **旧调用消失** | 是 | 是 |

调用点前后（同一条指令、同一个偏移）：

```
before  60: invokevirtual #48  // net/minecraft/class_332.method_48587:(Lclass_2960;IIIIIIIIIIII)V
after   60: invokestatic  #48  // top/mcbridge1201/bridge/DrawContextTextureBridge1214.drawNineSliced:
                               //   (Lclass_332;Lclass_2960;IIIIIIIIIIII)V
```

`invokevirtual` → `invokestatic` 后，原来的 receiver 正好成为桥的第一个参数，**栈形状不变**，
所以不需要重排局部变量。这是现有 `methodRedirects` 的机制，本轮只是第一次用在真实样本上。

## 4. 边界

- **没有启动 1.21.4**：桥能编译、调用被正确重定向，但"九宫格画出来对不对"**未验证**。
  参数顺序、`-1` 染色、`guiTextured` 的选择都只有静态依据。
- 只处理**一条调用**：ironchests 在 1.21.4 还有另外 20 项断裂（p250 分类）未动。
- 桥只嵌入主类；`bridge-shim` 编译产物不嵌入（1.21.4 的 fabric-api 自带那些类型）。
- 目标桥源码目录是**白名单**：只编 `bridge-1214`，意味着 1.21.1 的 33 个桥目前对 1.21.4
  不可用——这是有意的隔离，不是遗漏。
