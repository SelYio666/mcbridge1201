# CenturyBridge conversion report (1.20.1 -> 1.21.1, 7 segments)

## immediatelyfast -- ok_degraded_partial
- kept L2 mixin (target sig changed@1.20.6->1.21): MixinVertexConsumerProvider
- minecraft dep -> 1.21.1
- output: ImmediatelyFast-Fabric-1.5.5+1.20.4+1.21.1.jar
- stripped mixin: MixinBufferBuilder [load-bearing! may be unstable] -- L3@1.20.6->1.21: shadow-field field_1555
- stripped mixin: MixinMinecraftClient -- L2@1.20.4->1.20.5: inject-target method_1481
- stripped mixin: MixinVertexBuffer -- L2@1.20.6->1.21: inject-target method_43442; L2@1.20.6->1.21: inject-target method_43443
- stripped mixin: MixinFontManager -- L3@1.20.4->1.20.5: shadow-field field_24256; L3@1.20.4->1.20.5: shadow method_27542; L3@1.20.4->1.20.5: inject-target method_27541
- stripped mixin: MixinChatHud -- L2@1.20.4->1.20.5: inject-target method_1805; L2@1.20.4->1.20.5: inject-target method_1805
- stripped mixin: MixinInGameHud -- L2@1.20.4->1.20.5: inject-target method_1736; L2@1.20.4->1.20.5: inject-target method_1765; L2@1.20.4->1.20.5: inject-target method_1759; L2@1.20.4->1.20.5: inject-target method_1736; L2@1.20.4->1.20.5: inject-target method_1765; L2@1.20.4->1.20.5: inject-target method_1759; L2@1.20.4->1.20.5: inject-target method_1759
- stripped mixin: MixinBufferRenderer -- L2@1.20.6->1.21: inject-target method_43437; L2@1.20.6->1.21: inject-target method_43438
- stripped mixin: MixinMapRenderer [load-bearing! may be unstable] -- L2@1.20.4->1.20.5: inject-target method_32601
- L2 field @1.20.6->1.21: class_4597$class_4598.field_20953
- L2 method @1.20.4->1.20.5: class_377.method_2004
- L2 method @1.20.6->1.21: class_4597.method_22991
- L3 constructor: class_287.<init>(I)V
- L3 constructor: class_2960.<init>(Ljava/lang/String;)V
- L3 constructor: class_4597$class_4598.<init>(Lnet/minecraft/class_287;Ljava/util/Map;)V
- L3 field @1.20.4->1.20.5: class_377.field_2247
- tombstoned (lazy-fail) @1.20.6->1.21: net/minecraft/class_1921.method_23012(Lnet/minecraft/class_287;Lnet/minecraft/class_8251;)V
- tombstoned (lazy-fail) @1.20.6->1.21: net/minecraft/class_1921.method_24296()Ljava/util/Optional;
- tombstoned (lazy-fail) @1.20.6->1.21: net/minecraft/class_287$class_7433.method_43585()V
- tombstoned (lazy-fail) @1.20.6->1.21: net/minecraft/class_287.method_1326()Lnet/minecraft/class_287$class_7433;
- tombstoned (lazy-fail) @1.20.6->1.21: net/minecraft/class_287.method_1328(Lnet/minecraft/class_293$class_5596;Lnet/minecraft/class_293;)V
- tombstoned (lazy-fail) @1.20.6->1.21: net/minecraft/class_287.method_22893()Z
- tombstoned (lazy-fail) @1.20.6->1.21: net/minecraft/class_289.method_1349()Lnet/minecraft/class_287;
- tombstoned (lazy-fail) @1.20.6->1.21: net/minecraft/class_4588.method_1344()V
- tombstoned (lazy-fail) @1.20.6->1.21: net/minecraft/class_4588.method_22916(I)Lnet/minecraft/class_4588;
