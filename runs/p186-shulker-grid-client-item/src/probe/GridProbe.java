package probe;

import java.util.List;

import net.blay09.mods.balm.mixin.AbstractContainerScreenAccessor;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.minecraft.class_1735;
import net.minecraft.class_1792;
import net.minecraft.class_1799;
import net.minecraft.class_1802;
import net.minecraft.class_2960;
import net.minecraft.class_465;
import net.minecraft.class_490;
import net.minecraft.class_7923;
import net.minecraft.class_9288;
import net.minecraft.class_9326;
import net.minecraft.class_9334;

/**
 * p186 client-only item probe: build a shulker box with a real ContainerComponent on the client,
 * put it in the hotbar, open the inventory and log the slot geometry. Hovering that slot exercises
 * the companion's PreviewTooltipData path and the mod's grid renderer.
 */
public final class GridProbe implements ClientModInitializer {
    private int ticks;
    private boolean opened;
    private boolean logged;

    @Override
    public void onInitializeClient() {
        ClientTickEvents.END_CLIENT_TICK.register(client -> {
            if (client.field_1724 == null) {
                return;
            }
            ticks++;
            if (!opened && ticks > 40 && client.field_1755 == null) {
                client.field_1724.method_31548().field_7545 = 0;
                client.method_1507(new class_490(client.field_1724));
                opened = true;
                System.out.println("GRID_INV_OPEN tick=" + ticks);
            }
            if (opened && !logged && client.field_1755 instanceof class_465<?> screen) {
                class_1792 shulker = class_7923.field_41178
                        .method_10223(class_2960.method_60655("minecraft", "shulker_box"));
                class_1799 box = new class_1799(shulker, 1);
                class_9288 container = class_9288.method_57493(
                        List.of(new class_1799(class_1802.field_8477, 5)));
                class_9326 components = class_9326.method_57841()
                        .method_57854(class_9334.field_49622, container)
                        .method_57852();
                box.method_57366(components);
                client.field_1724.method_31548().method_5447(0, box);
                var accessor = (AbstractContainerScreenAccessor) screen;
                double scale = client.method_22683().method_4495();
                System.out.println("GRID_SCREEN left=" + accessor.getLeftPos()
                        + " top=" + accessor.getTopPos() + " scale=" + scale);
                for (int i = 0; i < client.field_1724.field_7512.field_7761.size(); i++) {
                    class_1735 slot = client.field_1724.field_7512.field_7761.get(i);
                    class_1799 stack = slot.method_7677();
                    if (!stack.method_7960() && stack.method_7909() == shulker) {
                        System.out.println("GRID_SLOT index=" + i
                                + " x=" + slot.field_7873 + " y=" + slot.field_7872
                                + " count=" + stack.method_7947()
                                + " map=" + stack.method_57380());
                        break;
                    }
                }
                logged = true;
            }
        });
    }
}
