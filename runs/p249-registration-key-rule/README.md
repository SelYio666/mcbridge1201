# p249 — 第一条 1.21.4 规则：注册键注入（B03 第一刀）

日期：2026-11-03。这是 **B03 的第一个可执行切片**：`rules/fabric-1.21.4/` 从零到第一条规则，
并在 fixture 上验证字节码形态。**没有启动 1.21.4 游戏**，所以这一刀只证明"调用被插进去了"，
不证明"`Item id not set` 消失了"。

## 1. 新规则类型：`registrationKeys`

现有规则类型都是「改一处已有引用」，而注册键缺口是**缺了一个从未发出的调用**
（测量见 `runs/p248-registry-key-gap`）。新增的类型是引擎里第一个**插入指令**的规则：

```jsonc
{
  "id": "1214.item-settings.registry-key",
  "registerOwner": "net/minecraft/class_2378",   // 认证这是注册点，不是任意 settings 使用
  "registerName": "method_10230",
  "settingsClass": "net/minecraft/class_1792$class_1793",
  "settingsCtorDesc": "()V",
  "setterOwner": "net/minecraft/class_1792$class_1793",
  "setterName": "method_63686",                   // 1.21.4 实测存在
  "setterDesc": "(Lnet/minecraft/class_5321;)Lnet/minecraft/class_1792$class_1793;",
  "keyFactoryOwner": "net/minecraft/class_5321",  // RegistryKey.of
  "keyFactoryName": "method_29179",
  "registryKeyOwner": "net/minecraft/class_2378", // Registry#registryKey()
  "registryKeyName": "method_30517"
}
```

注入的指令块（起始栈 `[.., settings]`）：

```
DUP
<重放 registry 加载>
INVOKEVIRTUAL class_2378.method_30517()   // registry 自己的 ResourceKey
<重放 id 加载>
INVOKESTATIC  class_5321.method_29179(...) // RegistryKey.of
INVOKEVIRTUAL class_1792$class_1793.method_63686(...)
POP                                       // 丢掉未带 key 的旧实例
```

结束栈 `[.., keyedSettings]`。**不需要桥**：四个调用点都是 1.21.4 已存在的方法，
所以这条规则不依赖任何 javac 产物。

## 2. 形态约束（宁可不动，也不猜）

只有当以下条件在**同一段直线代码**里同时成立才改写：

1. 有一个 `class_1792$class_1793.<init>()V`；
2. 它之前最近的两个**可重放加载**（`getstatic`/`getfield`/`aload`）分别是 id 与 registry；
3. 之后 `maxDistance`（默认 40）条指令内出现与规则匹配的 `register` 调用；
4. 窗口内遇到 `LabelNode` 就放弃——分支意味着"这段栈"不再是一条直线。

不满足就**保持原样**（表现为规则命中数不足，而不是悄悄产出一个错的东西）。
settings 由辅助方法构造、或值来自字段持有者的情况，本轮一律不处理。

## 3. 实测（`tools/run_registration_rule.py`）

```powershell
$env:JAVA_HOME = "<jdk21>"
python tools\run_registration_rule.py
```

| 检查 | 期望 | 实测 |
|---|---|---|
| 规则命中 | 1 次 | 1 次 |
| 改动类数 | 1 | 1 |
| 源侧是否已调用 setter | 无（-1） | -1 |
| 打补丁后 setter 偏移 | ≥0 | **30** |
| 先有 key 工厂、后有 setter | 是 | 是 |
| 先读 registry 的 ResourceKey、后有工厂 | 是 | 是 |
| setter 在 `class_1792.<init>` 之前 | 是 | 是 |

打补丁后的 `bootstrap()`（节选自 `disassembly-after.txt`）：

```
 9: dup
10: new     class_1792$class_1793
13: dup
14: invokespecial class_1793.<init>:()V
17: dup                                          ← 注入开始
18: getstatic class_7923.field_41178
21: invokevirtual class_2378.method_30517:()Lnet/minecraft/class_5321;
24: getstatic PROBE_ID
27: invokestatic class_5321.method_29179:(...)Lnet/minecraft/class_5321;
30: invokevirtual class_1793.method_63686:(Lnet/minecraft/class_5321;)Lnet/minecraft/class_1793;
33: pop                                          ← 注入结束
34: invokespecial class_1792.<init>:(Lnet/minecraft/class_1792$class_1793;)V
37: invokestatic class_2378.method_10230:(...)
```

顺带确认：`class_2378` 在 1.20.1 与 1.21.4 **都是 interface**，所以 `method_10230` 的
`InterfaceMethodref` 是本来就正确的，不是常量池种类问题。

## 4. 单元测试

`JarPatcherRegistrationKeyTest`（4 个用例，全过）：

- 注册点内联 settings → 注入，且 setter 早于值构造器；
- settings 造了出来但没注册 → **不动**（没有注册证据）；
- 值不是内联构造 → **不动**（没有 settings 可上键）；
- 打过补丁的类仍可被 ASM 解析。

全量单测 52/52（原 48 + 新 4）。

## 5. 边界

- **一条规则不是一次转换**：`targets/fabric-1.21.4.json` 的 `ruleOrder` 现在只有这一条，
  `status` 改为 `rule_package_started`，仍不是支持声明。
- **没有跑 1.21.4**：`Item id not set` 是否消失未验证；这是本轮唯一无法在此环境完成的半验证。
- **只覆盖内联形态**：ironchests 走的是 ResourcefulLib 包装器（见 p248），包装器内部的
  settings 构造还没有对应规则；p247 量出的 21 项新增断裂一处未处理。
- `patch` 用的目标索引来自 `targets/fabric-1.21.4.json`（stub/client/mappings 均在 `work/target`，
  不入库）。干净机器需要先跑 `tools/fetch_target_1214.py` 并 `remap-jar` 生成 stub。
