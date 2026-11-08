# Rule suggestions

plan: work\plan-silk.json (sha256 5eaa941e27fe)

| id | kind | confidence | target | note |
|---|---|---|---|---|
| textcomponent.callsite | callSiteAdaptation | high | net/minecraft/class_2178.method_9281 | bridge receives the old stack shape and must implement the 1.21.1 call; confidence covers the identity mapping, not the bridge body. static call: bridge signature equals the old descriptor |
| changedimension.callsite | callSiteAdaptation | high | net/minecraft/class_1297.method_5731 | bridge receives the old stack shape and must implement the 1.21.1 call; confidence covers the identity mapping, not the bridge body. instance call: bridge receives the receiver as first argument |
| tojson.callsite | callSiteAdaptation | high | net/minecraft/class_2561$class_2562.method_10867 | bridge receives the old stack shape and must implement the 1.21.1 call; confidence covers the identity mapping, not the bridge body. static call: bridge signature equals the old descriptor |
| performcommand.callsite | callSiteAdaptation | high | net/minecraft/class_2170.method_9249 | bridge receives the old stack shape and must implement the 1.21.1 call; confidence covers the identity mapping, not the bridge body. instance call: bridge receives the receiver as first argument |
| computeifabsent.callsite | callSiteAdaptation | high | net/minecraft/class_26.method_17924 | bridge receives the old stack shape and must implement the 1.21.1 call; confidence covers the identity mapping, not the bridge body. instance call: bridge receives the receiver as first argument |
| c2499.add.callsite | callSiteAdaptation | medium | net/minecraft/class_2483.add | bridge receives the old stack shape and must implement the 1.21.1 call; confidence covers the identity mapping, not the bridge body. call shape unknown (stub lookup failed): verify the receiver by hand |
| c2757.-init-.callsite | callSiteAdaptation | medium | net/minecraft/class_2757.<init> | bridge receives the old stack shape and must implement the 1.21.1 call; confidence covers the identity mapping, not the bridge body. instance call: bridge receives the receiver as first argument |
| c2658.-init-.callsite | callSiteAdaptation | medium | net/minecraft/class_2658.<init> | bridge receives the old stack shape and must implement the 1.21.1 call; confidence covers the identity mapping, not the bridge body. instance call: bridge receives the receiver as first argument |
| c2817.-init-.callsite | callSiteAdaptation | medium | net/minecraft/class_2817.<init> | bridge receives the old stack shape and must implement the 1.21.1 call; confidence covers the identity mapping, not the bridge body. instance call: bridge receives the receiver as first argument |
| c2736.-init-.callsite | callSiteAdaptation | medium | net/minecraft/class_2736.<init> | bridge receives the old stack shape and must implement the 1.21.1 call; confidence covers the identity mapping, not the bridge body. instance call: bridge receives the receiver as first argument |
| c266.-init-.callsite | callSiteAdaptation | medium | net/minecraft/class_266.<init> | bridge receives the old stack shape and must implement the 1.21.1 call; confidence covers the identity mapping, not the bridge body. instance call: bridge receives the receiver as first argument |

## No mechanical draft (needs human decision)

-  net/minecraft/class_1799.method_7977: no setHoverName continuation in 1.21.1 net.minecraft.world.item.ItemStack; needs a semantic port, not a mechanical rule
-  net/minecraft/class_634.method_2883: no send continuation in 1.21.1 net.minecraft.client.multiplayer.ClientPacketListener; needs a semantic port, not a mechanical rule
-  net/minecraft/class_1799.method_7911: no getOrCreateTagElement continuation in 1.21.1 net.minecraft.world.item.ItemStack; needs a semantic port, not a mechanical rule
-  net/minecraft/class_1799.method_7948: no getOrCreateTag continuation in 1.21.1 net.minecraft.world.item.ItemStack; needs a semantic port, not a mechanical rule
-  net/minecraft/class_269.method_1192: no getDisplaySlotByName continuation in 1.21.1 net.minecraft.world.scores.Scoreboard; needs a semantic port, not a mechanical rule
-  net/minecraft/class_1799.method_7938: no hasCustomHoverName continuation in 1.21.1 net.minecraft.world.item.ItemStack; needs a semantic port, not a mechanical rule
