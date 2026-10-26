package probe.mixin;

import com.misterpemodder.shulkerboxtooltip.ShulkerBoxTooltipClient;
import com.misterpemodder.shulkerboxtooltip.api.PreviewType;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

/**
 * p197 diagnostics: logs the mod's own key state right after each updatePreviewKeys() call and its
 * own getCurrentPreviewType() decision. This separates "the mod did not poll my keys" from "the mod
 * polled them but the renderer still chose NO_PREVIEW" - the ambiguity that made p196 misdiagnose
 * the config. Transitions only, so the log stays readable.
 */
@Mixin(ShulkerBoxTooltipClient.class)
public abstract class PreviewStateProbeMixin {
    private static Boolean lastPreview;
    private static Boolean lastFull;
    private static PreviewType lastType;

    @Inject(method = "updatePreviewKeys", at = @At("RETURN"), remap = false)
    private static void probe$updateKeys(CallbackInfo ci) {
        boolean preview = ShulkerBoxTooltipClient.isPreviewKeyPressed();
        boolean full = ShulkerBoxTooltipClient.isFullPreviewKeyPressed();
        if (lastPreview == null || lastPreview != preview || lastFull != full) {
            lastPreview = preview;
            lastFull = full;
            System.out.println("P197_KEYS preview=" + preview + " full=" + full
                    + " heldP=" + probe.ShulkerResidualProbe.previewHeld
                    + " heldF=" + probe.ShulkerResidualProbe.fullHeld);
        }
    }

    @Inject(method = "getCurrentPreviewType", at = @At("RETURN"), remap = false)
    private static void probe$previewType(boolean fullPreviewAvailable,
                                          CallbackInfoReturnable<PreviewType> cir) {
        PreviewType type = cir.getReturnValue();
        if (type != lastType) {
            lastType = type;
            System.out.println("P197_TYPE " + type + " fullAvail=" + fullPreviewAvailable);
        }
    }
}
