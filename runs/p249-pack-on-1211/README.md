# p249 — 反证：同一堆模组直接上 1.21.1（NeoForge）会被加载器拒绝

日期：2026-11-07。p248 证明这个包能在它自己的 1.20.1 + Forge 上跑；本回合回答“那能不能直接 1.21.1 启动”。

## 做法

- 取 p248 的 14 个 jar（12 个包的 mod + architectury + kotlinforforge），放进 `work/packtest-1211`；
- 用 `neoforge-21.1.264`（本仓库已验证能启动的 1.21.1 加载器）启动，不 quickplay；
- 等它自己退出/报错，收集加载器错误。

## 结果：起不来

```text
Caused by: java.lang.NoClassDefFoundError:
  net/minecraftforge/fml/loading/ImmediateWindowProvider
Caused by: java.lang.ClassNotFoundException:
  net.minecraftforge.fml.loading.ImmediateWindowProvider
```

`exited=true`，`loaded=false`，`mod_count=14`。

## 为什么

- 这些 jar 的 `META-INF/mods.toml` 声明的是 **Forge**，引用 `net.minecraftforge.fml.*`；
- NeoForge 21.1 是 1.21.1 的加载器，包名是 `net.neoforged.*`，没有 Forge 那套类；
- 另外 Forge 47 用的是 1.20.1 的 SRG 名表，与 1.21.1 的中介名也对不上。
- 换句话说：**不是本工具不努力，是“换加载器 + 换版本”本身要另一套移植**；
  本仓库的转换引擎面向 Fabric 1.20.1 → Fabric 1.21.1，不处理 Forge → NeoForge。

## 边界

- 这是“加载器拒绝”的证据，不是“这个包不能移植”的证明；
- 真要上 1.21.1，需要逐模组做 Forge→NeoForge 移植（入口点、SRG→mojmap、Mixin 目标都变了），
  超出本仓库当前范围。

## 复现

```text
py -3.12 runs/p249-pack-on-1211/probe.py
```
