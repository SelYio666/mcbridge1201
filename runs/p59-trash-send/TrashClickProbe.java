package probe;

import net.blay09.mods.balm.mixin.AbstractContainerScreenAccessor;
import net.blay09.mods.trashslot.TrashHelper;
import net.blay09.mods.trashslot.client.TrashSlotGuiHandler;
import net.blay09.mods.trashslot.client.TrashSlotSlot;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.api.ModInitializer;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;
import net.fabricmc.fabric.api.networking.v1.ServerPlayConnectionEvents;
import net.minecraft.class_1713;
import net.minecraft.class_1735;
import net.minecraft.class_1799;
import net.minecraft.class_1802;
import net.minecraft.class_3222;
import net.minecraft.class_465;
import net.minecraft.class_490;

public final class TrashClickProbe implements ModInitializer, ClientModInitializer {
    private int state;
    private int ticks;
    private int diamondSlot = -1;
    private int trashSlot = -1;
    private static class_3222 joined;
    private static int serverTicks;

    @Override
    public void onInitialize() {
        ServerPlayConnectionEvents.JOIN.register((handler, sender, server) -> {
            joined = handler.method_32311();
            joined.method_7270(new class_1799(class_1802.field_8477, 5));
        });
        ServerTickEvents.END_SERVER_TICK.register(server -> {
            if (joined == null) return;
            serverTicks++;
            if (serverTicks % 40 == 0) {
                class_1799 trash = TrashHelper.getTrashItem(joined);
                if (!trash.method_7960()) {
                    System.out.println("SERVER_TRASH count=" + trash.method_7947()
                            + " item=" + trash.method_7909());
                }
            }
        });
    }

    @Override
    public void onInitializeClient() {
        ClientTickEvents.END_CLIENT_TICK.register(client -> {
            if (client.field_1724 == null) return;
            ticks++;
            if (state == 0 && client.field_1755 == null && ticks > 20) {
                client.method_1507(new class_490(client.field_1724));
                state = 1;
                ticks = 0;
            } else if (state == 1 && ticks > 20) {
                TrashSlotSlot trash = TrashSlotGuiHandler.getTrashSlot();
                var component = TrashSlotGuiHandler.getTrashSlotComponent();
                System.out.println("TRASH_PROBE screen=" + client.field_1755
                        + " trash=" + (trash == null ? "null" : trash.field_7873 + "," + trash.field_7872)
                        + " component=" + component);
                if (component != null) {
                    try {
                        var mx = component.getClass().getDeclaredMethod("getAnchoredX");
                        var my = component.getClass().getDeclaredMethod("getAnchoredY");
                        mx.setAccessible(true);
                        my.setAccessible(true);
                        System.out.println("TRASH_PROBE componentAnchor=" + mx.invoke(component)
                                + "," + my.invoke(component));
                    } catch (ReflectiveOperationException e) {
                        System.out.println("TRASH_PROBE componentAnchorError=" + e);
                    }
                    System.out.println("TRASH_PROBE rectangle=" + component.getRectangle());
                }
                if (client.field_1755 instanceof class_465<?> screen) {
                    var accessor = (AbstractContainerScreenAccessor) screen;
                    System.out.println("TRASH_PROBE leftTop=" + accessor.getLeftPos() + ","
                            + accessor.getTopPos());
                }
                if (trash == null) return;
                var handler = client.field_1724.field_7512;
                trashSlot = handler.field_7761.indexOf(trash);
                for (int i = 0; i < handler.field_7761.size(); i++) {
                    class_1735 s = handler.field_7761.get(i);
                    class_1799 st = s.method_7677();
                    if (!st.method_7960() && st.method_7909() == class_1802.field_8477) {
                        diamondSlot = i;
                        System.out.println("TRASH_PROBE diamond slot=" + i + " count=" + st.method_7947());
                    }
                }
                System.out.println("TRASH_PROBE trashIndex=" + trashSlot + " slots=" + handler.field_7761.size());
                if (diamondSlot < 0 || trashSlot < 0) {
                    System.out.println("TRASH_PROBE_ABORT");
                    state = 99;
                    return;
                }
                client.field_1761.method_2906(handler.field_7763, diamondSlot, 0, class_1713.field_7790, client.field_1724);
                state = 2;
                ticks = 0;
            } else if (state == 2 && ticks > 10) {
                var handler = client.field_1724.field_7512;
                client.field_1761.method_2906(handler.field_7763, trashSlot, 0, class_1713.field_7790, client.field_1724);
                state = 3;
                ticks = 0;
            } else if (state == 3 && ticks > 15) {
                TrashSlotSlot trash = TrashSlotGuiHandler.getTrashSlot();
                System.out.println("TRASH_PROBE_RESULT cursor=" + client.field_1724.field_7512.method_34255()
                        + " trash=" + (trash == null ? "null" : trash.method_7677()));
                state = 99;
            }
        });
    }
}
