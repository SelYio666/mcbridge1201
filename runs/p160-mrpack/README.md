# p160 — 真实 mrpack（带 files 下载项 + overrides）导入验证

日期：2026-10-22。补上 P2 里“mrpack 只测过无 files 最小包”的空白。

## 方法

- 动态生成 `.mrpack`：
  - `modrinth.index.json`：`formatVersion=1`、依赖 `minecraft=1.21.1` / `fabric-loader=0.19.5`；
  - `files` 含一项真实下载：`mods/fabric-api.jar`，带 `sha1`/`sha512`/`fileSize`，
    下载地址指向本机 `http://127.0.0.1:8765/fabric-api.jar`（Python `http.server` 提供）；
  - `overrides/config/mrpack-probe.txt` 用于验证 overrides 落盘；
- 调用启动器真实代码路径 `backend.install_mrpack(pack, root=work/launcher-e2e)`（依赖用我们的安装器，
  files 走 minecraft-launcher-lib 的 mrpack 安装，`skipDependenciesInstall=True`）；
- 安装后校验：`mods/fabric-api.jar` 的 SHA-1 是否等于预期、overrides 文件是否存在且内容正确。

## 结果

```json
{"hash_ok": true, "override_ok": true, "launch": "fabric-loader-0.19.5-1.21.1"}
```

- 文件真的从本地 HTTP 下载并按 SHA-1 校验通过；
- overrides 正确解压到实例根目录；
- 返回的 launch 版本为 `fabric-loader-0.19.5-1.21.1`；
- 测试完成后已删除安装的 mod 与 override 文件，避免污染实例。

## 限制

- 只有一个 files 项、且是本地 HTTP，不是公网 Modrinth CDN；
- 没有启动游戏（只验证安装路径）；
- mrpack 内含 Fabric API jar，按仓库策略**不提交**，包放在 `work/tmp/mrpack-assets/`（已忽略）。

## 证据

`result.json`；生成脚本在 `work/tmp/p160_mrpack.py`（不提交 mod jar）。
