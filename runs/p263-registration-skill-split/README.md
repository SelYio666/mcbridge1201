# p263 — 两条注册键规则分工（不再竞争）

日期：2026-11-03。p260 撤回规则的理由之一是它和 `registrationKeys` 在同一处打架。
本回合把两条路径**分开**，并顺带发现一个会让产物损坏的匹配范围问题。

## 1. 分工

| 场景 | 谁负责 | 为什么 |
|---|---|---|
| settings 构造与 `Registry.register` **同方法**（fixture 的 `bootstrap`） | `registrationKeys` | 它能看到 id，在构造后注入 key |
| settings 在 **lambda 里**构造、id 在包装器栈上（ironchests 经 ResourcefulLib） | `registry-key-context` | 它借 `Supplier.get` 的上下文传 id |

实现上给两条规则各加了一道"让路"机制：

- `constructorRedirects` 新增 `skipWhenCallsOwner/Name`：**方法里出现注册调用就跳过**这条重定向；
- `insertBeforeCalls` 新增 `onlyInClass` / `onlyInMethodName` / `onlyInMethodDesc`：把插入限定到具体方法。

## 2. 那个 32 次命中是个警告

先按"全局匹配 `Supplier.get()`"跑 ironchests，结果：

```
rule resourcefullib.supplier.get-with-registry-context applied 32 time(s)
```

**32 个位置里只有 1 个**（`FabricRegistryEntry.of`）的局部变量 0/1 真的是
`(Registry, Identifier)`。其余 31 处的 local 0/1 是别的类型，而规则会照发
`getWithKey(Supplier, class_2378, class_2960)`——**字节码无法通过校验**。

所以加了 `onlyInClass` 之后：

| 输入 | supplier 规则 | context 规则 | registrationKeys |
|---|---:|---:|---:|
| fixture（bootstrap 内有 register） | — | **0**（让路）| **1** |
| ironchests（lambda 内构造） | **1**（只在那一个方法）| **8** | 0 |

fixture 上 `classes changed=1`、只命中 `registration-keys`；ironchests 上 `classes changed=10`，
两条规则各管各的。**没有一处是两边同时改的。**

## 3. 教训

**插入式规则必须限定范围**。它的参数来自局部变量槽，而"同一个被调用者"在不同类里
局部变量布局完全不同。全局匹配看起来命中了 32 次是"效果好"，实际是 31 个潜在的验证失败。

这条和 p261 的"目标成员校验"是同一类思路：**规则越宽，越需要证明它落对了地方**。

## 3b. 作用域现在有单元用例（2026-11-04，`runs/p272`）

`onlyInClass` / `onlyInMethodName` 之前只在真实 jar 上验过（命中 32 → 1）。现在 `JarPatcherInsertBeforeCallTest` 里有三个隔离用例：
匹配时触发、限定在别的类时不触发、限定在别的方法时不触发。

## 4. 回归

- 单测 **61/61**
- p249 / p252 / p254 / p256 / p257 全部 PASS
- `check_rule_targets.py`：6 个规则文件、3 组目标引用、**0 missing**

## 5. 边界

- **端到端仍未验证**：没有在 1.21.4 上跑过"包装器注册 → 上下文注入 → 键生效"这条链；
  `RegistryKeyContext` 的 ThreadLocal 生命周期（try/finally、嵌套恢复）**没有测试覆盖**。
- 没有启动 1.21.4。
- `onlyInMethodDesc` 里的描述符是按 javap 抄的；如果 ResourcefulLib 换版本，这个 scope 会失配
  （表现为规则命中 0 次，而不是改错东西——这是有意的默认）。
