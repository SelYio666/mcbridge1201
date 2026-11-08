# Rule suggestions

plan: work\plan-corpus.json (sha256 946b9827fc11)

| id | kind | confidence | target | note |
|---|---|---|---|---|
| getleaderbannerinstance.callsite | callSiteAdaptation | high | net/minecraft/class_3765.method_16515 | bridge receives the old stack shape and must implement the 1.21.1 call; confidence covers the identity mapping, not the bridge body. static call: bridge signature equals the old descriptor |
| getsuckshape.callsite | callSiteAdaptation | medium | net/minecraft/class_2615.method_11262 | bridge receives the old stack shape and must implement the 1.21.1 call; confidence covers the identity mapping, not the bridge body. instance call: bridge receives the receiver as first argument |
| c4180.-init-.callsite | callSiteAdaptation | medium | net/minecraft/class_4180.<init> | bridge receives the old stack shape and must implement the 1.21.1 call; confidence covers the identity mapping, not the bridge body. instance call: bridge receives the receiver as first argument |
| c2499.add.callsite | callSiteAdaptation | medium | net/minecraft/class_2483.add | bridge receives the old stack shape and must implement the 1.21.1 call; confidence covers the identity mapping, not the bridge body. call shape unknown (stub lookup failed): verify the receiver by hand |
| suck.callsite | callSiteAdaptation | medium | net/minecraft/class_2615.field_12026 | bridge receives the old stack shape and must implement the 1.21.1 call; confidence covers the identity mapping, not the bridge body. call shape unknown (stub lookup failed): verify the receiver by hand |
| width.field | fieldRedirect | medium | net/minecraft/class_4048.field_18067 | field net.minecraft.world.entity.EntityDimensions.width exists in 1.21.1 as comp_2185 but is not resolvable from mod code (private/removed constant) - bridge must supply the value or the semantic equivalent |
| height.field | fieldRedirect | medium | net/minecraft/class_4048.field_18068 | field net.minecraft.world.entity.EntityDimensions.height exists in 1.21.1 as comp_2186 but is not resolvable from mod code (private/removed constant) - bridge must supply the value or the semantic equivalent |

## Dropped (would conflict with existing rules)

- checkneighbourblocks.callsite: an existing rule already covers this exact match key

## No mechanical draft (needs human decision)

-  net/minecraft/class_1799.method_7969: no getTag continuation in 1.21.1 net.minecraft.world.item.ItemStack; needs a semantic port, not a mechanical rule
-  net/minecraft/class_2621.method_11289: no unpackLootTable continuation in 1.21.1 net.minecraft.world.level.block.entity.RandomizableContainerBlockEntity; needs a semantic port, not a mechanical rule
-  net/minecraft/class_3193.method_16143: no updateChunkToSave continuation in 1.21.1 net.minecraft.server.level.ChunkHolder; needs a semantic port, not a mechanical rule
-  net/minecraft/class_3210.method_14081: no updatePlayer continuation in 1.21.1 net.minecraft.server.level.PlayerMap; needs a semantic port, not a mechanical rule
-  net/minecraft/class_3222.method_14246: no untrackChunk continuation in 1.21.1 net.minecraft.server.level.ServerPlayer; needs a semantic port, not a mechanical rule
- lithium-fabric-mc1.20.1-0.11.4.jar net/minecraft/class_3193$class_3724.: class/API-level gap: needs a port or shim decision, no mechanical rule
