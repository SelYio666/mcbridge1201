# p267 — p250 的 "member-removed" 里只有 4 条真删

日期：2026-11-04。p250 把 ironchests 的 6 个成员判为 1.21.4 移除。逐条回到两套 intermediary
映射重新判定后：**4 条真删，2 条其实只是描述符变了**。

## 1. 修正结果

| 成员 | 调用点 owner（p250 记的） | 实际声明在 | 1.21.4 判定 |
|---|---|---|---|
| `field_11456` | `class_2464` | `class_2464` | **removed** |
| `method_29236` | `class_1269` | `class_1269` | **removed** |
| `method_39281` | `class_1936` | `class_1936` | **removed** |
| `method_24076` | `class_4722` | `class_4722` | **removed** |
| `method_9559` | `class_2237` | **`class_4970`** | **descriptor-changed**（6 参 → 8 参）|
| `method_26226` | `class_2680` | **`class_4970$class_4971`** | **descriptor-changed**（2 参 → 1 参）|

计数：`{removed: 4, descriptor-changed: 2}`。

## 2. p250 为什么判错

它记录的是**调用点看到的 owner**（`class_2237`、`class_2680`），但成员声明在父类
（`class_4970` 及其内部类）。查询逻辑是「(owner, name, desc) 精确匹配，否则算没了」，
**不爬继承链**——于是"声明在父类"和"描述符变了"两种情形都被记成"移除"。

javap 直接确认：

```
protected net.minecraft.class_2680 method_9559(8 个参数)     ← 1.21.4 里还在
public net.minecraft.class_243 method_26226(net.minecraft.class_2338)  ← 还在
```

## 3. 这对剩余工作意味着什么

**形状变了，不只是数量少了**：

- 2 条描述符变化 → 属于 `callSiteAdaptations` / `signatureAdaptations` 的领域（规则能处理），
  不需要手写桥；
- 4 条真删 → 仍然需要手写桥或明确降级：
  - `field_11456`（`RenderShape` 的某个常量）——1.21.4 里该 official 名被别的东西占用
    （`MapCodec`），常量本身没了；
  - `method_29236`（`InteractionResult` 的一个静态方法）——1.21.4 里连 official 名都不存在；
  - `method_39281`——official 名被 record 组件占用；
  - `method_24076`（`Sheets` 的一个静态方法）——不存在。

## 4. 教训

**"查不到"和"不存在"不是一回事。** 成员解析要按 JVMS 的规则爬继承链（这正是 p255 那个
JVM 测试在做的事）；只看声明类会把"父类里的成员"和"签名变化"都误报成删除。

这类误报的代价是**方向性的**：它让剩余工作量看起来比实际更大、形状更糟（"6 个都要手写桥"
vs "4 个手写 + 2 个改规则"）。

## 5. 边界

- 只做了映射与声明的静态查询，没有 patch、没有运行。
- 4 条真删里，本轮**没有**为任何一条写桥——只确认了"确实没有替代"。
- 2 条描述符变化也**还没有**写规则。
