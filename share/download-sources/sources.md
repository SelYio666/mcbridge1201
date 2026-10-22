# Minecraft 下载源速查（1.20.1 / 1.21.1）

> 公开下载入口整理，方便排查下载失败。不含任何游戏/模组文件。整理于 2026-10-22。

## Mojang 官方

| 用途 | 地址 |
|---|---|
| 版本清单 | https://piston-meta.mojang.com/mc/game/version_manifest_v2.json |
| 版本 JSON / 客户端 jar | 清单里该版本的 `url`；jar 在 `downloads.client.url` |
| 库 | https://libraries.minecraft.net/ （完整路径以版本 JSON 的 `libraries[].downloads.artifact.url` 为准） |
| 资源 | https://resources.download.minecraft.net/<hash前2位>/<hash> |
| Java 运行时清单 | https://launchermeta.mojang.com/v1/products/java-runtime/2ec0cc96c44e5a76b9c8b7c39df7210883d12871/all.json |

## 加载器

**Fabric**

```
版本列表     https://meta.fabricmc.net/v2/versions/loader/<MC版本>
安装 profile https://meta.fabricmc.net/v2/versions/loader/<MC版本>/<loader版本>/profile/json
Maven        https://maven.fabricmc.net/
```

**Forge**

```
推荐版本     https://files.minecraftforge.net/net/minecraftforge/forge/promotions_slim.json
安装器       https://maven.minecraftforge.net/net/minecraftforge/forge/<MC>-<forge版本>/forge-<MC>-<forge版本>-installer.jar
```

**NeoForge**

```
版本列表 API https://maven.neoforged.net/api/maven/versions/releases/net/neoforged/neoforge
安装器       https://maven.neoforged.net/releases/net/neoforged/neoforge/<版本>/neoforge-<版本>-installer.jar
```

## 国内镜像（第三方，非官方）

BMCLAPI 社区镜像，官方超时时兜底；速度与同步不保证。

```
资源   https://bmclapi2.bangbang93.com/assets/<hash前2位>/<hash>
Maven  https://bmclapi2.bangbang93.com/maven/<maven 相对路径>
```

## 实测状态（2026-10-22）

| 源 | 状态 |
|---|---|
| piston-meta 版本清单 | 可用 |
| resources 资源对象 | 可用 |
| meta.fabricmc.net | 可用 |
| Forge promotions | 可用 |
| launchermeta JVM 清单 | 可用 |
| BMCLAPI Maven | 可用 |
| BMCLAPI 资源 / 清单 | 波动：连续两次运行一次超时、一次通过 |
| libraries.minecraft.net | 按版本 JSON 完整路径可用（实测 206）；自拼路径可能 404 |
| maven.neoforged.net API | 间歇超时（本次复现；重试/换 urllib/稍后） |

## 校验

官方文件带 sha1，下载后 `Get-FileHash -Algorithm SHA1` 或 `sha1sum` 比对；资源对象按
`objects/<hash前2位>/<hash>` 存放，路径即校验值。

## 声明

仅收集公开地址，不提供、不托管、不分发游戏文件或模组 jar。请遵守 Minecraft EULA 与各镜像条款。
