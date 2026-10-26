# mcbridge1201锛圥0 鐮斿彂浠撳簱锛?

[![ci](https://github.com/SelYio666/mcbridge1201/actions/workflows/ci.yml/badge.svg)](https://github.com/SelYio666/mcbridge1201/actions/workflows/ci.yml)

> 鏂版墜鍏堣锛?*[浣跨敤璇存槑涓庢暀绋媇(docs/guide.md)**锛堝惎鍔ㄥ櫒 10 鍒嗛挓涓婃墜銆丳CL 鍏辩敤銆佹ā缁勮縼绉绘暀绋嬨€丗AQ锛夈€?

> 鏈€鏂板彂甯冿細**[v0.5.6](https://github.com/SelYio666/mcbridge1201/releases/tag/v0.5.6)**锛堜竴閿畨瑁呭埌 PCL锛氬浘褰㈤潰鏉?鍏ㄧ増鏈€夋嫨锛涗富宸ュ叿 v0.5.4锛夈€?

Minecraft Java 1.20.1 妯＄粍璺ㄧ増鏈吋瀹瑰钩鍙扮殑绗竴闃舵宸ヤ綔鍖恒€傛潵婧愬浐瀹氫负 **1.20.1**锛岄涓簿纭洰鏍囨槸 **Fabric 1.21.1**锛屽悓鏃舵娊鏍峰垎鏋?Forge 1.20.1銆?

鏈粨搴撳綋鍓嶄氦浠?P0 鐨勪簨瀹炰笌璇佹嵁锛屼互鍙?P1 鐨勭涓€娈佃繍琛屾椂缁撴灉锛氱幆澧冮攣瀹氥€佷笂娓稿紩鎿庨攣瀹氥€?0 浠界湡瀹炴牱鏈€?*鑷爺闈欐€佹崯浼ゅ垎鏋愬櫒**銆?*body-preserving 閲嶆槧灏勫櫒**銆丆enturyBridge 鐪熷疄杞崲浜х墿锛屽拰杩涗笘鐣?鍔熻兘绾ц瘉鎹€?*鍙 `runs/` 閲屾湁鏃ュ織涓庢埅鍥炬敮鎾戠殑妯＄粍澹扮О閫氳繃**锛堝 EntityCulling銆両mmediatelyFast 鐨勭Щ妞嶏級锛屽叾浣欎笉瀹ｇО鍏煎銆?

## 褰撳墠鐘舵€侊紙2026-10-23锛?

- **鍚姩鍣?*锛氱绾垮畨瑁?鍚姩鍘熺増 + Fabric/Forge/NeoForge锛涗笅杞芥簮鍙€夛紙鑷姩/浠呭畼鏂?闀滃儚浼樺厛锛? 婧愬仴搴风紦瀛?+ GUI 婧愭鏌ワ紱鍐呭祵 Python 鐨勪究鎼哄寘锛坴0.5.2锛夈€?
- **宸查獙璇佽繘涓栫晫**锛欶abric 1.21.1锛堝叏閲忓畨瑁?+ EntityCulling 鐪熺敓鏁堬級锛汭mmediatelyFast 1.21.1 batching 绉绘锛圚UD/鐗╁搧/overlay 璁℃暟銆両ris 1.8.1/1.8.14 + shader pack銆佷笓鐢ㄦ湇鍔″櫒澶氫汉鍔犲叆锛沗runs/p134`-`p150`锛夛紱**ImmediatelyFast 鍦板浘 atlas 鎭㈠锛歱175 鍗曚汉鐪熷疄鎵嬫寔 filled_map 娓叉煋锛沺177 涓ゅ紶鍦板浘鍒嗗埆钀藉埌 atlas tile 0/1 骞朵笌鐗╁搧灞曠ず妗嗗湴鍥惧悓灞忔覆鏌擄紱p181 鍔ㄦ€佹洿鏂帮紙绗簩娆′笂浼狅級+ 姝ｅ父閫€鍑烘竻鐞嗭紝骞朵慨澶嶉€€鍑烘椂鍚戝凡閲婃斁 NativeImage 鍐欏叆鐨勫穿婧冿紱p178 鍦?80 鐩旂敳鏋跺帇鍔涗笅鍚敤 VertexBuffer 鍔ㄦ€佷笂浼?fast path锛坥n 渚ф渶楂?76k 娆?glBufferSubData锛宱ff/on 鎴浘宸?0.0087%锛屼綆浜?off/off 瀵圭収锛屾棤 GL/mixin 閿欒锛?*锛坄runs/p175-map-atlas/`銆乣runs/p177-map-atlas-edge/`銆乣runs/p181-map-atlas-lifecycle/`銆乣runs/p178-vertex-upload/`锛夛紱NeoForge 21.1.264锛圓ppleSkin / Farmer's Delight / Jade + **涓撶敤鏈嶅姟鍣ㄥ鎴风鍔犲叆**锛宍runs/p161-neoforge-server/`锛?*甯?Farmer's Delight 鐨勬湇鍔＄/瀹㈡埛绔悓妯＄粍鍔犲叆**锛宍runs/p163-neoforge-fd-server/`锛夛紱Forge 1.20.1-47.4.28锛圓ppleSkin / Farmer's Delight + **涓撶敤鏈嶅姟鍣ㄥ鎴风鍔犲叆**锛宍runs/p159-forge-server/`锛?*甯?Farmer's Delight 鐨勫悓妯＄粍鍔犲叆**锛宍runs/p164-forge-fd-server/`锛夛紱mrpack 鐪熷疄 files 瀵煎叆閫氳繃锛坄runs/p160-mrpack/`锛夈€?
- **鏈€氳繃 / 鏈獙璇?*锛歋odium 1.20.1 杞崲鎺㈤拡涓?`blocked_static`锛坢issingClass=13銆乵issingMember=15銆乨escMismatch=16锛宍runs/p158-sodium-probe/`锛夛紝闇€绉绘鍏舵覆鏌撳唴鏍革紝鏈疆涓嶅仛锛汭ris 鍙獙璇佷簡 ImmediatelyFast 鐨勫吋瀹瑰垎鏀紙娌℃湁杞崲 Iris 鏈韩锛夛紱ImmediatelyFast 绔彛 jar 浠嶆湁 **2 涓?inert**锛屼絾瀹冧滑鏄畼鏂?1.21.1 宸插垹闄ょ殑 1.20.4 閬楃暀绫伙紙BufferBuilder/FontManager锛汣hatHud/MinecraftClient/BufferRenderer 宸插湪 p166鈥損168 閲嶇櫥璁帮紝涓や釜 map mixin 鍦?p175 鎭㈠锛孷ertexBuffer 鍦?p178 鍚敤锛涘鐓ц `runs/p180-inert-closure/`锛夛紱鍦板浘 atlas 宸查獙璇佸崟浜烘墜鎸?+ 涓ゅ紶鍦板浘锛坱ile 0/1锛? 鐗╁搧灞曠ず妗?+ p181 鍔ㄦ€佹洿鏂?姝ｅ父閫€鍑烘竻鐞嗭紱atlas 婊?1024 寮犳湭娴嬶紱鎬ц兘**涓嶅绉版敹鐩?*鈥斺€擧UD 鍦烘櫙宸紓鍦ㄥ櫔澹板唴锛坄runs/p148-bench/`锛夛紝80 鐩旂敳鏋跺疄浣撳帇鍔涗氦閿欎袱杞參绾?13%锛坄runs/p157-stress-interleaved/`锛夈€?
- **闂ㄧ**锛欽ava 25/25銆乣test_review_fixes` 鍏?95 椤癸紙鏈 **95/95**锛夈€乣check_hashes` 1194/1194銆乣verify_evidence` passed锛汣I push 瑙﹀彂宸查獙璇侊紙鏈€杩?`build` success锛岃 Actions锛夈€?
- 璇︽儏锛歔鎬婚獙鏀跺揩鐓(runs/p125-final-acceptance/README.md)銆乕FINAL-STATUS](docs/FINAL-STATUS.md)銆乕浣跨敤璇存槑](docs/guide.md)銆?

## 鐜扮姸锛?026-10-18锛?

| 椤圭洰 | 鐘舵€?| 璇佹嵁 |
|---|---|---|
| 鐜閿佸畾锛圝DK 21 / Gradle 9.8.1 / 鏃?JDK 17锛?| 宸茶褰?| [docs/baseline.md](docs/baseline.md) |
| Retromod / CenturyBridge 绮剧‘鎻愪氦銆佽鍙€佸伐浠?| 宸查攣瀹?| `manifests/upstream.lock.json` |
| 10 浠?1.20.1 鏍锋湰锛? Fabric + 5 Forge锛?| 宸蹭笅杞藉苟鏍￠獙 sha512 | `manifests/corpus.json` |
| 闈欐€佹崯浼ゅ垎鏋愶紙Fabric 1.21.1锛?| 10/10 宸茶窇閫氾紝ironchests 52/52 婧愮储寮曠‘璁?| `runs/p0-fabric-target/plan.json`銆乕static-matrix](docs/generated/static-matrix-fabric-1.21.1.md) |
| CenturyBridge 寮曟搸鏋勫缓 | 鍙紪璇戯紙闇€鏈湴 1 涓己澶辩被鐨?stub锛?| [docs/engine-selection.md](docs/engine-selection.md) |
| CenturyBridge 鐪熷疄杞崲 ironchests | 宸插畬鎴愶紝`ok_partial`锛?8 tombstone锛?| `work/cb/out/ironchests/report.md` |
| 鑷爺閲嶆槧灏勫櫒锛堜繚鐣欐柟娉曚綋锛?| 6148 绫绘湇鍔＄ jar 鍙敤锛屼慨澶?4 绫荤湡瀹炵己闄?| `java/.../remap/`銆乕docs/baseline.md](docs/baseline.md) 搂7.3 |
| 1.21.1 涓撶敤鏈嶅姟绔?| **BOOTED**锛歚Done (4.803s)`锛屾甯稿仠姝?| `runs/p1-server-baseline/` |
| 杞崲浠惰繍琛屾椂 | **BOOTED + 涓栫晫鍔犺浇**锛歚Done (1.134s)`锛?2 涓ā缁?| `runs/p3-server-accesswidener/` |
| 绗竴鏉¤浆鎹㈣鍒?+ 妗?| `ItemPredicate.ANY` 鈫?绌鸿皳璇嶏紱鍏ュ彛鐐归€氳繃 | `rules/fabric-1.21.1/container.json`銆乕rules/README.md](rules/README.md) |
| 甯搁噺姹犵绫讳慨姝?| 123 澶?Methodref鈫扞nterfaceMethodref + 3 涓?method handle锛堝惈 JiJ锛?| `java/.../rules/JarPatcher.java` |
| 瑙勫垯鏁?| `container.json` 7 鏉?+ `lithium.json` 璋冪敤鐐?2 鏉?Mixin 鐩爣/1 鏉″疄鐜扮被鏇挎崲 + `trashslot.json` 4 鏉?NBT/3 鏉?Balm 璋冪敤鐐?| `rules/fabric-1.21.1/` |
| 瀹瑰櫒濂戠害锛堟湇鍔＄鍛戒护锛?| **閫氳繃**锛氭斁缃?鈫?鎻掑叆 5 閽荤煶 鈫?NBT `Items` 鈫?閲嶅惎璇诲洖 5 | `runs/p5-contract-*/` |
| 鍏煎妗ｆ | ironchests `passed_within_scope`锛沴ithium / trashslot `booted_within_scope`锛沘ll-three bundle `passed_within_scope` | [profiles/README.md](profiles/README.md)銆乣profiles/bundle-all-three__fabric-1.21.1.json` |
| 鏀寔鐭╅樀 | 10 浠芥牱鏈殑闈欐€佺粨鏋?+ 杩愯鏃堕樁娈碉紙鏈繍琛?鈮?閫氳繃锛?| [docs/support-matrix.md](docs/support-matrix.md) |
| 绛惧悕閫傞厤瑙勫垯 | BlockEntity NBT 1 鍙?鈫?2 鍙傦紙甯?WrapperLookup锛夛紝鎸佷箙鍖栨仮澶?| `rules/fabric-1.21.1/container.json` 搂signatureAdaptations |
| **璋冪敤鐐圭鍚嶉€傞厤** | `callSiteAdaptations` + javac 妗ワ紱lithium `class_14.method_59` 鍛戒腑 2 澶勶紝`NoSuchMethodError` 娑堝け | [docs/baseline.md](docs/baseline.md) 搂7.17銆乣runs/p10-lithium-signature/` |
| **宓屽 jar 妗?* | 妗ユ寜 jar 宓屽叆浣跨敤瀹冪殑灞傜骇锛泂ynthetic nested jar + ironchests ResourcefulLib 鍥炲綊锛屽绾︿粛閫氳繃 | [docs/baseline.md](docs/baseline.md) 搂7.22銆乣runs/p18-nested-bridges/` |
| **BytecodeVerify** | 涓変釜琛ヤ竵 jar 椤跺眰 + nested ResourcefulLib锛?50 + 141 classes锛? failures锛汸26 瀹夊叏 Codec 鏋勫缓 73 + 142锛汸29 client bridge 47锛屽潎 0 failures | [docs/baseline.md](docs/baseline.md) 搂7.23銆伮?.30銆伮?.40銆乣runs/p19-bytecode-verify/`銆乣runs/p28-codec-verify/`銆乣runs/p38-client-bv/` |
| **Mixin 娉ㄥ叆鐩爣鎻愬彇** | 椤跺眰 + nested `.mixins.json`锛沗method` 鐩爣 + refmap + 鏋勯€犲櫒鏍￠獙 + refmap `@At` + ordinal 鎻愬彇锛沴ithium 214/86/10/3銆佽ˉ涓佷欢 209/84/0锛沬ronchests nested 1/1 | [docs/baseline.md](docs/baseline.md) 搂7.24鈥?.25銆伮?.36鈥?.38銆伮?.50鈥?.51銆乣runs/p21-refmap/`銆乣runs/p22-cross-analyze/`銆乣runs/p34-at-targets/`銆乣runs/p35-at-refmap/`銆乣runs/p36-patched-at/`銆乣runs/p48-nested-mixins/`銆乣runs/p49-at-ordinal/` |
| **Mixin 鐩爣鎻忚堪绗﹂€傞厤** | `mixinCallbackAdaptations`锛坅ppend/replace + refmap锛夛紱lithium `ExplosionMixin` 涓?POI storage 涓ゅ閫氳繃 | [docs/baseline.md](docs/baseline.md) 搂7.18銆乣runs/p11-lithium-explosion/` |
| **Mixin 瀹炵幇绫绘浛鎹?* | `mixinClassReplacements`锛沜hunk access 绉绘鍒?1.21.1 `ChunkResult` API锛宭ithium 鍒拌揪 `Done` | [docs/baseline.md](docs/baseline.md) 搂7.19銆乣runs/p13-chunk-port/` |
| 绗簩鏍锋湰 lithium | 杞崲骞跺姞杞芥垚鍔燂紱鏄惧紡闄嶇骇 2 鏉?mixin锛涜皟鐢ㄧ偣/2 澶?Mixin 鐩爣/chunk access 宸查€傞厤锛?*涓撶敤鏈嶅姟绔?BOOTED**锛坄Done (4.772s)`锛夛紝224-chunk 鍘嬪姏娴嬭瘯閫氳繃锛涙棤 lithium 鐜╂硶/瀹㈡埛绔绾?| `runs/p6-lithium/`銆乣runs/p10-lithium-signature/`銆乣runs/p11-lithium-explosion/`銆乣runs/p13-chunk-port/`銆乣runs/p23-chunk-stress/`銆乣rules/fabric-1.21.1/lithium.json` |
| chunk 鍘嬪姏娴嬭瘯宸ュ叿 | `tools/run_chunk_stress.py`锛?25 chunks + save/restart + 杩滆鏂█锛宍passed=true` | [docs/baseline.md](docs/baseline.md) 搂7.27銆乣runs/p24-chunk-stress-tool/` |
| 璇佹嵁鎬绘牎楠?| `tools/verify_evidence.py`锛?2 tests + 7 缁?verdict + P35/P36 at-target + profile + no tracked jars | [docs/baseline.md](docs/baseline.md) 搂7.41鈥?.42銆乣runs/p39-verify-evidence/`銆乣runs/p40-verify-extended/` |
| Codec dispatch 瀹夊叏閫傞厤 | javac `CodecDispatch` 鐢?`MapCodec.of` 鍖呰鏃?Codec锛涘绾?5/5锛況ecord-codec probe 涓庝笁鏍锋湰鍚屾湇 probe 鍧囬€氳繃 | [docs/baseline.md](docs/baseline.md) 搂7.28鈥?.29銆伮?.39銆伮?.45銆乣runs/p26-codec-safe/`銆乣runs/p37-codec-probe/`銆乣runs/p43-all-three-codec/` |
| **lithium + ironchests 鑱斿悎濂戠害** | 鍚屼竴瀹炰緥涓よ繘绋嬫斁缃?鎻掑叆/NBT/閲嶅惎璇诲洖 5 閽荤煶鍏ㄩ儴閫氳繃锛汸26 瀹夊叏 CodecDispatch 鐗堟湰涔熼€氳繃锛涗笁鏍锋湰锛?trashslot/Balm锛夊悓鏈嶅強 225-chunk 鍘嬪姏涔熼€氳繃 | [docs/baseline.md](docs/baseline.md) 搂7.20銆伮?.29銆伮?.43鈥?.44銆乣runs/p14-lithium-ironchests/`銆乣runs/p27-combined-safe-codec/`銆乣runs/p41-all-three/`銆乣runs/p42-all-three-chunk/` |
| 绗笁鏍锋湰 trashslot | 鍘熺敓 Balm 21 + 鍒濆鍖?缃戠粶杞借嵎妗?+ 4 涓?NBT 妗ワ紝**涓撶敤鏈嶅姟绔?BOOTED**锛坄Done (4.655s)`锛夛紱涓変釜鍖?codec锛堝惈 5 閽荤煶锛夊線杩旈€氳繃锛沜lientbound receiver 鍚庣画宸插湪瀹㈡埛绔墽琛岋紙p29/p64锛?| `runs/p15-trashslot/`銆乣runs/p16-balm/`銆乣runs/p17-balm-net/`銆乣runs/p29-client-receiver/`銆乣runs/p32-trashslot-codec/`銆乣runs/p33-all-packets/`銆乣rules/fabric-1.21.1/trashslot.json` |
| 瀹㈡埛绔娆¤繍琛岋紙PCL锛?| 1.21.1 Fabric 瀹㈡埛绔凡瑁咃紝浜旀ā缁勫姞杞斤紱RL 缃戠粶/Balm 瀹㈡埛绔垵濮嬪寲/ironchests 妯″瀷妗ュ悗**鍒拌揪涓昏彍鍗?*锛汢alm writer + lithium `VarInt` 妗ュ悗**杩涘叆鍗曚汉涓栫晫骞舵覆鏌?*锛涜儗鍖?+ TrashSlot 鎸夐挳宸叉覆鏌撱€? 閽荤煶鍙繘鑳屽寘锛泃rash **绉诲叆/鍙栧洖/clientbound/empty 鍧囬€氳繃**锛坄p63`/`p64`/`p65`锛夛紱IronChests **妯″瀷 + 鍚屾 NBT + 绠卞瓙 GUI锛堢湡瀹炰節瀹牸鑳屾櫙锛? 鍙栨斁浜や簰 + 鍏崇鎸佷箙鍖?S2C** 鍧囬€氳繃锛坄p66`鈥揱p72`锛夛紝淇娴佹按绾垮凡鍏ヤ粨锛坄p71`锛夛紱lithium 鐜╂硶鍐掔儫閫氳繃锛坄p73`锛岄潪瀹屾暣璇勪及锛夛紱鍙屽鎴风 **鏈嶅姟绔啋瀹㈡埛绔唴瀹瑰悓姝?+ 璁垮鍙栬蛋鈫掍富鏈哄彲瑙佺殑寰€杩斿潎閫氳繃**锛坄p75`/`p76`锛汱AN 灏濊瘯鐨勮璇佸瑙?`p74`锛夛紱**鍙岀鍏冲睆閫氳繃**锛坄p77`锛沗Screen.close()`锛屾湇鍔＄鑿滃崟鍥炶惤鍒?46 鏍硷級锛?*鍚岀鍙屽鎴风鎿嶄綔鎬绘暟瀹堟亽銆佹棤澶嶅埗**锛坄p78`锛夛紱**鍚?tick 骞跺彂鐐瑰嚮鏈嶅姟绔彧缁欎竴浜恒€佷笉澶嶅埗**锛坄p79`/`p80`锛屽共鍑€閲嶈窇纭杈撳琚籂姝ｏ級锛涚墿鐞?ESC **閫氳繃**锛坄p83`锛涗紶閫?鏂版柟鍧楀悗鎸?ESC锛屽弻绔洖钀?46 鏍硷紱鏃╁墠澶辫触瑙?`p81`/`p82`锛夛紱lithium TPS 閲囨牱 20.03锛坄p84`锛?89 鍖哄潡/60 绉掞級锛沞mpty-trash 鐪熷疄 Delete 閿凡閫氳繃锛坄p183`锛沗p85`/`p86` 鐨勬寜閿け璐ユ牴鍥犳槸娉ㄥ叆婕?`KEYEVENTF_EXTENDEDKEY`锛宲rovider 绾ц `p65`锛夛紱Shift+Delete 璺ㄦЫ鍒犻櫎锛堜袱鍙?5+3锛夐€氳繃锛坄p184`锛夛紱绌?cursor 鍙抽敭鍙?1 鐣?4 閫氳繃锛坄p185`锛夛紱鎵╂ā 6 涓牱鏈細5 闃绘柇 / 1 浠呭惎鍔紙`p88`锛岃 [mod-expansion](docs/mod-expansion.md)锛?| `runs/p50-client/`銆乣runs/p51-client-bridge/`銆乣runs/p52-client-balm/`銆乣runs/p53-client-world/`銆乣runs/p54-client-lithium/`銆乣runs/p55-client-gui/`銆乣runs/p56-client-item/`銆乣runs/p57-trash-persist/`銆乣runs/p58-trash-click/`銆乣runs/p59-trash-send/`銆乣runs/p60-trash-return/`銆乣runs/p61-trash-clean-return/`銆乣runs/p63-trash-debug/`銆乣runs/p64-trash-s2c/`銆乣runs/p65-trash-empty/`銆乣runs/p66-ironchests-gui/`銆乣runs/p67-ironchests-gui-nbt/`銆乣runs/p68-ironchests-gui/`銆乣runs/p69-ironchests-interaction/`銆乣runs/p70-ironchests-persist/`銆乣runs/p71-rebuild-pipeline/`銆乣runs/p72-ironchests-nine-slice/`銆乣runs/p73-lithium-play/`銆乣runs/p74-two-client/`銆乣runs/p75-two-client-server/`銆乣runs/p76-two-client-move/`銆乣runs/p77-two-client-close/`銆乣runs/p78-two-client-race/`銆乣runs/p79-two-client-simultaneous/`銆乣runs/p80-two-client-clean/`銆乣runs/p81-esc-key/`銆乣runs/p82-esc-onuse/`銆乣runs/p83-esc-teleport/`銆乣runs/p84-lithium-tps/`銆乣runs/p85-empty-key/`銆乣runs/p86-empty-hover/`銆乣runs/p87-independent-test/`銆乣runs/p88-mod-expansion/`銆乣runs/p183-trash-key/`銆乣runs/p184-trash-delete-all/`銆乣runs/p185-trash-undelete-right/`銆乕docs/mod-expansion](docs/mod-expansion.md)銆乕remaining-work](docs/remaining-work.md) |
| **ShulkerBoxTooltip 缃戞牸棰勮锛堥儴鍒嗭級** | p186锛歝lient-side `ContainerComponent` + `ComponentPreviewProvider` + grid renderer 鐨?t2/t4 妗ワ紝tooltip 鍑虹幇棰勮妗嗕笌 `Diamond 脳5`锛涚綉鏍?item icon 浠嶇己銆佺湡瀹?server item 浠嶇┖ | `runs/p186-shulker-grid-client-item/` |
| **涓€閿畨瑁呭埌 PCL锛坴0.5.5锛?* | 鍥惧舰闈㈡澘 `mcbridge-pcl-panel.zip` + 鍏?Python `mcbridge-pcl-setup.zip`锛涚増鏈笅鎷?鎼滅储/杩涘害/PCL2 鑷姩妫€娴嬶紱`from_source_install` 鏀寔 release/snapshot/old_* / all / latest-snapshot锛汸CL2 2.13.1.1 瀹炴祴 | `share/pcl-onclick/`銆乣runs/p137-pcl2-onclick/` |

## 浜ゆ帴

閰嶅鐨勬湰鍦?GUI 鍚姩鍣紙绂荤嚎瀹夎/鍚姩鍘熺増涓?Fabric锛岀晫闈㈠湪娴忚鍣ㄩ噷锛夎 [docs/launcher.md](docs/launcher.md)銆?
瑕佸彂缁欎笉鐢?GitHub 鐨勪汉锛歚python tools/build_portable.py` 鎵撲竴涓唴缃?Python 鐨勫厤瀹夎渚挎惡鍖咃紝
瑙?[docs/distribution.md](docs/distribution.md) 搂2.5銆?

鍏堣 [docs/handoff.md](docs/handoff.md)锛堜竴椤电増锛氳兘鍋氫粈涔堛€佸綋鍓嶉檷绾с€佷笅涓€姝ャ€佸鐜板懡浠わ級銆傚彂甯?鍒嗗彂杈圭晫涓庢楠よ [docs/distribution.md](docs/distribution.md)銆?

## 澶嶇幇

鏋勫缓鍓嶆彁涓庡共鍑€鐩綍澶嶇幇瑙?[docs/build.md](docs/build.md)銆?

鎵€鏈?Python 鑴氭湰鍙緷璧栨爣鍑嗗簱锛堟湰鏈?PowerShell/git 鐨?schannel TLS 涓嶅彲鐢紝Python 鐨?OpenSSL 鍙敤锛夈€?

```powershell
# 1) 閿佸畾涓婃父鎻愪氦涓庤鍙紙GitHub API 闄愭祦锛屾敼鐢?atom feed + codeload锛?
python tools/lock_upstream.py

# 2) 涓嬭浇 1.21.1/1.20.1 瀹㈡埛绔?jar銆乮ntermediary 鏄犲皠銆丗abric API銆丗abric Loader
python tools/fetch_target_env.py

# 3) 涓嬭浇 10 浠?1.20.1 鏍锋湰锛圡odrinth锛岃褰?sha256 涓?sha512 鏍￠獙锛?
python tools/fetch_corpus.py

# 4) 鏋勫缓鍒嗘瀽鍣紙JDK 21 + Gradle 9.8.1锛?
$env:JAVA_HOME='...\.toolchain\jdk'
$env:GRADLE_USER_HOME='...\.toolchain\gradle-home'
cd java; gradle --no-daemon installDist; cd ..

# 5) 闈欐€佹崯浼ゅ垎鏋?
java\build\install\mcbridge1201\bin\mcbridge1201.bat analyze `
  --mods work/corpus `
  --client-jar work/target/client-1.21.1.jar --mappings work/target/intermediary-1.21.1-v2.jar `
  --source-client-jar work/target/client-1.20.1.jar --source-mappings work/target/intermediary-1.20.1-v2.jar `
  --source-api "work/target/fabric-api-0.92.12+1.20.1.jar" `
  --api "work/target/fabric-api-0.102.0+1.21.1.jar" --api work/target/fabric-loader-0.19.5.jar `
  --target 1.21.1 --target-loader fabric --out runs/p0-fabric-target/plan.json
```

CenturyBridge 杞崲瑙?[docs/engine-selection.md](docs/engine-selection.md) 鐨勨€滅湡瀹炲皾璇曗€濅竴鑺傦紱瀹冮渶瑕佹湰鍦扮紪璇戜笂娓稿紩鎿庡苟鐢熸垚 7 鑺傚垎娈点€?

宸查獙璇佽寖鍥翠笌闃诲椤癸紙瀹㈡埛绔?GUI/缃戠粶/澶氫汉锛夎 [docs/remaining-work.md](docs/remaining-work.md) 鍜?[docs/progress.md](docs/progress.md)銆?

## 鐩綍

```text
docs/            鍩虹嚎銆佸紩鎿庨€夋嫨銆侀檺鍒躲€丄DR銆佺敓鎴愭姤琛?
java/            鑷爺鍒嗘瀽鍣紙Gradle锛孉SM + Gson锛?
manifests/       corpus / environment / upstream 涓変釜閿佹枃浠?
tools/           鎶撳彇銆佹牎楠屻€佹湇鍔＄杩愯銆佹姤鍛婅剼鏈?
runs/            璇佹嵁杈撳嚭锛坧lan.json銆佹湇鍔＄鏃ュ織锛?
work/            鏈湴宸ヤ綔闆嗭細娓告垙 jar銆佹牱鏈€佷笂娓告簮鐮併€佸疄渚嬶紙涓嶅叆搴擄級
third-party/     涓婃父璁稿彲璇佸壇鏈笌 NOTICE
patches/         瀵逛笂娓哥己浠剁殑鏄惧紡鏈湴琛ヤ竵锛堝甫璇存槑锛屼笉鏄笂娓镐唬鐮侊級
```

## 杈圭晫

- `work/` 涓嬬殑娓告垙 jar銆佹ā缁?jar銆佽浆鎹骇鐗?*鍙湪鏈満**锛屼笉闅忎粨搴撳垎鍙戯紱瀵瑰鍙簲鍒嗗彂宸ュ叿銆佽鍒欎笌 hash 娓呭崟銆?
- 闈欐€佸垎鏋愬彧鍒?`ANALYZED` 闃舵銆俙CLEAN_STATIC` 涓嶄唬琛ㄨ兘鍚姩锛屾洿涓嶄唬琛ㄧ帺娉曢€氳繃銆?
- 绗笁鏂逛綔鑰呰嚜鎶ワ紙Retromod 鐨?26.2 宸ヤ欢銆丆enturyBridge 鐨?1.21.1 妗堜緥锛変笌鏈粨搴撶嫭绔嬬粨鏋滃垎寮€璁板綍銆?

## License

MIT锛岃 [LICENSE](LICENSE)銆傜涓夋柟缁勪欢锛欳enturyBridge锛圡IT锛夈€乵inecraft-launcher-lib锛圔SD-2锛屽彲閫変緷璧栵級銆?

## p193 Shulker grid 残余 增量验收（2026-10-26，正常 UTF-8）

- 多物品网格（3 钻 + 2 绿宝石）、FULL 预览、真实 tooltip 路径、服务端 box（2 钻 + 4 绿宝石）四项全过；`runs/p193-shulker-grid-residual/`（`result.json` 4/4 true、`client.log`/`server.log`、`after-full/after-server/after-compact.png`）。
- 门禁：`test_review_fixes` 95/95、`check_hashes` 1194/1194、`verify_evidence` passed；无新 release（v0.5.6）。
- 边界：输入是 GLFW 回调级注入（非 OS 光标）；FULL 依赖 `preview.alwaysOn=true` + 预览键；服务端 box 只验证 dedicated `/item replace container.10`；27 格全满未测。
