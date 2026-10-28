package p202probe;

import java.nio.DoubleBuffer;

import net.blay09.mods.balm.mixin.AbstractContainerScreenAccessor;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.minecraft.class_1735;
import net.minecraft.class_1792;
import net.minecraft.class_1799;
import net.minecraft.class_2960;
import net.minecraft.class_310;
import net.minecraft.class_465;
import net.minecraft.class_490;
import net.minecraft.class_7923;
import net.minecraft.class_9288;
import net.minecraft.class_9334;
import org.lwjgl.BufferUtils;
import org.lwjgl.glfw.GLFW;

/**
 * p202: the two things p193/p196/p197 left open - a hover that comes from the WINDOW SYSTEM rather
 * than from a field write, and a 27-slot box whose slots carry DIFFERENT NBT.
 *
 * Hover. p191/p193/p197 aimed by writing Mouse.field_1795/field_1794 through an accessor, because
 * earlier runs could not get the game window to see cursor movement. That is a probe poke, not a
 * hover. Here the probe NEVER writes mouse state: it only reads. The cursor is moved from outside
 * this process (run.py -> SetCursorPos/SetCursorPos via user32) to the window coordinates this
 * probe announces in P202_TARGET, and the position then has to arrive through the normal chain
 *
 *     WM_MOUSEMOVE -> GLFW cursor-pos callback -> Mouse.onCursorPos -> Mouse.tick
 *                  -> GameRenderer -> Screen.render(DrawContext, mouseX, mouseY, delta)
 *                  -> HandledScreen.isMouseOver(slot) -> focusedSlot
 *
 * for the hover to happen at all. P202_CURSOR prints, side by side, what GLFW reports
 * (glfwGetCursorPos) and what the game computed from it (Mouse.getX/getY), so the two independent
 * reads have to agree; P202_HOVER_OK is printed only when HandledScreen.focusedSlot (field_2787)
 * is slot 10 AND no synthetic key has been sent yet (keysSent=false in the line).
 *
 * If the window never sees the OS move (that is what earlier runs hit), the probe says so with
 * P202_FALLBACK and places the cursor through GLFW's own glfwSetCursorPos - still a window-system
 * call that has to come back through the callback above, still not a field write - and the report
 * distinguishes osCursor vs glfwCursor instead of calling both "OS-level".
 *
 * NBT. The box is placed by the server on a 27-slot container where every slot differs: item id,
 * count, custom name, and a mix of enchantments / lore / custom_model_data / glint override. The
 * probe dumps the CLIENT's view of each of those 27 stacks (component map, verbatim) so the
 * heterogeneity is evidence, not a construction claim, and PreviewDrawProbeMixin logs every
 * drawItem call with its index, item, count and component map - 27 cells, 27 distinct payloads.
 *
 * Keys: to reach FULL the probe still forges the poll boundary for J(74)/K(75) exactly like p197
 * (InputPollMixin, defaults 340/342 can never satisfy it). That happens only AFTER the hover has
 * been proven, so the hover evidence stands on its own.
 */
public final class HoverNbtProbe implements ClientModInitializer {
    /** Rebound preview keys from the p197 config (also used by InputPollMixin). */
    public static final int PREVIEW_CODE = 74; // GLFW_KEY_J
    public static final int FULL_CODE = 75;    // GLFW_KEY_K

    public static volatile boolean previewHeld;
    public static volatile boolean fullHeld;

    private static final java.util.Set<Integer> POLLED =
            java.util.Collections.synchronizedSortedSet(new java.util.TreeSet<>());

    public static void notePoll(int code) {
        if (POLLED.add(code)) {
            System.out.println("P202_POLL code=" + code);
        }
    }

    private int ticks;
    private boolean opened;
    private boolean nbtLogged;
    private boolean windowLogged;
    private int targetTick = -1;
    private int hoverTick = -1;
    private int fallbackTick = -1;
    private int lastCursorLog = -100;
    private boolean compactRequested;
    private boolean fullRequested;
    private boolean fullReleased;
    private boolean previewReleased;
    private int fullTick = -1;
    private double targetX = -1;
    private double targetY = -1;
    private boolean keysSent;
    private int focusAttr = -1;
    private boolean focusRequested;

    @Override
    public void onInitializeClient() {
        ClientTickEvents.END_CLIENT_TICK.register(client -> {
            if (client.field_1724 == null) {
                return;
            }
            ticks++;
            if (ticks % 20 == 0) {
                System.out.println("P202_HEART tick=" + ticks + " screen="
                        + (client.field_1755 == null ? "null"
                                : client.field_1755.getClass().getSimpleName()));
            }
            // 1) the server box has to exist before the inventory is opened
            if (!opened && hasServerBox(client) && client.field_1755 == null) {
                if (!nbtLogged) {
                    nbtLogged = true;
                    dumpBox(client);
                }
                client.method_1507(new class_490(client.field_1724));
                opened = true;
                System.out.println("P202_OPEN tick=" + ticks);
            }
            if (client.field_1755 == null
                    || !(client.field_1755 instanceof class_465<?> screen)) {
                return;
            }
            var accessor = (AbstractContainerScreenAccessor) screen;
            double scale = client.method_22683().method_4495();
            long win = client.method_22683().method_4490();
            class_1735 target = findSlot(client, 10);
            if (target == null) {
                return;
            }
            double gx = accessor.getLeftPos() + target.field_7873 + 8;
            double gy = accessor.getTopPos() + target.field_7872 + 8;
            targetX = gx * scale;
            targetY = gy * scale;
            if (targetTick < 0) {
                targetTick = ticks;
                logWindow(client, win, scale, gx, gy);
            }
            focusAttr = GLFW.glfwGetWindowAttrib(win, GLFW.GLFW_FOCUSED);
            // Ask the window manager for focus once. A window that is not focused makes
            // Mouse.tick() skip the whole position update (class_310.method_1569 gate), so the
            // OS move would be recorded in the raw field and never reach Screen.render.
            if (!focusRequested && focusAttr == 0) {
                focusRequested = true;
                GLFW.glfwFocusWindow(win);
                System.out.println("P202_FOCUS_REQUEST tick=" + ticks);
            }
            // 2) hover, with no synthetic input sent yet
            if (hoverTick < 0 && ticks > targetTick) {
                Object focused = ((p202probe.mixin.HandledScreenAccessor) screen)
                        .p202$focusedSlot();
                if (focused instanceof class_1735 slot && slot.field_7872 == target.field_7872
                        && slot.field_7873 == target.field_7873
                        && slot.method_7677() == target.method_7677()) {
                    hoverTick = ticks;
                    System.out.println("P202_HOVER_OK tick=" + ticks
                            + " index=" + slotIndex(client, slot)
                            + " item=" + idOf(slot.method_7677().method_7909())
                            + " compsOfHoveredStack=" + componentOf(slot.method_7677())
                            + " keysSent=false"
                            + " glfw=" + glfwCursor(win)
                            + " raw=" + round(((p202probe.mixin.MouseReadAccessor) client.field_1729)
                            .p202$rawX()) + ","
                            + round(((p202probe.mixin.MouseReadAccessor) client.field_1729)
                            .p202$rawY())
                            + " mouse=" + round(client.field_1729.method_1603()) + ","
                            + round(client.field_1729.method_1604())
                            + " target=" + round(targetX) + "," + round(targetY));
                }
            }
            // 3) honest fallback: if the window never saw the OS move, place the cursor through
            //    GLFW instead of writing Mouse fields, and label it as such.
            if (hoverTick < 0 && ticks > targetTick + 200 && fallbackTick < 0) {
                fallbackTick = ticks;
                GLFW.glfwSetCursorPos(win, targetX, targetY);
                System.out.println("P202_FALLBACK tick=" + ticks + " reason=no-hover-after-200t"
                        + " glfwSetCursorPos=" + round(targetX) + "," + round(targetY)
                        + " focus=" + focusAttr);
            }
            if (targetTick > 0 && ticks - lastCursorLog >= 10) {
                lastCursorLog = ticks;
                var mouse = (p202probe.mixin.MouseReadAccessor) client.field_1729;
                System.out.println("P202_CURSOR tick=" + ticks + " glfw=" + glfwCursor(win)
                        + " raw=" + round(mouse.p202$rawX()) + "," + round(mouse.p202$rawY())
                        + " mouse=" + round(client.field_1729.method_1603()) + ","
                        + round(client.field_1729.method_1604())
                        + " target=" + round(targetX) + "," + round(targetY)
                        + " focus=" + focusAttr
                        + " hovered=" + (((p202probe.mixin.HandledScreenAccessor) screen)
                        .p202$focusedSlot() != null));
            }
            // 4) preview keys, only after the hover is established
            if (hoverTick > 0 && !compactRequested && ticks >= hoverTick + 80) {
                compactRequested = true;
                keysSent = true;
                previewHeld = true;
                client.field_1774.method_1466(win, PREVIEW_CODE, PREVIEW_CODE, 1, 0);
                System.out.println("P202_COMPACT_REQUEST tick=" + ticks + " J=" + PREVIEW_CODE
                        + " hoverTick=" + hoverTick);
            }
            if (compactRequested && !fullRequested && ticks >= hoverTick + 200) {
                fullRequested = true;
                fullHeld = true;
                fullTick = ticks;
                client.field_1774.method_1466(win, FULL_CODE, FULL_CODE, 1, 0);
                System.out.println("P202_FULL_REQUEST tick=" + ticks + " K=" + FULL_CODE);
            }
            if (fullRequested && !fullReleased && ticks >= fullTick + 240) {
                fullReleased = true;
                fullHeld = false;
                client.field_1774.method_1466(win, FULL_CODE, FULL_CODE, 0, 0);
                System.out.println("P202_FULL_RELEASE tick=" + ticks);
            }
            if (fullReleased && !previewReleased && ticks >= fullTick + 400) {
                previewReleased = true;
                previewHeld = false;
                client.field_1774.method_1466(win, PREVIEW_CODE, PREVIEW_CODE, 0, 0);
                System.out.println("P202_RELEASE_ALL tick=" + ticks);
                System.out.println("P202_POLLS " + POLLED);
                System.out.println("P202_DONE hoverTick=" + hoverTick
                        + " fallbackTick=" + fallbackTick
                        + " osCursor=" + (hoverTick > 0 && fallbackTick < 0)
                        + " glfwCursor=" + (hoverTick > 0 && fallbackTick > 0)
                        + " keysSent=" + keysSent
                        + " nbtStacks=" + Counters.NBT_STACKS
                        + " nbtDistinct=" + Counters.NBT_DISTINCT
                        + " drawItemCalls=" + Counters.DRAW_ITEM_CALLS
                        + " drawnDistinctNonAir=" + Counters.DRAWN_DISTINCT_NONAIR.size()
                        + " drawnItemIds=" + Counters.DRAWN_ITEMS.size()
                        + " drawItemsCalls=" + Counters.DRAW_ITEMS_CALLS
                        + " lastType=" + Counters.LAST_TYPE);
            }
        });
    }

    private void logWindow(class_310 client, long win, double scale, double gx, double gy) {
        if (windowLogged) {
            return;
        }
        windowLogged = true;
        System.out.println("P202_TARGET gx=" + round(gx) + " gy=" + round(gy)
                + " scale=" + round(scale) + " winx=" + round(targetX) + " winy=" + round(targetY));
        System.out.println("P202_WINDOW handle=" + win
                + " m4480=" + client.method_22683().method_4480()
                + " m4486=" + client.method_22683().method_4486()
                + " m4502=" + client.method_22683().method_4502()
                + " m4507=" + client.method_22683().method_4507()
                + " scale=" + round(scale)
                + " focus=" + GLFW.glfwGetWindowAttrib(win, GLFW.GLFW_FOCUSED)
                + " focused_method=" + client.method_1569());
    }

    /** Client view of the 27 stacks the server put in the box, component map verbatim. */
    private static void dumpBox(class_310 client) {
        class_1799 stack = client.field_1724.method_31548().method_5438(10);
        System.out.println("P202_BOX item=" + idOf(stack.method_7909())
                + " count=" + stack.method_7947()
                + " container=" + (componentOf(stack).contains("minecraft:container")));
        Object raw = stack.method_57353().method_57829(class_9334.field_49622);
        if (!(raw instanceof class_9288 container)) {
            System.out.println("P202_NBT missing=no-container-component type="
                    + (raw == null ? "null" : raw.getClass().getName()));
            return;
        }
        int seq = 0;
        java.util.Set<String> keys = new java.util.LinkedHashSet<>();
        java.util.Set<String> ids = new java.util.LinkedHashSet<>();
        java.util.Set<String> names = new java.util.LinkedHashSet<>();
        for (class_1799 entry : container.method_59715()) {
            if (entry.method_7960()) {
                continue;
            }
            String comps = componentOf(entry);
            String item = idOf(entry.method_7909());
            String name = extractCustomName(comps);
            keys.add(comps);
            ids.add(item);
            names.add(name);
            System.out.println("P202_NBT seq=" + seq
                    + " item=" + item
                    + " count=" + entry.method_7947()
                    + " name=" + name
                    + " comps=" + shorten(comps));
            seq++;
        }
        Counters.NBT_STACKS = seq;
        Counters.NBT_DISTINCT = keys.size();
        System.out.println("P202_NBT_SUM stacks=" + seq + " distinctComponents=" + keys.size()
                + " distinctItems=" + ids.size() + " distinctNames=" + names.size());
    }

    private static String extractCustomName(String comps) {
        int at = comps.indexOf("custom_name=");
        if (at < 0) {
            return "none";
        }
        int end = comps.indexOf(',', at);
        String tail = end < 0 ? comps.substring(at) : comps.substring(at, end);
        return tail.replace('\n', ' ').replace('\r', ' ');
    }

    private static String shorten(String text) {
        String flat = text.replace('\n', ' ').replace('\r', ' ');
        return flat.length() <= 240 ? flat : flat.substring(0, 237) + "...";
    }

    private static String componentOf(class_1799 stack) {
        try {
            return String.valueOf(stack.method_57353());
        } catch (Throwable t) {
            return "error:" + t;
        }
    }

    private static String glfwCursor(long win) {
        DoubleBuffer x = BufferUtils.createDoubleBuffer(1);
        DoubleBuffer y = BufferUtils.createDoubleBuffer(1);
        GLFW.glfwGetCursorPos(win, x, y);
        return round(x.get(0)) + "," + round(y.get(0));
    }

    private static int slotIndex(class_310 client, class_1735 slot) {
        java.util.List<class_1735> slots = client.field_1724.field_7512.field_7761;
        for (int i = 0; i < slots.size(); i++) {
            if (slots.get(i) == slot) {
                return i;
            }
        }
        return -1;
    }

    private static String idOf(class_1792 item) {
        return String.valueOf(class_7923.field_41178.method_10221(item));
    }

    private static double round(double value) {
        return Math.round(value * 10.0) / 10.0;
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
        return !stack.method_7960() && stack.method_7909() == class_7923.field_41178
                .method_10223(class_2960.method_60655("minecraft", "shulker_box"));
    }
}
