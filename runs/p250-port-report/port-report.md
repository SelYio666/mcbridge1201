# 移植评估（结构级）

只读 jar 结构/元数据，不启动游戏；结论是分诊，不是承诺。

| jar | 加载器 | mod id | mixin | AT | Kotlin | 原生库 | 内嵌 jar | 判定 | 阻塞原因 |
|---|---|---|---|---|---|---|---|---|---|
| [信雅互联] Connector-1.0.0-beta.48+1.20.1.jar | unknown |  | 0 |  |  | 0 | 2 | **BLOCKED** | coremod |
| pmshaders-1.0.2-1.20.1-forge.jar | forge | pmshaders | 1 |  |  | 0 | 0 | **BLOCKED** | render/optimizer core |
| bookwyrms-1.20.1-1.2.0.jar | forge | bookwyrms | 0 |  |  | 0 | 0 | **EASY** |  |
| dcrapi-0.1.1.jar | forge | dcrapi | 0 |  | Y | 0 | 0 | **EASY** |  |
| syals_delight-1.0.0.jar | forge | syals_delight | 0 |  |  | 0 | 0 | **EASY** |  |
| CreativeCore_FORGE_v2.12.37_mc1.20.1.jar | forge | creativecore | 3 |  |  | 0 | 0 | **HARD** |  |
| GlitchCore-forge-1.20.1-0.0.1.1.jar | forge | glitchcore | 2 | Y |  | 0 | 0 | **HARD** |  |
| [内存泄漏修复] memoryleakfix-forge-1.17+-1.1.5.jar | forge | memoryleakfix | 2 |  |  | 0 | 0 | **HARD** |  |
| [意志坚定] ToughAsNails-forge-1.20.1-9.2.0.171.jar | forge | toughasnails | 2 | Y |  | 0 | 0 | **HARD** |  |
| pmweather-0.16.4-1.20.1-alpha.jar | forge | pmweather | 1 | Y |  | 0 | 0 | **HARD** |  |
| zombiegame-1.20.1-1.2.jar | forge | zombiegame | 0 |  |  | 0 | 0 | **HARD** |  |
| ftb-library-forge-2001.2.12.jar | forge | ftblibrary | 1 |  |  | 0 | 0 | **MEDIUM** |  |

## 汇总

BLOCKED=2 · EASY=3 · HARD=6 · MEDIUM=1
