package probe.mixin;

import net.blay09.mods.trashslot.client.TrashSlotSlot;
import net.minecraft.class_1657;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(targets = "net.blay09.mods.trashslot.client.deletion.DefaultDeletionProvider", remap = false)
public class TrashProviderDebugMixin {
    @Inject(method = "undeleteLast", at = @At("HEAD"), remap = false, require = 0)
    private void debugUndelete(class_1657 player, TrashSlotSlot slot, boolean rightClick, CallbackInfo ci) {
        System.out.println("DEBUG_PROVIDER_UNDELETE trash=" + slot.method_7677()
                + " right=" + rightClick);
    }
}
