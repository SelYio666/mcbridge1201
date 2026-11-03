# p264 — ThreadLocal 生命周期的测试（泄漏会让下一个注册拿到错的 id）

日期：2026-11-03。`RegistryKeyContext` 的上下文是唯一"设计上承重、零测试覆盖"的地方：
如果它泄漏，**下一次注册会用到上一个模组的 id**——这是数据损坏，不是外观问题。

本回合补了 4 个用例，全部通过。

## 1. 测什么

| 用例 | 断言 |
|---|---|
| 正常 | supplier 运行期间能看到 pending id；返回后**清空** |
| 抛异常 | supplier 抛异常后仍然**清空**（这正是把 set 放进 try/finally 的原因）|
| 嵌套 | 内层注册看到内层 id，结束后**恢复外层**而不是清空；外层结束后清空 |
| 线程隔离 | 另一个线程**看不到**本线程的上下文 |

第 3 条是重点：清空是最容易写错的版本，它会让"外层注册"在下一次 `settings()` 时丢掉 key。

## 2. 三个踩到的坑（都值得记下来）

**（一）lambda 不能抛受检异常。** `Supplier.get()` 不声明 checked 异常，而反射调用会抛
`Exception`——测试里用 `unchecked(...)` 包装，否则编译就过不去。

**（二）`BuiltInRegistries` 静态初始化需要游戏。** 第一版用
`class_7923.field_41178` 取 `Registry<Item>`，测试直接 `ExceptionInInitializerError`。
本轮只测 ThreadLocal，不测 `settings()` 的 key 注入，所以 registry 传 `null` 就够——
`getWithKey` 只把它存进上下文，不读它。

**（三）1.21.4 的 `Identifier` 构造器私有化了**，改用静态工厂 `method_60655(ns, path)`；
而且 path 只允许小写（`mainThread` 会抛 "Non [a-z0-9/._-] character"）。

这三条都写进测试注释里，因为下一个人还会踩。

## 3. 实现方式

测试不用 MC 运行时：`URLClassLoader` 加载 **编译好的桥 + 1.21.4 stub + 依赖 jar**，
反射调用、反射读私有 `PENDING` 字段。缺 `work/` 资源时 `assumeTrue` **跳过**，不假装通过。

## 4. 结论

- 上下文在正常/异常/嵌套/跨线程四种情形下的清理语义**成立**。
- 全套单测 **65/65**（原 61 + 新 4）。

## 5. 边界

- **`settings()` 的 key 注入本身没有测**：本轮只覆盖上下文的生命周期，没有断言
  "Settings 上真的挂到了正确的 RegistryKey"。那条需要能构造 `Registry` 实例，本机做不到。
- 依赖 `work/` 下的桥产物与 stub，**干净 checkout 会跳过**——所以它不算门禁的一部分。
- 没有启动 1.21.4；没有并发压测（只有"另一个线程看不到"这一条隔离性断言）。
