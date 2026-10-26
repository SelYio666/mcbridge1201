package probe.mixin;

import com.misterpemodder.shulkerboxtooltip.impl.tooltip.PreviewTooltipData;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

import java.util.Optional;

import net.minecraft.class_1799;
import net.minecraft.class_5632;

/**
 * Traces the converted mod's own fabric/ItemStackMixin.onGetTooltipData: whether it runs for the
 * hovered stack, whether it cancels, and which provider ends up in its PreviewTooltipData.
 * The mixin target is a class_1799 mixin, so `this` is the hovered stack.
 */
@Mixin(com.misterpemodder.shulkerboxtooltip.mixin.client.fabric.ItemStackMixin.class)
public abstract class ModTooltipDataProbeMixin {

    @Inject(method = "onGetTooltipData", at = @At("HEAD"), remap = false)
    private void probe$enter(CallbackInfoReturnable<Optional<class_5632>> cir) {
        class_1799 self = (class_1799) (Object) this;
        System.out.println("MODDATA enter item=" + self.method_7909()
                + " count=" + self.method_7947());
    }

    @Inject(method = "onGetTooltipData", at = @At("RETURN"), remap = false)
    private void probe$return(CallbackInfoReturnable<Optional<class_5632>> cir) {
        Optional<class_5632> value = cir.getReturnValue();
        Object provider = null;
        if (value.isPresent() && value.get() instanceof PreviewTooltipData data) {
            provider = data.provider();
        }
        System.out.println("MODDATA return present=" + value.isPresent()
                + " data=" + (value.isPresent() ? value.get().getClass().getName() : "-")
                + " provider=" + (provider == null ? "-" : provider.getClass().getName()));
    }
}
