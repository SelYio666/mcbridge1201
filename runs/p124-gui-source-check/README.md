# p124 — GUI“检查下载源”端到端

日期：2026-10-22。验证新增的 GUI 源健康检查：本地 HTTP 服务、`POST /api/check-sources`
运行 canary、`GET /api/source-health` 读取模式与健康、结果写入 `<root>/.mcbridge/canary`
（**不覆盖仓库证据**）。

## 结果

```json
{
  "started": true,
  "summary": {"core_ok": true, "mirrors_ok": false, "neoforge_ok": false,
              "core_failures": [], "mirror_failures": ["bmcl manifest"]},
  "health_mode": "auto",
  "canary_file_written": true
}
```

- 核心官方（Mojang 元数据/客户端/库/资源、Fabric、Forge）全部可达；
- 本次 BMCL 的 manifest 镜像超时（`mirror_failures: ["bmcl manifest"]`），另 NeoForge 两项超时——
  这正是 canary 要暴露的**当前健康**，不是核心链路故障；
- `canary.json` 写到了 `work/launcher-e2e/.mcbridge/canary/`，测试结束后删除 `.mcbridge`；
- 服务端 `SOURCE_CHECK` 状态机正常：`started → running → result`，无异常。

## 复现

```text
python launcher/server.py            # 打开界面，高级设置 → 检查下载源
# 或直接调接口：
POST /api/check-sources
GET  /api/check-sources
GET  /api/source-health
```

## 限制

- 单次网络采样；镜像/NeoForge 的失败不代表永久不可用；
- 只验证了“检查 + 展示”链路；没有在真实浏览器里做点击 UI 的自动化（DOM 未跑 E2E）。
