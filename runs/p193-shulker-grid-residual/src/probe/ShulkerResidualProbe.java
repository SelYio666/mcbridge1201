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
import net.minecraft.class_310;
import net.minecraft.class_1761;
import net.minecraft.class_481;
import net.minecraft.class_490;
import net.minecraft.class_7706;
import probe.mixin.CreativeTabInvoker;
import net.minecraft.class_7923;
import net.minecraft.class_9288;
import net.minecraft.class_9326;
import net.minecraft.class_9334;
import probe.mixin.MouseAccessor;

/**
 * p193: the three p187 residuals, all through the REAL screen path (no HudRenderCallback is
 * registered - every SBT_/GRID markers marker can only come from the vanilla inventory tooltip):
 *
 * 1. multi-item grid: a client-side box with 3 diamonds + 2 emeralds (inventory slot 9) and a
 *    real server box (/item replace, slot 10) must each draw TWO slots in the COMPACT grid;
 * 2. FULL preview: hold RIGHT_SHIFT (the mod's default full-preview key, KEYSYM 342) via the
 *    real Keyboard.onKey callback while hovering - the renderer must log type=FULL;
 * 3. real hover: the mouse is aimed by writing the raw Mouse fields (p191 method); the screen
 *    computes its own hoveredSlot and renders the tooltip itself.
 *
 * Phase order: A) hover client box, COMPACT; B) hold RSHIFT over the same box -> FULL;
 * C) once the server box synced into slot 10, release RSHIFT and hover the server box.
 */
public final class ShulkerResidualProbe implements ClientModInitializer {
    /** Set while the FULL preview should read as "right shift held" (see InputPollMixin). */
    public static volatile boolean fullPollActive;
    private int ticks;
    private boolean opened;
    private boolean tabSwitched;
    private boolean phaseB;
    private int reopenTick = -1;
    private boolean fullPressed;
    private int clientAimTick = -1;
    private int serverAimTick = -1;

    @Override
    public void onInitializeClient() {
        ClientTickEvents.END_CLIENT_TICK.register(client -> {
            if (client.field_1724 == null) {
                return;
            }
            ticks++;
            if (ticks % 20 == 0) {
                System.out.println("P193_HEART tick=" + ticks + " screen="
                        + (client.field_1755 == null ? "null"
                                : client.field_1755.getClass().getSimpleName()));
            }
            if (ticks == 60) {
                class_1799 box = new class_1799(shulkerItem(), 1);
                class_9288 container = class_9288.method_57493(List.of(
                        new class_1799(class_1802.field_8477, 3),
                        new class_1799(emeraldItem(), 2)));
                class_9326 components = class_9326.method_57841()
                        .method_57854(class_9334.field_49622, container)
                        .method_57852();
                box.method_57366(components);
                client.field_1724.method_31548().method_5447(9, box);
                System.out.println("P193_CLIENT_BOX slot=9 diamondx3+emeraldx2");
            }
            if (!opened && ticks == 70 && client.field_1755 == null) {
                // In creative mode vanilla replaces InventoryScreen with the creative screen
                // (class_481) during init - p193 heartbeat proved it; work WITH it: open, then
                // switch to the inventory tab (p191 CreativeTabInvoker).
                client.method_1507(new class_490(client.field_1724));
                opened = true;
                System.out.println("P193_OPEN");
            }
            if (opened && !tabSwitched && ticks == 75
                    && client.field_1755 instanceof class_481 creative) {
                class_1761 inventoryTab = null;
                for (class_1761 tab : class_7706.method_47341()) {
                    if (tab.method_47312() == class_1761.class_7916.field_41053) {
                        inventoryTab = tab;
                        break;
                    }
                }
                if (inventoryTab != null) {
                    ((CreativeTabInvoker) creative).mcbridge$selectTab(inventoryTab);
                    tabSwitched = true;
                    System.out.println("P193_TAB inventory");
                }
            }
            if (fullPressed && !phaseB && ticks >= clientAimTick + 200) {
                phaseB = true;
                fullPollActive = false;
                long win = client.method_22683().method_4490();
                client.field_1774.method_1466(win, 256, 1, 1, 0);   // GLFW_PRESS ESC
                client.field_1774.method_1466(win, 256, 1, 0, 0);   // GLFW_RELEASE ESC
                System.out.println("P193_PHASEB tick=" + ticks);
            }
            if (phaseB && reopenTick < 0 && ticks >= clientAimTick + 220
                    && client.field_1755 == null) {
                reopenTick = ticks;
                client.method_1507(new class_490(client.field_1724));
                System.out.println("P193_SURVIVAL_SCREEN tick=" + ticks + " screen="
                        + client.field_1755.getClass().getSimpleName());
            }
            if (client.field_1755 == null
                    || !(client.field_1755 instanceof net.minecraft.class_465<?> screen)) {
                return;
            }
            var accessor = (AbstractContainerScreenAccessor) screen;
            double scale = client.method_22683().method_4495();
            if (ticks % 20 == 0) {
                int listPos = 0;
                for (class_1735 slot : client.field_1724.field_7512.field_7761) {
                    class_1799 stack = slot.method_7677();
                    if (!stack.method_7960() && stack.method_7909() == shulkerItem()) {
                        System.out.println("P193_BOX_SLOT listPos=" + listPos
                                + " x=" + slot.field_7873 + " y=" + slot.field_7872
                                + " map=" + stack.method_57380());
                    }
                    listPos++;
                }
                System.out.println("P193_GEOM left=" + accessor.getLeftPos()
                        + " top=" + accessor.getTopPos() + " scale=" + scale);
            }
            // phase switch (survival only): once the server box synced into slot 10, retarget.
            boolean serverPhase = serverAimTick >= 0;
            if (!serverPhase && phaseB && hasServerBox(client)
                    && client.field_1755 != null) {
                serverAimTick = ticks;
                serverPhase = true;
                System.out.println("P193_SERVER_AIM tick=" + ticks);
            }
            if (ticks == 80) {
                System.out.println("P193_DIAG screen-open-no-aim survived");
            }
            // aim the in-game mouse at the current target slot centre (diagnostics: only from
            // tick 140, so a freeze before/after cleanly separates screen-open from hover).
            if (ticks == 140) {
                System.out.println("P193_DIAG starting aim");
            }
            class_1735 target = ticks < 140 ? null : findSlot(client, serverPhase ? 10 : 9);
            if (target != null && ticks % 2 == 0) {
                double gx = accessor.getLeftPos() + target.field_7873 + 8;
                double gy = accessor.getTopPos() + target.field_7872 + 8;
                var mouse = (MouseAccessor) client.field_1729;
                mouse.mcbridge$setRawX(gx * scale);
                mouse.mcbridge$setRawY(gy * scale);
                if (clientAimTick < 0 && !serverPhase) {
                    clientAimTick = ticks;
                    System.out.println("P193_CLIENT_AIM gx=" + gx + " gy=" + gy);
                }
            }
            // FULL preview: flip the poll-synthesized right-shift for 6 s (the harness takes
            // the after-full screenshot and switches the player to survival in that window).
            if (!fullPressed && clientAimTick > 0 && !serverPhase
                    && ticks >= clientAimTick + 80) {
                fullPressed = true;
                fullPollActive = true;
                long win = client.method_22683().method_4490();
                client.field_1774.method_1466(win, 342, 342, 1, 0);  // triggers updatePreviewKeys
                System.out.println("P193_FULL_REQUEST tick=" + ticks);
            }
            // Phase B: after the FULL window, close the screen (real ESC through the key
            // callback) and re-open the inventory - in survival it stays the real class_490.
        });
    }

    private static class_1792 shulkerItem() {
        return class_7923.field_41178
                .method_10223(class_2960.method_60655("minecraft", "shulker_box"));
    }

    private static class_1792 emeraldItem() {
        return class_7923.field_41178
                .method_10223(class_2960.method_60655("minecraft", "emerald"));
    }

    /** Inventory-tab slots are class_484 wrappers whose field_7874 is always 0; the LIST
     * POSITION is the PlayerInventory index (p191). */
    private static class_1735 findSlot(class_310 client, int invIndex) {
        java.util.List<class_1735> slots = client.field_1724.field_7512.field_7761;
        if (invIndex < 0 || invIndex >= slots.size()) {
            return null;
        }
        class_1735 slot = slots.get(invIndex);
        return slot.field_7871 == client.field_1724.method_31548() ? slot : null;
    }

    private static boolean hasServerBox(class_310 client) {
        class_1799 stack = client.field_1724.method_31548().method_5438(10);
        return !stack.method_7960() && stack.method_7909() == shulkerItem();
    }
}
