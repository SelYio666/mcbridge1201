package probe;

import net.blay09.mods.trashslot.TrashHelper;
import net.fabricmc.api.ModInitializer;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;
import net.fabricmc.fabric.api.networking.v1.ServerPlayConnectionEvents;
import net.minecraft.class_1799;
import net.minecraft.class_1802;
import net.minecraft.class_3222;

/** Server-side half of the p183 probe: seed the trash and report its server state. */
public final class TrashKeyServerProbe implements ModInitializer {
    private static class_3222 joined;
    private static int serverTicks;

    @Override
    public void onInitialize() {
        ServerPlayConnectionEvents.JOIN.register((handler, sender, server) -> joined = handler.method_32311());
        ServerTickEvents.END_SERVER_TICK.register(server -> {
            if (joined == null) {
                return;
            }
            serverTicks++;
            if (serverTicks == 40) {
                TrashHelper.setTrashItem(joined, new class_1799(class_1802.field_8477, 5));
                System.out.println("KEY_SEED_SERVER");
            }
            if (serverTicks % 40 == 0) {
                class_1799 trash = TrashHelper.getTrashItem(joined);
                System.out.println("SERVER_TRASH empty=" + trash.method_7960()
                        + " count=" + trash.method_7947());
            }
        });
    }
}
