package probe.mixin;

import net.blay09.mods.balm.mixin.AbstractContainerScreenAccessor;
import net.blay09.mods.trashslot.config.TrashSlotConfig;
import net.minecraft.class_437;
import net.minecraft.class_465;
import net.minecraft.class_3675;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

/**
 * p189 diagnostic: dumps the hovered slot and the creative flag at runKeyBindings RETURN, so a
 * missed creative branch can be attributed (null hovered slot vs config flag vs class check).
 */
@Mixin(targets = "net.blay09.mods.trashslot.client.TrashSlotGuiHandler", remap = false)
public class TrashHoverDebugMixin {
    @Inject(method = "runKeyBindings", at = @At("RETURN"), remap = false, require = 0)
    private static void runHover(class_437 screen, class_3675.class_307 input, int key, int scan,
                                 int mods, CallbackInfoReturnable<Boolean> cir) {
        if (!(screen instanceof class_465<?> containerScreen)) {
            return;
        }
        net.minecraft.class_1735 hovered =
                ((AbstractContainerScreenAccessor) containerScreen).getHoveredSlot();
        System.out.println("DEBUG_HOVERED ret=" + cir.getReturnValue()
                + " key=" + key + " mods=" + mods
                + " creativeFlag=" + TrashSlotConfig.getActive().enableDeleteKeysInCreative
                + " hovered=" + (hovered == null ? "null"
                        : hovered.getClass().getSimpleName() + " slotIndex=" + hovered.field_7874
                        + " container=" + hovered.field_7871.getClass().getSimpleName()
                        + " item=" + hovered.method_7677()));
    }
}
