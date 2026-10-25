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
 * p190 server probe (multi-client trash isolation): seeds each joining player's trash with a
 * distinct stack (GridUser -> 5 diamonds, TrashB -> 3 iron ingots) and reports BOTH players'
 * server-side trash every 2 s, so the per-player separation is visible in the server log.
 */
public final class MultiTrashServerProbe implements ModInitializer {
    private static final Map<String, class_3222> joined = new LinkedHashMap<>();
    private static int serverTicks;
    private static boolean seeded;

    @Override
    public void onInitialize() {
        ServerPlayConnectionEvents.JOIN.register((handler, sender, server) -> {
            class_3222 player = handler.method_32311();
            joined.put(player.method_7334().getName(), player);
            System.out.println("MULTI_JOIN name=" + player.method_7334().getName()
                    + " total=" + joined.size());
        });
        ServerTickEvents.END_SERVER_TICK.register(server -> {
            if (joined.isEmpty()) {
                return;
            }
            serverTicks++;
            if (!seeded && serverTicks >= 40 && joined.containsKey("GridUser")
                    && joined.containsKey("TrashB")) {
                seeded = true;
                TrashHelper.setTrashItem(joined.get("GridUser"),
                        new class_1799(class_1802.field_8477, 5));
                TrashHelper.setTrashItem(joined.get("TrashB"),
                        new class_1799(class_1802.field_8477, 3));
                System.out.println("MULTI_SEED first=diamondx5 second=diamondx3");
            }
            if (serverTicks % 40 == 0) {
                for (Map.Entry<String, class_3222> entry : joined.entrySet()) {
                    class_1799 trash = TrashHelper.getTrashItem(entry.getValue());
                    System.out.println("MULTI_SERVER user=" + entry.getKey()
                            + " trash=" + (trash.method_7960() ? "empty"
                                    : trash.method_7909() + "x" + trash.method_7947()));
                }
            }
        });
    }
}
