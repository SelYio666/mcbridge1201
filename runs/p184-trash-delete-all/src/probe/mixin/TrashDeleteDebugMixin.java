package probe.mixin;

import net.blay09.mods.trashslot.client.TrashSlotSlot;
import net.minecraft.class_1703;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(targets = "net.blay09.mods.trashslot.client.deletion.DefaultDeletionProvider", remap = false)
public class TrashDeleteDebugMixin {
    @Inject(method = "deleteContainerItem", at = @At("HEAD"), remap = false, require = 0)
    private void deleteHead(class_1703 container, int slotNumber, boolean isDeleteAll,
                            TrashSlotSlot trashSlot, CallbackInfo ci) {
        System.out.println("DEBUG_DELETE_CONTAINER slot=" + slotNumber + " all=" + isDeleteAll);
    }
}
