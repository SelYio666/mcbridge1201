package probe.mixin;

import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

import java.util.List;
import java.util.Optional;

import net.minecraft.class_332;
import net.minecraft.class_327;
import net.minecraft.class_5632;

/**
 * Logs what tooltip data reaches the vanilla tooltip renderer
 * (DrawContext.drawTooltip(TextRenderer, List, Optional, int, int)).
 */
@Mixin(class_332.class)
public abstract class DrawTooltipProbeMixin {

    @Inject(method = "method_51437(Lnet/minecraft/class_327;Ljava/util/List;Ljava/util/Optional;II)V",
            at = @At("HEAD"))
    private void probe$drawTooltip(class_327 textRenderer, List<?> text,
                                   Optional<class_5632> data, int x, int y, CallbackInfo ci) {
        if (data.isPresent()) {
            System.out.println("DRAWTOOLTIP lines=" + text.size()
                    + " data=" + data.get().getClass().getName());
        }
    }
}
