package mcbfixture.mixin;

import net.minecraft.class_1309;
import net.minecraft.class_1792;
import net.minecraft.class_1799;
import net.minecraft.class_1937;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/**
 * Mixin coverage with a real intermediary target: the injector points at a 1.20.1 member name and
 * a four-argument callback. A conversion that changes the target descriptor has to migrate the
 * callback signature together with the {@code @Inject(method=...)} string, or Mixin refuses it.
 */
@Mixin(class_1792.class)
public abstract class FixtureMixin {
    @Inject(method = "method_7852", at = @At("HEAD"))
    private void mcbfixture$beforeUse(class_1937 world, class_1309 user, class_1799 stack, int remaining,
                                      CallbackInfo ci) {
    }
}
