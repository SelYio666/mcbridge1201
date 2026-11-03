# p248 — 1.21.4 注册键缺口测绘（B03 前置）

日期：2026-11-03。这是 **B03（注册与资源适配）的前置测量**，不是 B03 本身：
本回合没有转换任何 jar、没有写规则、没有启动游戏。它只回答一个问题——
「1.20.1 的注册点长什么样，1.21.4 要求的那个调用到底缺在哪」。

## 1. 缺口是什么性质

1.21.2 起 block/item 的 settings 在注册时**必须**预先带上注册键，否则
`NullPointerException: Item id not set`（[官方说明](https://fabricmc.net/2024/10/14/1212.html)）。

这对转换器是一种**新类别**：不是"引用了错误的成员"，而是**少了一个从未发出的调用**。
现有规则类型都是围绕"改一处已有引用"设计的：

| 规则类型 | 为什么表达不了这个缺口 |
|---|---|
| `callSiteAdaptations` | 没有可改的调用点：1.20.1 代码从未调用过 key setter |
| `constructorRedirects` | 构造器参数里没有 key；key 要从后面 register 用到的 id 推出来 |
| `bodyRedirects` | 会把整段主体换掉，而这里需要的是**在中间插入**一条调用 |

## 2. 实测（`tools/scan_registration_sites.py`）

目标侧（用 `javap` 直接读 1.21.4 stub）：

```
class_1792$class_1793.method_63686 (Lnet/minecraft/class_5321;)Lnet/minecraft/class_1792$class_1793;
class_1792$class_1793.method_60745 (Lnet/minecraft/class_5321;)Lnet/minecraft/class_9793;
```

`method_63686` 就是 `Settings#registryKey(RegistryKey<Item>)`——要注入的那一个。

源侧（1.20.1 输入）：

| 输入 | class 数 | 直接 register | 注册包装器 | Item.Settings | 已调用目标 setter | **缺口类** |
|---|---:|---:|---:|---:|---:|---:|
| `fixtures/source-fabric-1.20.1` | 6 | 1 | 0 | 1 | 0 | **1** |
| `ironchests-5.0.2`（含嵌套 jar） | 206 | 2 | 15 | 6 | 0 | **1** |

四项检查全过：目标存在该 setter、描述符是 `RegistryKey` 重载、源侧从不调用它、缺口在至少一个输入里真实存在。

### 一个把结论改正的发现

第一版扫描器只认 `class_2378.method_10230` 并且只看外层 jar，结论是
**ironchests 的 register 调用数 = 0**——也就是"这个真实样本没有注册点"。

那是错的。下钻 `META-INF/jars/` 后的真相是：ironchests 通过
`com.teamresourceful.resourcefullib.common.registry.ResourcefulRegistries.create(Registry, String)`
创建注册包装器（15 个类用到它），真正的 `register` 在**嵌套 jar 的 ResourcefulLib 里**：

```
METHOD com/teamresourceful/resourcefullib/common/registry/ResourcefulRegistries
       create (Lnet/minecraft/class_2378;Ljava/lang/String;)Lcom/teamresourceful/resourcefullib/common/registry/ResourcefulRegistry;
```

所以「注册形态」至少两种：直接 `Registry.register` 与第三方包装器；
**缺口定位必须下钻 JiJ，否则真实模组会被判成"没有注册"**。这条已经写进脚本的模式集。

顺带一个对实现有利的线索：包装器形态下 `create(registry, modid)` 拿得到 registry，
`register(name, ...)` 拿得到 name，于是 key 可以在包装器内部由 `(registry, modid+name)` 派生——
比"在调用方做数据流追踪"简单得多。

## 3. 规则草案（未实现）

`result.json` 里的 `ruleDraft` 记录了拟议形态：一种 `registrationSiteRewrite`，
匹配"值由同方法内构造的 Settings 产生、随后被 register"的组合，改写为带 key 的桥调用。
它需要三个前置：

1. 能把 register 调用与被注册的构造关联起来的字节码数据流；
2. 能区分 registry 种类（item/block/entity）以选择 `RegistryKeys.*`；
3. 对"值来自字段持有者"的情况做决定（fixture 外的常见形态）。

明确标注：`status: draft_only_not_implemented`。

## 4. 边界

- **没有转换**：`patch` 未运行，没有产物。
- **没有规则**：仓库里不存在 `registrationSiteRewrite` 这个类型，草案不代表已有能力。
- **没有游戏**：`Item id not set` 这类 NPE 只有 1.21.4 实例能证伪；本回合给出的只是
  "目标有这个 setter / 源没有调用它"的静态事实。
- **扫描的判据是常量池子串**，不做控制流：它回答"这个类里有没有这两种东西"，
  不回答"这两条指令是否在同一方法、是否真的相邻"。作为缺口测绘够用，作为规则生成输入不够。
- 只扫了 fixture 与 ironchests 两个输入，没有扩大到 corpus 的其余 8 份样本。
