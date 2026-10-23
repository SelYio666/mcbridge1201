package probe;

import net.blay09.mods.trashslot.TrashHelper;
import net.fabricmc.api.ModInitializer;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;
import net.fabricmc.fabric.api.networking.v1.ServerPlayConnectionEvents;
import net.minecraft.class_1661;
import net.minecraft.class_1799;
import net.minecraft.class_1802;
import net.minecraft.class_3222;

/** p184 server probe: two diamond stacks, then report the total after Shift+Delete. */
public final class TrashDeleteServerProbe implements ModInitializer {
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
                class_1661 inventory = joined.method_31548();
                inventory.method_5447(0, new class_1799(class_1802.field_8477, 5));
                inventory.method_5447(1, new class_1799(class_1802.field_8477, 3));
                System.out.println("DELETE_SEED_SERVER");
            }
            if (serverTicks % 40 == 0) {
                class_1661 inventory = joined.method_31548();
                int total = 0;
                for (int i = 0; i < inventory.method_5439(); i++) {
                    class_1799 stack = inventory.method_5438(i);
                    if (stack.method_7909() == class_1802.field_8477) {
                        total += stack.method_7947();
                    }
                }
                System.out.println("SERVER_DIAMONDS count=" + total);
            }
        });
    }
}
