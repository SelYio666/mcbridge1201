package probe;

import net.blay09.mods.trashslot.TrashHelper;
import net.fabricmc.api.ModInitializer;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;
import net.minecraft.class_1799;
import net.minecraft.class_3222;

/** p189 server probe: reports the joined creative player's trash and hotbar state every 2 s. */
public final class CreativeServerProbe implements ModInitializer {
    private static class_3222 joined;
    private static int serverTicks;

    @Override
    public void onInitialize() {
        net.fabricmc.fabric.api.networking.v1.ServerPlayConnectionEvents.JOIN.register(
                (handler, sender, server) -> joined = handler.method_32311());
        ServerTickEvents.END_SERVER_TICK.register(server -> {
            if (joined == null) {
                return;
            }
            serverTicks++;
            if (serverTicks % 40 == 0) {
                class_1799 trash = TrashHelper.getTrashItem(joined);
                class_1799 hot0 = joined.method_31548().method_5438(0);
                class_1799 hot1 = joined.method_31548().method_5438(1);
                System.out.println("SERVER_STATE trash=" + describe(trash)
                        + " hot0=" + describe(hot0) + " hot1=" + describe(hot1));
            }
        });
    }

    private static String describe(class_1799 stack) {
        return stack.method_7960() ? "empty" : stack.method_7909() + "x" + stack.method_7947();
    }
}
