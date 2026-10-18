# P0 引擎选择：Retromod vs CenturyBridge

日期：2026-10-18。依据是 `manifests/upstream.lock.json` 中的精确提交、本轮实际编译/转换结果，以及 `docs/baseline.md` 里的日志。没有跑起来的项目一律写“未验证”，不用作者自报替代。

## 1. 决策

- **首个实际路线**：Fabric 1.20.1 → Fabric 1.21.1。
- **首个引擎**：**CenturyBridge**（`dextawa/CenturyBridge@cf4ebeba2eaaa49d3746162cc2c10b670d681aec`，MIT），作为**研究/转换底座**接入；不把它当成熟产品包装。
- **Retromod**：保留为第二候选，**不 fork**。它的已发布工件是 26.2 Fabric/Quilt（`1.4.0-snapshot.1+26.2-fabric`），与 1.21.1 目标不匹配；其 Maven 源码支持面未在本轮验证。等 1.21.1 或明确的源码构建结果出现再比较。
- **不新造引擎**：CenturyBridge 已经实际产出 ironchests 的 1.21.1 转换件和逐符号账本；在没有复现它的缺口之前另建核心会重复劳动（对应 ADR-0002）。
- **Forge 路线**：不并入本轮。1.20.1 Forge 的 SRG 名与 NeoForge 1.21.1 的 Mojang 名之间需要独立索引，且 Connector 不能反向使用；单列里程碑（对应方案 §7.4）。

## 2. 比较表

| 评价项 | Retromod | CenturyBridge | 仍未知 |
|---|---|---|---|
| 构建复现 | Maven 根 `pom.xml` + `build.sh`；**未构建** | 无构建系统；`javac` 直编；**可编译（46 类）**，但需补上游缺失的 `MixinCheck.java` | Retromod 在 JDK 21 下能否一次构建通过 |
| 目标工件 | 只有 26.2 Fabric/Quilt 预发布产物；**无 1.21.1 工件** | 无 Release；**本轮产出 1.21.1 转换件**（`ok_partial`） | Retromod 源码是否支持 1.21.1 |
| 源码可维护性 | 1320 个源文件、模块化 Maven；未读全 | 14 个引擎源文件 + 分版本 shim 树（`core/shims/<ver>`）；分段 JSON 冻结、可增量 | 上游主干是否接受补丁（未联系作者） |
| 功能语义诚实度 | 技术文档承认“部分旧渲染只能加载、模型可能不显示”；会屏蔽错误 Mixin | 明确区分 `ok`/`ok_partial`/`degraded`，死调用生成 **tombstone（惰性抛错）**，报告逐条标注死在哪一节边界 | 两者都未做运行时行为验证 |
| 扩展难度 | 有逐模组兼容数据库，但扩展点未验证 | 分段链 + shim 树 + wiring JSON，新增目标=加一节；`build.sh` 有 4 道门禁 | 真实桥接工作量（需要写 NBT/组件桥） |
| 依赖处理 | 有版本/加载器识别；细节未验证 | 会改 `fabric.mod.json` 的 minecraft 依赖；**不处理 Fabric API 模块替换** | 重复 mod id、JiJ 递归的完整处理 |
| 验证质量 | README 有验证说明；未复测 | 有 `BytecodeVerify` 数据流校验工具（本轮未编译运行）；作者自报客户端行为链未复现 | 两者都需要本项目独立跑契约 |
| 许可 | MIT | MIT | — |

## 3. 为什么不是“CenturyBridge 已成功”

作者的 1.21.1 案例（ironchests 注册/放置/GUI/存取/退出重进）本轮**没有复现**：本机服务端启动被环境阻塞（`docs/baseline.md` §7），客户端完全没有运行。我们只独立得到：

- `TRANSFORMED`：转换件存在、hash 固定；
- 28 个 tombstone、55 条未记账引用、1 个 class issue、1 个 constructor issue；
- 其中 NBT 家族（`class_1799.method_7948/7969/7980/7985`）与 `class_2586.method_38242` 与本项目静态分析器的结论**互相吻合**（两条独立路径指向同一批跨版本变化），这是目前最强的交叉证据。

## 4. 三个最重要的行为缺口（按优先级）

1. **物品/方块实体 NBT → 数据组件（1.20.5 墙）**
   - 证据：CenturyBridge 把 `class_1799` 的 4 个 NBT 方法、`class_1856/2040/2048/2090/2102/2073` 的 JSON 读写全部 tombstone；本项目静态分析器对 ironchests 报 `method_7948` 14 次、`method_7969` 8 次、`method_7985` 6 次。
   - 影响：容器/箱子类模组的存档与同步直接依赖它；不补就是“能加载、开箱即炸”。
   - 下一步：用 `ItemStack` 的 `getNbt/setNbt/getOrCreateNbt` → `DataComponentMap` 的真实桥，写容器 fixture + ironchests 的单机契约。

2. **Fabric API 自身 API 删除/改名**
   - 证据：`ModelLoadingRegistry` / `ExtraModelProvider` / `BakedModelManagerHelper` 在 1.21.1 Fabric API 不存在；`ServerPlayNetworking.PlayChannelHandler` / `ClientPlayNetworking.PlayChannelHandler` 改名（ironchests 经 ResourcefulLib 的 JiJ 代码命中）。
   - 影响：客户端模型注册与网络通道是容器 GUI 的前置。
   - 下一步：在转换层加“Fabric API 符号重定向表”，并把这 36 条（去重后 7 类 + 5 成员）做成规则。

3. **Mixin 目标存活判定与注入点质量**
   - 证据：lithium 224 个 mixin、create 57 个 mixin 配置；本轮只判断 `@Mixin` 目标**类**是否存在（lithium 命中 1 个消失类），没有判断 `@Inject` 的 method/ordinal/slice 是否仍唯一。
   - 影响：优化器/大型模组的失败通常是“类还在、注入点没了”，属于会静默改行为的类别。
   - 下一步：接 Mixin 注解解析，输出每个注入点的目标方法、匹配数、处置（保留/改写/降级/阻塞）。

## 5. 工程决定

- **离线转换先行**：CenturyBridge 本身就是离线 `convert`，符合 ADR-0003；不改造成运行时自动发现。
- **不复制上游代码进本仓库**：`work/upstream/` 只放快照与许可证；自研部分只有分析器和脚本。若后续要 fork，需先在 `docs/adr` 记录原因、上游同步方式。
- **本地补丁要显式**：`patches/centurybridge/MixinCheck.java` 是为编译而加的空实现，注释标明“不是上游代码、门禁未实现”。任何依赖 mixin-check 的结论都不得引用。
- **目标工件不存在就不下载替代品**：Retromod 的 26.2 工件没有拿来跑 1.21.1。

## 6. 下一条可执行命令

在可写环境（`Files.isWritable` 正常）里：

```powershell
python tools/setup_server.py --instance work/instances/fabric-1.21.1-server
python tools/run_server.py --instance work/instances/fabric-1.21.1-server `
  --log runs/p1-server-baseline/server.log --timeout 300
# 期望：日志出现 "Done ("，脚本自动 stop，退出码 0
```

拿到 `BOOTED` 后，再把 `work/cb/out/ironchests/ironchests-5.0.2-fabric+1.21.1.jar` 放进 `mods/`，用同一脚本记录失败栈；这是“转换件能否被 Loader 接受”的第一条真实证据。然后才进入 NBT→组件的桥实现。
