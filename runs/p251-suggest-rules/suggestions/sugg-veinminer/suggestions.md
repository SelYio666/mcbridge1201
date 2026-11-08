# Rule suggestions

plan: work\plan-popular.json (sha256 3c7bcd8cfe3c)

| id | kind | confidence | target | note |
|---|---|---|---|---|
| textcomponent.callsite | callSiteAdaptation | high | net/minecraft/class_2178.method_9281 | bridge receives the old stack shape and must implement the 1.21.1 call; confidence covers the identity mapping, not the bridge body. static call: bridge signature equals the old descriptor |
| hurtandbreak.callsite | callSiteAdaptation | high | net/minecraft/class_1799.method_7956 | bridge receives the old stack shape and must implement the 1.21.1 call; confidence covers the identity mapping, not the bridge body. instance call: bridge receives the receiver as first argument |
| broadcastbreakevent.callsite | callSiteAdaptation | medium | net/minecraft/class_1309.method_20235 | bridge receives the old stack shape and must implement the 1.21.1 call; confidence covers the identity mapping, not the bridge body. call shape unknown (stub lookup failed): verify the receiver by hand |
