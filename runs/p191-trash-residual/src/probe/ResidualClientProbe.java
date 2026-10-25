package probe;

import net.minecraft.class_1761;
import net.minecraft.class_1735;
import net.minecraft.class_1799;
import net.minecraft.class_310;
import net.minecraft.class_481;
import net.minecraft.class_7706;
import net.minecraft.class_7699;
import net.minecraft.class_1802;
import net.blay09.mods.trashslot.client.TrashSlotGuiHandler;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import probe.mixin.CreativeTabInvoker;

/**
 * p191 residual probe (creative inventory tab): opens the creative screen, switches to the
 * INVENTORY tab (the only tab with Type.INVENTORY), and dumps the menu slots + geometry every
 * second so the harness can hover the main-inventory slots. Also records whether the trash slot
 * canvas exists on the creative screen (upstream adds the component only on supported screens).
 * At tick 200 it switches back to the default tab for the creative-list no-delete check.
 */
public final class ResidualClientProbe implements ClientModInitializer {
    private int ticks;
    private boolean opened;
    private int invAimTick = -1;
    private int invPressedTick = -1;
    private int listAimTick = -1;
    private int listPressedTick = -1;
    private boolean switchedBack;

    @Override
    public void onInitializeClient() {
        ClientTickEvents.END_CLIENT_TICK.register(client -> {
            if (client.field_1724 == null) {
                return;
            }
            ticks++;
            if (!opened && ticks == 60 && client.field_1755 == null) {
                client.method_1507(new class_481(client.field_1724,
                        class_7699.method_45397(), false));
                opened = true;
                System.out.println("RES_OPEN tick=" + ticks);
            }
            if (opened && ticks == 65 && client.field_1755 instanceof class_481 creative) {
                class_1761 inventoryTab = null;
                for (class_1761 tab : class_7706.method_47341()) {
                    if (tab.method_47312() == class_1761.class_7916.field_41053) {
                        inventoryTab = tab;
                        break;
                    }
                }
                if (inventoryTab != null) {
                    ((CreativeTabInvoker) creative).mcbridge$selectTab(inventoryTab);
                    System.out.println("RES_TAB inventory selected");
                } else {
                    System.out.println("RES_TAB inventory NOT FOUND");
                }
                System.out.println("RES_CANVAS trashComponent="
                        + TrashSlotGuiHandler.getTrashSlotComponent());
            }
            if (opened && !switchedBack && invPressedTick > 0 && ticks >= invPressedTick + 100
                    && client.field_1755 instanceof class_481 creative) {
                switchedBack = true;
                ((CreativeTabInvoker) creative).mcbridge$selectTab(class_7706.method_47328());
                System.out.println("RES_TAB_BACK default");
            }
            // Aiming phases (OS cursor injection is unreliable on this machine): while the
            // inventory tab is up (ticks 70..150), keep the in-game mouse pinned on the slot
            // holding the 7-diamond stack; after the switch back (tick 200+), pin it on the
            // first creative-list slot. The harness only injects the Delete key.
            if (opened && ticks >= 70 && ticks % 2 == 0
                    && client.field_1755 instanceof class_481 screen) {
                var accessor = (net.blay09.mods.balm.mixin.AbstractContainerScreenAccessor) screen;
                double sc = client.method_22683().method_4495();
                class_1735 target = null;
                String phase = null;
                if (!switchedBack) {
                    for (class_1735 slot : client.field_1724.field_7512.field_7761) {
                        class_1799 stack = slot.method_7677();
                        if (slot.field_7871 == client.field_1724.method_31548()
                                && !stack.method_7960()
                                && stack.method_7947() == 7
                                && stack.method_7909() == class_1802.field_8477) {
                            target = slot;
                            phase = "inv";
                            break;
                        }
                    }
                } else {
                    for (class_1735 slot : client.field_1724.field_7512.field_7761) {
                        if (slot.getClass().getSimpleName().equals("class_482")
                                && slot.field_7873 > 0 && slot.field_7872 > 0) {
                            target = slot;
                            phase = "list";
                            break;
                        }
                    }
                }
                if (target != null) {
                    double gx = accessor.getLeftPos() + target.field_7873 + 8;
                    double gy = accessor.getTopPos() + target.field_7872 + 8;
                    var mouse = (probe.mixin.MouseAccessor) client.field_1729;
                    mouse.mcbridge$setRawX(gx * sc);
                    mouse.mcbridge$setRawY(gy * sc);
                    if ("inv".equals(phase) && invAimTick < 0) {
                        invAimTick = ticks;
                    }
                    if ("list".equals(phase) && listAimTick < 0) {
                        listAimTick = ticks;
                    }
                    if (ticks % 20 == 0) {
                        System.out.println("RES_AIM phase=" + phase
                                + " gx=" + gx + " gy=" + gy);
                    }
                }
            }
            // Synthetic Delete through the REAL Keyboard.onKey GLFW-callback path: OS key
            // injection is unreliable on this machine (focus races), and the callback entry is
            // the exact code a real key press runs (ScreenKeyEvent.Press.Post included).
            // Event-driven: the inv press only fires 2 s AFTER the 7-diamond stack appears in
            // the menu (server sync settles), the list press 2 s after the tab switch back.
            if (opened && invPressedTick < 0 && invAimTick > 0 && ticks >= invAimTick + 40
                    && client.field_1755 != null) {
                long window = client.method_22683().method_4490();
                client.field_1774.method_1466(window, 261, 339, 1, 0);
                client.field_1774.method_1466(window, 261, 339, 0, 0);
                invPressedTick = ticks;
                System.out.println("RES_KEY phase=inv tick=" + ticks);
            }
            if (opened && listPressedTick < 0 && listAimTick > 0 && ticks >= listAimTick + 40
                    && client.field_1755 != null) {
                long window = client.method_22683().method_4490();
                client.field_1774.method_1466(window, 261, 339, 1, 0);
                client.field_1774.method_1466(window, 261, 339, 0, 0);
                listPressedTick = ticks;
                System.out.println("RES_KEY phase=list tick=" + ticks);
            }
            if (opened && ticks % 20 == 0 && client.field_1755 instanceof class_481) {
                var accessor = (net.blay09.mods.balm.mixin.AbstractContainerScreenAccessor)
                        client.field_1755;
                int i = 0;
                for (class_1735 slot : client.field_1724.field_7512.field_7761) {
                    class_1799 stack = slot.method_7677();
                    System.out.println("RES_SLOT i=" + i
                            + " class=" + slot.getClass().getSimpleName()
                            + " container=" + slot.field_7871.getClass().getSimpleName()
                            + " slotIndex=" + slot.field_7874
                            + " x=" + slot.field_7873 + " y=" + slot.field_7872
                            + " item=" + (stack.method_7960() ? "empty"
                                    : stack.method_7909() + "x" + stack.method_7947()));
                    i++;
                }
                double scale = client.method_22683().method_4495();
                System.out.println("RES_GEOM left=" + accessor.getLeftPos()
                        + " top=" + accessor.getTopPos()
                        + " scale=" + scale);
                System.out.println("RES_MOUSE gx=" + (client.field_1729.method_1603() / scale)
                        + " gy=" + (client.field_1729.method_1604() / scale));
            }
        });
    }
}
