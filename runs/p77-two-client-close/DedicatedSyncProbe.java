package probe;

import java.util.List;

import net.fabricmc.api.ModInitializer;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;
import net.minecraft.class_1263;
import net.minecraft.class_1268;
import net.minecraft.class_1657;
import net.minecraft.class_1799;
import net.minecraft.class_1802;
import net.minecraft.class_2248;
import net.minecraft.class_2338;
import net.minecraft.class_2350;
import net.minecraft.class_243;
import net.minecraft.class_2960;
import net.minecraft.class_3222;
import net.minecraft.class_3965;
import net.minecraft.class_7923;

/** Dedicated-server side of the two-client sync test. */
public final class DedicatedSyncProbe implements ModInitializer {
    private static int twoPlayerTicks = -1;
    private static class_2338 chestPos;

    private static void openChest(class_3222 guest, class_2338 pos) {
        var world = guest.method_51469();
        guest.method_14251(world, pos.method_10263() + 0.5, pos.method_10264(),
                pos.method_10260() + 2.5, 0.0f, 0.0f);
        var be = world.method_8321(pos);
        if (!(be instanceof net.minecraft.class_2621 blockEntity)) {
            System.out.println("DED_OPEN no-block-entity be=" + be);
            return;
        }
        net.minecraft.class_3908 provider = new net.minecraft.class_3908() {
            @Override
            public net.minecraft.class_1703 createMenu(int syncId, net.minecraft.class_1661 inv,
                                                      class_1657 player) {
                return blockEntity.createMenu(syncId, inv, player);
            }

            @Override
            public net.minecraft.class_2561 method_5476() {
                return net.minecraft.class_2561.method_43470("Iron Chest");
            }
        };
        var opened = guest.method_17355(provider);
        System.out.println("DED_OPEN opened=" + opened + " guest=" + guest);
    }

    @Override
    public void onInitialize() {
        ServerTickEvents.END_SERVER_TICK.register(server -> {
            List<class_3222> players = server.method_3760().method_14571();
            if (players.size() < 2) {
                twoPlayerTicks = -1;
                chestPos = null;
                return;
            }
            twoPlayerTicks++;
            class_3222 host = players.get(0);
            class_3222 guest = players.get(1);
            if (twoPlayerTicks == 60) {
                int x = (int) Math.floor(host.method_23317()) + 2;
                int y = (int) Math.floor(host.method_23318());
                int z = (int) Math.floor(host.method_23319());
                chestPos = new class_2338(x, y, z);
                class_2248 chest = class_7923.field_41175.method_10223(
                        class_2960.method_60655("ironchests", "iron_chest"));
                boolean placed = host.method_51469().method_8652(
                        chestPos, chest.method_9564(), 3);
                System.out.println("DED_PLACED placed=" + placed + " pos=" + chestPos);
            }
            if (twoPlayerTicks == 100 && chestPos != null) {
                var be = host.method_51469().method_8321(chestPos);
                if (be instanceof class_1263 inv) {
                    inv.method_5447(0, new class_1799(class_1802.field_8477, 7));
                    System.out.println("DED_SET slot0=" + inv.method_5438(0));
                } else {
                    System.out.println("DED_SET no-inventory be=" + be);
                }
            }
            if (twoPlayerTicks == 140 && chestPos != null) {
                openChest(guest, chestPos);
            }
            if (twoPlayerTicks == 200 && chestPos != null) {
                var be = host.method_51469().method_8321(chestPos);
                if (be instanceof class_1263 inv) {
                    System.out.println("DED_AFTER slot0=" + inv.method_5438(0));
                }
            }
            if (twoPlayerTicks == 240 && chestPos != null) {
                System.out.println("DED_OPEN_HOST");
                openChest(host, chestPos);
            }
            if (twoPlayerTicks == 420 || twoPlayerTicks == 520) {
                System.out.println("DED_MENUS hostSlots=" + host.field_7512.field_7761.size()
                        + " guestSlots=" + guest.field_7512.field_7761.size());
            }
        });
    }
}
