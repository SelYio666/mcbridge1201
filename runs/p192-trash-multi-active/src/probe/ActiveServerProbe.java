package probe;

import net.blay09.mods.trashslot.TrashHelper;
import net.fabricmc.api.ModInitializer;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;
import net.fabricmc.fabric.api.networking.v1.ServerPlayConnectionEvents;
import net.minecraft.class_1799;
import net.minecraft.class_1802;
import net.minecraft.class_3222;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * p192 server probe: three players. Seeds A (GridUser) = 5, B (TrashB) = 4 and C (TrashC) = 3
 * diamonds once all three joined, then reports every player's server-side trash every 2 s. The
 * per-player isolation and B's active drain (4 -> 3 -> empty) are read from these lines; A's
 * REJOIN state (trash reset to empty by TrashSlot's own PlayerLoginEvent) too.
 */
public final class ActiveServerProbe implements ModInitializer {
    private static final Map<String, class_3222> joined = new LinkedHashMap<>();
    private static int serverTicks;
    private static boolean seeded;

    @Override
    public void onInitialize() {
        ServerPlayConnectionEvents.JOIN.register((handler, sender, server) -> {
            class_3222 player = handler.method_32311();
            joined.put(player.method_7334().getName(), player);
            System.out.println("ACTIVE_JOIN name=" + player.method_7334().getName()
                    + " total=" + joined.size());
        });
        ServerTickEvents.END_SERVER_TICK.register(server -> {
            if (joined.size() < 3) {
                return;
            }
            serverTicks++;
            if (!seeded && serverTicks >= 40) {
                seeded = true;
                TrashHelper.setTrashItem(joined.get("GridUser"),
                        new class_1799(class_1802.field_8477, 5));
                TrashHelper.setTrashItem(joined.get("TrashB"),
                        new class_1799(class_1802.field_8477, 4));
                TrashHelper.setTrashItem(joined.get("TrashC"),
                        new class_1799(class_1802.field_8477, 3));
                System.out.println("ACTIVE_SEED GridUser=5 TrashB=4 TrashC=3");
            }
            if (serverTicks % 40 == 0) {
                for (Map.Entry<String, class_3222> entry : joined.entrySet()) {
                    class_1799 trash = TrashHelper.getTrashItem(entry.getValue());
                    System.out.println("ACTIVE_SERVER user=" + entry.getKey()
                            + " trash=" + (trash.method_7960() ? "empty"
                                    : trash.method_7909() + "x" + trash.method_7947()));
                }
            }
        });
    }
}
