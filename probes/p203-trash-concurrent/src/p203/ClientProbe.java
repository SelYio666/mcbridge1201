package p203;

import net.blay09.mods.balm.mixin.AbstractContainerScreenAccessor;
import net.blay09.mods.trashslot.client.TrashSlotGuiHandler;
import net.blay09.mods.trashslot.client.TrashSlotSlot;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.minecraft.class_1799;
import net.minecraft.class_1802;
import net.minecraft.class_310;
import net.minecraft.class_490;
import p203.mixin.MouseAccessor;
import p203.mixin.MouseInvoker;

import java.nio.file.Files;
import java.nio.file.Path;

/**
 * p203 client probe. Both clients open the inventory, seed their LOCAL trash UI (A=5, B=4 — the
 * server does not push trash content, p64), aim the in-game mouse at their own trash slot and then
 * wait for a shared fire instant.
 *
 * <p>The instant comes from a file the harness writes only after both clients report READY, so
 * launch time and fire time are decoupled. Each client polls the clock once per tick; when it is
 * within 60 ms of the target it busy-spins the remainder on the client thread and fires the moment
 * the clock crosses. Both clients therefore fire within a couple of milliseconds of each other
 * rather than within a tick of each other, which is what makes "same server tick" plausible at all.
 *
 * <p>Actions are taken through the same callback paths p191/p192 used: the private GLFW
 * mouse-button callback for B's right-click (take one) and Keyboard.onKey for A's Delete (empty).
 */
public final class ClientProbe implements ClientModInitializer {
    private static final String ROLE = System.getProperty("p203.role", "none");
    private static final int SEED = Integer.getInteger("p203.seed", 0);
    private static final String ACTION = System.getProperty("p203.action", "none");
    private static final String FIRE_FILE = System.getProperty("p203.fireFile", "");

    private int ticks;
    private boolean opened;
    private boolean seeded;
    private boolean aimed;
    private boolean announced;
    private long fireAt = -1L;
    private boolean fired;

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
                System.out.println("P203_OPEN role=" + ROLE);
            }
            if (!opened) {
                return;
            }
            TrashSlotSlot trash = TrashSlotGuiHandler.getTrashSlot();
            if (!seeded && ticks >= 70 && trash != null) {
                trash.method_7673(new class_1799(class_1802.field_8477, SEED));
                seeded = true;
                System.out.println("P203_SEED role=" + ROLE + " trash=diamondx" + SEED);
            }
            if (!seeded || trash == null || !(client.field_1755 instanceof class_490)) {
                return;
            }
            // Keep the in-game cursor pinned on our own trash slot every tick until we fire.
            class_490 screen = (class_490) client.field_1755;
            var accessor = (AbstractContainerScreenAccessor) screen;
            double scale = client.method_22683().method_4495();
            if (trash.field_7873 > 0) {
                double gx = accessor.getLeftPos() + trash.field_7873 + 8;
                double gy = accessor.getTopPos() + trash.field_7872 + 8;
                var mouse = (MouseAccessor) client.field_1729;
                mouse.p203$setRawX(gx * scale);
                mouse.p203$setRawY(gy * scale);
                if (!aimed) {
                    aimed = true;
                    System.out.println("P203_AIM role=" + ROLE + " gx=" + gx + " gy=" + gy
                            + " scale=" + scale);
                }
            }
            if (aimed && !announced) {
                announced = true;
                System.out.println("P203_READY role=" + ROLE + " seed=" + SEED
                        + " action=" + ACTION + " tick=" + ticks);
            }
            if (aimed && ticks % 20 == 0) {
                class_1799 inTrash = trash.method_7677();
                System.out.println("P203_TRASH role=" + ROLE + " tick=" + ticks
                        + " trash=" + ConcurrentProbe.describe(inTrash)
                        + " carried=" + ConcurrentProbe.describe(
                                client.field_1724.field_7512.method_34255()));
            }
            if (!fired) {
                maybeFire(client);
            }
        });
    }

    private void maybeFire(class_310 client) {
        if (fireAt < 0) {
            if (FIRE_FILE.isEmpty()) {
                return;
            }
            try {
                String text = Files.readString(Path.of(FIRE_FILE)).trim();
                if (!text.isEmpty()) {
                    fireAt = Long.parseLong(text.split("\\s+")[0]);
                    System.out.println("P203_ARM role=" + ROLE + " fireAt=" + fireAt
                            + " now=" + System.currentTimeMillis()
                            + " waitMs=" + (fireAt - System.currentTimeMillis()));
                }
            } catch (Exception ignored) {
                // not written yet, or half-written; next tick
            }
            return;
        }
        long now = System.currentTimeMillis();
        if (now < fireAt - 60) {
            return;
        }
        while (System.currentTimeMillis() < fireAt) {
            Thread.onSpinWait();
        }
        long epoch = System.currentTimeMillis();
        fire(client);
        fired = true;
        System.out.println("P203_FIRE role=" + ROLE + " action=" + ACTION
                + " epochMs=" + epoch + " driftMs=" + (epoch - fireAt) + " tick=" + ticks);
    }

    private void fire(class_310 client) {
        long window = client.method_22683().method_4490();
        if ("delete".equals(ACTION)) {
            client.field_1774.method_1466(window, 261, 339, 1, 0);
            client.field_1774.method_1466(window, 261, 339, 0, 0);
        } else if ("take".equals(ACTION)) {
            ((MouseInvoker) client.field_1729).p203$onMouseButton(window, 1, 1, 0);
            ((MouseInvoker) client.field_1729).p203$onMouseButton(window, 1, 0, 0);
        }
    }
}
