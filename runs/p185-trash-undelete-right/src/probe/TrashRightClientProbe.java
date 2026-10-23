package probe;

import net.blay09.mods.balm.mixin.AbstractContainerScreenAccessor;
import net.blay09.mods.trashslot.client.TrashSlotGuiHandler;
import net.blay09.mods.trashslot.client.TrashSlotSlot;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.minecraft.class_1799;
import net.minecraft.class_1802;
import net.minecraft.class_465;
import net.minecraft.class_490;

/** p185 client probe: seed the trash, open the inventory, log geometry and the post-click state. */
public final class TrashRightClientProbe implements ClientModInitializer {
    private int clientTicks;

    @Override
    public void onInitializeClient() {
        ClientTickEvents.END_CLIENT_TICK.register(client -> {
            if (client.field_1724 == null) {
                return;
            }
            clientTicks++;
            if (clientTicks == 60) {
                TrashSlotSlot trash = TrashSlotGuiHandler.getTrashSlot();
                if (trash != null) {
                    trash.method_7673(new class_1799(class_1802.field_8477, 5));
                    System.out.println("KEY_SEED_CLIENT");
                }
            }
            if (clientTicks == 80 && client.field_1755 == null) {
                client.method_1507(new class_490(client.field_1724));
                System.out.println("KEY_INV_OPEN");
            }
            if (clientTicks == 100 && client.field_1755 instanceof class_465<?> screen) {
                TrashSlotSlot trash = TrashSlotGuiHandler.getTrashSlot();
                if (trash != null) {
                    var accessor = (AbstractContainerScreenAccessor) screen;
                    double scale = client.method_22683().method_4495();
                    System.out.println("KEY_SCREEN left=" + accessor.getLeftPos()
                            + " top=" + accessor.getTopPos()
                            + " trashX=" + trash.field_7873
                            + " trashY=" + trash.field_7872
                            + " scale=" + scale
                            + " trash=" + trash.method_7677());
                }
            }
            if (clientTicks == 140 || clientTicks == 180) {
                var carried = client.field_1724.field_7512.method_34255();
                TrashSlotSlot trash = TrashSlotGuiHandler.getTrashSlot();
                System.out.println("RIGHT_STATE carried=" + carried.method_7947()
                        + " trash=" + (trash == null ? "null" : trash.method_7677().method_7947()));
            }
        });
    }
}
