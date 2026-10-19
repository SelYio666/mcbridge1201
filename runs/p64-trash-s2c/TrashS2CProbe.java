package probe;

import net.blay09.mods.balm.api.Balm;
import net.blay09.mods.trashslot.client.TrashSlotGuiHandler;
import net.blay09.mods.trashslot.client.TrashSlotSlot;
import net.blay09.mods.trashslot.network.MessageTrashSlotContent;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.api.ModInitializer;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;
import net.fabricmc.fabric.api.networking.v1.ServerPlayConnectionEvents;
import net.minecraft.class_1657;
import net.minecraft.class_1799;
import net.minecraft.class_1802;
import net.minecraft.class_3222;

public final class TrashS2CProbe implements ModInitializer, ClientModInitializer {
    private static class_3222 joined;
    private static int serverTicks;
    private int clientTicks;

    @Override
    public void onInitialize() {
        ServerPlayConnectionEvents.JOIN.register((handler, sender, server) -> joined = handler.method_32311());
        ServerTickEvents.END_SERVER_TICK.register(server -> {
            if (joined == null) return;
            serverTicks++;
            if (serverTicks == 60) {
                try {
                    Class<?> bridge = Class.forName("top.mcbridge1201.bridge.BalmNetworkingBridge");
                    Class<?> net = Class.forName("net.blay09.mods.balm.api.network.BalmNetworking");
                    var method = bridge.getMethod("sendTo", net, class_1657.class, Object.class);
                    method.invoke(null, Balm.getNetworking(), (class_1657) joined,
                            new MessageTrashSlotContent(new class_1799(class_1802.field_8477, 3)));
                    System.out.println("S2C_SENT");
                } catch (ReflectiveOperationException e) {
                    System.out.println("S2C_SEND_ERROR " + e);
                }
            }
        });
    }

    @Override
    public void onInitializeClient() {
        ClientTickEvents.END_CLIENT_TICK.register(client -> {
            if (client.field_1724 == null) return;
            clientTicks++;
            if (clientTicks == 140) {
                TrashSlotSlot trash = TrashSlotGuiHandler.getTrashSlot();
                System.out.println("S2C_CLIENT trash="
                        + (trash == null ? "null" : trash.method_7677()));
            }
        });
    }
}
