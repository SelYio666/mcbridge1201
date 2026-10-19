package probe;

import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.api.ModInitializer;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;
import net.fabricmc.fabric.api.networking.v1.ServerPlayConnectionEvents;
import net.minecraft.class_1799;
import net.minecraft.class_1802;
import net.minecraft.class_2248;
import net.minecraft.class_2338;
import net.minecraft.class_3222;
import net.minecraft.class_2960;
import net.minecraft.class_7923;

public final class LithiumPlayProbe implements ModInitializer, ClientModInitializer {
    private static class_3222 joined;
    private static int serverTicks;
    private int clientTicks;
    private int centerX;
    private int centerY;
    private int centerZ;
    private int placeX;
    private int placeY;
    private int placeZ;

    @Override
    public void onInitialize() {
        ServerPlayConnectionEvents.JOIN.register((handler, sender, server) -> joined = handler.method_32311());
        ServerTickEvents.END_SERVER_TICK.register(server -> {
            if (joined == null) return;
            serverTicks++;
            var world = joined.method_51469();
            if (serverTicks == 40) {
                centerX = (int) Math.floor(joined.method_23317());
                centerY = (int) Math.floor(joined.method_23318());
                centerZ = (int) Math.floor(joined.method_23319());
                int cx = centerX >> 4;
                int cz = centerZ >> 4;
                int loaded = 0;
                for (int dx = -4; dx <= 4; dx++) {
                    for (int dz = -4; dz <= 4; dz++) {
                        if (world.method_8497(cx + dx, cz + dz) != null) {
                            loaded++;
                        }
                    }
                }
                joined.method_7270(new class_1799(class_1802.field_8477, 5));
                System.out.println("LITHIUM_CHUNKS loaded=" + loaded + "/81 center=" + cx + "," + cz);
            }
            var breakPos = new class_2338(centerX, centerY - 1, centerZ);
            if (serverTicks == 60) {
                System.out.println("LITHIUM_BEFORE state=" + world.method_8320(breakPos));
            }
            if (serverTicks == 80) {
                boolean broke = joined.field_13974.method_14266(breakPos);
                System.out.println("LITHIUM_BREAK broke=" + broke
                        + " after=" + world.method_8320(breakPos));
            }
            if (serverTicks == 120) {
                class_2248 stone = class_7923.field_41175.method_10223(
                        class_2960.method_60655("minecraft", "stone"));
                var placePos = new class_2338(centerX + 1, centerY - 1, centerZ);
                boolean placed = world.method_8652(placePos, stone.method_9564(), 3);
                System.out.println("LITHIUM_PLACE placed=" + placed
                        + " state=" + world.method_8320(placePos));
                placeX = centerX + 1;
                placeY = centerY - 1;
                placeZ = centerZ;
            }
            if (serverTicks == 140) {
                var placePos = new class_2338(placeX, placeY, placeZ);
                System.out.println("LITHIUM_BREAK_BEFORE state=" + world.method_8320(placePos));
                boolean broke = joined.field_13974.method_14266(placePos);
                System.out.println("LITHIUM_BREAK_REAL broke=" + broke
                        + " after=" + world.method_8320(placePos));
            }
            if (serverTicks == 160 || serverTicks == 240) {
                System.out.println("LITHIUM_SERVER_ALIVE tick=" + serverTicks
                        + " pos=" + joined.method_23317() + "," + joined.method_23318()
                        + "," + joined.method_23319());
            }
        });
    }

    @Override
    public void onInitializeClient() {
        ClientTickEvents.END_CLIENT_TICK.register(client -> {
            if (client.field_1724 == null) return;
            clientTicks++;
            if (clientTicks == 240) {
                System.out.println("LITHIUM_CLIENT_ALIVE screen=" + client.field_1755
                        + " pos=" + client.field_1724.method_23317() + ","
                        + client.field_1724.method_23318() + ","
                        + client.field_1724.method_23319());
            }
        });
    }
}
