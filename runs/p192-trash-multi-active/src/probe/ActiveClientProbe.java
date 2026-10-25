package probe;

import net.blay09.mods.balm.mixin.AbstractContainerScreenAccessor;
import net.blay09.mods.trashslot.client.TrashSlotGuiHandler;
import net.blay09.mods.trashslot.client.TrashSlotSlot;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.minecraft.class_1799;
import net.minecraft.class_1802;
import net.minecraft.class_310;
import net.minecraft.class_490;
import probe.mixin.MouseAccessor;
import probe.mixin.MouseInvoker;

/**
 * p192 client probe. Every client opens the survival inventory and seeds its LOCAL trash UI to
 * 4 diamonds (the server does not push trash content, p64). Only the client started with
 * -Dp192.actor=true performs the actions, entirely through the real GLFW callback paths
 * (OS input injection is unreliable on this machine, see p191): the in-game mouse is aimed at
 * the trash slot by writing the raw mouse fields, then a right-click (take one, leave N - p185
 * semantics) and later a Delete key (empty - p183 semantics) are synthesized through
 * Mouse.onMouseButton / Keyboard.onKey.
 */
public final class ActiveClientProbe implements ClientModInitializer {
    private static final boolean ACTOR = Boolean.getBoolean("p192.actor");
    private int ticks;
    private boolean opened;
    private boolean seeded;
    private int aimTick = -1;
    private int onlineTick = -1;
    private int rightClickTick = -1;
    private int deleteTick = -1;

    @Override
    public void onInitializeClient() {
        ClientTickEvents.END_CLIENT_TICK.register(client -> {
            if (client.field_1724 == null) {
                return;
            }
            ticks++;
            if (!opened && ticks == 60 && client.field_1755 == null) {
                client.method_1507(new class_490(client.field_1724));
                opened = true;
                System.out.println("P192_OPEN actor=" + ACTOR);
            }
            if (opened && !seeded && ticks >= 70) {
                TrashSlotSlot trash = TrashSlotGuiHandler.getTrashSlot();
                if (trash != null) {
                    trash.method_7673(new class_1799(class_1802.field_8477, 4));
                    seeded = true;
                    System.out.println("P192_SEED trash=diamondx4");
                }
            }
            if (opened && ticks % 40 == 0) {
                TrashSlotSlot trash = TrashSlotGuiHandler.getTrashSlot();
                class_1799 stack = trash == null ? null : trash.method_7677();
                System.out.println("P192_TRASH screen=" + client.field_1755.getClass().getSimpleName()
                        + " trash=" + (stack == null || stack.method_7960() ? "empty"
                                : stack.method_7909() + "x" + stack.method_7947()));
            }
            if (!ACTOR || !opened) {
                return;
            }
            // Wait until all three players are online; the server seeds the trash ~2 s after
            // the third join, and acting before the seed makes the packets no-ops (run 1).
            boolean allOnline = client.field_1687 != null
                    && client.field_1687.method_18456().size() >= 3;
            if (!allOnline) {
                if (ticks % 40 == 0) {
                    System.out.println("P192_WAIT online="
                            + (client.field_1687 == null ? 0
                                    : client.field_1687.method_18456().size()));
                }
                return;
            }
            if (onlineTick < 0) {
                onlineTick = ticks;
            }
            if (ticks < onlineTick + 60) {  // seed + settle margin
                return;
            }
            // Aim the in-game mouse at the trash slot centre (gui coords from the screen).
            if (aimTick < 0 && seeded && client.field_1755 instanceof class_490 screen
                    && TrashSlotGuiHandler.getTrashSlot() != null) {
                TrashSlotSlot trash = TrashSlotGuiHandler.getTrashSlot();
                if (trash.field_7873 > 0) {  // drawBackground has positioned the slot
                    var accessor = (AbstractContainerScreenAccessor) screen;
                    double scale = client.method_22683().method_4495();
                    double gx = accessor.getLeftPos() + trash.field_7873 + 8;
                    double gy = accessor.getTopPos() + trash.field_7872 + 8;
                    var mouse = (MouseAccessor) client.field_1729;
                    mouse.mcbridge$setRawX(gx * scale);
                    mouse.mcbridge$setRawY(gy * scale);
                    aimTick = ticks;
                    System.out.println("P192_AIM gx=" + gx + " gy=" + gy);
                }
            }
            if (aimTick > 0) {
                // Keep the mouse pinned on the trash slot every other tick.
                TrashSlotSlot trash = TrashSlotGuiHandler.getTrashSlot();
                if (client.field_1755 instanceof class_490 screen && trash != null
                        && ticks % 2 == 0 && deleteTick < 0) {
                    var accessor = (AbstractContainerScreenAccessor) screen;
                    double scale = client.method_22683().method_4495();
                    var mouse = (MouseAccessor) client.field_1729;
                    mouse.mcbridge$setRawX((accessor.getLeftPos() + trash.field_7873 + 8) * scale);
                    mouse.mcbridge$setRawY((accessor.getTopPos() + trash.field_7872 + 8) * scale);
                }
            }
            long window = client.method_22683().method_4490();
            if (rightClickTick < 0 && aimTick > 0 && ticks >= aimTick + 40) {
                ((MouseInvoker) client.field_1729).mcbridge$onMouseButton(window, 1, 1, 0);
                ((MouseInvoker) client.field_1729).mcbridge$onMouseButton(window, 1, 0, 0);
                rightClickTick = ticks;
                System.out.println("P192_RIGHT_CLICK trash take-one");
            }
            if (deleteTick < 0 && rightClickTick > 0 && ticks >= rightClickTick + 80) {
                client.field_1774.method_1466(window, 261, 339, 1, 0);
                client.field_1774.method_1466(window, 261, 339, 0, 0);
                deleteTick = ticks;
                System.out.println("P192_DELETE trash empty");
            }
        });
    }
}
