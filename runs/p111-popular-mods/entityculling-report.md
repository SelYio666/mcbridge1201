# CenturyBridge conversion report (1.20.1 -> 1.21.1, 7 segments)

## entityculling -- ok_degraded_partial
- minecraft dep -> 1.21.1
- output: entityculling-fabric-1.11.3-mc1.20.1+1.21.1.jar
- stripped mixin: EntityRendererMixin [load-bearing! may be unstable] -- L2@1.20.4->1.20.5: shadow method_3926
- (bundled) L2 method @1.20.1->1.20.2: class_1735.method_48931
- (bundled) L2 method @1.20.1->1.20.2: class_437.method_25401
- (bundled) L2 method @1.20.1->1.20.2: class_437.method_25420
- (bundled) L2 method @1.20.6->1.21: class_286.method_43433
- (bundled) L2 method @1.20.6->1.21: class_4597.method_22991
- (bundled) L3 constructor: class_2658.<init>(Lnet/minecraft/class_2960;Lnet/minecraft/class_2540;)V
- (bundled) L3 constructor: class_2817.<init>(Lnet/minecraft/class_2960;Lnet/minecraft/class_2540;)V
- (bundled) L3 constructor: class_2960.<init>(Ljava/lang/String;)V
- (bundled) L3 constructor: class_370.<init>(Lnet/minecraft/class_370$class_371;Lnet/minecraft/class_2561;Lnet/minecraft/class_2561;)V
- (bundled) L3 field @1.20.2->1.20.3: class_370$class_371.field_2218
- (bundled) tombstoned (lazy-fail) @1.20.1->1.20.2: net/minecraft/class_1071.method_4654(Lcom/mojang/authlib/GameProfile;)Ljava/util/Map;
- (bundled) tombstoned (lazy-fail) @1.20.1->1.20.2: net/minecraft/class_1071.method_4656(Lcom/mojang/authlib/minecraft/MinecraftProfileTexture;Lcom/mojang/authlib/minecraft/MinecraftProfileTexture$Type;)Lnet/minecraft/class_2960;
- (bundled) tombstoned (lazy-fail) @1.20.1->1.20.2: net/minecraft/class_634.method_2883(Lnet/minecraft/class_2596;)V
- (bundled) tombstoned (lazy-fail) @1.20.1->1.20.2: net/minecraft/class_742.method_3117()Lnet/minecraft/class_2960;
- (bundled) tombstoned (lazy-fail) @1.20.1->1.20.2: net/minecraft/class_742.method_3119()Lnet/minecraft/class_2960;
- (bundled) tombstoned (lazy-fail) @1.20.4->1.20.5: net/minecraft/class_1799.method_7938()Z
- (bundled) tombstoned (lazy-fail) @1.20.4->1.20.5: net/minecraft/class_1799.method_7969()Lnet/minecraft/class_2487;
- (bundled) tombstoned (lazy-fail) @1.20.4->1.20.5: net/minecraft/class_1799.method_7985()Z
- (bundled) tombstoned (lazy-fail) @1.20.4->1.20.5: net/minecraft/class_2512.method_10683(Lnet/minecraft/class_2487;)Lcom/mojang/authlib/GameProfile;
- (bundled) tombstoned (lazy-fail) @1.20.6->1.21: net/minecraft/class_287.method_1326()Lnet/minecraft/class_287$class_7433;
- (bundled) tombstoned (lazy-fail) @1.20.6->1.21: net/minecraft/class_287.method_1328(Lnet/minecraft/class_293$class_5596;Lnet/minecraft/class_293;)V
- (bundled) tombstoned (lazy-fail) @1.20.6->1.21: net/minecraft/class_289.method_1349()Lnet/minecraft/class_287;
- (bundled) tombstoned (lazy-fail) @1.20.6->1.21: net/minecraft/class_4588.method_1344()V
