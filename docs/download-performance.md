# 下载性能：连接复用 + gzip（P0）

日期：2026-10-22。目标：解决“小文件多、握手多”的瓶颈，不改变源选择/校验策略。

## 状态：默认开启，可用 `MCBRIDGE_POOLED=0` 关闭

测试或调试需要走原始 urllib 路径时设 `MCBRIDGE_POOLED=0`；回归套件在连接池开启状态下连跑 3 次
均为 64/64。

## 改了什么

| 项 | 之前 | 现在 |
|---|---|---|
| HTTP 传输 | 每个文件 `urllib.urlopen`，**新建 TLS 连接** | `launcher/fetch.py`：urllib3 `PoolManager` 连接池，同 host 复用 |
| 元数据 | 不请求压缩 | `Accept-Encoding: gzip, deflate`，`decode_content=True` 自动解压 |
| 错误语义 | urllib 的 `HTTPError`/`URLError` | 保持不变：4xx/5xx → `HTTPError`（403/404/410 仍视为“此源没有”），超时 → `URLError` |
| 校验 | 落盘后再读一遍算 sha1 | 边写边算，省一次全文件读取 |
| 回退 | — | 没有 urllib3 时自动退回原 urllib 实现，行为不变 |

`mclaunch.download()` 的镜像重试、健康度、`.part`、进度回调都保留；只换了传输层。

## 基准（2026-10-22，同一网络、同一批 120 个资源对象）

```text
assets: 120  (1.21.1)
urllib (conn per file)         67.52s    69.18 MB     1.8 req/s
pooled (keep-alive+gzip)       13.20s    69.18 MB     9.1 req/s
speedup: 5.12x

# 第二次（同一天、网络抖动时）
urllib 69.45s / pooled 12.61s / 5.51x
# 第三次（较慢时段）
urllib 67.52s / pooled 20.69s / 3.26x
```

三次区间 **3.3×–5.5×**；波动来自网络，字节数完全一致（69.18 MB）。

复现：

```text
python tools/bench_fetch.py 120
```

说明：这是**小文件**场景的收益；大文件（client jar、模组 jar）主要受带宽限制，提升有限。

## 功能回归

用新传输层执行了一次真实安装（1.21.1 原版 + Fabric 0.19.5）到临时目录：

```text
vid fabric-loader-0.19.5-1.21.1   elapsed 70.9 s
profile json 存在；libraries 78 个 jar
```

镜像回退、sha1 校验、进度回调均沿用原有逻辑，未改动。

## 后续（未做）

- 自适应并发（AIMD）+ `Retry-After`：镜像 429 时自动降速；
- Range 续传：中断后从 `.part` 继续；
- 按路径类型选源（assets 镜像优先、maven 官方优先）；
- 可选 aria2 加速大文件。

> 注：本文件由“下载源/下载优化”这条线维护；`launcher/mclaunch.py` 的源策略部分由另一条工作线在改，
> 两者改动区域不同（传输层 vs 源选择），合并时注意都保留。
