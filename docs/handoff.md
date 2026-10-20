# 交接摘要（一页）


更新（2026-10-20 21:05）：**刷怪压力 soak 通过**（40 僵尸，3 分钟 20.00 TPS）。红石/多小时未测。证据 `runs/p103-mob-soak/`。
更新（2026-10-20 20:35）：**FallingTree 倒树通过**（20→16，持斧生存）。补 `ItemStack.damage` 桥；空手会 INVALID_PLAYER_STATE 是 mod 行为。证据 `runs/p102-fallingtree-fell/`。
更新（2026-10-20 20:10）：**FallingTree 倒树根因缩小**：事件已投递、LOGS 标签正常，缺口在 `TreeHandler.breakTree`。证据 `runs/p102-fallingtree-fell/`。
更新（2026-10-20 20:05）：**FallingTree 单块破坏过、倒树未触发**。补 2 个 tombstone 桥；倒树失败已如实记录在 `runs/p102-fallingtree-fell/`。
更新（2026-10-20 19:30）：**AppleSkin 真实悬停通过**（tooltip 追加 FoodOverlay 行）。修复状态效果 API ×4、ItemTooltipCallback 桥、bodyRedirect 静态方法。证据 `runs/p101-appleskin-hover/`。
更新（2026-10-20 14:15）：**Shulker 真实悬停通过**（tooltip `Diamond x5`）。修复二参 Identifier 私有构造；单机水下出生/端间模组一致性已记录。证据 `runs/p100-shulker-hover/`。
更新（2026-10-20 14:05）：**Lithium 4 分钟 soak 通过**（20.00 TPS，堆平稳）。刷怪/红石/长时未测。证据 `runs/p99-lithium-soak/`。
更新（2026-10-20 13:50）：**桥一致性门禁通过**（六件套 problems=0）。新增检查脚本；补丁器覆盖同名桥、保留未引用桥。证据 `runs/p98-bridge-consistency/`。
更新（2026-10-20 13:40）：**Mod Menu 配置界面通过**（10 行选项可见）。修复 OptionsList 旧构造、Screen 排除加 class_4667、旧 renderBackground 转发。证据 `runs/p97-modmenu-config/`。
更新（2026-10-20 13:20）：**多模组联合冒烟通过**（进世界无崩溃）。修 Shulker sendPacket/writeNbt/末影箱 NBT。注意桥内嵌冲突：多 jar 需同 bridge-dir 重打。证据 `runs/p96-combined-smoke/`。
更新（2026-10-20 13:10）：**搜索过滤通过**（"menu" 8→2，Showing 2/8）。真实输入与配置界面仍未测。
更新（2026-10-20 12:55）：**滚动联动通过**（scroll 0→40、rowTop 71→31，两张截图）。真实滚轮/搜索/配置界面未测。
更新（2026-10-20 12:50）：**Mod Menu 列表行可见**。修复 Screen.render 误改名 + 新增 bodyRedirects（列表/描述面板用 DrawContext 重绘）。背景简化为填充；洋红棋盘=本机缺材质。证据 `runs/p94-modmenu-list/`。
更新（2026-10-20 12:40）：**Mod Menu 列表截图**：界面/按钮正常、8 条目存在，但列表行未绘制（视觉缺陷）；截图 `runs/p94-modmenu-list/modmenu-list.png`，下一步查行/滚动几何。
更新（2026-10-20 12:35）：**AppleSkin tooltip 状态效果路径通过**（契约级，金苹果 size=2）。真实悬停未测。证据 `runs/p95-appleskin-tooltip/`。
更新（2026-10-20 12:25）：**Mod Menu 模组列表通过（日志级）**。打开并稳定 60 tick；新增纹理按钮重绘桥、TextWidget tick 桥、构造重定向宽松回退、列表父类桥。未测：截图、滚动/搜索/配置交互。证据 `runs/p94-modmenu-list/`。
更新（2026-10-20 12:15）：**Mod Menu 列表未通过**，已推进到 `class_344` 纹理按钮构造阻断；本轮新增通用覆盖改名/重复丢弃、超类替换与两个列表桥。证据 `runs/p94-modmenu-list/`。
更新（2026-10-20 11:30）：**Clumps 合并通过（companion 桥）**。`java/src/compat-clumps/` 每 20 tick 合并 2 格内的球，写和 + discard；实测 3+7→10。tick 驱动、固定 2 格、不读配置。证据 `runs/p93-clumps-merge/`。
更新（2026-10-19 23:35）：**Clumps 仍待办**。服务端 tick 合并桥草拟在 `work/tmp/clumpsmerge`；经验球可 summon，但实体查询/重启后为 0，fixture 未收敛，未声称通过。
更新（2026-10-19 23:25）：**Mod Menu 主菜单通过**。私有字段反射 + `methodRenames`（render→renderWidget），无 ICCE/IllegalAccess，新崩溃无；模组列表未打开。证据 `runs/p92-modmenu/`。
更新（2026-10-19 23:15）：**ShulkerBoxTooltip provider 契约通过**。旧 NBT 路径桥到 `CONTAINER`、`DyeColor` 颜色分量补桥、网络 shim 补齐；探针 `diamondCount=5 expected=5`，真实悬停未测。证据 `runs/p91-shulker-provider/`。
更新（2026-10-19 23:10）：**FallingTree 入服通过**。服务端旧 send 走桥、客户端 receiver 收包，`TestPlayer joined the game`；砍树未测。证据 `runs/p90-fallingtree-join/`。
更新（2026-10-19 23:05）：**AppleSkin 食物 tombstone 已修**。食物组件桥把 5 个旧 API 映射到 `DataComponentTypes.FOOD`；HUD 不再抛 tombstone，仅剩原版材质缓存告警。证据 `runs/p89-legacy-networking/appleskin-hud.log`。
更新（2026-10-19 22:50）：**补两处验证**。区块压力测试的 `# >` 回显假阳性现在有 `--self-test` 负向用例；新增 `tools/check_hashes.py`，清单 525 项全部通过，`hash_evidence.py` 遇缺失文件直接失败。
更新（2026-10-19 22:50）：**旧 Fabric 网络桥落地**。`FabricLegacyNetworking` + `PlayChannelHandler` shim + 单参 `Identifier` 规则；AppleSkin 初始化/发包已过（HUD 仍撞 tombstone），FallingTree 客户端可启动，入服未复测。证据 `runs/p89-legacy-networking/`。
更新（2026-10-19 22:35）：**扩模 6 个样本：5 阻断、1 仅启动**。分析器多 loader 误判已修（Fabric entrypoints 优先，闲置 Forge 引用不再判 `wrong_loader`），`gradle test installDist` 23/23。缺口与所需规则见 `docs/mod-expansion.md`，报告与证据在 `runs/p88-mod-expansion/`。
更新（2026-10-19 21:50）：**独立测试报告的 6 项已修**。文档改成三段流水线（原始 jar 不能直接 patch）、区块压力测试过滤 `# >` 回显、`run_server.py` 传播 JVM 退出码、Lithium 降级写进文档、双客户端探针自铺平台并守卫 54 槽、SHA256SUMS 重生成。报告与日志在 `runs/p87-independent-test/`。`verify_evidence.py` 仍 passed。
更新（2026-10-19 22:10）：**empty-trash 按键诊断**。注册 Balm `ScreenKeyEvent.Press.Post` 监听后注入 Delete，`KEY_EVENT` 计数 0；P83 ESC 能生效，说明按键到 GLFW 但没进 Balm 屏幕按键事件。物理 empty 暂无法用现有 harness 验证，动作本身 P65 已过。证据 `runs/p86-empty-hover/`。
更新（2026-10-19 22:00）：**empty-trash 悬停后仍失败**。已量出矩形 `(227,207)-(258,231)`、scale=3、物理 (1176,873)；四种 Delete 组合都没清空。坐标已排除，剩下是注入路径/配置/修饰键问题。empty 本身 P65 已通过。证据 `runs/p86-empty-hover/`。
更新（2026-10-19 21:45）：**empty-trash 真实按键受阻**。只注入 Shift+Delete 时 trash 仍是 5，说明需要鼠标悬停；需先算组件矩形再移动鼠标。empty 本身已在 P65 通过。证据 `runs/p85-empty-key/`。
更新（2026-10-19 21:35）：**lithium TPS 采样通过**。289/289 区块、1200 tick/59.92s → 20.03 TPS，无掉 tick。单次 60 秒、无玩家/生物，属于健全性检查。证据 `runs/p84-lithium-tps/`。
更新（2026-10-19 21:25）：**物理 ESC 通过**。清空坐标→放新箱子→玩家传送到箱子旁后，开箱 `screen=ChestScreen slots=90`；系统注入 ESC 后 `screen=class_433 slots=46`、服务端 `slots=46`。真实按键关箱成功。证据 `runs/p83-esc-teleport/`。
更新（2026-10-19 21:15）：**物理 ESC 二次尝试仍受阻**。真实 `onUse` 返回 `CONSUME`，但 80 tick 内菜单关闭、客户端无 `ChestScreen`；两种开屏路径在当前世界状态都留不住菜单。物理 ESC 仍未验证，需重置世界/位置或查 `canUse`。证据 `runs/p82-esc-onuse/`。
更新（2026-10-19 21:05）：**物理 ESC 尝试受阻**。provider 开箱后菜单立刻被服务端关掉（tick 160 已 46 格），客户端无 ChestScreen，按键注入无对象；物理 ESC 仍未验证，下一步用真实 `onUse` 开屏。证据 `runs/p81-esc-key/`。
更新（2026-10-19 20:55）：**干净同 tick 并发验证完成**。清空双方背包与箱子后同 tick 点击：两端都预测 7，100 tick 后赢家仍 7、输家被纠正为 0；服务端 `DED_TOTAL chest=0 host=0 guest=7`，总数 7 无复制。证据 `runs/p80-two-client-clean/`。
更新（2026-10-19 20:45）：**同 tick 并发点击不复制**。两端同在世界时间 2700 点击，均预测 `slot54=7`，但服务端只给一人（`DED_TOTAL chest=0 host=0 guest=7`），总数 7；第二次跑看到失败方被服务端槽位更新纠正（`LAN_POST slot54=0`），但该次库存未清空，需干净重测。证据 `runs/p79-two-client-simultaneous/`。
更新（2026-10-19 20:35）：**两客户端操作同一箱子不复制**。访客取走 7 钻石后主机再操作：服务端 `DED_TOTAL chest=0 hostSlot54=0 guestSlot54=7`，总数仍为 7。属于先后争用，非同一 tick 并发。证据 `runs/p78-two-client-race/`。
更新（2026-10-19 20:25）：**双端关屏通过**。`setScreen(null)` 只关客户端（服务端仍 90 格）；改用 `Screen.close()`（`method_25419`）后两端 `LAN_CLOSED slots=46`，服务端 tick 420/520 均 `hostSlots=46 guestSlots=46`。真实 ESC 键未测。证据 `runs/p77-two-client-close/`。
更新（2026-10-19 20:10）：**双客户端取放往返通过**。访客从箱子取走 7 钻石（`LAN_GUEST_MOVED slot0=air slot54=7`），服务端 `DED_AFTER slot0=air`，主机再开箱看到空箱（`LAN_MENU player=HostA slot0=air`）。中途修复“离箱 11 格菜单失效导致越界崩溃”。证据 `runs/p76-two-client-move/`。
更新（2026-10-19 20:00）：**双客户端同步通过（专用服务器）**。RL 移植拆成服务端安全的 `RawChannel` + 仅客户端 `FabricClientPacketHelper`，修掉专用服务器 `NoClassDefFoundError class_638`；专用服务器（online-mode=false）+ 两个离线客户端：`DED_SET slot0=7`、`DED_OPEN OptionalInt[1] guest=GuestB`、访客 `LAN_GUEST_MENU slot0=7 minecraft:diamond`。证据 `runs/p75-two-client-server/`。
更新（2026-10-19 19:45）：**双客户端尝试被 LAN 正版验证阻断**。主机开 LAN 25566 成功，离线访客连入即被踢，画面 `Failed to log in: Invalid session`；写 `server.properties online-mode=false` 无效。下一步：专用服务器（online-mode=false）+ 把 RL 移植拆成服务端安全部分。证据 `runs/p74-two-client/`。
更新（2026-10-19 19:25）：**lithium 玩法冒烟通过**。强制加载 9×9 区块 `81/81`，放石头并用 `ServerPlayerGameMode.destroyBlock` 真实破坏（stone → air），服务端 tick 160/240 存活、客户端 `LITHIUM_CLIENT_ALIVE`，无崩溃。冒烟，不含 TPS/长期稳定性。证据 `runs/p73-lithium-play/`。
更新（2026-10-19 19:20）：**IronChests 背景改为真实九宫格纹理**。上游源码确认 `GeneratedScreenRenderer` 调用 1.20.1 `drawNineSlicedTexture(...4,4,4,4,256,256,0,0)`；桥改为 9 次 `method_25293`，截图显示带边框的浅色面板，不再纯灰。重建脚本默认先重编桥（修掉 stale bridge 的 `NoSuchMethodError`），sha256 `20864ad9…`。证据 `runs/p72-ironchests-nine-slice/`。
更新（2026-10-19 12:45）：**IronChests 修复流水线入仓**。`tools/rebuild_ironchests_client.py` 把「NBT 规则 → 替换内嵌 ResourcefulLib → 屏幕/纹理规则」串成一条命令，RL helper 源码收进 `java/src/nested/java/`；重建产物 sha256 与手工验证版一致（`c0589eeb…`），冒烟测试 GUI 打开、放入 50 钻石、关箱重开仍在。证据 `runs/p71-rebuild-pipeline/`。
更新（2026-10-19 12:25）：**修复关箱重开清空 + S2C 同步通过**。补测关箱发现重开清空箱子；根因是转换器对调了 `readNbt`/`writeNbt` 的方法体（`method_11007` 实际写、`method_11014` 实际清空并读），而 P67 的桥按名字调反。对调 `IronChestsNbtBridge` 后：关箱后 25 仍在，重开服务端/客户端都是 25。P67 已加更正说明。证据 `runs/p70-ironchests-persist/`。
更新（2026-10-19 12:20）：**IronChests GUI 交互通过**。客户端 `clickSlot` 把 25 钻石从热键栏 81 放进箱子槽 0，再取回到背包槽 54；服务端同一菜单 tick 220/260/300 的状态与客户端一致，无复制/丢失。证据 `runs/p69-ironchests-interaction/`。
更新（2026-10-19 12:15）：**IronChests 箱子 GUI 通过**。服务端 `IRONCHESTS_USE result=CONSUME`，客户端 `IRONCHESTS_SCREEN=tech.thatgravyboat.ironchests.client.ChestScreen`；截图有 Iron Chest 标题、9×6 格子、背包和物品，无崩溃。为此移植了内嵌 ResourcefulLib 2.0.6 服务端网络（work-only）、修正 channel 公式为 `ironchests:main/sync`，并加了两条规则（`screen.render-background-one-arg`、`ironchests.draw-texture`）。背景纯灰是旧纹理参数只映射前 10 个。证据 `runs/p68-ironchests-gui/`。
更新（2026-10-19 08:10）：**TrashSlot 不是普通 handler slot**。probe 取到 `TrashSlotSlot` 坐标 `152,165`、component anchor `231,211`，但 `handler.field_7761.indexOf(trash)=-1`（46 个槽），说明垃圾桶是客户端自定义 component 绘制/拦截，普通 `clickSlot` 无法定位。P56 的点击/拖拽失败由此解释；实际转移仍未完成。证据 `runs/p58-trash-click/`。
更新（2026-10-19 01:25，修正）：**trash 重进为空是 TrashSlot 登录重置**。`setTrashItem` 同会话读回 5 钻石，live `BalmData/TrashSlot` 也是 `{count:5,id:"minecraft:diamond"}`；但 `PlayerLoginEvent` 显式把 trash 设为 `ItemStack.EMPTY`，所以重进为空不能证明 NBT 桥失败。P57 原结论已修正；GUI 拖放仍是独立未解问题。证据 `runs/p57-trash-persist/`。
更新（2026-10-19 01:15）：**真实 ItemStack 进入背包，trash 拖放未成功**。probe 给玩家 5 钻石，背包显示正常；点击/拖拽到 TrashSlot 按钮后物品仍停在光标，trash 未接收，logs 无异常。这是未验证项，不声称通过。证据 `runs/p56-client-item/`。
更新（2026-10-19 01:05）：**背包 + TrashSlot GUI 渲染**。客户端 probe 自动打开 `InventoryScreen`；截图显示原版背包和右下角 TrashSlot 按钮。空 trash 按钮点击无可见变化；物品移入/移出、持久化、容器 GUI、同步仍未验证。证据 `runs/p55-client-gui/`。
更新（2026-10-19 01:00）：**客户端进入世界并渲染**。补 `LithiumVarIntBridge` 后世界生成通过；客户端登录单人世界、渲染地形/HUD（`runs/p54-client-lithium/world.png`）。证据 `runs/p54-client-lithium/`。
更新（2026-10-19 00:55）：**世界加入越过 Balm payload**。修正旧 Balm writer 参数顺序 `(packet, buf)` 后，`trash_slot_content` 编码错误消失；客户端进入世界生成，新阻断为 lithium `class_2540.method_10815` tombstone（`VarInt.getByteSize`）。证据 `runs/p53-client-world/`。
更新（2026-10-19 00:50）：**客户端到达主菜单**。PCL Fabric 1.21.1 客户端加载五模组并进入主菜单；Balm 客户端初始化、ironchests 模型桥已补。进入世界时 `BalmNetworking.sendTo` payload 编码仍失败（`class_9129` vs `MessageTrashSlotContent`），未进入世界/GUI。证据 `runs/p52-client-balm/`。
更新（2026-10-19 00:40）：**ResourcefulLib 客户端网络桥生效**。重写嵌套 RL 2.0.6 的 `FabricClientPacketHelper` 到 1.21.1 Payload API；客户端越过 ironchests **main** 入口点，新阻断为 `ModelLoadingRegistry` 缺失与 `BalmClient.initialize(String,Runnable)` 缺失。证据 `runs/p51-client-bridge/`。
更新（2026-10-19 00:35）：**首次真实客户端运行（PCL）**。1.21.1 Fabric 客户端已装；五模组加载后 ironchests 入口点崩溃于 `ClientPlayNetworking$PlayChannelHandler` 缺失（旧 ResourcefulLib 2.0.6 客户端网络 API）。换 ResourcefulLib 3.0.12 又缺 `PacketHandler`。这是新的真实客户端阻断。证据 `runs/p50-client/`。
更新（2026-10-19 00:05）：**`@At.ordinal` 提取**。`Injection.atOrdinal` + `mixinAtOrdinals`；lithium 86 at-targets 中 10 个带 ordinal；只提取，不做匹配指令计数/越界校验；测试 **22/22**。证据 `runs/p49-at-ordinal/`。
更新（2026-10-18 23:59）：**nested jar mixin 展开**。scanner 读取 `META-INF/jars/*.jar` 内的 `.mixins.json`；ironchests P26 从 0/0 变为 1 mixin/1 injection（unresolved 0），lithium 保持 202/214/86/3；测试 **21/21**。证据 `runs/p48-nested-mixins/`。
更新（2026-10-18 23:58）：**字段 `@At` 解析测试**。FIELD target `class_14.field_99:L...;` 的 owner/name/desc/`atTargetField` 全部断言；测试 **20/20**。证据 `runs/p47-field-at/`。
更新（2026-10-18 23:55）：**多 method injection 数组回归测试**。`method_59`+`method_60` 产生两条 Injection 且共享 at-target；测试 **19/19**。证据 `runs/p46-multi-method/`。
更新（2026-10-18 23:50）：**剩余工作边界**。新增 `docs/remaining-work.md`：服务端/静态工作已覆盖；客户端 GUI/网络/多人因无 client fixture 未执行；chunk 优化、nested mixin 静态分析、Forge 分析列为非阻塞后续。没有新增“客户端通过”声明。
更新（2026-10-18 23:45）：**三样本 bundle profile**。`profiles/bundle-all-three__fabric-1.21.1.json`，`passed_within_scope`：coexistence + 容器 5/5 + 225-chunk stress + CodecDispatch probe；client/GUI pending。证据 `profiles/`。
更新（2026-10-18 23:42）：**三样本 + CodecDispatch probe 通过**。all-three 实例加载 P37 probe，`Done (5.425s)`、`CODEC_DISPATCH_PROBE_OK`；安全 Codec 包装在三样本同服时仍正常。证据 `runs/p43-all-three-codec/`。
更新（2026-10-18 23:55）：**三样本同服 chunk 压力通过**。all-three 实例 225 chunks、远角方块 save/restart 断言全 true，两进程 exit 0；证据 `runs/p42-all-three-chunk/`。
更新（2026-10-18 23:50）：**三样本同服通过**。lithium + ironchests(P26) + trashslot(P29)/Balm 21 同实例 `Done (4.632s)`；容器契约两次重启 5/5。证据 `runs/p41-all-three/`。
更新（2026-10-18 23:45）：**证据总校验扩展**。`tools/verify_evidence.py` 增加 P35/P36 at-target 计数和 lithium profile 检查；全部 checks true，exit 0。证据 `runs/p40-verify-extended/`。
更新（2026-10-18 23:40）：**证据总校验工具**。`tools/verify_evidence.py` 检查 18 个测试、P14/P24/P26/P27/P33/P37/P38 证据及“无 tracked jar”；`passed=true`，exit 0。证据 `runs/p39-verify-evidence/`。
更新（2026-10-18 23:35）：**P29 client bridge 的 BytecodeVerify**。`trashslot-client-aw.jar` 顶层 47 classes / 0 failures，覆盖 `BalmNetworkingBridge`/`$Payload`/`$Client`；客户端分支仍未执行。证据 `runs/p38-client-bv/`。
更新（2026-10-18 23:30）：**CodecDispatch 语义 probe 通过**。`RecordCodecBuilder` 的 `Box(int a)` 经 `CodecDispatch.dispatch` encode 为 `{"a":1,"type":"k"}`、decode 回 `Box(1)`，日志 `CODEC_DISPATCH_PROBE_OK`；服务端 `Done (4.847s)`、exit 0。直接验证 P26 安全 MapCodec 包装。证据 `runs/p37-codec-probe/`。
更新（2026-10-18 23:25）：**at-target 补丁前后对照**。转换件 `214 injections / 86 at-targets / 3 unresolved`，补丁件 `209 / 84 / 0`；P11/P13 清掉已知构造器，at-target 解析保持一致。证据 `runs/p36-patched-at/`。
更新（2026-10-18 23:20）：**refmap `@At` 目标解析**。`atRawTarget` 也走 refmap，lithium 的 `mixinAtTargets` 从 0 提升到 **86**，unresolved 仍 3（已知构造器），没有新增 false positive；测试 18/18。证据 `runs/p35-at-refmap/`。
更新（2026-10-18 23:15）：**`@At` 目标提取（保守）**。scanner 解析 `@Inject` 等的 `@At(value,target)`，analyzer 对 intermediary 的 INVOKE/FIELD 目标做存在性检查；转换后 lithium `mixinInjections=214`、`mixinAtTargets=0`（Yarn/refmap 跳过）、3 个已知构造器 unresolved；测试 18/18。证据 `runs/p34-at-targets/`。
更新（2026-10-18 23:10）：**trashslot 三个包 codec 全部往返通过**。`MessageTrashSlotClick`/`MessageTrashSlotContent` 的空栈与 5 钻石、`MessageDeleteFromSlot(3,true)` 均通过（`TRASHSLOT_ALL_CODEC_OK`）；服务端 `Done (4.993s)`、exit 0。仍不含客户端投递/GUI。证据 `runs/p33-all-packets/`。
更新（2026-10-18 23:05）：**trashslot packet codec 往返通过**。服务器内 probe 对空栈与 5 钻石执行 `MessageTrashSlotClick.encode/decode`，断言 empty/count/item 全部通过（`TRASHSLOT_CODEC_OK`）；服务端 `Done (5.025s)`、exit 0。仍不含客户端网络投递。证据 `runs/p32-trashslot-codec/`。
更新（2026-10-18 23:00）：**CodecDispatch 选择回归测试**。验证 `--bridge-dir` 提供的 javac `CodecDispatch` 优先于 generated fallback，且不嵌入 `CodecDispatch$Adapter`；测试 18/18。证据 `runs/p31-codec-selection/`。
更新（2026-10-18 22:55）：**lithium / trashslot 兼容档案**。新增两份 `booted_within_scope` profile 与 `profiles/README.md` 索引；lithium 记录 boot/225-chunk/combined，trashslot 记录原生 Balm 21 与 boot/网络；客户端/玩法仍 pending。证据 `profiles/`。
更新（2026-10-18 22:50）：**trashslot clientbound receiver 已接入**。`BalmNetworkingBridge$Client` 在客户端用 `ClientPlayNetworking.registerGlobalReceiver` 调用旧 `BiConsumer<Player,T>`；服务端反射跳过，仍 `Done (4.894s)`。客户端分支未执行，不能宣称客户端通过；证据 `runs/p29-client-receiver/`。
更新（2026-10-18 22:45）：**P26 安全 Codec 构建的 BytecodeVerify**。顶层 73 classes / 0 failures，nested ResourcefulLib 142 classes / 0 failures，exit 0；运行侧由 P26/P27 契约覆盖。证据 `runs/p28-codec-verify/`。
更新（2026-10-18 22:40）：**安全 CodecDispatch 联合回归**。lithium + P26 `ironchests-safe-aw.jar` 同实例，两进程容器契约 5/5、两次 `Done`、exit 0；P26 未破坏 P14 共存路径。证据 `runs/p27-combined-safe-codec/`。
更新（2026-10-18 22:35）：**Codec.dispatch 安全 MapCodec 适配**。活跃路径改用 javac `CodecDispatch`，用 `MapCodec.of(MapEncoder, MapDecoder)` 真正包装旧 `Codec`，不再依赖 `assumeMapUnsafe`；ironchests 容器契约 5/5，测试 17/17。证据 `runs/p26-codec-safe/`。
更新（2026-10-18 22:30）：**Codec.dispatch 空结果保护**。`CodecDispatch$Guard` 把 `assumeMapUnsafe` 的 null-success 变成 `DataResult.error`；重新补丁 ironchests 后容器契约 5/5 通过，测试 17/17。证据 `runs/p25-codec-guard/`。
更新（2026-10-18 22:25）：**chunk 压力测试工具化**。新增 `tools/run_chunk_stress.py`，两进程 force-load 225 chunks、远角方块、save/restart、`execute if block` 断言；本次 `chunksMarked=225`、`STRESS_OK_A/B`、`passed=true`，exit 0。证据 `runs/p24-chunk-stress-tool/`。
更新（2026-10-18 22:20）：**lithium chunk-access 压力测试通过**。224 个 forceload chunk（`[-7,-7]` 到 `[7,7]`），远角钻石/绿宝石块 save/restart 后均被 `execute if block` 读回（`STRESS_OK_A/B`），两次 `Done`、exit 0。证据 `runs/p23-chunk-stress/`。
更新（2026-10-18 22:15）：**注入目标静态检查交叉验证**。同一 1.21.1 索引下：转换后 lithium `214/3`（3 个 unresolved 正是 P11/P13 的构造器阻断），补丁后 lithium `209/0`；Balm `43/0`，ironchests/trashslot 顶层无 mixin。证据 `runs/p22-cross-analyze/`。
更新（2026-10-18 22:10）：**refmap 注入目标解析**。读取 mixin config 的 refmap，把命名目标映射到 `Lowner;method(desc)`（含构造器），`Analyzer` 静态复现 lithium 的 3 个已知构造器变化：`class_4180`(POI)、`class_3610`(FluidState)、`class_1927`(Explosion)。测试 16/16；证据 `runs/p21-refmap/`。
更新（2026-10-18 22:05）：**Mixin 注入目标提取 + 保守校验**。`ArtifactScanner` 解析 `@Inject`/`@Redirect` 等的 `method` 目标，`Analyzer` 新增 `mixinInjections`/`mixinInjectionsUnresolved`；只校验 intermediary 名称+描述符，命名/refmap/构造器跳过。测试 15/15；转换后 lithium 实跑 214 个注入目标、0 unresolved；证据 `runs/p20-mixin-inject/`。
更新（2026-10-18 21:55）：**BytecodeVerify 已跑**。对 ironchests/lithium/trashslot 三个补丁 jar 顶层类验证 650 classes / 0 failures；对 ironchests nested ResourcefulLib 验证 141 classes / 0 failures。仅栈深度校验；证据 `runs/p19-bytecode-verify/`。
更新（2026-10-18 21:52）：**嵌套 jar 的桥改为按 jar 嵌入**。`JarPatcher` 为每层 jar 记录 `used` 集合并把生成的/javac 桥嵌入使用它的那个 jar；新增 synthetic nested jar 测试，ironchests 重补丁只在 nested ResourcefulLib jar 多出 `IdentifierFactory`，容器契约 5/5 仍通过。测试 13/13；证据 `runs/p18-nested-bridges/`。
更新（2026-10-18 21:50）：**trashslot 到达专用服务端 `Done`**。原生 Balm 21.0.66 + `Balm.initialize` call-site 桥 + 旧 Balm 网络注册 → Fabric `PacketType`/`StreamCodec` 载荷桥 + 4 个 ItemStack/NBT 桥，`Done (4.655s)`，世界加载/保存。仍是 BOOTED，客户端 GUI/网络包往返未验证；证据 `runs/p17-balm-net/`。
更新（2026-10-18 21:45）：**Balm 初始化调用点桥已推进 trashslot，但卡在 Balm 网络 API**。`Balm.initialize(String,Runnable)` → `initialize(String, EmptyLoadContext, Runnable)` 的 call-site 桥生效，旧的初始化 `NoSuchMethodError` 消失；下一失败是 `BalmNetworking.registerServerboundPacket(Identifier, Class, BiConsumer, Function, BiConsumer)`，Balm 21 已改为 `PacketType`/`StreamCodec` 载荷注册。仍未 boot，规则保持 prepared/unverified；证据 `runs/p16-balm/`。
更新（2026-10-18 21:40）：**第三个样本 trashslot 受阻于 Balm/Fabric networking**。trashslot 自身 4 个 ItemStack/NBT tombstone 已写桥并 patch，但依赖 Balm：转换 Balm 7.3.44 后卡在 Fabric API 移除的 `ServerPlayNetworking$PlayChannelHandler`，原生 Balm 21.0.66 又缺 `Balm.initialize(String,Runnable)`。未 boot；规则标记 prepared/unverified，证据 `runs/p15-trashslot/`。
更新（2026-10-18 21:35）：**lithium + ironchests 联合容器契约通过**。同一 Fabric 1.21.1 专用服务端实例加载两份转换件，两进程放置/插入/NBT/重启读回 5 钻石全部通过；P13 chunk access 移植没有破坏容器持久化，两样本可共存。证据 `runs/p14-lithium-ironchests/`，说明 `docs/baseline.md` §7.20。仍不含 lithium 自身玩法/客户端。
更新（2026-10-18 21:25）：**lithium 到达专用服务端 `Done`**。`ServerChunkManagerMixin` 的 chunk access 实现移植到 1.21.1 `ChunkResult`/`GenerationChunkHolder` API（保留 mixin 类与 `@Overwrite`，不是 strip），启动 `Done (4.772s)`，世界加载/保存，命令 chunk 探针通过。规则 `mixinClassReplacements`，证据 `runs/p13-chunk-port/`，说明 `docs/baseline.md` §7.19。仍只是 BOOTED，不是玩法/客户端兼容。
更新（2026-10-18 21:05）：**Mixin 目标描述符适配已实现**。lithium 的 `ExplosionMixin` 与 POI `SerializingRegionBasedStorageMixin` 两处 `@Inject` 目标签名迁移成功，服务端推进到 chunk access 的 `ChunkHolderExtended` cast；下一阻断是 1.21.1 chunk API 形状 + CenturyBridge tombstone，不是描述符。规则 `rules/fabric-1.21.1/lithium.json`，证据 `runs/p11-lithium-explosion/`，说明 `docs/baseline.md` §7.18。
更新（2026-10-18 20:50）：**调用点签名适配已实现并用 lithium 的 `class_14.method_59` 验收**。补丁后 `NoSuchMethodError` 消失，启动推进到下一失败（`world.explosions.ExplosionMixin` 的注入目标变化）。规则 `rules/fabric-1.21.1/lithium.json`，证据 `runs/p10-lithium-signature/`，说明 `docs/baseline.md` §7.17。
更新（2026-10-18 20:20）：`ItemPredicate.fromJson` 的降级已消除——改用反射读取 BuiltInRegistries 并通过 RegistryOps 解析 codec，启动日志不再出现 falling back，兼容档案已升为 `passed_within_scope`（服务端范围）。
日期：2026-10-18。给下一个接手者：先读这页，再按需展开 `docs/baseline.md`。

## 现在能做什么

在 `work/instances/fabric-1.21.1-server`（Fabric 1.21.1 + Fabric API 0.102.0）里：

- 归档的 `ironchests 5.0.2`（1.20.1 原始 jar）经过 CenturyBridge 转换 + 本项目规则补丁后，**随服务端启动并加载世界**（`Done (1.2s)`，42 个模组）。
- **容器契约通过**（服务端命令范围）：放置 `ironchests:iron_chest` → 插入 5 钻石 → NBT 出现 `Items` → 进程重启 → 读回 `count=5`。一键：

```powershell
$env:JAVA_HOME='C:\Users\27682\Documents\新建文件夹\.toolchain\jdk'
python tools/run_contract.py --instance work/instances/fabric-1.21.1-server --out runs/contract
```

## 关键机制（都已实现并实测）

| 机制 | 位置 | 作用 |
|---|---|---|
| body-preserving 重映射 | `java/.../remap/JarRemapper.java` | 解决本机 Fabric remap 被 zipfs 只读阻塞；方法/字段/lambda 名称传播 |
| 规则引擎 | `java/.../rules/` | 字段/方法/句柄重定向、构造器重定向、常量池种类修正、**调用点签名适配**（javac 桥）、覆写签名适配、**Mixin 目标描述符适配**（append/replace + refmap）、**Mixin 实现类替换**（API 形状变化）、**mixin 降级** |
| 规则包 | `rules/fabric-1.21.1/container.json`、`lithium.json` | ironchests 7 条 + lithium 调用点/2 条 Mixin 目标规则，全部有触发证据 |
| 降级档案 | `rules/fabric-1.21.1/lithium-degraded.json` | mixin 剥离，显式记录 |
| 契约脚本 | `tools/run_contract.py` | 两进程重启 + 断言 + verdict.json |
| 报表 | `tools/build_reports.py` | 生成兼容档案 + 支持矩阵 |

## 当前最高证据阶段

`CONTRACT_PASSED`（**仅限**专用服务端 + 命令 API + 单进程重启）。ironchests 兼容档案状态 `passed_within_scope`；lithium 到达专用服务端 `BOOTED`（`Done (4.772s)`），lithium+ironchests 联合容器契约通过；trashslot 也到达专用服务端 `BOOTED`（`Done (4.655s)`，原生 Balm 21 + 载荷桥），但无 lithium/trashslot 自身玩法或客户端契约，lithium 仍有 2 条显式 mixinStrip。

## 未解决（按优先级）

1. **lithium 仅到 BOOTED**：专用服务端 `Done`、世界加载/保存、命令 chunk 探针通过；lithium+ironchests 联合容器契约也通过（§7.20），但没有 lithium 自身玩法、客户端 GUI/渲染或多人同步。2 条显式 `mixinStrips` 仍在，chunk 优化也减少了（旧多入口缓存/off-thread 快路径未重写）。
2. **`mixinClassReplacements` 的覆盖面/优化**：chunk access 已用实现类替换打通；还需验证该模式在更多 API 形状变化上的可维护性，并决定是否重写被放弃的优化。
3. **调用点适配的覆盖面**：已覆盖顶层 jar 的直接调用和 `MethodHandle`；P18 已把桥按 jar 嵌入嵌套 jar（synthetic + ironchests JiJ 回归），可继续覆盖更多样本/多层嵌套/更多句柄形状。
4. **Mixin 目标描述符适配的覆盖面**：已处理 Explosion 与 POI storage；仍需覆盖更多 `@Inject`/`@Redirect`/`@ModifyConstant` 目标变化。
5. **第三个样本 trashslot 仅到 BOOTED**：原生 Balm 21 + 初始化/网络载荷桥 + 4 个 NBT 桥已让专用服务端 `Done`；但无客户端连接，clientbound receiver 未安装，包 encode/decode 与 ItemStack NBT 桥未被玩家动作触发，客户端 GUI/玩法未验证。
6. **客户端侧**：GUI 打开、右键交互、渲染、两个客户端同步。本机无显示验证，需要客户端实例。
7. **Forge 成员级分析**：目前只有命名空间级；需要 tsrg(SRG) + Mojang 映射的联合索引。
8. **`BytecodeVerify`**：已对三个顶层补丁 jar + 一个 nested jar 运行（0 failures，§7.23）；其他 nested jar/客户端路径未覆盖，且仅栈深度校验。
9. **Mixin 注入点级分析**：已提取 `@Inject`/`@Redirect` 的 `method` 目标，支持 refmap 和构造器，并静态复现 lithium 的 3 个已知构造器变化；ordinal/slice/局部变量和非 refmap 命名目标仍未解析。

> 已完成（不要再当未解决）：`ItemPredicate.fromJson` 的 registry-aware 构造（2026-10-18 20:20，profile `passed_within_scope`）；lithium 的 `class_14.method_59` 调用点签名适配（20:50，§7.17）；lithium `ExplosionMixin` + POI storage 的 Mixin 目标描述符适配（21:05，§7.18）；lithium chunk access 的 1.21.1 实现类移植与 `BOOTED`（21:25，§7.19）；lithium+ironchests 联合容器契约（21:35，§7.20）。

## 复现路径（从零）

```powershell
python tools/fetch_target_env.py     # 1.21.1 client jar / mappings / Fabric API / loader
python tools/fetch_corpus.py         # 10 份样本（校验 sha512）
cd java; gradle --no-daemon installDist; cd ..
python tools/setup_server.py --instance work/instances/fabric-1.21.1-server
python tools/remap_server.py --instance work/instances/fabric-1.21.1-server --loader 0.19.5 `
  --mappings work/cb/data/mappings/intermediary-1.21.1.tiny
python tools/run_server.py --instance work/instances/fabric-1.21.1-server --log runs/boot.log
```

转换 ironchests 需要 CenturyBridge 引擎（`work/upstream/src/...`，编译脚本见 `docs/baseline.md` §6），然后：

```powershell
mcbridge1201 patch --in <converted.jar> --out patched.jar --rules rules/fabric-1.21.1/container.json `
  --client-jar work/target/client-1.21.1.jar --mappings work/target/intermediary-1.21.1-v2.jar `
  --lib <datafixerupper.jar>
python tools/inject_aw.py --jar patched.jar --out final.jar --aw rules/fabric-1.21.1/mcbridge.accesswidener
```

lithium 调用点 + Mixin 目标 + chunk access 移植（完整命令和日志见 `runs/p10-lithium-signature/README.md`、`runs/p11-lithium-explosion/README.md`、`runs/p13-chunk-port/README.md`）：

```powershell
python tools/build_bridges.py --stub work/cb/data/jars/client-1.21.1-intermediary.jar `
  --lib work/lib/gson-2.11.0.jar --lib <datafixerupper.jar> --out work/bridges
python tools/build_mixins.py --stub work/remap/server-intermediary.jar `
  --lib <sponge-mixin.jar> --lib work/bridges --out work/mixins
mcbridge1201 patch --in <lithium converted.jar> --out lithium-patched.jar `
  --rules rules/fabric-1.21.1/lithium-degraded.json `
  --rules rules/fabric-1.21.1/lithium.json `
  --bridge-dir work/bridges --bridge-dir work/mixins
```

## 不要做的事

- 不要把 `fromJson` 的全匹配回退当作兼容成功；如果未来重新出现，档案里必须保持 `degraded`。
- 不要用 mixin 剥离掩盖核心逻辑（存档/掉落/同步）。
- 不要分发游戏 jar、模组 jar 或转换件；只分发工具、规则与哈希清单。
- 不要把静态 `ANALYZED` 或 `blocked_static` 写成“可运行”。
