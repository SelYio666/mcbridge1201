# p252 — 崩溃→规则闭环（compat 方向 B）

日期：2026-11-08。新增 `tools/suggest_from_crash.py`：从服务器/客户端日志或崩溃报告里解析
运行期链路错误（`NoSuchMethodError` / `NoSuchFieldError` / `NoClassDefFoundError` /
`ClassNotFoundException`，带引号与裸签名两种形态都认），把每个符号翻译成内部描述符后
**复用 p251 的映射机械**（suggest_rules.Version + 冲突检查 + ACC_STATIC 接收者判定），
输出候选规则或"已有规则已覆盖"的判定，stdout 直接打印"建议规则 + 证据行"。

```text
python tools/suggest_from_crash.py --log <log> --out <dir> [--rules rules/fabric-1.21.1]
```

处理顺序（与 A 的计划驱动路径同一条流水线）：

1. 先查现有规则：constructorRedirect / callSiteAdaptation / methodRedirect /
   fieldRedirect 的匹配键命中 → `already covered`，不产生草稿；
2. 方法崩溃且 1.21.1 保留同名同 id（只是描述符变了）→ callSiteAdaptation 草稿
   （evidence 引用崩溃行 + 目标新描述符）；
3. 其余走 suggest_missing_member（搬家/改名/Mojang 名延续），全都不认识 → note；
4. 非 MC/Fabric 符号（模组自己的类、第三方库）→ note：**这是依赖或移植问题，
   不该用转换规则掩盖**。

## 验收：真实失败样本，从日志到建议规则全自动

| 输入 | 输出 | 证据 |
|---|---|---|
| `entityculling-identifier-crash.txt`（p111 的真实崩溃：`NoSuchMethodError: 'void net.minecraft.class_2960.<init>(java.lang.String)'`） | **already covered**——命中既有 `identifier-single-arg.json` 的 constructorRedirect（p89 加入，当时正是修这个崩溃） | `suggestions/entityculling-identifier/` |
| `logs/crash-server.log`（p251 的 before：silk-persistence 在世界加载抛 `NoSuchMethodError class_26.method_17924`）+ 当前规则 | **already covered**——命中 p251 新增的 `silk-persistence.json`（崩溃与规则的键逐字节一致） | `suggestions/before7-with-current-rules/` |
| 同一份崩溃日志 + 规则目录**回放到没有 silk 规则的修复前状态**（`work/tmp/rules-replay`，仅去掉 silk-persistence.json） | **自动生成草稿 `computeifabsent.callsite`（callSiteAdaptation，high，bridgeDesc 带接收者）**——与 p251 里人工挑选并实现的规则同 id、同键、同目标描述符 | `suggestions/before7-replay-no-silk-rule/` |

第三行就是"崩溃日志 → 建议规则"的端到端演示：工具自己从日志拿到的 `(owner, name,
desc)` 联接映射后给出的建议，与人工从 analyzer 计划里挑选实现的最终规则完全一致。

## 边界（如实）

- 工具只认四类链路错误；`InvalidMixinException` / `ClassCastException` 等不在本轮
  范围（immediatelyfast-crash.txt 的 `@Overwrite` 描述符错配属于 mixin 迁移，需要
  `mixinCallbackAdaptations` 形状的建议，未做）。
- 崩溃日志里没有描述符的字段错误（`NoSuchFieldError owner.field`）只能按名字+类型
  继续猜，当前会走 missingMember 的 field 分支（需要 desc 才能精确，crash 文本没有
  就如实降置信度/给 note）。
- `ClassNotFoundException` 的 MC 类分支只给"转换/加载器问题"的方向性 note，不产草稿。
- 回放目录是一次性演示输入（`--rules work/tmp/rules-replay`），不入库；正式使用时
  直接指 `rules/fabric-1.21.1`。

## 复现

```text
py -3.12 tools/suggest_from_crash.py --log runs/p252-crash-to-rule/logs/entityculling-identifier-crash.txt --out <out>
py -3.12 tools/suggest_from_crash.py --log runs/p252-crash-to-rule/logs/crash-server.log --out <out>
# 修复前状态回放（去 silk 规则的规则副本由使用者自建）
```
