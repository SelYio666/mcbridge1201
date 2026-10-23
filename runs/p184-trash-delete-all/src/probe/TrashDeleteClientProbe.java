package probe;

import net.blay09.mods.balm.mixin.AbstractContainerScreenAccessor;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.minecraft.class_1735;
import net.minecraft.class_1799;
import net.minecraft.class_1802;
import net.minecraft.class_465;
import net.minecraft.class_490;

/** p184 client probe: open the inventory, log the first diamond slot geometry and counts. */
public final class TrashDeleteClientProbe implements ClientModInitializer {
    private int clientTicks;
    private boolean opened;

    @Override
    public void onInitializeClient() {
        ClientTickEvents.END_CLIENT_TICK.register(client -> {
            if (client.field_1724 == null) {
                return;
            }
            clientTicks++;
            if (clientTicks == 20 || clientTicks == 150 || clientTicks == 180) {
                var trash = net.blay09.mods.trashslot.client.TrashSlotGuiHandler.getTrashSlot();
                if (trash != null) {
                    trash.method_7673(class_1799.field_8037);
                    System.out.println("DELETE_TRASH_CLEAR tick=" + clientTicks);
                }
            }
            if (clientTicks == 80 && client.field_1755 == null) {
                client.method_1507(new class_490(client.field_1724));
                opened = true;
                System.out.println("DELETE_INV_OPEN");
            }
            if (!opened) {
                return;
            }
            if (clientTicks == 100 && client.field_1755 instanceof class_465<?> screen) {
                var accessor = (AbstractContainerScreenAccessor) screen;
                double scale = client.method_22683().method_4495();
                System.out.println("DELETE_SCREEN left=" + accessor.getLeftPos()
                        + " top=" + accessor.getTopPos()
                        + " scale=" + scale);
                for (int i = 0; i < client.field_1724.field_7512.field_7761.size(); i++) {
                    class_1735 slot = client.field_1724.field_7512.field_7761.get(i);
                    class_1799 stack = slot.method_7677();
                    if (!stack.method_7960() && stack.method_7909() == class_1802.field_8477) {
                        System.out.println("DELETE_SLOT index=" + i
                                + " x=" + slot.field_7873
                                + " y=" + slot.field_7872
                                + " count=" + stack.method_7947());
                        break;
                    }
                }
            }
            if ((clientTicks - 100) % 40 == 0 && clientTicks > 100) {
                int total = 0;
                for (int i = 0; i < client.field_1724.field_7512.field_7761.size(); i++) {
                    class_1799 stack = client.field_1724.field_7512.field_7761.get(i).method_7677();
                    if (stack.method_7909() == class_1802.field_8477) {
                        total += stack.method_7947();
                    }
                }
                System.out.println("CLIENT_DIAMONDS count=" + total);
            }
        });
    }
}
