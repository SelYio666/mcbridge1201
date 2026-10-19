package probe;

import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.api.ModInitializer;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;
import net.fabricmc.fabric.api.networking.v1.ServerPlayConnectionEvents;
import net.minecraft.class_1268;
import net.minecraft.class_1657;
import net.minecraft.class_1703;
import net.minecraft.class_2248;
import net.minecraft.class_2338;
import net.minecraft.class_2350;
import net.minecraft.class_2378;
import net.minecraft.class_243;
import net.minecraft.class_2960;
import net.minecraft.class_3222;
import net.minecraft.class_3908;
import net.minecraft.class_3965;
import net.minecraft.class_7923;

public final class EscProbe implements ModInitializer, ClientModInitializer {
    private static class_3222 joined;
    private static class_2338 chestPos;
    private static int serverTicks;
    private int clientTicks;

    private static void openChest(class_3222 player, class_2338 pos) {
        var world = player.method_51469();
        var state = world.method_8320(pos);
        var hit = new class_3965(new class_243(pos.method_10263() + 0.5,
                pos.method_10264() + 0.5, pos.method_10260() - 1.0),
                class_2350.field_11043, pos, false);
        class_2248 chestBlock = class_7923.field_41175.method_10223(
                class_2960.method_60655("ironchests", "iron_chest"));
        try {
            var method = chestBlock.getClass().getMethod("method_9534",
                    net.minecraft.class_2680.class, net.minecraft.class_1937.class,
                    class_2338.class, class_1657.class,
                    class_1268.class, class_3965.class);
            System.out.println("ESC_OPEN result=" + method.invoke(chestBlock, state, world, pos,
                    player, class_1268.field_5808, hit));
        } catch (ReflectiveOperationException e) {
            System.out.println("ESC_OPEN_ERROR cause=" + e.getCause());
        }
    }

    @Override
    public void onInitialize() {
        ServerPlayConnectionEvents.JOIN.register((handler, sender, server) -> joined = handler.method_32311());
        ServerTickEvents.END_SERVER_TICK.register(server -> {
            if (joined == null) return;
            serverTicks++;
            if (serverTicks == 40) {
                var world = joined.method_51469();
                int x = (int) Math.floor(joined.method_23317()) + 2;
                int y = (int) Math.floor(joined.method_23318());
                int z = (int) Math.floor(joined.method_23319());
                chestPos = new class_2338(x, y, z);
                class_2248 chest = class_7923.field_41175.method_10223(
                        class_2960.method_60655("ironchests", "iron_chest"));
                class_2248 air = class_7923.field_41175.method_10223(
                        class_2960.method_60655("minecraft", "air"));
                world.method_8652(chestPos, air.method_9564(), 3);
                boolean placed = world.method_8652(chestPos, chest.method_9564(), 3);
                joined.method_14251(world, x + 0.5, y, z + 1.5, 0.0f, 0.0f);
                System.out.println("ESC_PLACED=" + placed + " pos=" + chestPos
                        + " player=" + joined.method_23317() + "," + joined.method_23318()
                        + "," + joined.method_23319());
            }
            if (serverTicks == 80) {
                openChest(joined, chestPos);
            }
            if (serverTicks >= 160 && serverTicks % 80 == 0) {
                System.out.println("ESC_SERVER_MENU tick=" + serverTicks
                        + " slots=" + joined.field_7512.field_7761.size());
            }
        });
    }

    @Override
    public void onInitializeClient() {
        ClientTickEvents.END_CLIENT_TICK.register(client -> {
            if (client.field_1724 == null) return;
            clientTicks++;
            if (clientTicks >= 140 && clientTicks % 40 == 0) {
                System.out.println("ESC_CLIENT tick=" + clientTicks
                        + " screen=" + (client.field_1755 == null ? "null"
                                : client.field_1755.getClass().getName())
                        + " slots=" + client.field_1724.field_7512.field_7761.size());
            }
        });
    }
}
