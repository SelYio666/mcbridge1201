package probe.mixin;

import net.minecraft.class_3675;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

/**
 * p197 poll boundary: the mod asks InputConstants.isKeyDown(window, code) for the code it decoded
 * from configuration.controls (ShulkerBoxTooltipClient: key.get().getCode() -> isKeyDown). The
 * GLFW poll reads the real OS keyboard, which a callback-level synthesis cannot reach on this
 * machine (p191/p193), so the probe reports held state HERE - but only for the two rebound codes
 * (F=70, G=71). Everything downstream (updatePreviewKeys -> getCurrentPreviewType -> renderer) is
 * the mod's own logic, and 340/342 (the defaults) are never satisfied, so the run can only pass if
 * the mod really polled the rebound codes.
 */
@Mixin(class_3675.class)
public class InputPollMixin {
    @Inject(method = "method_15987", at = @At("HEAD"), cancellable = true)
    private static void mcbridge$reboundPreviewKeys(long window, int code,
                                                    CallbackInfoReturnable<Boolean> cir) {
        probe.ShulkerResidualProbe.notePoll(code);
        if (code == probe.ShulkerResidualProbe.PREVIEW_CODE
                && probe.ShulkerResidualProbe.previewHeld) {
            cir.setReturnValue(true);
        } else if (code == probe.ShulkerResidualProbe.FULL_CODE
                && probe.ShulkerResidualProbe.fullHeld) {
            cir.setReturnValue(true);
        }
    }
}
