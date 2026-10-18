# 支持矩阵（生成物）

目标：Fabric 1.21.1（loader 0.19.5，Fabric API 0.102.0+1.21.1）。来源：Minecraft 1.20.1。

| 样本 | 加载器 | 静态判定 | 缺类 | 缺成员 | 描述符变 | API 缺失 | 源索引确认 | 运行时阶段 |
|---|---|---|---|---|---|---|---|---|
| appleskin-fabric-mc1.20.1-2.5.2.jar | fabric | blocked_static | 0 | 11 | 14 | 1 | 27/27 | 未运行 |
| create-1.20.1-6.0.8.jar | forge | wrong_loader | 0 | 0 | 0 | 0 | 0/0 | 未运行 |
| curios-forge-5.14.1+1.20.1.jar | forge | wrong_loader | 0 | 0 | 0 | 0 | 0/0 | 未运行 |
| ironchests-5.0.2-fabric.jar | fabric | blocked_static | 1 | 20 | 19 | 7 | 52/52 | CONTRACT_PASSED（服务端命令范围） |
| jei-1.20.1-forge-15.71.0.224.jar | forge | wrong_loader | 0 | 0 | 0 | 0 | 0/0 | 未运行 |
| journeymap-forge-1.20.1-6.0.7.jar | forge | wrong_loader | 0 | 0 | 0 | 0 | 0/0 | 未运行 |
| lithium-fabric-mc1.20.1-0.11.4.jar | fabric | blocked_static | 1 | 7 | 6 | 0 | 13/14 | BOOTED（专用服务端 Done，世界加载/保存；chunk access 已移植，优化减少；与 ironchests 联合容器契约通过；无 lithium 玩法/客户端；2 条 mixinStrip；见 runs/p13-chunk-port/、runs/p14-lithium-ironchests/） |
| modmenu-7.2.2.jar | fabric | blocked_static | 4 | 7 | 14 | 0 | 24/25 | 未运行 |
| Patchouli-1.20.1-85-FORGE.jar | forge | wrong_loader | 0 | 0 | 0 | 0 | 0/0 | 未运行 |
| trashslot-fabric-1.20.1-15.1.5.jar | fabric | blocked_static | 0 | 2 | 0 | 0 | 2/2 | 未运行 |

分母：每份样本各自的静态问题条数；运行时阶段只对实际启动过的样本填写。
“未运行”不代表通过。
