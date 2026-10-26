package probe.mixin;

import net.minecraft.class_3675;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

/**
 * Boundary synthesis at the GLFW POLL level (p191 philosophy at the other end): the mod checks
 * the full-preview key with InputConstants.isKeyDown(window, 342), which reads the OS keyboard
 * state - unreachable from a callback and flaky through keybd_event on this machine (focus
 * races). While the probe requests it, report RIGHT_SHIFT as held; everything downstream
 * (getCurrentPreviewType -> FULL) is the mod's real logic.
 */
@Mixin(class_3675.class)
public class InputPollMixin {
    @Inject(method = "method_15987", at = @At("HEAD"), cancellable = true)
    private static void mcbridge$holdFullPreviewKey(long window, int code,
                                                    CallbackInfoReturnable<Boolean> cir) {
        if (code == 342 && probe.ShulkerResidualProbe.fullPollActive) {
            cir.setReturnValue(true);
        }
    }
}
