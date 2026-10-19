package probe;

import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.api.ModInitializer;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;
import net.fabricmc.fabric.api.networking.v1.ServerPlayConnectionEvents;
import net.minecraft.class_1268;
import net.minecraft.class_1799;
import net.minecraft.class_2248;
import net.minecraft.class_2338;
import net.minecraft.class_2350;
import net.minecraft.class_2378;
import net.minecraft.class_243;
import net.minecraft.class_2960;
import net.minecraft.class_3222;
import net.minecraft.class_3965;
import net.minecraft.class_7923;

public final class IronChestsGuiProbe implements ModInitializer, ClientModInitializer {
    private static class_3222 joined;
    private static int serverTicks;
    private int ticks;
    private int state;

    @Override
    public void onInitialize() {
        ServerPlayConnectionEvents.JOIN.register((handler, sender, server) -> joined = handler.method_32311());
        ServerTickEvents.END_SERVER_TICK.register(server -> {
            if (joined == null) return;
            serverTicks++;
            if (serverTicks == 40) {
                class_2378<class_2248> blocks = class_7923.field_41175;
                class_2248 chest = blocks.method_10223(class_2960.method_60655("ironchests", "iron_chest"));
                class_1799 item = new class_1799(class_7923.field_41178.method_10223(
                        class_2960.method_60655("ironchests", "iron_chest")));
                System.out.println("IRONCHESTS_SERVER block=" + chest + " item=" + item);
                joined.method_7270(item);
                boolean placed = joined.method_51469().method_8652(
                        new class_2338(78, 65, -68), chest.method_9564(), 3);
                System.out.println("IRONCHESTS_PLACED=" + placed);
            }
        });
    }

    @Override
    public void onInitializeClient() {
        ClientTickEvents.END_CLIENT_TICK.register(client -> {
            if (client.field_1724 == null) return;
            ticks++;
            if (state == 0 && ticks == 120) {
                var pos = new class_2338(78, 65, -68);
                var hit = new class_3965(new class_243(78.5, 65.5, -67.5),
                        class_2350.field_11036, pos, false);
                client.field_1761.method_2896(client.field_1724, class_1268.field_5808, hit);
                System.out.println("IRONCHESTS_INTERACT screen=" + client.field_1755);
                state = 1;
                ticks = 0;
            } else if (state == 1 && ticks == 40) {
                System.out.println("IRONCHESTS_SCREEN=" + client.field_1755);
                state = 2;
            }
        });
    }
}
