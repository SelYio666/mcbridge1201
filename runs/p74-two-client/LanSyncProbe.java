package probe;

import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.api.ModInitializer;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;
import net.fabricmc.fabric.api.networking.v1.ServerPlayConnectionEvents;
import net.minecraft.class_1263;
import net.minecraft.class_1268;
import net.minecraft.class_1657;
import net.minecraft.class_1799;
import net.minecraft.class_1802;
import net.minecraft.class_1934;
import net.minecraft.class_2248;
import net.minecraft.class_2338;
import net.minecraft.class_2350;
import net.minecraft.class_243;
import net.minecraft.class_2960;
import net.minecraft.class_3222;
import net.minecraft.class_3965;
import net.minecraft.class_7923;
import net.minecraft.server.MinecraftServer;

public final class LanSyncProbe implements ModInitializer, ClientModInitializer {
    private static MinecraftServer server;
    private static class_3222 host;
    private static int twoPlayerTicks = -1;
    private int clientTicks;
    private boolean lanOpened;
    private boolean guestLogged;

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
            System.out.println("LAN_HOST_OPEN result=" + result + " player=" + player);
        } catch (ReflectiveOperationException e) {
            System.out.println("LAN_HOST_OPEN_ERROR cause=" + e.getCause());
        }
    }

    @Override
    public void onInitialize() {
        ServerPlayConnectionEvents.JOIN.register((handler, sender, srv) -> {
            server = srv;
            if (host == null) {
                host = handler.method_32311();
            }
        });
        ServerTickEvents.END_SERVER_TICK.register(srv -> {
            server = srv;
            var players = srv.method_3760().method_14571();
            if (players.size() < 2 || host == null) {
                twoPlayerTicks = -1;
                return;
            }
            twoPlayerTicks++;
            class_3222 guest = null;
            for (var p : players) {
                if (p != host) {
                    guest = p;
                }
            }
            if (guest == null) return;
            if (twoPlayerTicks == 40) {
                var world = host.method_51469();
                var be = world.method_8321(new class_2338(78, 65, -68));
                if (be instanceof class_1263 inv) {
                    inv.method_5437(0, new class_1799(class_1802.field_8477, 7));
                    System.out.println("LAN_HOST_SET slot0=" + inv.method_5438(0));
                } else {
                    System.out.println("LAN_HOST_SET no-inventory be=" + be);
                }
            }
            if (twoPlayerTicks == 80) {
                openChest(guest);
            }
        });
    }

    @Override
    public void onInitializeClient() {
        ClientTickEvents.END_CLIENT_TICK.register(client -> {
            if (client.field_1724 == null) return;
            clientTicks++;
            if (client.method_1576() != null && !lanOpened && clientTicks == 120) {
                boolean ok = client.method_1576().method_3763(
                        class_1934.values()[0], false, 25566);
                lanOpened = true;
                System.out.println("LAN_OPEN ok=" + ok + " port=25566");
            }
            if (client.method_1576() == null && !guestLogged && client.field_1755 != null
                    && client.field_1755.getClass().getName().contains("ChestScreen")) {
                var handler = client.field_1724.field_7512;
                System.out.println("LAN_GUEST_MENU screen=" + client.field_1755
                        + " sync=" + handler.field_7763
                        + " slot0=" + handler.method_7611(0).method_7677());
                guestLogged = true;
            }
        });
    }
}
