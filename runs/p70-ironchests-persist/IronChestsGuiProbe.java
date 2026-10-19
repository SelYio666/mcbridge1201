package probe;

import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.api.ModInitializer;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;
import net.fabricmc.fabric.api.networking.v1.ServerPlayConnectionEvents;
import net.minecraft.class_1263;
import net.minecraft.class_1268;
import net.minecraft.class_1657;
import net.minecraft.class_1703;
import net.minecraft.class_1713;
import net.minecraft.class_1799;
import net.minecraft.class_1802;
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

    private static String stack(class_1703 handler, int slot) {
        try {
            return handler.method_7611(slot).method_7677().toString();
        } catch (RuntimeException e) {
            return "ERR:" + e;
        }
    }

    private static void openChest(class_3222 player) {
        var world = player.method_51469();
        var pos = new class_2338(78, 65, -68);
        var state = world.method_8320(pos);
        var hit = new class_3965(new class_243(78.5, 65.5, -68.0),
                class_2350.field_11043, pos, false);
        class_2248 chestBlock = class_7923.field_41175.method_10223(
                class_2960.method_60655("ironchests", "iron_chest"));
        try {
            var method = chestBlock.getClass().getMethod("method_9534",
                    net.minecraft.class_2680.class, net.minecraft.class_1937.class,
                    class_2338.class, class_1657.class,
                    class_1268.class, class_3965.class);
            var result = method.invoke(chestBlock, state, world, pos, player,
                    class_1268.field_5808, hit);
            System.out.println("IRONCHESTS_USE result=" + result + " state=" + state);
        } catch (ReflectiveOperationException e) {
            System.out.println("IRONCHESTS_USE_ERROR cause=" + e.getCause());
            if (e.getCause() != null) {
                e.getCause().printStackTrace(System.out);
            }
        }
    }

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
                joined.method_7270(new class_1799(class_1802.field_8477, 10));
                boolean placed = joined.method_51469().method_8652(
                        new class_2338(78, 65, -68), chest.method_9564(), 3);
                System.out.println("IRONCHESTS_PLACED=" + placed);
            }
            if (serverTicks == 60) {
                System.out.println("IRONCHESTS_STATE="
                        + joined.method_51469().method_8320(new class_2338(78, 65, -68)));
            }
            if (serverTicks == 80 || serverTicks == 300) {
                System.out.println("IRONCHESTS_OPEN_AT=" + serverTicks);
                openChest(joined);
            }
            if (serverTicks == 240 || serverTicks == 280 || serverTicks == 320) {
                var be = joined.method_51469().method_8321(new class_2338(78, 65, -68));
                var inv = be instanceof class_1263 ? (class_1263) be : null;
                System.out.println("IRONCHESTS_BE tick=" + serverTicks + " slot0="
                        + (inv == null ? "no-inventory:" + be : inv.method_5438(0)));
            }
            if (serverTicks == 220 || serverTicks == 320) {
                var handler = joined.field_7512;
                System.out.println("IRONCHESTS_SERVER_MENU tick=" + serverTicks
                        + " sync=" + handler.field_7763
                        + " slot0=" + stack(handler, 0));
            }
        });
    }

    @Override
    public void onInitializeClient() {
        ClientTickEvents.END_CLIENT_TICK.register(client -> {
            if (client.field_1724 == null) return;
            ticks++;
            if (state == 0 && ticks == 140) {
                System.out.println("IRONCHESTS_SCREEN=" + client.field_1755);
                state = 1;
                ticks = 0;
            } else if (state == 1 && ticks == 60) {
                var handler = client.field_1724.field_7512;
                int source = -1;
                for (int i = 54; i < handler.field_7761.size(); i++) {
                    if (!handler.method_7611(i).method_7677().method_7960()) {
                        source = i;
                        break;
                    }
                }
                System.out.println("IRONCHESTS_CLICK_SOURCE=" + source
                        + " slot0=" + stack(handler, 0));
                if (source >= 0 && client.field_1755 != null
                        && client.field_1755.getClass().getName().contains("ChestScreen")) {
                    client.field_1761.method_2906(handler.field_7763, source, 0,
                            class_1713.field_7790, client.field_1724);
                    client.field_1761.method_2906(handler.field_7763, 0, 0,
                            class_1713.field_7790, client.field_1724);
                    System.out.println("IRONCHESTS_PUT slot0=" + stack(handler, 0));
                    state = 2;
                    ticks = 0;
                }
            } else if (state == 2 && ticks == 60) {
                System.out.println("IRONCHESTS_BEFORE_CLOSE slot0="
                        + stack(client.field_1724.field_7512, 0));
                client.method_1507(null);
                System.out.println("IRONCHESTS_CLOSED screen=" + client.field_1755);
                state = 3;
                ticks = 0;
            } else if (state == 3 && ticks == 120) {
                var handler = client.field_1724.field_7512;
                System.out.println("IRONCHESTS_REOPEN screen=" + client.field_1755
                        + " sync=" + handler.field_7763
                        + " slot0=" + stack(handler, 0));
                state = 4;
            }
        });
    }
}
