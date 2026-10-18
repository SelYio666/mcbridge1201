package probe;

import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.api.ModInitializer;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.fabricmc.fabric.api.networking.v1.ServerPlayConnectionEvents;
import net.minecraft.class_1799;
import net.minecraft.class_1802;
import net.minecraft.class_490;

public final class GuiProbe implements ModInitializer, ClientModInitializer {
    private boolean opened;

    @Override
    public void onInitialize() {
        ServerPlayConnectionEvents.JOIN.register((handler, sender, server) ->
                handler.method_32311().method_7270(new class_1799(class_1802.field_8477, 5)));
    }

    @Override
    public void onInitializeClient() {
        ClientTickEvents.END_CLIENT_TICK.register(client -> {
            if (!opened && client.field_1724 != null) {
                opened = true;
                client.method_1507(new class_490(client.field_1724));
                System.out.println("GUI_PROBE_OPENED");
            }
        });
    }
}
