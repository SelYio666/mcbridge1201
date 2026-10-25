package probe.mixin;

import net.blay09.mods.trashslot.network.MessageDeleteFromSlot;
import net.minecraft.class_3222;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/** Server-side log for MessageDeleteFromSlot.handle (slot, all) and the menu identity. */
@Mixin(MessageDeleteFromSlot.class)
public class MessageDeleteDebugMixin {
    @Inject(method = "handle", at = @At("HEAD"), remap = false, require = 0)
    private static void handleHead(class_3222 player, MessageDeleteFromSlot message, CallbackInfo ci) {
        net.minecraft.class_1703 menu = player.field_7512;
        System.out.println("SERVER_DELETE slot=" + ((MessageDeleteAccessorMixin) message).mcbridge$slotNumber()
                + " all=" + ((MessageDeleteAccessorMixin) message).mcbridge$isDeleteAll()
                + " menu=" + menu.getClass().getSimpleName()
                + " menuSize=" + menu.field_7761.size()
                + " carried=" + menu.method_34255());
    }
}
