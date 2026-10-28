package p202probe.mixin;

import net.minecraft.class_3675;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

/**
 * Same poll boundary as p197: the mod asks InputConstants.isKeyDown(window, code) for the code it
 * decoded from configuration.controls. The probe forges held state here for the two rebound codes
 * only (J=74, K=75), so a COMPACT/FULL render can only happen if the mod polled those codes;
 * the defaults (340/342) can never satisfy this mixin.
 *
 * p202 sends these keys only after P202_HOVER_OK, so the hover evidence does not depend on them.
 */
@Mixin(class_3675.class)
public class InputPollMixin {
    @Inject(method = "method_15987", at = @At("HEAD"), cancellable = true)
    private static void p202$reboundPreviewKeys(long window, int code,
                                                CallbackInfoReturnable<Boolean> cir) {
        p202probe.HoverNbtProbe.notePoll(code);
        if (code == p202probe.HoverNbtProbe.PREVIEW_CODE
                && p202probe.HoverNbtProbe.previewHeld) {
            cir.setReturnValue(true);
        } else if (code == p202probe.HoverNbtProbe.FULL_CODE
                && p202probe.HoverNbtProbe.fullHeld) {
            cir.setReturnValue(true);
        }
    }
}
