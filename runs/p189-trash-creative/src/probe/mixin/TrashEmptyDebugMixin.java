package probe.mixin;

import net.blay09.mods.trashslot.client.TrashSlotSlot;
import net.blay09.mods.trashslot.client.deletion.DefaultDeletionProvider;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(targets = "net.blay09.mods.trashslot.client.deletion.DefaultDeletionProvider", remap = false)
public class TrashEmptyDebugMixin {
    @Inject(method = "emptyTrashSlot", at = @At("HEAD"), remap = false, require = 0)
    private void emptyHead(TrashSlotSlot slot, CallbackInfo ci) {
        System.out.println("DEBUG_EMPTY_PROVIDER trash=" + slot.method_7677());
    }
}
