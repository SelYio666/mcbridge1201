package net.raphimc.immediatelyfast.injection.mixins.core;

import net.minecraft.class_310;
import net.raphimc.immediatelyfast.feature.core.BenchHooks;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/**
 * Benchmark-only sampler: prints the client FPS every ~2s from the main loop. It lives in the
 * always-enabled "core" package so it keeps working when hud_batching (and its mixin package)
 * is disabled in the A/B run.
 */
@Mixin(class_310.class)
public abstract class MixinMinecraftClientBench {

    private static final boolean ENABLED = Boolean.getBoolean("mcbridge.bench");

    @Inject(method = {"method_1523"}, at = {@At("HEAD")})
    private void immediatelyFast$sampleFps(CallbackInfo ci) {
        if (!ENABLED) {
            return;
        }
        long now = System.currentTimeMillis();
        if (now - BenchHooks.lastFpsLog > 2000) {
            BenchHooks.lastFpsLog = now;
            try {
                System.out.println("[mcbridge-port] fps=" + class_310.method_1551().method_47599());
            } catch (Throwable ignored) {
                // client not ready
            }
        }
    }
}
