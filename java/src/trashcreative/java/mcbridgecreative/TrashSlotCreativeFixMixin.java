package mcbridgecreative;

import net.blay09.mods.balm.api.network.BalmNetworking;
import net.blay09.mods.balm.mixin.AbstractContainerScreenAccessor;
import net.blay09.mods.trashslot.client.TrashSlotSlot;
import net.blay09.mods.trashslot.client.TrashSlotGuiHandler;
import net.blay09.mods.trashslot.client.deletion.DeletionProvider;
import net.blay09.mods.trashslot.config.TrashSlotConfig;
import net.blay09.mods.trashslot.network.MessageDeleteFromSlot;
import net.blay09.mods.trashslot.client.ModKeyMappings;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

import net.minecraft.class_1657;
import net.minecraft.class_1735;
import net.minecraft.class_310;
import net.minecraft.class_3675;
import net.minecraft.class_437;
import net.minecraft.class_481;

/**
 * 1.21.1 adaptation of TrashSlot's creative delete keys. The upstream 1.20.x branch checks
 * hoveredSlot.getClass() == Slot.class with a "SlotWrapper" fallback, but the 1.21.1 creative
 * screen (class_481) overwrites the hover handling so AbstractContainerScreen.hoveredSlot stays
 * null (p189: DEBUG_HOVERED hovered=null for creative tab slots AND hotbar slots), and the
 * SlotWrapper inner class no longer exists. The creative branch can therefore never run after the
 * conversion.
 *
 * <p>This companion re-implements the branch with 1.21.1 facts: the creative screen's menu keeps
 * the player inventory slots (hotbar at menu indices 45..53, container = PlayerInventory), and the
 * delete message resolves against the server-side InventoryMenu where the hotbar is 36..44, which
 * is exactly the upstream "index - 9" arithmetic. When the trash slot canvas exists the creative
 * provider runs (it also empties the trash - upstream creative semantics); without a canvas the
 * delete message is sent directly because the provider would dereference the null slot.
 */
@Mixin(targets = "net.blay09.mods.trashslot.client.TrashSlotGuiHandler", remap = false)
public class TrashSlotCreativeFixMixin {

    @Inject(method = "runKeyBindings", at = @At("HEAD"), cancellable = true, remap = false)
    private static void mcbridgecreative$creativeDeleteKeys(class_437 screen,
                                                            class_3675.class_307 input, int key,
                                                            int scan, int mods,
                                                            CallbackInfoReturnable<Boolean> cir) {
        try {
            mcbridgecreative$handle(screen, key, scan, mods, cir);
        } catch (Throwable t) {
            System.out.println("[mcbridge-creative] handler-throw " + t);
            t.printStackTrace();
        }
    }

    private static void mcbridgecreative$handle(class_437 screen, int key, int scan, int mods,
                                                CallbackInfoReturnable<Boolean> cir) {
        DeletionProvider provider = TrashSlotConfig.getDeletionProvider();
        if (key == 261) {
            System.out.println("[mcbridge-creative] head key=261 provider=" + (provider == null
                    ? "null" : provider.getClass().getSimpleName())
                    + " screen=" + screen.getClass().getName());
        }
        if (provider == null || !(screen instanceof class_481 creative)) {
            return;
        }
        boolean isDelete = ModKeyMappings.keyBindDelete.isActiveAndMatchesKey(key, scan, mods);
        boolean isDeleteAll = ModKeyMappings.keyBindDeleteAll.isActiveAndMatchesKey(key, scan, mods);
        if ((!isDelete && !isDeleteAll) || !TrashSlotConfig.getActive().enableDeleteKeysInCreative) {
            return;
        }
        class_310 client = class_310.method_1551();
        class_1657 player = client.field_1724;
        if (player == null) {
            return;
        }
        // Mouse position in gui-scaled coordinates: the raw mouse position is window-relative
        // (verified p188: method_1603/1604 return window px), the gui scale from the window.
        double scale = client.method_22683().method_4495();
        double mouseX = client.field_1729.method_1603() / scale;
        double mouseY = client.field_1729.method_1604() / scale;
        var accessor = (AbstractContainerScreenAccessor) creative;
        TrashSlotSlot trashSlot = TrashSlotGuiHandler.getTrashSlot();
        if (key == 261) {
            StringBuilder dump = new StringBuilder("[mcbridge-creative] hover-dump mouse=("
                    + mouseX + "," + mouseY + ")");
            for (class_1735 slot : player.field_7512.field_7761) {
                if (slot.field_7871 == player.method_31548()) {
                    dump.append(" [").append(slot.field_7874).append("](")
                            .append(slot.field_7873).append(',').append(slot.field_7872)
                            .append(")h=").append(accessor.callIsHovering(slot, mouseX, mouseY));
                }
            }
            System.out.println(dump);
        }
        for (class_1735 slot : player.field_7512.field_7761) {
            if (slot.field_7871 != player.method_31548()) {
                continue;
            }
            if (!accessor.callIsHovering(slot, mouseX, mouseY)) {
                continue;
            }
            // Hotbar slots sit at menu indices 45..53 in the creative menu; the delete message
            // resolves against the server-side InventoryMenu where the hotbar is 36..44.
            int menuIndex = slot.field_7874;
            if (menuIndex < 45 || menuIndex > 53) {
                continue;
            }
            int slotNumber = menuIndex - 9;
            DeletionProvider creativeProvider = TrashSlotConfig.getCreativeDeletionProvider();
            if (trashSlot != null) {
                creativeProvider.deleteContainerItem(player.field_7512, slotNumber,
                        isDeleteAll, trashSlot);
            } else {
                // No trash canvas on the creative screen: the provider would dereference the
                // null slot when emptying it, so send the delete message directly through the
                // fabric client networking channel the converted mod registered.
                BalmNetworking networking = net.blay09.mods.balm.api.Balm.getNetworking();
                top.mcbridge1201.bridge.BalmNetworkingBridge.sendToServer(networking,
                        new MessageDeleteFromSlot(slotNumber, isDeleteAll));
            }
            System.out.println("[mcbridge-creative] delete slotNumber=" + slotNumber
                    + " all=" + isDeleteAll + " canvas=" + (trashSlot != null));
            cir.setReturnValue(true);
            return;
        }
    }
}
