package probe.mixin;

import net.blay09.mods.trashslot.TrashHelper;
import net.blay09.mods.trashslot.network.MessageTrashSlotClick;
import net.minecraft.class_1799;
import net.minecraft.class_3222;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

import java.lang.reflect.Field;

@Mixin(targets = "net.blay09.mods.trashslot.network.MessageTrashSlotClick", remap = false)
public class TrashPacketDebugMixin {
    private static Object field(Object target, String name) {
        try {
            Field f = target.getClass().getDeclaredField(name);
            f.setAccessible(true);
            return f.get(target);
        } catch (ReflectiveOperationException e) {
            return "ERR:" + e;
        }
    }

    @Inject(method = "handle", at = @At("HEAD"), remap = false, require = 0)
    private static void debugHandleHead(class_3222 player, MessageTrashSlotClick message, CallbackInfo ci) {
        System.out.println("DEBUG_PACKET_HEAD msg=" + field(message, "itemStack")
                + " right=" + field(message, "isRightClick")
                + " serverCarried=" + player.field_7512.method_34255()
                + " serverTrash=" + TrashHelper.getTrashItem(player));
    }

    @Inject(method = "handle", at = @At("RETURN"), remap = false, require = 0)
    private static void debugHandleReturn(class_3222 player, MessageTrashSlotClick message, CallbackInfo ci) {
        System.out.println("DEBUG_PACKET_RETURN serverCarried="
                + player.field_7512.method_34255()
                + " serverTrash=" + TrashHelper.getTrashItem(player));
    }
}
