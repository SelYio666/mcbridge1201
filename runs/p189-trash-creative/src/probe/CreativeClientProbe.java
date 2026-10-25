package probe;

import net.blay09.mods.balm.mixin.AbstractContainerScreenAccessor;
import net.blay09.mods.trashslot.client.TrashSlotGuiHandler;
import net.blay09.mods.trashslot.client.TrashSlotSlot;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.minecraft.class_1735;
import net.minecraft.class_1792;
import net.minecraft.class_1799;
import net.minecraft.class_1802;
import net.minecraft.class_481;
import net.minecraft.class_7699;

/**
 * p189 client probe (creative delete keys): opens the creative inventory and repeatedly logs the
 * geometry of every hotbar slot that holds diamonds, so the harness can hover them. TrashSlot's
 * creative branch runs for SlotWrapper hotbar slots on any creative tab, so no tab switch is
 * needed; the diamonds are placed server-side (/item replace on the hotbar) and sync to the
 * client's real inventory.
 */
public final class CreativeClientProbe implements ClientModInitializer {
    private int ticks;
    private boolean opened;

    @Override
    public void onInitializeClient() {
        ClientTickEvents.END_CLIENT_TICK.register(client -> {
            if (client.field_1724 == null) {
                return;
            }
            ticks++;
            if (!opened && ticks == 60 && client.field_1755 == null) {
                client.method_1507(new class_481(client.field_1724,
                        class_7699.method_45397(), false));
                opened = true;
                System.out.println("CRE_OPEN tick=" + ticks);
            }
            if (ticks == 62) {
                System.out.println("CRE_SCREENCHECK screen="
                        + (client.field_1755 == null ? "null" : client.field_1755.getClass().getName()));
            }
            if (opened && client.field_1755 instanceof class_481
                    && ticks % 40 == 0) {
                TrashSlotSlot trash = TrashSlotGuiHandler.getTrashSlot();
                int i = 0;
                var accessor = (net.blay09.mods.balm.mixin.AbstractContainerScreenAccessor)
                        client.field_1755;
                for (class_1735 slot : client.field_1724.field_7512.field_7761) {
                    class_1799 stack = slot.method_7677();
                    System.out.println("CRE_SLOT left=" + accessor.getLeftPos()
                            + " top=" + accessor.getTopPos()
                            + " i=" + i
                            + " class=" + slot.getClass().getSimpleName()
                            + " container=" + slot.field_7871.getClass().getSimpleName()
                            + " slotIndex=" + slot.field_7874
                            + " x=" + slot.field_7873 + " y=" + slot.field_7872
                            + " item=" + (stack.method_7960() ? "empty"
                                    : stack.method_7909() + "x" + stack.method_7947())
                            + " trash=" + (trash == null ? "null" : trash.method_7677()));
                    i++;
                }
            }
        });
    }
}
