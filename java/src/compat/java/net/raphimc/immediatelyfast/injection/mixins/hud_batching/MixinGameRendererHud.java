package net.raphimc.immediatelyfast.injection.mixins.hud_batching;

import net.minecraft.class_329;
import net.minecraft.class_332;
import net.minecraft.class_757;
import net.minecraft.class_9779;
import net.raphimc.immediatelyfast.ImmediatelyFast;
import net.raphimc.immediatelyfast.feature.batching.BatchingBuffers;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Redirect;

/**
 * 1.21.1 HUD batching wrapper. Upstream uses MixinExtras WrapOperation around
 * InGameHud.render(DrawContext, TickCounter) inside GameRenderer.method_3192; a plain @Redirect
 * is equivalent here and avoids the MixinExtras dependency.
 */
@Mixin(class_757.class)
public abstract class MixinGameRendererHud {

    @Redirect(method = {"method_3192"},
              at = @At(value = "INVOKE",
                       target = "Lnet/minecraft/class_329;method_1753(Lnet/minecraft/class_332;Lnet/minecraft/class_9779;)V"))
    private void hudBatching(class_329 instance, class_332 context, class_9779 tickCounter) {
        if (ImmediatelyFast.runtimeConfig.hud_batching) {
            BatchingBuffers.runBatched(context, () -> instance.method_1753(context, tickCounter));
        } else {
            instance.method_1753(context, tickCounter);
        }
    }
}
