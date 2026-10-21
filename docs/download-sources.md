# 下载源策略与实测记录

最后更新：2026-10-21。本文回答：**哪些地址有镜像、镜像怎么验证的、失败怎么重试、怎么查
一个文件到底从哪来**。

## 1. 外部实测报告（2026-10-21）

一份独立的外部测试（`mcbridge1201-下载源测试-2026-10-21.md`，23:10–23:20 采样）对当时的
提交做了下载源实测，结论摘要：

| 环节 | 外部测试结果 |
|---|---|
| Mojang 版本清单 / JSON / 资源索引 | 正常 |
| 1.20.1、1.21.1 客户端 jar | 两个均通过大小 + SHA-1 + ZIP/CRC |
| 原版依赖库 / 资源对象 | 抽样通过；观测到 BMCL 失败后回退官方成功 |
| Fabric Loader 列表 / profile | 正常 |
| Fabric Maven 文件 | 13 个里 9 个失败（TLS 超时/中断）；**BMCL maven 对 fabric-api、intermediary 返回 404** |
| Forge | 推广列表正常；安装器下载波动（一个 TLS 超时、一个成功） |
| NeoForge | API 两次连接失败，无法验证 |

本仓库对报告的每条建议都在代码里落实了；报告本身是外部数据，镜像是否可用以本仓库
2026-10-21 23:47 的复测为准（见 §3）。

## 2. 现在的实现

### 2.1 逐路径镜像（不整域名替换）

`launcher/mclaunch.py` 的 `MIRRORS` 只重写**验证过**的前缀：

| 官方前缀 | 镜像 | 验证 |
|---|---|---|
| `resources.download.minecraft.net/` | `bmclapi2.bangbang93.com/assets/` | 外部测试回退成功 |
| `libraries.minecraft.net/` | `bmclapi2.bangbang93.com/maven/` | 外部测试回退成功 |
| `piston-data.mojang.com/` | `bmclapi2.bangbang93.com/` | 自带下载成功 |
| `piston-meta.mojang.com/` | `bmclapi2.bangbang93.com/` | 本仓库复测 HTTP 200（278,138 B） |
| `launchermeta.mojang.com/` | `bmclapi2.bangbang93.com/` | 同一 BMCL 元数据服务 |
| `meta.fabricmc.net/v2/` | `bmclapi2.bangbang93.com/fabric-meta/v2/` | 本仓库复测 HTTP 200（403,856 B） |
| `maven.fabricmc.net/net/fabricmc/fabric-loader/` | `bmclapi2.bangbang93.com/maven/net/fabricmc/fabric-loader/` | 本仓库复测 HTTP 200（1,984,980 B） |

**故意不镜像**（复测 404，机械替换只会把可用地址换成 404）：

- `maven.fabricmc.net` 下的 `fabric-api`、`intermediary`；
- `files.minecraftforge.net` 的推广列表（BMCL 对应路径 404）；
- NeoForge API（暂无验证可用的镜像）。

### 2.2 重试与错误分类

`download(url, dest, sha1=None, retries=3)`：

- 每个候选地址最多 `retries` 次，只对**可恢复错误**重试（超时、TLS、5xx、连接重置）；
- `403 / 404 / 410` 视为“这个源没有”，**立即换下一个源**，不浪费重试；
- SHA-1 不匹配：删除 `.part`，同一源重试，仍失败再换源；
- 结束/失败都会清理 `.part`；
- 返回**实际提供文件的 URL**。

`http_json(url)` 同样走镜像列表：官方元数据失败会尝试 BMCL 元数据镜像（版本清单、Fabric meta）。
成功的元数据在进程内缓存 15 分钟（`METADATA_TTL`），避免重复安装/刷新时反复拉列表；
`max_age=0` 可强制绕过缓存。

### 2.3 完整性校验

- 原版 client / libraries / assets / native：继续用 Mojang 索引里的 SHA-1；
- **Fabric Loader 库**：`download_maven()` 读取仓库的 `.sha1` 侧车文件后校验；
- **Forge / NeoForge 安装器**：同样用 `.sha1` 侧车校验（仓库发布侧车时）；
- 研究脚本 `tools/fetch_target_env.py` 走 `fetchlib.download()`，记录 `sourceUrl`。

侧车校验只证明“与仓库当前内容一致”，不防仓库本身被替换；研究用的锁定件仍以
`manifests/*.lock.json` 的 SHA-256 为准。

### 2.4 来源可见

每次下载/失败都会记一条 `DOWNLOAD_EVENTS`：

```json
{"file": "fabric-loader-0.19.5.jar", "url": "...", "final": "...",
 "mirror": false, "redirected": false, "bytes": 1984980, "attempts": 1,
 "error": null, "time": "2026-10-21 23:49:59"}
```

`url` 是发起请求的候选地址，`final` 是跟随重定向后的真实地址（例如 BMCL 的客户端请求
会跳到 `piston-data.mojang.com`，`redirected=true`），`mirror` 表示是否用了镜像候选。

启动器额外提供：

```text
GET /api/downloads?limit=50
```

用于排查“到底从官方还是镜像下载的、失败原因是什么”。

## 3. 本仓库复测（2026-10-21 23:47–23:50）

| 地址 | 结果 |
|---|---|
| `maven.fabricmc.net/.../fabric-loader-0.19.5.jar` | 200，1,984,980 B，侧车 SHA-1 通过 |
| `bmclapi2.../maven/net/fabricmc/fabric-loader/...jar` | 200（重定向到 `mirror.nyist.edu.cn/bmclapi`），1,984,980 B |
| `bmclapi2.../maven/net/fabricmc/fabric-api/...jar` | **404** |
| `bmclapi2.../maven/net/fabricmc/intermediary/...-v2.jar` | **404** |
| `bmclapi2.../fabric-maven/...` | 404（该前缀不存在，勿用） |
| `bmclapi2.../mc/game/version_manifest_v2.json` | 200，278,138 B |
| `bmclapi2.../fabric-meta/v2/versions/loader/1.21.1` | 200，403,856 B |
| `bmclapi2.../forge/promotions_slim.json` | 404 |
| `bmclapi2.../neoforge/versions` | 404 |
| `piston-meta.mojang.com` 版本清单（经 `http_json`） | 成功，920 个版本 |

## 4. 门禁与复现

离线回归（不联网，mock `urlopen`）已并入统一门禁，覆盖 12 项：
镜像顺序、Fabric API 不镜像、元数据镜像、`http_json` 回退、元数据缓存命中与 `max_age=0` 绕过、
404 不重试、瞬时错误重试、校验失败回退、侧车 SHA-1 与缓存、来源记录、`/api/downloads`。

```text
python tools/test_review_fixes.py      # DOWNLOAD 组
```

真实网络抽检：

```text
python tools/test_launcher_e2e.py --root <root> --version <vid>
python launcher/mclaunch.py install 1.21.1 <root> fabric
```

## 5. 限制（如实）

- 外部报告与本次复测都只覆盖**抽样**：没有下载两版全部依赖与 3,900+ 资源对象，也没把
  “能下载”当成“能进游戏”；
- 镜像节点会变（BMCL 会把请求转到 `mirror.nyist.edu.cn` 等节点），今天的 404/200 不保证长期；
- Fabric API / intermediary 目前没有验证可用的 BMCL 镜像，只能靠官方 + 重试；
- NeoForge API 在部分网络不可达时，启动器会直接报错并停在“版本列表取不到”，不会瞎猜版本。
