# p118 — 全量冷安装 + 真进世界（1.21.1 原版）

日期：2026-10-22。目标：不再只做“文件链抽样”，而是从**空目录**完整安装 1.21.1（全部 assets），
再真正进入一个世界。全部测试数据都在 D 盘（`work` 已 junction 到 `D:\mcbridge-data\work`），
证据拷出后实例已删除。

## 1. 全量冷安装

```text
python launcher/mclaunch.py install 1.21.1 <root> vanilla   # 实际由 work/tmp 包装脚本记录进度
```

| 指标 | 值 |
|---|---:|
| 总耗时 | **115.0 s** |
| 落盘总字节 | **933,579,822**（≈890 MB） |
| assets 完成数 | **3911 / 3911** |
| 唯一资源对象 | 3888（索引里存在同 hash 多别名） |
| 文件总数 | 3998 |
| 保留窗口内失败/重试 | 0 / 0（`DOWNLOAD_EVENTS` 只保留最近 400 条，见限制） |
| 总下载事件（保留窗口） | 400 |

`install.log` 是每 15 秒的快照（phase / done / total / bytes / speed / source）。

## 2. 进世界

- 冷安装本身没有存档，于是把本仓库已有的 **1.21.1 服务端世界**
  （`work/instances/fabric-1.21.1-server/world`，7.3 MB，4 个 region 文件）拷到
  `<root>/saves/ColdWorld`；
- 用 `--quickPlaySingleplayer ColdWorld` 直接进世界；
- **第一次失败**：卡在首次启动的“无障碍引导”界面（`debug-30s` 阶段看到的菜单），
  quickPlay 不生效；写入 `options.txt` 关闭引导后重来：

  ```text
  onboardAccessibility:false
  skipMultiplayerWarning:true
  ```

- 第二次成功，日志标记：

  ```text
  [Server thread/INFO]: Starting integrated minecraft server version 1.21.1
  [Server thread/INFO]: Preparing start region for dimension minecraft:overworld
  [Server thread/INFO]: ColdWorldUser joined the game
  ```

- 截图 `world.png`：窗口标题 `Minecraft 1.21.1 - Singleplayer`，HUD（生命/饥饿/物品栏）与地形
  可见，右下角还有“Move with WASD”教程提示——是真正的游戏内画面。

## 3. 证据

| 文件 | 内容 |
|---|---|
| `install-summary.json` | 安装耗时/字节/资源数/最终进度快照 |
| `install.log` | 安装期间每 15s 的进度快照 |
| `launch.log` | 成功进世界的客户端日志（含 integrated server 与 join 标记） |
| `world-result.json` | 标记提取结果（world_loaded / integrated_server / spawn_prepared） |
| `world.png` | 游戏内截图 |

## 4. 清理

- 证据拷出后删除整个 `<root>`（**890.6 MB**）；`root_cleaned_after_evidence: true`；
- `work` 在 D 盘，C 盘只增加了几百 KB 的证据文件。

## 5. 限制（如实）

- 只验证 **原版 1.21.1**；Fabric/Forge/NeoForge 的全量安装未在本 run 重跑；
- 世界是“服务端生成后拷入客户端”的，不是客户端新建世界流程；进入后只观察了画面与 join 日志，
  **没有**做长时间游玩、存档写回重进、多人等契约；
- `DOWNLOAD_EVENTS` 是 400 条环形缓冲，`failures/retries=0` 只代表**保留窗口**内为 0；
  整个安装没有抛异常（`ok=true`），但逐次尝试的完整统计没有全部留下；
- 首次启动引导会阻断 quickPlay，这是 1.21.1 客户端行为，不是本工具缺陷；脚本已用
  `options.txt` 规避。
