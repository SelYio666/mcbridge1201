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
        var be = player.method_51469().method_8321(pos);
        if (!(be instanceof net.minecraft.class_2621 blockEntity)) {
            System.out.println("ESC_OPEN no-block-entity be=" + be);
            return;
        }
        class_3908 provider = new class_3908() {
            @Override
            public class_1703 createMenu(int syncId, net.minecraft.class_1661 inv, class_1657 p) {
                return blockEntity.createMenu(syncId, inv, p);
            }

            @Override
            public net.minecraft.class_2561 method_5476() {
                return net.minecraft.class_2561.method_43470("Iron Chest");
            }
        };
        System.out.println("ESC_OPEN opened=" + player.method_17355(provider));
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
                System.out.println("ESC_PLACED=" + world.method_8652(chestPos, chest.method_9564(), 3)
                        + " pos=" + chestPos);
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
