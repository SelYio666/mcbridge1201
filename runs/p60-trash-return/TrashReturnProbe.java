package probe;

import net.blay09.mods.trashslot.TrashHelper;
import net.blay09.mods.trashslot.client.TrashSlotGuiHandler;
import net.blay09.mods.trashslot.client.TrashSlotSlot;
import net.blay09.mods.trashslot.client.deletion.DeletionProvider;
import net.blay09.mods.trashslot.config.TrashSlotConfig;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.api.ModInitializer;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;
import net.fabricmc.fabric.api.networking.v1.ServerPlayConnectionEvents;
import net.minecraft.class_1799;
import net.minecraft.class_1802;
import net.minecraft.class_3222;
import net.minecraft.class_490;

public final class TrashReturnProbe implements ModInitializer, ClientModInitializer {
    private static class_3222 joined;
    private static int serverTicks;
    private int state;
    private int ticks;

    @Override
    public void onInitialize() {
        ServerPlayConnectionEvents.JOIN.register((handler, sender, server) -> {
            joined = handler.method_32311();
            joined.method_7270(new class_1799(class_1802.field_8477, 5));
        });
        ServerTickEvents.END_SERVER_TICK.register(server -> {
            if (joined == null) return;
            serverTicks++;
            if (serverTicks == 40) {
                TrashHelper.setTrashItem(joined, new class_1799(class_1802.field_8477, 5));
                System.out.println("RETURN_PROBE_SEEDED");
            }
            if (serverTicks % 40 == 0) {
                class_1799 trash = TrashHelper.getTrashItem(joined);
                System.out.println("RETURN_SERVER empty=" + trash.method_7960()
                        + " count=" + trash.method_7947());
            }
        });
    }

    @Override
    public void onInitializeClient() {
        ClientTickEvents.END_CLIENT_TICK.register(client -> {
            if (client.field_1724 == null) return;
            ticks++;
            if (state == 0 && client.field_1755 == null && ticks > 20) {
                client.method_1507(new class_490(client.field_1724));
                state = 1;
                ticks = 0;
            } else if (state == 1 && ticks > 80) {
                TrashSlotSlot trash = TrashSlotGuiHandler.getTrashSlot();
                DeletionProvider provider = TrashSlotConfig.getDeletionProvider();
                if (trash != null) {
                    trash.method_7673(new class_1799(class_1802.field_8477, 5));
                }
                System.out.println("RETURN_GUI trash=" + (trash == null ? "null" : trash.method_7677())
                        + " provider=" + provider);
                if (trash != null && provider != null) {
                    provider.undeleteLast(client.field_1724, trash, false);
                    System.out.println("RETURN_AFTER cursor="
                            + client.field_1724.field_7512.method_34255()
                            + " trash=" + trash.method_7677());
                }
                state = 2;
                ticks = 0;
            } else if (state == 2 && ticks > 20) {
                TrashSlotSlot trash = TrashSlotGuiHandler.getTrashSlot();
                System.out.println("RETURN_FINAL cursor="
                        + client.field_1724.field_7512.method_34255()
                        + " trash=" + (trash == null ? "null" : trash.method_7677()));
                state = 99;
            }
        });
    }
}
