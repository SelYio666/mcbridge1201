package probe;

import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.minecraft.class_490;

public final class InventoryProbe implements ClientModInitializer {
    private boolean opened;

    @Override
    public void onInitializeClient() {
        ClientTickEvents.END_CLIENT_TICK.register(client -> {
            if (!opened && client.field_1724 != null) {
                opened = true;
                client.method_1507(new class_490(client.field_1724));
                System.out.println("INVENTORY_PROBE_OPENED");
            }
        });
    }
}
