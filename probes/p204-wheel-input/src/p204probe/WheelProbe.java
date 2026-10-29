package p204probe;

import java.lang.reflect.Field;

import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.minecraft.class_310;
import net.minecraft.class_342;
import net.minecraft.class_350;
import net.minecraft.class_437;
import net.minecraft.class_442;
import org.lwjgl.glfw.GLFW;

/**
 * p204: does a REAL OS mouse wheel and a REAL OS keyboard reach the Mod Menu screen?
 *
 * p104 tried three Windows injection methods and the list's scroll amount stayed 0.0, so the whole
 * input path was recorded as "not verified in this environment". p202 then found the actual cause
 * of that class of failure: the game window was not on top, so the point under the cursor belonged
 * to the terminal, and nothing arrived at the game. p204 re-runs the wheel on top of that fix and
 * keeps the probe strictly passive:
 *
 *   * the probe NEVER sets the scroll amount (class_350.method_60321 / method_25307 are not called
 *     anywhere in this probe, and the only accessors it holds have no setters);
 *   * it only reads: scroll amount (method_25341), max scroll (method_25331), entry count
 *     (method_25396), row height (ListAccessor), widget rectangles (WidgetAccessor), the search
 *     field's text (method_1882);
 *   * it announces the window coordinates of the list centre and the search box, and the cursor is
 *     moved there from outside the JVM (runs/p204-wheel-input/run.py);
 *   * every scroll the window delivers is logged by ScrollProbeMixin at Mouse.method_1598, and every
 *     key/char the text field receives by TextFieldMixin.
 *
 * So if P204_SCROLL_STATE shows 0 -> 12 -> 24 -> 36 -> clamped, the number came out of vanilla's
 * own scroll arithmetic (itemHeight / 2 per notch), driven by an event that was logged one layer
 * below the widget.
 */
public final class WheelProbe implements ClientModInitializer {
    private static int scrollEvents;
    private static int charEvents;
    private static int keyEvents;

    public static void noteScroll(double dx, double dy) {
        scrollEvents++;
        System.out.println("P204_SCROLL n=" + scrollEvents
                + " dx=" + round(dx) + " dy=" + round(dy));
    }

    public static void noteChar(char chr) {
        charEvents++;
        System.out.println("P204_CHAR n=" + charEvents + " c=" + chr
                + " code=" + (int) chr);
    }

    public static void noteKey(int keyCode, int scanCode) {
        keyEvents++;
        System.out.println("P204_KEY n=" + keyEvents + " code=" + keyCode
                + " scan=" + scanCode);
    }

    private int ticks;
    private boolean opened;
    private int openTick = -1;
    private int openAttempts;
    private int lastAttempt = -100;
    private boolean lostLogged;
    private int lastChangeTick = -1;
    private boolean donePrinted;
    private boolean ready;
    private double lastScroll = -1;
    private int lastEntries = -1;
    private String lastText = "";
    private boolean listedHeader;

    @Override
    public void onInitializeClient() {
        ClientTickEvents.END_CLIENT_TICK.register(client -> {
            ticks++;
            if (!opened) {
                // Only from the real title screen: the client installs its own title screen a few
                // ticks after startup and would silently replace anything opened before that
                // (the first p204 run lost the ModsScreen exactly this way, and the wheel then hit
                // a screen that had no list at all).
                if (!(client.field_1755 instanceof class_442)) {
                    return;
                }
                if (ticks - lastAttempt >= 40 && openAttempts < 15) {
                    lastAttempt = ticks;
                    openAttempts++;
                    if (openModsScreen(client)) {
                        opened = true;
                        openTick = ticks;
                    }
                }
                return;
            }
            class_437 screen = client.field_1755;
            if (screen == null) {
                return;
            }
            if (!screen.getClass().getName().startsWith("com.terraformersmc.modmenu.gui.")) {
                if (!lostLogged) {
                    lostLogged = true;
                    System.out.println("P204_SCREEN_LOST tick=" + ticks + " now="
                            + screen.getClass().getName());
                }
                return;
            }
            lostLogged = false;
            class_350<?> list = findList(screen);
            class_342 search = findSearch(screen);
            if (list == null) {
                if (ticks % 40 == 0) {
                    System.out.println("P204_HEART tick=" + ticks + " screen="
                            + screen.getClass().getName() + " list=none");
                }
                return;
            }
            double scale = client.method_22683().method_4495();
            if (!ready) {
                announce(client, list, search, scale);
                ready = true;
            }
            double scroll = list.method_25341();
            int entries = list.method_25396().size();
            String text = search == null ? "" : search.method_1882();
            if (Math.abs(scroll - lastScroll) > 1e-6 || entries != lastEntries
                    || !text.equals(lastText)) {
                System.out.println("P204_SCROLL_STATE tick=" + ticks
                        + " scroll=" + round(scroll)
                        + " max=" + list.method_25331()
                        + " entries=" + entries
                        + " text=\"" + text + "\""
                        + " scrollEvents=" + scrollEvents
                        + " charEvents=" + charEvents
                        + " keyEvents=" + keyEvents);
                lastScroll = scroll;
                lastEntries = entries;
                lastText = text;
                lastChangeTick = ticks;
            }
            if (ticks % 25 == 0) {
                System.out.println("P204_HEART tick=" + ticks
                        + " screen=" + screen.getClass().getSimpleName()
                        + " scroll=" + round(scroll)
                        + " entries=" + entries
                        + " text=\"" + text + "\""
                        + " focus=" + focusAttr(client)
                        + " searchFocused=" + (search != null && search.method_25370())
                        + " scrollEvents=" + scrollEvents
                        + " charEvents=" + charEvents);
            }
            // Settled: nothing has changed for 5 s. Printing here (instead of at a fixed tick)
            // means the summary describes the state after the last real input, not after a timer.
            // ...and only once both input channels have actually been exercised, so a quiet gap
            // between the control phases cannot be mistaken for the end of the run (the first
            // version printed its "final" summary at tick 143, before the wheel test even started).
            if (!donePrinted && scrollEvents > 0 && charEvents > 0
                    && ticks - lastChangeTick >= 100) {
                donePrinted = true;
                System.out.println("P204_DONE tick=" + ticks
                        + " scroll=" + round(list.method_25341())
                        + " max=" + list.method_25331()
                        + " entries=" + list.method_25396().size()
                        + " text=\"" + (search == null ? "" : search.method_1882()) + "\""
                        + " scrollEvents=" + scrollEvents
                        + " charEvents=" + charEvents
                        + " keyEvents=" + keyEvents);
            }
        });
    }

    /** Open Mod Menu's mod list; the class is reached reflectively so the probe needs no mod dep. */
    private boolean openModsScreen(class_310 client) {
        try {
            Class<?> cls = Class.forName("com.terraformersmc.modmenu.gui.ModsScreen");
            String parent = client.field_1755.getClass().getSimpleName();
            Object screen = cls.getConstructor(class_437.class).newInstance(client.field_1755);
            client.method_1507((class_437) screen);
            System.out.println("P204_OPEN tick=" + ticks + " parent=" + parent
                    + " screen=" + client.field_1755.getClass().getName());
            return true;
        } catch (Throwable t) {
            System.out.println("P204_OPEN_FAILED tick=" + ticks + " error=" + t);
            return false;
        }
    }

    private void announce(class_310 client, class_350<?> list, class_342 search, double scale) {
        var listAcc = (p204probe.mixin.WidgetAccessor) list;
        var listImpl = (p204probe.mixin.ListAccessor) list;
        int lx = listAcc.p204$x(), ly = listAcc.p204$y();
        int lw = listAcc.p204$width(), lh = listAcc.p204$height();
        System.out.println("P204_WINDOW handle=" + client.method_22683().method_4490()
                + " m4480=" + client.method_22683().method_4480()
                + " m4486=" + client.method_22683().method_4486()
                + " m4502=" + client.method_22683().method_4502()
                + " m4507=" + client.method_22683().method_4507()
                + " scale=" + round(scale)
                + " focus=" + focusAttr(client));
        System.out.println("P204_RECT list gui=" + lx + "," + ly + "," + lw + "," + lh
                + " win=" + win(lx, scale) + "," + win(ly, scale)
                + " itemHeight=" + listImpl.p204$itemHeight()
                + " entries=" + list.method_25396().size()
                + " max=" + list.method_25331()
                + " scroll=" + round(list.method_25341()));
        System.out.println("P204_POINT listCenter win="
                + win(lx + lw / 2.0, scale) + "," + win(ly + lh / 2.0, scale));
        if (search != null) {
            var acc = (p204probe.mixin.WidgetAccessor) search;
            int sx = acc.p204$x(), sy = acc.p204$y();
            int sw = acc.p204$width(), sh = acc.p204$height();
            System.out.println("P204_RECT search gui=" + sx + "," + sy + "," + sw + "," + sh
                    + " win=" + win(sx, scale) + "," + win(sy, scale)
                    + " text=\"" + search.method_1882() + "\"");
            System.out.println("P204_POINT searchCenter win="
                    + win(sx + sw / 2.0, scale) + "," + win(sy + sh / 2.0, scale));
        }
        System.out.println("P204_READY tick=" + ticks + " scrollEvents=" + scrollEvents);
    }

    private static long win(double gui, double scale) {
        return Math.round(gui * scale);
    }

    /** GLFW's own view of the window focus; keyboard events only reach a focused window. */
    private static int focusAttr(class_310 client) {
        return GLFW.glfwGetWindowAttrib(client.method_22683().method_4490(), GLFW.GLFW_FOCUSED);
    }

    /** The first scrollable list on the screen - Mod Menu's own widget, not a probe-side object. */
    private static class_350<?> findList(class_437 screen) {
        class_350<?> best = null;
        for (var child : screen.method_25396()) {
            if (child instanceof class_350<?> candidate) {
                if (best == null || candidate.method_25331() > best.method_25331()) {
                    best = candidate;
                }
            }
        }
        if (best != null) {
            return best;
        }
        Object field = readField(screen, "modList");
        return field instanceof class_350<?> list ? list : null;
    }

    private static class_342 findSearch(class_437 screen) {
        Object field = readField(screen, "searchBox");
        if (field instanceof class_342 box) {
            return box;
        }
        for (var child : screen.method_25396()) {
            if (child instanceof class_342 box) {
                return box;
            }
        }
        return null;
    }

    private static Object readField(Object owner, String name) {
        for (Class<?> c = owner.getClass(); c != null; c = c.getSuperclass()) {
            try {
                Field field = c.getDeclaredField(name);
                field.setAccessible(true);
                return field.get(owner);
            } catch (NoSuchFieldException ignored) {
                // keep walking up
            } catch (Throwable t) {
                System.out.println("P204_REFLECT_FAILED " + name + " " + t);
                return null;
            }
        }
        return null;
    }

    private static double round(double value) {
        return Math.round(value * 100.0) / 100.0;
    }
}
