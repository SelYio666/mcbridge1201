package p202probe.mixin;

import java.util.List;
import java.util.Optional;

import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

import net.minecraft.class_327;
import net.minecraft.class_332;
import net.minecraft.class_5632;

/**
 * Records what actually reaches the vanilla tooltip renderer. A tooltip only exists for a hovered
 * slot, so DRAWTOOLTIP with the mod's PreviewTooltipData is the last link of the hover chain -
 * and it is emitted by the game, not by the probe.
 */
@Mixin(class_332.class)
public abstract class DrawTooltipProbeMixin {

    @Inject(method = "method_51437(Lnet/minecraft/class_327;Ljava/util/List;Ljava/util/Optional;II)V",
            at = @At("HEAD"))
    private void p202$drawTooltip(class_327 textRenderer, List<?> text,
                                  Optional<class_5632> data, int x, int y, CallbackInfo ci) {
        if (data.isPresent()) {
            System.out.println("P202_TOOLTIP lines=" + text.size()
                    + " data=" + data.get().getClass().getName()
                    + " at=" + x + "," + y);
        }
    }
}
