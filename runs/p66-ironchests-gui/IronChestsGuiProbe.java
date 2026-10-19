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
            if (serverTicks == 60) {
                System.out.println("IRONCHESTS_STATE="
                        + joined.method_51469().method_8320(new class_2338(78, 65, -68)));
            }
            if (serverTicks == 80) {
                var world = joined.method_51469();
                var pos = new class_2338(78, 65, -68);
                var state = world.method_8320(pos);
                var hit = new class_3965(new class_243(78.5, 65.5, -68.0),
                        class_2350.field_11043, pos, false);
                class_2248 chestBlock = class_7923.field_41175.method_10223(
                        class_2960.method_60655("ironchests", "iron_chest"));
                try {
                    var method = chestBlock.getClass().getMethod("method_9534",
                            net.minecraft.class_2680.class, net.minecraft.class_1937.class,
                            class_2338.class, net.minecraft.class_1657.class,
                            class_1268.class, class_3965.class);
                    var result = method.invoke(chestBlock, state, world, pos, joined,
                            class_1268.field_5808, hit);
                    System.out.println("IRONCHESTS_USE result=" + result + " state=" + state);
                } catch (ReflectiveOperationException e) {
                    System.out.println("IRONCHESTS_USE_ERROR cause=" + e.getCause());
                    if (e.getCause() != null) {
                        e.getCause().printStackTrace(System.out);
                    }
                }
            }
        });
    }

    @Override
    public void onInitializeClient() {
        ClientTickEvents.END_CLIENT_TICK.register(client -> {
            if (client.field_1724 == null) return;
            ticks++;
            if (state == 0 && ticks == 140) {
                System.out.println("IRONCHESTS_SCREEN=" + client.field_1755
                        + " class=" + (client.field_1755 == null ? "null"
                                : client.field_1755.getClass().getName()));
                state = 1;
                ticks = 0;
            } else if (state == 1 && ticks == 60) {
                System.out.println("IRONCHESTS_SCREEN_LATE=" + client.field_1755);
                state = 2;
            }
        });
    }
}
