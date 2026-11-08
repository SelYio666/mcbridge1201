# p256 — VeinMiner 真实玩家挖矿 E2E（p255 边界关闭）

日期：2026-11-09。**结论：真实客户端挖矿触发 vein-mine，16 块煤矿全链破坏，镐耐久恰好
-16，双侧 0 链接错误，pass=true。** VeinMiner 从 p111 的"仅启动"、p251 的"世界加载即崩
→ 修复后 Done"、p255 的"桥探针验证"，到本轮**功能级通过**。

## 设施

- **真实客户端**：复用 PCL 安装的 1.21.1（`%APPDATA%\.minecraft`，只读 junction assets、
  拷贝 libraries/版本/natives 到独立 gameDir），KnotClient 直启 + 离线登录 +
  `--quickPlayMultiplayer` 入服（1.21.1 没有 `--quickPlayServer` 这个旗标）。
- **服务端**：vein-probe-server 实例 = 补丁后的 VeinMiner（p255 两桥）+ p251 的 silk 链
  + FLK + fabric-api。每轮跑前清空 `world/playerdata/*.dat` **和 `*.dat_old`**（服务器会
  回读 dat_old，曾把两轮前死亡的玩家复活成 Health 0 的尸体）。
- **编排**（`drive.py`，单进程双子系统）：服务端 stdin 控制台下发指令；客户端窗口
  TOPMOST+ALT 键前景锁旁路+SendInput（sneak 按住 + LMB 按住 5 秒）。
- **断言全部在服务端**（无像素校验）：柱子（2×2×4 煤矿，16 块）在入服**前**建好；
  玩家 tp 到柱顶、俯视 90°、发钻石镐；挖完 `fill air replace coal_ore` 计数 + 
  `data get SelectedItem` 读耐久组件。

## 结果（logs/、result.json）

```text
TestPlayer logged in at (1.0, 124.0, 1.0)
input: sneak + LMB 5s
VERDICT {"ore_left_of_16": 0, "pickaxe_damage": 16, "server_linkage_errors": 0,
         "client_linkage_errors": 0, "pass": true}
```

- **ore_left_of_16 = 0**：vein-mine 连锁拿走整柱（潜行+挖第一块 → VeinMiner 的
  `beforeBlockBreak` 通过 → `breakAdjusted` 协程破坏全链）；
- **pickaxe_damage = 16**：耐久恰好每块 1 点——1 点来自原版 `mineBlock`，15 点来自
  VeinMiner 的 `damageItem` → **p255 的 `ItemStackHurtAndBreakLegacy` 桥 → 1.21.1 四参
  hurtAndBreak（ServerPlayer 分支）**——即耐久同步与 ITEM_DURABILITY_CHANGED 判据都在
  真实玩家路径上跑过；
- 两侧日志 0 条 NoSuchMethodError/NoSuchFieldError。

## 调试史（全部留痕，与结论一样重要）

1. Knot 类路径缺 `asm-analysis`（用服务端实例的 ow2 全套替换）；
2. 相对 `--gameDir` 被 cwd 拼成 `gameDir/work/e2e/...`（改绝对路径）;
3. 两次 drive 运行重叠，前一台服务器占着 25565（确认无进程后重跑）；
4. `--quickPlayServer` 不是 1.21.1 的旗标（正确是 `--quickPlayMultiplayer`）；accessToken
   传 "0" 让 profile 解析炸（用 UUID 形状的占位符）；
5. 玩家反复出生即死：playerdata 只删 `.dat` 不够——服务器回读 `.dat_old`（里面是两轮前
   的死亡状态）；`doFallDamage` 不是原版 gamerule（静默无效），真正的保护是"入服前建柱
   + 入服立即 tp + 缓降/抗性"；
6. 焦点竞态：`SetForegroundWindow` 间歇被拒（ALT 键前景锁旁路 + 重试解决）；
7. **VeinMiner 默认配置是矿石不是原木**：`beforeBlockBreak` 的门是
   `Block.getDescriptionId()`（翻译键）与 veinBlocks 集合比对——注册 id（
   `minecraft:oak_log`）永远不命中；换翻译键（`block.minecraft.*`）或直接用默认矿石集
   （coal_ore 在默认集里）才触发。手写的 blocks.json/settings.json 走翻译键也验证过
   schema（`LinkedHashSetSerializer(StringSerializer)` + settings 五字段）；
8. **VeinMiner 自己的配置写路径坏了**（每轮启动都会把 settings.json/blocks.json 重建成
   0 字节——encodeToString 静默失败，疑似 kotlinx serializer module 问题）：E2E 依赖
   内置默认值运行；配置写损伤另立后续工单，不与本轮通过混淆。

## 边界（如实）

- 单客户端、单柱子、单一 vein 形状；多人真人同服未覆盖；
- 耐久同步是靠耐久数值（16）间接观测，没有第二客户端看 HUD；
- VeinMiner 配置文件写入损坏是独立遗留问题（可能 1.20.1 原版就坏），本轮不修、不声称修；
- 客户端来自 PCL 安装素材（只读复用），未验证全新下载路径。

## 复现

```text
py -3.12 runs/p256-veinminer-e2e/drive.py --server-instance work/instances/vein-probe-server \
    --client-dir work/e2e/vm-client/gameDir --out runs/p256-veinminer-e2e
# 前置：work/e2e/vm-client/gameDir 由 PCL 素材搭好（versions/libraries 拷贝、assets junction），
# classpath 由 runs/p256-veinminer-e2e/README 描述的 1.21.1.json 解析 + fabric extras。
```
