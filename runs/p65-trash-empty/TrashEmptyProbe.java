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

public final class TrashEmptyProbe implements ModInitializer, ClientModInitializer {
    private static class_3222 joined;
    private static int serverTicks;
    private int clientTicks;

    @Override
    public void onInitialize() {
        ServerPlayConnectionEvents.JOIN.register((handler, sender, server) -> joined = handler.method_32311());
        ServerTickEvents.END_SERVER_TICK.register(server -> {
            if (joined == null) return;
            serverTicks++;
            if (serverTicks == 40) {
                TrashHelper.setTrashItem(joined, new class_1799(class_1802.field_8477, 5));
                System.out.println("EMPTY_PROBE_SEEDED");
            }
            if (serverTicks % 40 == 0) {
                class_1799 t = TrashHelper.getTrashItem(joined);
                System.out.println("EMPTY_SERVER empty=" + t.method_7960() + " count=" + t.method_7947());
            }
        });
    }

    @Override
    public void onInitializeClient() {
        ClientTickEvents.END_CLIENT_TICK.register(client -> {
            if (client.field_1724 == null) return;
            clientTicks++;
            if (clientTicks == 100) {
                TrashSlotSlot trash = TrashSlotGuiHandler.getTrashSlot();
                DeletionProvider provider = TrashSlotConfig.getDeletionProvider();
                if (trash != null) trash.method_7673(new class_1799(class_1802.field_8477, 5));
                System.out.println("EMPTY_BEFORE trash=" + (trash == null ? "null" : trash.method_7677()));
                if (provider != null && trash != null) {
                    provider.emptyTrashSlot(trash);
                    System.out.println("EMPTY_AFTER trash=" + trash.method_7677());
                }
            }
        });
    }
}
