# 转换规则

每条规则绑定精确的 `(owner, name, descriptor)` 与目标版本，必须有 id、能力声明、风险和证据。不做“按名字猜”的匹配。

## 应用方式

```powershell
mcbridge1201 patch --in <converted.jar> --out <patched.jar> \
  --rules rules/fabric-1.21.1/container.json \
  --client-jar work/target/client-1.21.1.jar \
  --mappings work/target/intermediary-1.21.1-v2.jar \
  --lib <datafixerupper.jar>
```

- 递归处理嵌套 jar（JiJ）。
- `--client-jar/--mappings/--lib` 可选；提供时额外做 **常量池种类修正**：1.20.5 之后部分类型（如 `com.mojang.serialization.DataResult`）从 class 变成 interface，旧字节码的 `Methodref` 必须改成 `InterfaceMethodref`，方法句柄（`MethodHandle` 常量/indy 参数）同样要改。
- 输出确定性：entry 时间戳固定为 0；修补会使签名失效，因此删除 `META-INF/*.SF|RSA|DSA|EC`。

## 字段重定向 schema

```json
{
  "schemaVersion": "0.1-draft",
  "target": "fabric-1.21.1",
  "fieldRedirects": [
    {
      "id": "itempredicate.any.static-field",
      "sourceOwner": "net/minecraft/class_2073",
      "sourceName": "field_9640",
      "sourceDesc": "Lnet/minecraft/class_2073;",
      "bridgeClass": "top/mcbridge1201/bridge/ItemPredicateAny",
      "bridgeMethod": "any",
      "bridgeDesc": "()Lnet/minecraft/class_2073;",
      "capability": "item.predicate.any",
      "risk": "low",
      "evidence": "为什么这个替换在语义上成立，以及触发它的真实崩溃"
    }
  ]
}
```

桥类由 `BridgeGenerator` 用 ASM 生成并嵌入输出 jar，因此规则不依赖额外安装的桥 mod。

## 现有规则

| id | 目标 | 语义依据 | 状态 |
|---|---|---|---|
| `itempredicate.any.static-field` | `ItemPredicate.ANY` → 空谓词 | 1.20.1 的 ANY 匹配所有物品；1.21.1 的空 `ItemPredicate` 同样匹配所有 | 已应用，ironchests 入口点因此通过 |
| `codec.dispatch.mapcodec-shape` | `Codec.dispatch` 第二参数返回 MapCodec | 1.20.5 引入 MapCodec；桥用 `MapCodec.assumeMapUnsafe` 包装 | 已应用 2 处；`assumeMapUnsafe` 在 `MapCodec$7` 处 NPE，需要更强的适配器 |
| `itempredicate.fromjson.static` | `ItemPredicate.fromJson` 的 tombstone 调用（MethodHandle） | 1.21.1 用 `ItemPredicate.CODEC.parse(JsonOps.INSTANCE, json).result().orElse(null)` 重建 | 已应用 1 处 |
| `constant-kind-fix(-handle)` | class→interface 的常量池种类 | 1.20.5 的 DFU 接口化 | 已应用 123 + 3 处 |

规则匹配还支持 `MethodHandle`（lambda 实现）——CenturyBridge 的 tombstone 经常以句柄形式出现，不是直接 `invokestatic`。
