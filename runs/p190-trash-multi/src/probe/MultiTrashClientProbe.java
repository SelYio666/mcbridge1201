package probe;

import net.blay09.mods.trashslot.client.TrashSlotGuiHandler;
import net.blay09.mods.trashslot.client.TrashSlotSlot;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.minecraft.class_1799;
import net.minecraft.class_1802;
import net.minecraft.class_490;

/**
 * p190 client probe: opens the inventory after joining and reports the local trash slot content
 * every 2 s (per-player clientbound sync evidence) plus the screen geometry once, for the harness
 * that drives player A's trash interactions.
 */
public final class MultiTrashClientProbe implements ClientModInitializer {
    private int ticks;
    private boolean opened;
    private boolean seeded;

    @Override
    public void onInitializeClient() {
        ClientTickEvents.END_CLIENT_TICK.register(client -> {
            if (client.field_1724 == null) {
                return;
            }
            ticks++;
            if (!opened && ticks == 60 && client.field_1755 == null) {
                // survival players open the survival inventory; creative players open the
                // creative screen - both show the trash slot (the config default is enabled).
                client.method_1507(new class_490(client.field_1724));
                opened = true;
                System.out.println("MULTI_INV_OPEN tick=" + ticks);
            }
            // Seed the LOCAL trash UI once the slot exists (same approach as p183): the server
            // does not push trash content on its own (the clientbound update is a reply, p64).
            // Player A's harness then drives take-one/empty through the real GUI while player
            // B's client stays untouched.
            if (opened && ticks >= 70 && ticks % 10 == 0 && !seeded) {
                TrashSlotSlot trash = TrashSlotGuiHandler.getTrashSlot();
                if (trash != null) {
                    trash.method_7673(new class_1799(class_1802.field_8477, 5));
                    seeded = true;
                    System.out.println("MULTI_CLIENT_SEED trash=diamondx5");
                }
            }
            if (opened && ticks % 40 == 0) {
                TrashSlotSlot trash = TrashSlotGuiHandler.getTrashSlot();
                class_1799 stack = trash == null ? null : trash.method_7677();
                var accessor = (net.blay09.mods.balm.mixin.AbstractContainerScreenAccessor)
                        client.field_1755;
                System.out.println("TRASH_CLIENT screen="
                        + client.field_1755.getClass().getSimpleName()
                        + " left=" + accessor.getLeftPos() + " top=" + accessor.getTopPos()
                        + " trashX=" + (trash == null ? -1 : trash.field_7873)
                        + " trashY=" + (trash == null ? -1 : trash.field_7872)
                        + " scale=" + client.method_22683().method_4495()
                        + " trash=" + (stack == null || stack.method_7960() ? "empty"
                                : stack.method_7909() + "x" + stack.method_7947()));
            }
        });
    }
}
