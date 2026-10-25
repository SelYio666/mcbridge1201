package probe.mixin;

import net.blay09.mods.trashslot.client.TrashSlotSlot;
import net.minecraft.class_1703;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/** Logs every creative-provider delete call (proof the creative branch ran). */
@Mixin(targets = "net.blay09.mods.trashslot.client.deletion.CreativeDeletionProvider", remap = false)
public class CreativeDeleteDebugMixin {
    @Inject(method = "deleteContainerItem", at = @At("HEAD"), remap = false, require = 0)
    private void deleteHead(class_1703 container, int slotNumber,
                            boolean isDeleteAll, TrashSlotSlot trashSlot, CallbackInfo ci) {
        System.out.println("DEBUG_CREATIVE_DELETE slot=" + slotNumber + " all=" + isDeleteAll);
    }
}
