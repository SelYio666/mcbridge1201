# p125 鈥?鎬婚獙鏀讹紙2026-10-22锛?
鏈枃浠舵槸涓€娆?*鍙氦鎺ョ殑楠屾敹蹇収**锛氬湪杩欏彴鏈哄櫒涓婃妸浠撳簱鐨勮嚜鍔ㄥ寲闂ㄧ鍏ㄩ儴閲嶈窇浜嗕竴閬嶏紝骞舵妸
鈥滃凡楠岃瘉 / 鏈獙璇佲€濈殑杈圭晫鍐欐竻妤氥€傜粨璁哄彧瑕嗙洊涓嬮潰鍒楀嚭鐨勮寖鍥达紝涓嶅鎺ㄣ€?
## 闂ㄧ缁撴灉锛堟湰娆￠噸璺戯級

| 闂ㄧ | 缁撴灉 |
|---|---|
| `gradle -p java test installDist` | 鉁?BUILD SUCCESSFUL |
| Java JUnit | 鉁?25/25 |
| `python tools/test_review_fixes.py` | 鉁?**73/73** |
| `python tools/check_hashes.py` | 鉁?**946/946**锛坢ismatch 0 / missing 0锛?|
| `python tools/verify_evidence.py` | 鉁?passed锛?3/73锛?|
| GitHub CI锛坢aster锛宲ush+dispatch锛?| 鉁?push 瑙﹀彂宸查獙璇侊紙澶氭 `build` success锛屾渶鏂拌 Actions锛夛紱姝ゅ墠鏃?run 鏄?GitHub Actions degraded performance |
| Release 璧勪骇 | 鉁?`v0.5.1` / `mcbridge-launcher-0.5.1.zip` |
| 宸ヤ綔鍖?| 鉁?骞插噣锛坄git status` 鏃犳敼鍔級 |

鐜锛歐indows + JDK 21锛坄.toolchain/jdk`锛夈€丟radle 9.8.1锛坄.toolchain/gradle`锛夈€?鏈湴 CPython 3.12 杩愯鏃讹紱缃戠粶涓轰腑鍥藉ぇ闄嗙幆澧冿紙瀹樻柟婧?+ BMCL 闀滃儚锛夈€?
## 宸查獙璇侊紙鍙互瀵瑰璇达級

| 鑳藉姏 | 璇佹嵁 |
|---|---|
| Fabric 1.21.1 鍏ㄩ噺鍐峰畨瑁咃紙3,911/3,911 assets銆?33.6 MB銆? 澶辫触锛夊苟杩涘叆鍗曚汉涓栫晫 | `runs/p118-full-install-world/`锛堝惈涓栫晫鎴浘銆乮nstall-summary.json锛?|
| NeoForge 21.1.264 瀹夎骞跺埌杈句富鑿滃崟 | `runs/p116-neoforge-launch/`锛堝惈涓昏彍鍗曟埅鍥俱€乮nstaller/launch 鏃ュ織锛?|
| NeoForge 甯︽ā缁勮繘涓栫晫锛欰ppleSkin / Farmer's Delight / Jade | `runs/p127`銆乣runs/p128`銆乣runs/p130`锛堝惈涓栫晫鎴浘銆佹ā缁勬棩蹇椼€丣ade tooltip锛?|
| Forge 1.20.1-47.4.28 甯︽ā缁勮繘涓栫晫锛欰ppleSkin / Farmer's Delight | `runs/p129`銆乣runs/p131` |
| Forge/NeoForge 瀹夎鑷姩琛ュ師鐗?base锛坬uickPlay 鍙傛暟涓嶄涪锛?| `runs/p127`銆乣runs/p129`銆丩OADER/NEOFORGE 鍥炲綊 |
| 娓叉煋妯＄粍鑳藉姏锛欵ntityCulling 鐨?mixin 绉绘鍚庣湡姝ｇ敓鏁?| `runs/p119-entityculling-mixin/`锛團3 `Skipped: 1`锛? `runs/p121-entityculling-ab/`锛堝紑/鍏冲鐓э級 |
| 涓嬭浇婧愶細鎸夎矾寰勯獙璇佺殑 BMCL 闀滃儚锛堝惈 intermediary锛夈€?04 蹇€€銆佽秴鏃堕噸璇曘€丼HA-1銆佹潵婧愯褰?| `runs/p122-source-canary/`銆乣docs/download-sources.md` |
| 涓嬭浇婧愭ā寮忥細鑷姩 / 浠呭畼鏂?/ 闀滃儚浼樺厛锛涘け璐?host 鍋ュ悍缂撳瓨 + GUI canary 鍥炲啓 | `runs/p122`銆乣runs/p123`銆乣runs/p124` |
| 1.20.1 鍏ㄩ噺鍐峰畨瑁?111.7 s / 739 MB / verify OK锛堟祴瀹屽垹闄わ級 | `runs/p122-source-canary/full-1.20.1.json` |
| 渚挎惡鍖咃紙鍐呭祵 Python銆佹棤闇€姊瓙/鏃犻渶 Python 鐜锛?| v0.4.6 璧勪骇锛宍tools/test_portable.py` OK |
| 瑙勫垯寮曟搸 + 璇佹嵁闂ㄧ + CI锛堣鍒?妗?璇佹嵁缁戝畾锛?| `docs/FINAL-STATUS.md`銆乣runs/SHA256SUMS.txt` |

## 鏈獙璇?/ 鏄庣‘涓嶇畻閫氳繃锛堜笉鑳藉澶栬锛?
| 椤?| 鐘舵€?|
|---|---|
| ImmediatelyFast 娓叉煋鎵瑰鐞?| 鉁?宸茬Щ妞嶅苟鐢熸晥锛氬崟浜?+ 涓撶敤鏈嶅姟鍣ㄥ浜猴紙hud=4659銆乮temModel=2258銆乮temOverlay=1129锛夛紝鍏抽棴寮€鍏冲綊闆讹紙`runs/p134`銆乣runs/p141`銆乣runs/p137`锛夛紱Iris 1.8.1/1.8.14 + shader pack r5.3锛坄runs/p142`/`p143`/`p145`/`p146`锛夈€乮tem per-lighting锛坄runs/p149`/`p150`锛?|
| Sodium / Iris | 鉂?鏈Е纰?|
| 娓叉煋妯＄粍鈥滄€ц兘鎻愬崌鈥濇暟瀛?| 鉂?鏈祴锛堝彧鏈?EntityCulling 鐨?F3 璁℃暟锛屼笉鏄抚鐜囧熀鍑嗭級 |
| 瀹屾暣闀滃儚妯″紡鍏ㄩ噺瀹夎 | 鉂?鍙仛浜嗘湁鐣岄摼璺紙瀹㈡埛绔?搴?120 璧勬簮锛夛紱鍏ㄩ噺闀滃儚澶參宸蹭腑姝紙p123锛?|
| NeoForge/Forge 鐨?*甯︽ā缁?*涓栫晫 | 鉁?宸插仛锛坧127鈥損131锛氭樉绀?鍐呭/鏁版嵁鍚屾锛夛紱**鏈祴** NeoForge/Forge 涓撶敤鏈嶅姟鍣ㄣ€佸鏉傚鏂瑰潡妯＄粍 |
| 澶氫汉**涓撶敤**鏈嶅姟鍣紙dedicated server锛?| 鉁?Fabric 1.21.1锛氭棭鏈熷弻瀹㈡埛绔紙p75/p76锛? 鍚姩鍣ㄥ鎴风鍔犲叆锛坧132锛夛紱**鏈祴** NeoForge/Forge 涓撶敤鏈嶅姟鍣?|
| 渚挎惡鍖呭湪鍏朵粬鏈哄櫒/鏃犵綉鐜 | 鉂?鏈獙璇侊紙浠呮湰鏈鸿В鍖?+ `test_portable`锛?|
| 鐪熷疄娴忚鍣ㄩ噷鐨?UI 鐐瑰嚮 E2E | 鉂?鏈仛锛堝彧楠岃瘉浜?HTTP 绔偣涓庤繑鍥?JSON锛?|
| 闀挎椂闂?soak / 宕╂簝鎭㈠ | 鉂?鏈仛 |

## 澶嶇幇鍛戒护

```text
# Java
gradle -p java test installDist

# Python 闂ㄧ
python tools/test_review_fixes.py
python tools/check_hashes.py
python tools/verify_evidence.py

# 涓嬭浇婧愬仴搴凤紙鍙€夛級
python tools/check_download_sources.py
python tools/check_download_sources.py --strict

# 瀹夎/鍚姩锛堢ず渚嬶級
python launcher/mclaunch.py install 1.21.1 <娓告垙鐩綍>
python launcher/server.py

# 渚挎惡鍖?python tools/build_portable.py --label 0.4.4
python tools/test_portable.py --root <娴嬭瘯鐩綍> --version 1.21.1
```

## p175 澧為噺楠屾敹锛?026-10-23锛?
| 闂ㄧ | 缁撴灉 |
|---|---|
| `gradle -p java test installDist` | 鉁?BUILD SUCCESSFUL |
| Java JUnit | 鉁?25/25 |
| `python tools/test_review_fixes.py` | 鉁?**79/79**锛堟柊澧?6 鏉″湴鍥?atlas 瑙勫垯/婧愮爜鍥炲綊锛?|
| `python tools/check_hashes.py` | 鉁?**962/962**锛坢ismatch 0 / missing 0锛?|
| `python tools/verify_evidence.py` | 鉁?passed锛?9/79锛?|
| ImmediatelyFast mixin 瀹¤ | `listed=36 inert=3`锛涗袱涓?map mixin 涓嶅啀 inert锛坄runs/p175-map-atlas/audit.log`锛?|
| 鍦板浘 atlas 鐪熷疄娓叉煋 | 鉁?鍗曚汉 `ColdWorldMap` 鎵嬫寔 `filled_map`锛沗map-atlas bind 鈥?immediatelyfast:map_atlas/0`锛涙棤 ClassCastException/鏃?crash锛坄runs/p175-map-atlas/`锛?|
| Release 璧勪骇 | 鉁?`v0.5.2` / `mcbridge-launcher-0.5.2.zip` |

鍓╀綑 3 涓?inert 浠嶆槸 `MixinBufferBuilder`銆乣MixinVertexBuffer`銆乣MixinFontManager`锛堜笌鍦板浘鏃犲叧锛?鍘熷洜瑙?`runs/p169-inert-analysis/`锛夈€傚湴鍥惧彧楠岃瘉浜嗗崟浜虹涓€浜虹О鎵嬫寔鍦板浘锛岀墿鍝佸睍绀烘/澶氬湴鍥?鍔ㄦ€佹洿鏂?鏈祴銆?
## p178 澧為噺楠屾敹锛?026-10-23锛?
| 闂ㄧ | 缁撴灉 |
|---|---|
| `gradle -p java test installDist` | 鉁?BUILD SUCCESSFUL |
| Java JUnit | 鉁?25/25 |
| `python tools/test_review_fixes.py` | 鉁?**81/81**锛堟柊澧?2 鏉?VertexBuffer 瑙勫垯/璇佹嵁鍥炲綊锛?|
| `python tools/check_hashes.py` | 鉁?**1000/1000**锛坢ismatch 0 / missing 0锛?|
| `python tools/verify_evidence.py` | 鉁?passed锛?1/81锛?|
| ImmediatelyFast mixin 瀹¤ | `listed=37 inert=2`锛涗粎鍓?`MixinBufferBuilder`銆乣MixinFontManager`锛坄runs/p178-vertex-upload/audit.log`锛?|
| VertexBuffer 鍔ㄦ€佷笂浼?fast path | 鉁?80 鐩旂敳鏋跺帇鍔涖€乷ff/off + on/on 瀵圭収锛沷n 渚?60/79 鏉?fast 鏍囪銆佹渶楂?76k 娆?`glBufferSubData`锛沷ff/on 鍍忕礌宸?0.0087%锛堜綆浜?off/off 瀵圭収 0.214%锛夛紱鏃?GL/mixin 閿欒 |
| 鍦板浘 atlas 杈圭晫 | 鉁?p177锛氫袱寮犲湴鍥?tile 0/1 + 鐗╁搧灞曠ず妗嗗悓灞忔覆鏌?|
| Release 璧勪骇 | 鉁?`v0.5.3` / `mcbridge-launcher-0.5.3.zip` |

涓嶅绉版€ц兘鏀剁泭锛歱178 鍙瘉鏄?fast path 鎵ц涓旀棤瑙嗚/GL 鍥炲綊锛屾病鏈夊抚鐜囧熀鍑嗭紱鍙祴浜嗕竴鍙?NVIDIA
鏈哄櫒鍜屼竴涓悎鎴愬帇鍔涘満鏅€?
## p180 澧為噺楠屾敹锛?026-10-23锛?
| 闂ㄧ | 缁撴灉 |
|---|---|
| `python tools/test_review_fixes.py` | 鉁?**82/82**锛堟柊澧?1 鏉♀€滀笉寰楄鐧昏姝?mixin鈥濆洖褰掞級 |
| `python tools/check_hashes.py` | 鉁?**1005/1005** |
| `python tools/verify_evidence.py` | 鉁?passed锛?2/82锛?|
| 瀹樻柟 1.21.1 mixin 瀹¤ | `listed=37 inert=0 problems=0`锛坄runs/p180-inert-closure/audit-native.log`锛?|
| 绔彛 mixin 瀹¤ | `listed=37 inert=2 problems=0`锛涗袱涓?inert 鍦ㄥ畼鏂?jar 涓笉瀛樺湪锛?.20.4 閬楃暀姝讳唬鐮侊級 |
| Release | 鏃犳柊 release锛泇0.5.3 浠嶆槸褰撳墠鍙戝竷锛坧180 鍙湁鏂囨。/璇佹嵁/鍥炲綊锛?|

## p181 澧為噺楠屾敹锛?026-10-23锛?
| 闂ㄧ | 缁撴灉 |
|---|---|
| `python tools/test_review_fixes.py` | 鉁?鍏?**83 椤?*锛堟湰娆?**82/82** + `/api/jvm` 缃戠粶瓒呮椂 skip锛涙柊澧?1 鏉?atlas closed 瀹堝崼鍥炲綊锛?|
| `python tools/check_hashes.py` | 鉁?**1022/1022** |
| `python tools/verify_evidence.py` | 鉁?passed锛堟帴鍙?`/api/jvm` skip锛?|
| 鍦板浘鍔ㄦ€佹洿鏂?| 鉁?`locked=0` held map锛屾暟鎹寘绉诲姩鐜╁锛沗map-atlas update count=2`锛屾埅鍥炬樉绀哄湴褰㈣鐩栧垵濮嬪浘妗?|
| 姝ｅ父閫€鍑烘竻鐞?| 鉁?client stop 鈫?`Stopping!` 鈫?`keep-dummy` 鈫?`close id=0` 鈫?`clear atlases=1`锛沞xit 0銆乧rash=null |
| 閫€鍑哄穿婧冧慨澶?| 鉁?淇鍓?`Image is not allocated`锛坄crash-before-fix-map.txt`锛夛紱`MapAtlasTexture.isClosed` 瀹堝崼鍚庝笉鍐嶅穿 |
| Release 璧勪骇 | 鉁?`v0.5.4` / `mcbridge-launcher-0.5.4.zip` |

## p183 澧為噺楠屾敹锛?026-10-23锛?
| 闂ㄧ | 缁撴灉 |
|---|---|
| `python tools/test_review_fixes.py` | 鉁?鍏?**84 椤?*锛堟湰娆?**84/84**锛涙柊澧?1 鏉?TrashSlot UI empty 閿洖褰掞紝`/api/jvm` 鏈鏈?skip锛?|
| `python tools/check_hashes.py` | 鉁?**1035/1035** |
| `python tools/verify_evidence.py` | 鉁?passed锛堟帴鍙?`/api/jvm` skip锛?|
| TrashSlot 鐪熷疄 empty 閿?| 鉁?inventory 鎮仠 trash 鈫?Delete(261) 鈫?`DEBUG_EMPTY_PROVIDER` 鈫?`SERVER_TRASH empty=true`锛沗after.png` 鏄剧ず trash 绌?|
| 澶辫触鏍瑰洜 | 鉁?p65/p85/p86 鐨?Delete 澶辫触鏄敞鍏ユ紡 `KEYEVENTF_EXTENDEDKEY`锛堟敹鍒?KP_DECIMAL 330锛夛紝涓嶆槸 Balm/mod锛涙棤浜у搧浠ｇ爜鏀瑰姩 |
| Release | 浠呰瘉鎹?鍥炲綊锛屾部鐢?`v0.5.4`锛堟棤鏂扮増鏈級 |

## p184 澧為噺楠屾敹锛?026-10-23锛?
| 闂ㄧ | 缁撴灉 |
|---|---|
| `python tools/test_review_fixes.py` | 鉁?鍏?**85 椤?*锛堟湰娆?**85/85**锛涙柊澧?1 鏉?TrashSlot Shift+Delete 鍥炲綊锛?|
| `python tools/check_hashes.py` | 鉁?**1048/1048** |
| `python tools/verify_evidence.py` | 鉁?passed |
| Shift+Delete 璺ㄦЫ | 鉁?涓ゅ彔 5+3 閽荤煶锛坰lot 0/1锛夛紝Shift+Delete 鈫?`DEBUG_DELETE_CONTAINER all=true` 鈫?鏈嶅姟绔?瀹㈡埛绔?8鈫?锛沗after.png` 绌?|
| 绗竴娆″皾璇?| 鈿狅笍 `give` 5+3 鍚堝苟鎴愪竴鍙?8锛岃櫧 `all=true` 浣嗘棤娉曡瘉鏄庤法妲斤紱鏈€缁堟敼涓?`method_5447` 鐩存帴鍐欎袱涓Ы浣?|
| Release | 浠呰瘉鎹?鍥炲綊锛屾部鐢?`v0.5.4`锛堟棤鏂扮増鏈級 |

## p185 澧為噺楠屾敹锛?026-10-23锛?
| 闂ㄧ | 缁撴灉 |
|---|---|
| `python tools/test_review_fixes.py` | 鉁?鍏?**86 椤?*锛堟湰娆?**86/86**锛涙柊澧?1 鏉?TrashSlot right-click undelete 鍥炲綊锛?|
| `python tools/check_hashes.py` | 鉁?**1061/1061** |
| `python tools/verify_evidence.py` | 鉁?passed |
| 绌?cursor 鍙抽敭 undelete | 鉁?trash 5 鈫?鍙抽敭 鈫?cursor 1銆乼rash 4銆佹湇鍔＄ 4锛沗DEBUG_CLICK button=1 hovering=true`銆乣DEBUG_PROVIDER_UNDELETE right=true` |
| focus/origin | 鉁?鍏?`focus_window` 鍐?`ClientToScreen`锛岄伩鍏?`ShowWindow` 鍚庡師鐐规紓绉伙紱涓€у乏閿悆鎺夋縺娲荤偣鍑?|
| Release | 浠呰瘉鎹?鍥炲綊锛屾部鐢?`v0.5.4`锛堟棤鏂扮増鏈級 |

## p186 澧為噺楠屾敹锛?026-10-24锛?
| 闂ㄧ | 缁撴灉 |
|---|---|
| `python tools/test_review_fixes.py` | 鉁?鍏?**87 椤?*锛堟湰娆?**87/87**锛涙柊澧?1 鏉?Shulker grid wrapper/t2/t4 鍥炲綊锛?|
| `python tools/check_hashes.py` | 鉁?**1072/1072** |
| `python tools/verify_evidence.py` | 鉁?passed |
| Shulker grid 閮ㄥ垎鎭㈠ | 鉁?client-side component + wrapper锛歚SBT_WRAP show=true inv=27 nonAir=1`锛泃ooltip 鍑虹幇棰勮妗嗕笌 `Diamond 脳5`锛坄grid.png`锛?|
| 浠嶆湭瑙ｅ喅 | 鈿狅笍 缃戞牸 slot 鍐?item icon 鏈敾锛涚湡瀹?server `/item replace` 鏍堜粛 `!minecraft:container` |
| Release | 浠呴儴鍒嗚瘉鎹?鍥炲綊锛屾部鐢?`v0.5.4`锛堟棤鏂扮増鏈級 |

## v0.5.5 涓€閿畨瑁呭埌 PCL 澧為噺楠屾敹锛?026-10-24锛?
| 闂ㄧ | 缁撴灉 |
|---|---|
| `python tools/test_review_fixes.py` | 鉁?鍏?**88 椤?*锛堟湰娆?**88/88**锛涙柊澧?1 鏉?PCL 涓€閿潰鏉?鐗堟湰閫夋嫨鍥炲綊锛?|
| `python tools/check_hashes.py` | 鉁?**1085/1085** |
| `python tools/verify_evidence.py` | 鉁?passed |
| 鍥惧舰闈㈡澘 | 鉁?`mcbridge-pcl-panel.zip`锛圧elease v0.5.5锛夛細鐗堟湰涓嬫媺/鎼滅储銆乺elease/snapshot/old_* / all銆佽繘搴︽潯/鏃ュ織銆丳CL2 鐩綍鑷姩妫€娴?|
| 鍏?Python 瀹夎鍣?| 鉁?`mcbridge-pcl-setup.zip`锛汸CL2 2.13.1.1 渚挎惡鐗堝疄娴?1.20.4 鐗堟湰鍒楄〃鍑虹幇锛坄runs/p137-pcl2-onclick/`锛?|
| 鐗堟湰閫夋嫨 | 鉁?`from_source_install.py --list --version-type all`銆乣--version latest-snapshot`锛泇0.5.5 release |
| Release | **v0.5.5**锛堜富宸ュ叿 v0.5.4锛?|

## 宸茬煡椋庨櫓

- 闀滃儚鑺傜偣浼氶殢鏃堕棿/鍦板尯鍙樺寲锛宑anary 鍙槸鍗曟閲囨牱锛?- 瑙勫垯鏂囦欢鎸?`capability/risk/evidence` 缁戝畾锛屾柊澧炶兘鍔涘繀椤诲厛鏈夌湡瀹?boot/杩涗笘鐣岃瘉鎹紱
- `work/` 涓?`dist/` 涓嶅叆搴擄紱浠撳簱涓嶅垎鍙戞父鎴?妯＄粍/杞崲鍚庣殑 jar锛?- ImmediatelyFast 宸插畬鎴?batching 寮曟搸绉绘锛圚UD/鐗╁搧鎵瑰鐞嗙敓鏁堬紝A/B 鍙鐜帮級锛汭ris銆乸er-lighting 鐗╁搧鍙樹綋涓庡抚鐜囧熀鍑嗕粛鏈仛銆?

## p187 Shulker 网格 icon + 服务端物品 增量验收（2026-10-24，本段为正常 UTF-8；上文历史段落保持原样）

| 门禁 | 结果 |
|---|---|
| `python tools/test_review_fixes.py` | ✅ 共 **89 项**（本次 **89/89**；新增 1 条 SBT grid icon + server-box 回归） |
| `python tools/check_hashes.py` | ✅ **1098/1098** |
| `python tools/verify_evidence.py` | ✅ passed |
| 网格 icon | ✅ `GRID_DRAWITEMS ... items=1 first=minecraft:diamondx5`、`GRID_DRAWITEM stack=minecraft:diamond count=5`；`grid.png` 槽内 diamond 图标 ×5 正常绘制 |
| 服务端物品 | ✅ `/item replace ... container.3` 同步的 shulker：`GRID_SERVERBOX slot=3 nonAir=1`，HUD 源 `source=server`，同一条管线渲染 |
| 根因 | set-as-get（`method_57379(type,null)`=set，首次读即清空 CONTAINER，p110 起服务端物品坏掉）→ 改为 `getComponents().get`；转换剥掉了 mod 的 ItemStackMixin → companion 1.1.0 重新注入 getTooltipData + 注册 component-first provider；harness 写 `preview.alwaysOn=true` |
| Release | 沿用 `v0.5.5`（主工具 v0.5.4；p187 无新 release） |
| CI | run `40109967951` success（head `31a0494`） |
| 隐患 | 未验证：FULL 预览类型、多物品网格、预览键交互、真实鼠标 hover（harness 改用 HudRenderCallback 驱动同一条管线，OS 光标注入不可靠） |

## p188 map atlas 1024 溢出 增量验收（2026-10-25，正常 UTF-8）

| 门禁 | 结果 |
|---|---|
| `python tools/test_review_fixes.py` | ✅ 共 **90 项**（本次 **90/90**；新增 1 条 map atlas overflow 回归） |
| `python tools/check_hashes.py` | ✅ **1110/1110** |
| `python tools/verify_evidence.py` | ✅ passed |
| 溢出 | ✅ 1024 张填满 atlas 0 后：`map-atlas create id=1`（恰好一次）、`assign map=1025 packed=65536`（atlas 1 tile 0）、`bind map=map/1025 texture=immediatelyfast:map_atlas/1` |
| 上传证明 | ✅ `atlas1-pixel-check mismatches=0`（4 采样点读回 atlas 1 NativeImage 与 MapState 颜色一致；update marker 节流故用像素） |
| 退出清理 | ✅ `map-atlas clear atlases=2`、exit 0、errors=[]、crash=null |
| Release | 沿用 `v0.5.5`（主工具 v0.5.4；p188 无新 release，实现零改动） |
| 隐患 | 第三个 atlas（2048+ 张）、跨 atlas 同屏视觉、真实服务端 1024+ 张地图端到端未测 |

## p189/p190 TrashSlot creative 删除 + 多客户端 增量验收（2026-10-25，正常 UTF-8）

| 门禁 | 结果 |
|---|---|
| `python tools/test_review_fixes.py` | ✅ 共 **92 项**（本次 **92/92**；新增 p189 creative 删除 + p190 多客户端两条回归） |
| `python tools/check_hashes.py` | ✅ **1143/1143** |
| `python tools/verify_evidence.py` | ✅ passed |
| p189 creative | ✅ 真缺陷修复：1.21.1 creative 界面 hoveredSlot 恒 null + SlotWrapper 消失使原分支永不可达；companion 重写后 Shift+Delete 连锁（slot=36 all=true，InventoryMenu 46 槽）+ Delete + 清 trash 全通过 |
| p190 多客户端 | ✅ A：5→4（右键取 1）→empty（Delete）；B 服务端 trash 全程 diamondx3、客户端 UI 不变（reply 只回发送者） |
| Release | 沿用 `v0.5.5`（主工具 v0.5.4；无新 release） |
| 隐患 | creative inventory tab 27 格、creative 右键 undelete、B 主动操作、三客户端、重进保持未测 |

## p191/p192 TrashSlot creative/多客户端残余 增量验收（2026-10-25，正常 UTF-8）

| 门禁 | 结果 |
|---|---|
| `python tools/test_review_fixes.py` | ✅ 共 **94 项**（本次 **94/94**；新增 p191 creative tab + p192 三客户端两条回归） |
| `python tools/check_hashes.py` | ✅ **1175/1175** |
| `python tools/verify_evidence.py` | ✅ passed |
| p191 | ✅ inventory tab 主背包格删除（SERVER_DELETE slot=18，class_484 identity 映射）；creative 列表格上游不删；右键 undelete 不适用（无画布） |
| p192 | ✅ B 主动 4→3→empty 只影响 B；C 服务端/客户端不变；A 重进 trash=empty（上游登录重置） |
| Release | 沿用 `v0.5.5`（主工具 v0.5.4；无新 release） |
| 隐患 | 双端同时操作、四客户端未测 |

## v0.5.6 release 增量（2026-10-25，正常 UTF-8）

- tag `v0.5.6`（target `44b5528`），5 资产：主工具便携包 0.5.6（`tools/test_portable.py` OK）、
  shulkerpreview/trashcreativefix companion jar、PCL 面板/setup（沿用 v0.5.5 字节一致）；
- 服务端 sha256 与本地记录全部一致（见 acceptance.json `release_v056`）；
- 一键 PCL 仍为 v0.5.5 资产（未变更）。

## p193 Shulker grid 残余 增量验收（2026-10-26，正常 UTF-8）

| 门禁 | 结果 |
|---|---|
| `python tools/test_review_fixes.py` | ✅ 共 **95 项**（本次 **95/95**；新增 1 条 p193 Shulker grid 残余回归） |
| `python tools/check_hashes.py` | ✅ **1194/1194** |
| `python tools/verify_evidence.py` | ✅ passed |
| p193 | ✅ client 多物品 3 钻 + 2 绿宝石、FULL、真实 tooltip 路径、server box 2 钻 + 4 绿宝石；`result.json` 4/4 true |
| Release | 沿用 `v0.5.6`（p193 无 mod 改动、无新 release） |
| 隐患 | GLFW 回调级输入（非 OS 光标）、FULL 依赖 alwaysOn+预览键、27 格全满未测 |
## p194 第三 atlas / 跨 atlas 同帧 增量验收（2026-10-26，正常 UTF-8）

| 门禁 | 结果 |
|---|---|
| `python tools/test_review_fixes.py` | ✅ 共 **96 项**（本次 **96/96**；新增 1 条 p194 第三 atlas/跨 atlas 回归） |
| `python tools/check_hashes.py` | ✅ **1206/1206** |
| `python tools/verify_evidence.py` | ✅ passed |
| p194 | ✅ 2050 map ids：`create id=2` 一次、`assign map=2049 packed=131072`/`2050=131328`、`bind map_atlas/2`；HUD 同帧 map 1/1025/2049；atlas1/2 像素 0；退出 `clear atlases=3` |
| Release | 沿用 `v0.5.6`（p194 无 mod 改动、无新 release） |
| 隐患 | 真实服务端 1024+ 张地图端到端、三 atlas 并排视觉（HUD 原点）、3×4096² ≈192 MB 压力未测 |
## p195 v0.5.6 交付验证 增量（2026-10-26，正常 UTF-8）

| 门禁 | 结果 |
|---|---|
| `python tools/test_review_fixes.py` | ✅ 共 **97 项**（本次 **97/97**；新增 1 条 p195 交付验证回归） |
| `python tools/check_hashes.py` | ✅ **1212/1212** |
| `python tools/verify_evidence.py` | ✅ passed |
| p195 portable | ✅ `dist/mcbridge-launcher-0.5.6.zip` 在全新 `work/tmp/p195-portable` 根目录 `test_portable.py --version 1.21.1`：deps + `/api/status` + `/guide` 全过（RESULT: OK） |
| p195 panel smoke | ✅ `tools/pcl_panel.py` 打开，103 个正式版、PCL 目录默认值正常（`panel-smoke.png`）；PCL2 本机路径不存在 |
| panel 资产 | ⚠️ 只下载到 3,361,813/12,361,982 bytes，`gh release download` 挂起已终止 |
| Release | 沿用 `v0.5.6`（无 mod 改动、无新 release） |
| 隐患 | 完整 PCL2 安装点击/进度/PCL2 版本刷新、干净/离线主机、panel 资产重下未验证 |
## p196 Shulker grid 27 格全满 增量（2026-10-26，正常 UTF-8）

| 门禁 | 结果 |
|---|---|
| `python tools/test_review_fixes.py` | ✅ 共 **98 项**（本次 **98/98**；新增 1 条 p196 27 格回归） |
| `python tools/check_hashes.py` | ✅ **1231/1231** |
| `python tools/verify_evidence.py` | ✅ passed |
| p196 | ✅ 27 种物品 `GRID_DRAWITEMS items=27`、FULL、server box、真实 hover；`result.json` 4/4 true |
| Release | 沿用 `v0.5.6`（p196 无 mod 改动、无新 release） |
| 隐患 | 预览键重绑定当轮未生效（写错 config 分类 + F 触发交换副手）；27 格不同 NBT/附魔未测（重绑定已由 p197 关闭） |
## p197 Shulker 预览键重绑定 增量（2026-10-26，正常 UTF-8）

| 门禁 | 结果 |
|---|---|
| `python tools/test_review_fixes.py` | ✅ 共 **99 项**（本次 **99/99**；新增 1 条 p197 重绑定回归） |
| `python tools/check_hashes.py` | ✅ **1254/1254** |
| `python tools/verify_evidence.py` | ✅ passed |
| p197 | ✅ `controls.previewKey=J(74)`/`fullPreviewKey=K(75)`、`alwaysOn=false`；mod 状态机 `NO_PREVIEW→COMPACT→FULL→COMPACT→NO_PREVIEW`；27 格 `GRID_DRAWITEMS items=27`；`result.json` 7/7 true |
| 更正 | p196 “mod 忽略 config previewKey” 为误判（字段写在 `preview` 分类）；bytecode 显示读取 `controls.previewKey/fullPreviewKey` |
| Release | 沿用 `v0.5.6`（无 mod 改动、无新 release） |
| 隐患 | 键状态仍在 `isKeyDown` 轮询边界注入（无 OS 级物理按键）；27 格不同 NBT/附魔未测 |
