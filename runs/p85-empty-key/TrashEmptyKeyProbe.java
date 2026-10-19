package probe;

import net.blay09.mods.trashslot.client.TrashSlotGuiHandler;
import net.blay09.mods.trashslot.client.TrashSlotSlot;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.minecraft.class_1799;
import net.minecraft.class_1802;
import net.minecraft.class_490;

public final class TrashEmptyKeyProbe implements ClientModInitializer {
    private int ticks;

    @Override
    public void onInitializeClient() {
        ClientTickEvents.END_CLIENT_TICK.register(client -> {
            if (client.field_1724 == null) return;
            ticks++;
            if (ticks == 100) {
                client.method_1507(new class_490(client.field_1724));
                System.out.println("TRASH_OPEN screen=" + client.field_1755);
            }
            if (ticks == 140) {
                TrashSlotSlot trash = TrashSlotGuiHandler.getTrashSlot();
                if (trash != null) {
                    trash.method_7673(new class_1799(class_1802.field_8477, 5));
                }
                System.out.println("TRASH_SEED trash="
                        + (trash == null ? "null" : trash.method_7677()));
            }
            if (ticks >= 180 && ticks % 40 == 0) {
                TrashSlotSlot trash = TrashSlotGuiHandler.getTrashSlot();
                System.out.println("TRASH_STATE tick=" + ticks
                        + " screen=" + client.field_1755
                        + " trash=" + (trash == null ? "null" : trash.method_7677()));
            }
        });
    }
}
