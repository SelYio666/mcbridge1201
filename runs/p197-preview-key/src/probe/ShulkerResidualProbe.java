package probe;

import java.util.Set;
import java.util.TreeSet;

import net.blay09.mods.balm.mixin.AbstractContainerScreenAccessor;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.minecraft.class_1735;
import net.minecraft.class_1792;
import net.minecraft.class_1799;
import net.minecraft.class_2960;
import net.minecraft.class_310;
import net.minecraft.class_490;
import net.minecraft.class_7923;
import probe.mixin.MouseAccessor;

/**
 * p197: preview-key REBINDING through the mod's own configuration.
 *
 * p196 assumed the mod polled a hardcoded RIGHT_SHIFT (342) and recorded "config ignored". The
 * bytecode says otherwise: ShulkerBoxTooltipClient.isKeyPressed() polls
 * InputConstants.isKeyDown(window, config.controls.<key>.get().getCode()); the defaults are
 * previewKey=340 (LEFT_ALT) and fullPreviewKey=342 (RIGHT_SHIFT). p196 wrote its key under
 * configuration.preview - a category that has no such field - so the file decoded to defaults.
 *
 * Here the config is written with the real schema:
 *   preview.alwaysOn = false
 *   controls.previewKey     = key.keyboard.j (74)
 *   controls.fullPreviewKey = key.keyboard.k (75)
 *
 * J/K are chosen because they have NO vanilla key binding, so a synthetic press cannot also swap
 * the offhand or open a creative search field (F did exactly that to p197's first attempt and
 * silently removed the hover, which looked like a preview failure).
 *
 * The probe drives one survival inventory holding a real server-provided 27-item shulker box and
 * walks the four states:
 *   F/J held only          -> COMPACT
 *   J + K held             -> FULL
 *   K released, J held     -> COMPACT
 *   J released             -> NO_PREVIEW
 *
 * InputPollMixin only ever reports 74/75 as held; 340/342 can never satisfy it, so a COMPACT/FULL
 * render can only happen if the mod decoded the rebound codes. P197_CONFIG additionally logs the
 * live config codes and P197_KEYS/P197_TYPE log the mod's own state machine transitions.
 */
public final class ShulkerResidualProbe implements ClientModInitializer {
    /** p197 rebinding targets (also read by InputPollMixin). */
    public static final int PREVIEW_CODE = 74; // GLFW_KEY_J (unbound in vanilla)
    public static final int FULL_CODE = 75;    // GLFW_KEY_K (unbound in vanilla)

    /** Poll-boundary held state, set per phase; the mixin only synthesises these codes. */
    public static volatile boolean previewHeld;
    public static volatile boolean fullHeld;

    private static final Set<Integer> POLLED =
            java.util.Collections.synchronizedSortedSet(new TreeSet<>());

    public static void notePoll(int code) {
        if (POLLED.add(code)) {
            System.out.println("P197_POLL code=" + code);
        }
    }

    public static String polledCodes() {
        synchronized (POLLED) {
            return POLLED.toString();
        }
    }

    private int ticks;
    private boolean opened;
    private boolean configLogged;
    private boolean compactRequested;
    private boolean fullRequested;
    private boolean fullReleased;
    private boolean previewReleased;
    private int aimTick = -1;
    private int fullTick = -1;

    @Override
    public void onInitializeClient() {
        ClientTickEvents.END_CLIENT_TICK.register(client -> {
            if (client.field_1724 == null) {
                return;
            }
            ticks++;
            if (ticks % 20 == 0) {
                System.out.println("P197_HEART tick=" + ticks + " screen="
                        + (client.field_1755 == null ? "null"
                                : client.field_1755.getClass().getSimpleName()));
            }
            // Wait for the server box to exist before opening the survival inventory.
            if (!opened && hasServerBox(client) && client.field_1755 == null) {
                client.method_1507(new class_490(client.field_1724));
                opened = true;
                System.out.println("P197_OPEN tick=" + ticks);
            }
            if (client.field_1755 == null
                    || !(client.field_1755 instanceof net.minecraft.class_465<?> screen)) {
                return;
            }
            var accessor = (AbstractContainerScreenAccessor) screen;
            double scale = client.method_22683().method_4495();
            class_1735 target = findSlot(client, 10);
            if (target != null) {
                double gx = accessor.getLeftPos() + target.field_7873 + 8;
                double gy = accessor.getTopPos() + target.field_7872 + 8;
                var mouse = (MouseAccessor) client.field_1729;
                mouse.mcbridge$setRawX(gx * scale);
                mouse.mcbridge$setRawY(gy * scale);
                if (aimTick < 0) {
                    aimTick = ticks;
                    System.out.println("P197_AIM gx=" + gx + " gy=" + gy
                            + " left=" + accessor.getLeftPos()
                            + " top=" + accessor.getTopPos() + " scale=" + scale);
                }
            }
            if (aimTick > 0 && !configLogged) {
                configLogged = true;
                logConfig();
            }
            // Phase 1: previewKey = J only -> COMPACT.
            if (!compactRequested && aimTick > 0 && ticks >= aimTick + 40) {
                compactRequested = true;
                previewHeld = true;
                long win = client.method_22683().method_4490();
                client.field_1774.method_1466(win, PREVIEW_CODE, PREVIEW_CODE, 1, 0);
                System.out.println("P197_COMPACT_REQUEST tick=" + ticks + " J=" + PREVIEW_CODE);
            }
            // Phase 2: fullPreviewKey = K additionally held -> FULL.
            if (!fullRequested && compactRequested && ticks >= aimTick + 160) {
                fullRequested = true;
                fullHeld = true;
                fullTick = ticks;
                long win = client.method_22683().method_4490();
                client.field_1774.method_1466(win, FULL_CODE, FULL_CODE, 1, 0);
                System.out.println("P197_FULL_REQUEST tick=" + ticks + " K=" + FULL_CODE);
            }
            // Phase 3: release K only; J stays held -> COMPACT again.
            if (fullRequested && !fullReleased && ticks >= fullTick + 240) {
                fullReleased = true;
                fullHeld = false;
                long win = client.method_22683().method_4490();
                client.field_1774.method_1466(win, FULL_CODE, FULL_CODE, 0, 0);
                System.out.println("P197_FULL_RELEASE tick=" + ticks);
            }
            // Phase 4: release J -> NO_PREVIEW; report the poll set.
            if (fullReleased && !previewReleased && ticks >= fullTick + 400) {
                previewReleased = true;
                previewHeld = false;
                long win = client.method_22683().method_4490();
                client.field_1774.method_1466(win, PREVIEW_CODE, PREVIEW_CODE, 0, 0);
                System.out.println("P197_RELEASE_ALL tick=" + ticks);
                System.out.println("P197_POLLS " + polledCodes());
            }
        });
    }

    private static void logConfig() {
        try {
            var config = com.misterpemodder.shulkerboxtooltip.ShulkerBoxTooltip.config;
            if (config == null) {
                System.out.println("P197_CONFIG null");
                return;
            }
            var previewKey = config.controls.previewKey.get();
            var fullKey = config.controls.fullPreviewKey.get();
            System.out.println("P197_CONFIG alwaysOn=" + config.preview.alwaysOn
                    + " preview=" + previewKey.method_1441() + " previewCode="
                    + previewKey.method_1444()
                    + " full=" + fullKey.method_1441() + " fullCode=" + fullKey.method_1444());
        } catch (Throwable t) {
            System.out.println("P197_CONFIG error=" + t);
        }
    }

    private static class_1792 shulkerItem() {
        return class_7923.field_41178
                .method_10223(class_2960.method_60655("minecraft", "shulker_box"));
    }

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
