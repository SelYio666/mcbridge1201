# p124 — GUI“检查下载源”端到端（含健康回写）

日期：2026-10-22。验证：本地 HTTP 服务、`POST /api/check-sources` 运行 canary、
`GET /api/source-health` 读取模式与健康、结果写到 `<root>/.mcbridge/canary`（不覆盖仓库证据），
以及**检查结果会合并回源健康缓存**。

## 结果（最新一次）

```json
{
  "started": true,
  "summary": {"core_ok": true, "mirrors_ok": true, "neoforge_ok": false,
              "core_failures": [], "mirror_failures": [], "health_hosts": 10},
  "health_mode": "auto",
  "health_hosts": 10,
  "canary_file_written": true
}
```

- 核心官方、已验证镜像全通；NeoForge 两项超时（该 host 当前不可用，单独分桶显示）；
- canary 额外输出 `health.json`，服务端用 `mclaunch.merge_source_health()` 写进
  `<root>/.mcbridge/source-health.json`：10 个 host 进入缓存；
- 之后 `auto` 模式排序会参考这些健康记录（`GET /api/source-health` 能看到 10 个 host）；
- 早一次采样里 BMCL manifest 曾超时（`mirror_failures: ["bmcl manifest"]`），说明结果随网络变化，
  这里只记录最新一次。

## 复现

```text
python launcher/server.py            # 高级设置 → 检查下载源
POST /api/check-sources
GET  /api/check-sources
GET  /api/source-health
```

## 限制

- 单次网络采样；镜像/NeoForge 的失败不代表永久不可用；
- 没有在真实浏览器里做点击 UI 的自动化（DOM 未跑 E2E），只验证了 HTTP 端点与结果文件。
