# Rule suggestions

plan: work\plan-corpus.json (sha256 946b9827fc11)

| id | kind | confidence | target | note |
|---|---|---|---|---|
| savewithfullmetadata.callsite | callSiteAdaptation | high | net/minecraft/class_2586.method_38242 | bridge receives the old stack shape and must implement the 1.21.1 call; confidence covers the identity mapping, not the bridge body. instance call: bridge receives the receiver as first argument |
| appendhovertext.callsite | callSiteAdaptation | high | net/minecraft/class_1792.method_7851 | bridge receives the old stack shape and must implement the 1.21.1 call; confidence covers the identity mapping, not the bridge body. instance call: bridge receives the receiver as first argument |
| readblockpos.callsite | callSiteAdaptation | high | net/minecraft/class_2512.method_10691 | bridge receives the old stack shape and must implement the 1.21.1 call; confidence covers the identity mapping, not the bridge body. static call: bridge signature equals the old descriptor |
| fromjson.callsite | callSiteAdaptation | high | net/minecraft/class_2561$class_2562.method_10877 | bridge receives the old stack shape and must implement the 1.21.1 call; confidence covers the identity mapping, not the bridge body. static call: bridge signature equals the old descriptor |
| writeblockpos.callsite | callSiteAdaptation | high | net/minecraft/class_2512.method_10692 | bridge receives the old stack shape and must implement the 1.21.1 call; confidence covers the identity mapping, not the bridge body. static call: bridge signature equals the old descriptor |
| tojson.callsite | callSiteAdaptation | high | net/minecraft/class_2561$class_2562.method_10867 | bridge receives the old stack shape and must implement the 1.21.1 call; confidence covers the identity mapping, not the bridge body. static call: bridge signature equals the old descriptor |
| hurtandbreak.callsite | callSiteAdaptation | high | net/minecraft/class_1799.method_7956 | bridge receives the old stack shape and must implement the 1.21.1 call; confidence covers the identity mapping, not the bridge body. instance call: bridge receives the receiver as first argument |
| savewithid.callsite | callSiteAdaptation | high | net/minecraft/class_2586.method_38243 | bridge receives the old stack shape and must implement the 1.21.1 call; confidence covers the identity mapping, not the bridge body. instance call: bridge receives the receiver as first argument |
| movement-slowdown.callsite | callSiteAdaptation | high | net/minecraft/class_1294.field_5909 | bridge receives the old stack shape and must implement the 1.21.1 call; confidence covers the identity mapping, not the bridge body. call shape unknown (stub lookup failed): verify the receiver by hand |
| dig-slowdown.callsite | callSiteAdaptation | high | net/minecraft/class_1294.field_5901 | bridge receives the old stack shape and must implement the 1.21.1 call; confidence covers the identity mapping, not the bridge body. call shape unknown (stub lookup failed): verify the receiver by hand |
| writenbt.callsite | callSiteAdaptation | high | net/minecraft/class_2540.method_10794 | bridge receives the old stack shape and must implement the 1.21.1 call; confidence covers the identity mapping, not the bridge body. instance call: bridge receives the receiver as first argument |
| gettooltiplines.callsite | callSiteAdaptation | high | net/minecraft/class_1799.method_7950 | bridge receives the old stack shape and must implement the 1.21.1 call; confidence covers the identity mapping, not the bridge body. instance call: bridge receives the receiver as first argument |
| computeifabsent.callsite | callSiteAdaptation | high | net/minecraft/class_26.method_17924 | bridge receives the old stack shape and must implement the 1.21.1 call; confidence covers the identity mapping, not the bridge body. instance call: bridge receives the receiver as first argument |
| c1293.-init-.callsite | callSiteAdaptation | medium | net/minecraft/class_1293.<init> | bridge receives the old stack shape and must implement the 1.21.1 call; confidence covers the identity mapping, not the bridge body. instance call: bridge receives the receiver as first argument |
| load.callsite | callSiteAdaptation | medium | net/minecraft/class_2586.method_11014 | bridge receives the old stack shape and must implement the 1.21.1 call; confidence covers the identity mapping, not the bridge body. instance call: bridge receives the receiver as first argument |
| save.retarget | methodRedirect | medium | net/minecraft/class_1799.method_7953 | net.minecraft.world.item.ItemStack.save is method_57379 (Lkp;Ljava/lang/Object;)Ljava/lang/Object; in 1.21.1; descriptor differs, bridge must convert. instance call: bridge receives the receiver as first argument |

## Dropped (would conflict with existing rules)

- load.callsite-2: an existing rule already covers this exact match key
- loadallitems.callsite: an existing rule already covers this exact match key
- saveadditional.callsite: an existing rule already covers this exact match key
- saveallitems.callsite: an existing rule already covers this exact match key

## No mechanical draft (needs human decision)

-  net/minecraft/class_1799.method_7948: no getOrCreateTag continuation in 1.21.1 net.minecraft.world.item.ItemStack; needs a semantic port, not a mechanical rule
-  net/minecraft/class_1799.method_7969: no getTag continuation in 1.21.1 net.minecraft.world.item.ItemStack; needs a semantic port, not a mechanical rule
-  net/minecraft/class_1799.method_7985: no hasTag continuation in 1.21.1 net.minecraft.world.item.ItemStack; needs a semantic port, not a mechanical rule
-  net/minecraft/class_2096.method_9038: no getMin continuation in 1.21.1 net.minecraft.advancements.critereon.MinMaxBounds; needs a semantic port, not a mechanical rule
-  net/minecraft/class_1799.method_7980: no setTag continuation in 1.21.1 net.minecraft.world.item.ItemStack; needs a semantic port, not a mechanical rule
-  net/minecraft/class_1860.method_8114: no getId continuation in 1.21.1 net.minecraft.world.item.crafting.Recipe; needs a semantic port, not a mechanical rule
-  net/minecraft/class_4588.method_23763: no normal continuation in 1.21.1 com.mojang.blaze3d.vertex.VertexConsumer; needs a semantic port, not a mechanical rule
-  net/minecraft/class_4588.method_1344: no endVertex continuation in 1.21.1 com.mojang.blaze3d.vertex.VertexConsumer; needs a semantic port, not a mechanical rule
-  net/minecraft/class_2090.field_9685: no ANY continuation in 1.21.1 net.minecraft.advancements.critereon.LocationPredicate; needs a semantic port, not a mechanical rule
-  net/minecraft/class_2096.method_9042: no getMax continuation in 1.21.1 net.minecraft.advancements.critereon.MinMaxBounds; needs a semantic port, not a mechanical rule
-  net/minecraft/class_7923.field_41176: no ENCHANTMENT continuation in 1.21.1 net.minecraft.core.registries.BuiltInRegistries; needs a semantic port, not a mechanical rule
-  net/minecraft/class_1657.method_20236: no broadcastBreakEvent continuation in 1.21.1 net.minecraft.world.entity.LivingEntity; needs a semantic port, not a mechanical rule
-  net/minecraft/class_1799.method_7938: no hasCustomHoverName continuation in 1.21.1 net.minecraft.world.item.ItemStack; needs a semantic port, not a mechanical rule
-  net/minecraft/class_2073.field_9640: no ANY continuation in 1.21.1 net.minecraft.advancements.critereon.ItemPredicate; needs a semantic port, not a mechanical rule
-  net/minecraft/class_332.method_48587: no blitNineSliced continuation in 1.21.1 net.minecraft.client.gui.GuiGraphics; needs a semantic port, not a mechanical rule
-  net/minecraft/class_161$class_162.method_698: no serializeToJson continuation in 1.21.1 net.minecraft.advancements.Advancement$Builder; needs a semantic port, not a mechanical rule
-  net/minecraft/class_2102.field_9709: no ANY continuation in 1.21.1 net.minecraft.advancements.critereon.MobEffectsPredicate; needs a semantic port, not a mechanical rule
-  net/minecraft/class_2040.field_9581: no ANY continuation in 1.21.1 net.minecraft.advancements.critereon.EntityFlagsPredicate; needs a semantic port, not a mechanical rule
-  net/minecraft/class_2048.field_9599: no ANY continuation in 1.21.1 net.minecraft.advancements.critereon.EntityPredicate; needs a semantic port, not a mechanical rule
- ironchests-5.0.2-fabric.jar net/minecraft/class_2444.: class/API-level gap: needs a port or shim decision, no mechanical rule
- ironchests-5.0.2-fabric.jar net/fabricmc/fabric/api/client/model/ExtraModelProvider.: class/API-level gap: needs a port or shim decision, no mechanical rule
- ironchests-5.0.2-fabric.jar net/fabricmc/fabric/api/networking/v1/ServerPlayNetworking$PlayChannelHandler.: class/API-level gap: needs a port or shim decision, no mechanical rule
- ironchests-5.0.2-fabric.jar net/fabricmc/fabric/api/client/networking/v1/ClientPlayNetworking$PlayChannelHandler.: class/API-level gap: needs a port or shim decision, no mechanical rule
- ironchests-5.0.2-fabric.jar net/fabricmc/fabric/api/client/model/BakedModelManagerHelper.: class/API-level gap: needs a port or shim decision, no mechanical rule
- ironchests-5.0.2-fabric.jar net/fabricmc/fabric/api/client/model/ModelLoadingRegistry.: class/API-level gap: needs a port or shim decision, no mechanical rule
- ironchests-5.0.2-fabric.jar net/fabricmc/fabric/api/client/model/ModelLoadingRegistry.: class/API-level gap: needs a port or shim decision, no mechanical rule
- ironchests-5.0.2-fabric.jar net/fabricmc/fabric/api/client/model/ModelLoadingRegistry.: class/API-level gap: needs a port or shim decision, no mechanical rule
- ironchests-5.0.2-fabric.jar net/fabricmc/fabric/api/networking/v1/ServerPlayNetworking.: class/API-level gap: needs a port or shim decision, no mechanical rule
- ironchests-5.0.2-fabric.jar net/fabricmc/fabric/api/networking/v1/ServerPlayNetworking.: class/API-level gap: needs a port or shim decision, no mechanical rule
- ironchests-5.0.2-fabric.jar net/fabricmc/fabric/api/screenhandler/v1/ExtendedScreenHandlerType.: class/API-level gap: needs a port or shim decision, no mechanical rule
- ironchests-5.0.2-fabric.jar net/fabricmc/fabric/api/client/networking/v1/ClientPlayNetworking.: class/API-level gap: needs a port or shim decision, no mechanical rule
- ironchests-5.0.2-fabric.jar net/fabricmc/fabric/api/client/networking/v1/ClientPlayNetworking.: class/API-level gap: needs a port or shim decision, no mechanical rule
