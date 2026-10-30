package p210probe;

import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.List;

import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.minecraft.class_2960;
import net.minecraft.class_350;
import net.minecraft.class_310;
import net.minecraft.class_437;
import net.minecraft.class_442;

/**
 * Asks Mod Menu for AppleSkin's config screen, the same call {@code ModsScreen} makes while it is
 * being initialised, and records what comes back (p210).
 *
 * <p>The point is to exercise the real path rather than construct a Cloth screen by hand:
 * {@code ModsScreen.method_25426} walks every mod and calls {@code ModMenu.getConfigScreen}, which is
 * where {@code ConfigBuilderImpl.<init>} reads the removed {@code Screen.field_44669} and where four
 * mods logged {@code NoSuchFieldError} in runs/p204-wheel-input/client.log. This probe reaches the
 * same static call reflectively so it needs no compile-time Mod Menu dependency, catches whatever it
 * throws, and prints the stack instead of letting the client swallow it.
 *
 * <p>It also dumps the {@code Identifier} constants 1.21.1's {@code Screen} still exposes, so the
 * value the bridge returns can be compared with the ones the game itself uses instead of trusted.
 */
public final class ClothProbe implements ClientModInitializer {
    private static final String CONFIG_MOD = "appleskin";

    private int ticks;
    private boolean opened;
    private int openedAt;
    private boolean asked;
    private boolean dumpedConstants;
    private Object configScreen;
    private int switchedAt = -1;
    private boolean toggled;
    private boolean done;

    @Override
    public void onInitializeClient() {
        ClientTickEvents.END_CLIENT_TICK.register(client -> {
            ticks++;
            if (!dumpedConstants) {
                dumpedConstants = true;
                dumpScreenConstants();
            }
            if (!opened) {
                // Same condition p204 learned the hard way: only from the real title screen, because
                // the client installs its own title screen a few ticks after startup and would
                // replace anything opened earlier.
                if (!(client.field_1755 instanceof class_442)) {
                    return;
                }
                if (ticks > 60 && openModsScreen(client)) {
                    opened = true;
                    openedAt = ticks;
                }
                return;
            }
            if (!asked && ticks - openedAt >= 20) {
                asked = true;
                askForConfig(client);
                return;
            }
            if (configScreen != null && switchedAt < 0) {
                client.method_1507((class_437) configScreen);
                switchedAt = ticks;
                System.out.println("P210_SCREEN switched=true screen="
                        + client.field_1755.getClass().getName()
                        + " title=\"" + title(client.field_1755) + "\""
                        + " widgets=" + widgetCount(client.field_1755));
                describe(client.field_1755);
            }
            if (switchedAt > 0 && ticks % 20 == 0) {
                System.out.println("P210_HEART tick=" + ticks
                        + " screen=" + (client.field_1755 == null ? "null"
                        : client.field_1755.getClass().getSimpleName())
                        + " widgets=" + widgetCount(client.field_1755));
            }
            if (!toggled && switchedAt > 0 && ticks - switchedAt >= 60) {
                toggled = true;
                toggleFirstOption(client);
                return;
            }
            if (!done && switchedAt > 0 && ticks - switchedAt >= 100) {
                done = true;
                System.out.println("P210_DONE tick=" + ticks
                        + " screen=" + (client.field_1755 == null ? "null"
                        : client.field_1755.getClass().getName())
                        + " widgets=" + widgetCount(client.field_1755));
            }
        });
    }

    private boolean openModsScreen(class_310 client) {
        try {
            Class<?> cls = Class.forName("com.terraformersmc.modmenu.gui.ModsScreen");
            Object screen = cls.getConstructor(class_437.class).newInstance(client.field_1755);
            client.method_1507((class_437) screen);
            System.out.println("P210_OPEN tick=" + ticks + " screen="
                    + client.field_1755.getClass().getName());
            return true;
        } catch (Throwable t) {
            System.out.println("P210_OPEN_FAILED tick=" + ticks + " error=" + t);
            printStack(t);
            return false;
        }
    }

    private void askForConfig(class_310 client) {
        System.out.println("P210_ASK mod=" + CONFIG_MOD + " parent="
                + client.field_1755.getClass().getName());
        long start = System.nanoTime();
        try {
            Class<?> modMenu = Class.forName("com.terraformersmc.modmenu.ModMenu");
            Method get = modMenu.getMethod("getConfigScreen", String.class, class_437.class);
            Object screen = get.invoke(null, CONFIG_MOD, client.field_1755);
            long micros = (System.nanoTime() - start) / 1000;
            if (screen == null) {
                System.out.println("P210_CONFIG ok=false screen=null micros=" + micros);
                return;
            }
            configScreen = screen;
            System.out.println("P210_CONFIG ok=true screen=" + screen.getClass().getName()
                    + " micros=" + micros
                    + " title=\"" + title((class_437) screen) + "\""
                    + " widgets=" + widgetCount((class_437) screen));
        } catch (Throwable t) {
            Throwable cause = t.getCause() == null ? t : t.getCause();
            System.out.println("P210_CONFIG ok=false error=" + cause);
            printStack(cause);
        }
    }

    /** What the game itself offers as a screen backdrop on this version - the bridge's value is
     * compared against these rather than asserted from a wiki. */
    private void dumpScreenConstants() {
        for (Field field : class_437.class.getFields()) {
            if (field.getType() != class_2960.class) {
                continue;
            }
            try {
                Object value = field.get(null);
                System.out.println("P210_SCREEN_CONST field=" + field.getName()
                        + " value=" + value);
            } catch (Throwable t) {
                System.out.println("P210_SCREEN_CONST field=" + field.getName() + " error=" + t);
            }
        }
    }

    private static String title(class_437 screen) {
        try {
            Object title = screen.getClass().getMethod("method_25440").invoke(screen);
            return String.valueOf(title);
        } catch (Throwable t) {
            return "?";
        }
    }

    /** Screen.children() is {@code method_25460} in some versions and the list field in others;
     * reflection over both keeps the probe compiling against no particular one. */
    private static String widgetCount(class_437 screen) {
        if (screen == null) {
            return "-";
        }
        Object children = null;
        try {
            Field field = class_437.class.getDeclaredField("field_22786");
            field.setAccessible(true);
            children = field.get(screen);
        } catch (Throwable ignored) {
            // fall through to the method
        }
        if (children == null) {
            try {
                Method m = class_437.class.getMethod("method_25460");
                children = m.invoke(screen);
            } catch (Throwable t) {
                return "?";
            }
        }
        if (children instanceof List<?> list) {
            return Integer.toString(list.size());
        }
        return "?";
    }

    private static void printStack(Throwable t) {
        for (StackTraceElement frame : t.getStackTrace()) {
            System.out.println("P210_STACK at " + frame);
        }
    }

    /**
     * A Cloth config screen keeps its option rows inside an EntryListWidget child, so
     * {@code Screen.children().size()} is 3 whether the list has one row or fifty. Printing what each
     * child is - and, for a list, how many entries it holds - is what tells "opened" apart from
     * "opened and empty", which is the state the first run of this probe was actually in.
     */
    private static void describe(class_437 screen) {
        Object children = childrenOf(screen);
        if (!(children instanceof List<?> list)) {
            System.out.println("P210_DESCRIBE screen=" + screen.getClass().getName() + " children=?");
            return;
        }
        System.out.println("P210_DESCRIBE screen=" + screen.getClass().getName()
                + " children=" + list.size());
        for (int i = 0; i < list.size(); i++) {
            Object child = list.get(i);
            if (child == null) {
                System.out.println("P210_CHILD i=" + i + " null");
                continue;
            }
            StringBuilder line = new StringBuilder("P210_CHILD i=" + i + " class="
                    + child.getClass().getName());
            Object entries = entryListOf(child);
            if (entries instanceof List<?> rows) {
                line.append(" rows=").append(rows.size());
                // The class of each row matters more than the count: thirteen EmptyEntry objects is
                // a list that exists and has nothing in it, which is what "opened but blank" looks
                // like from the outside.
                java.util.Map<String, Integer> kinds = new java.util.TreeMap<>();
                for (Object row : rows) {
                    String kind = row == null ? "null" : row.getClass().getSimpleName();
                    if (kind.isEmpty()) {
                        kind = row.getClass().getName();
                        kind = kind.substring(kind.lastIndexOf('.') + 1);
                    }
                    kinds.merge(kind, 1, Integer::sum);
                }
                line.append(" kinds=").append(kinds);
                StringBuilder chain = new StringBuilder();
                for (Class<?> type = child.getClass(); type != null; type = type.getSuperclass()) {
                    chain.append(chain.length() == 0 ? "" : " -> ").append(type.getSimpleName());
                }
                line.append(" chain=[").append(chain).append(']');
            }
            System.out.println(line);
        }
    }

    /**
     * Proves the screen is usable, not just visible: find the first boolean option, read its value,
     * click its ON/OFF button through the screen the way a user does, and read the value again.
     *
     * <p>"It opened and drew thirteen rows" says nothing about whether a click reaches anything.
     * The value lives in Cloth's entry ({@code BooleanListEntry.getValue()}), and the button is a
     * plain {@code class_4185}; the click is delivered with {@code Screen.method_25402} at the
     * button's centre so Cloth's own hit-testing and the patched widgets are on the path. If that
     * click does not move the value, the button's action is pressed directly
     * ({@code ButtonWidget.method_25306}) and reported separately - a direct press that works while
     * the screen-level click does not is a different (and important) result, so the two are never
     * collapsed into one line.
     */
    private void toggleFirstOption(class_310 client) {
        class_437 screen = client.field_1755;
        if (screen == null) {
            System.out.println("P210_TOGGLE error=no screen");
            return;
        }
        Object row = firstBooleanRow(screen);
        if (row == null) {
            System.out.println("P210_TOGGLE error=no boolean row in the list");
            return;
        }
        Object before = valueOf(row);
        Object button = buttonOf(row);
        System.out.println("P210_TOGGLE_ROW class=" + row.getClass().getName()
                + " before=" + before
                + " button=" + (button == null ? "null" : button.getClass().getName())
                + " box=" + (button == null ? "-" : geom(button)));

        if (button != null) {
            int[] box = boxOf(button);
            if (box != null) {
                try {
                    Method click = class_437.class.getMethod("method_25402", double.class,
                            double.class, int.class);
                    boolean handled = (Boolean) click.invoke(screen,
                            box[0] + box[2] / 2.0, box[1] + box[3] / 2.0, 0);
                    Object afterClick = valueOf(row);
                    System.out.println("P210_CLICK handled=" + handled
                            + " at=" + (box[0] + box[2] / 2) + "," + (box[1] + box[3] / 2)
                            + " before=" + before + " after=" + afterClick
                            + " screen=" + (client.field_1755 == null ? "null"
                            : client.field_1755.getClass().getSimpleName()));
                } catch (Throwable t) {
                    Throwable cause = t.getCause() == null ? t : t.getCause();
                    System.out.println("P210_CLICK error=" + cause);
                    printStack(cause);
                }
            } else {
                System.out.println("P210_CLICK error=button geometry unavailable");
            }
        }

        Object afterClick = valueOf(row);
        boolean pressed = false;
        if (button != null && String.valueOf(before).equals(String.valueOf(afterClick))) {
            // The screen-level click did not move it. Press the action itself so the run still says
            // whether the toggle's own logic works, and keep the two results apart in the log.
            try {
                Method press = button.getClass().getMethod("method_25306");
                press.invoke(button);
                pressed = true;
            } catch (Throwable t) {
                for (Class<?> type = button.getClass(); type != null; type = type.getSuperclass()) {
                    try {
                        Method press = type.getDeclaredMethod("method_25306");
                        press.setAccessible(true);
                        press.invoke(button);
                        pressed = true;
                        break;
                    } catch (NoSuchMethodException ignored) {
                        // keep walking up
                    } catch (Throwable t2) {
                        System.out.println("P210_PRESS error=" + t2);
                        break;
                    }
                }
            }
        }
        Object after = valueOf(row);
        System.out.println("P210_TOGGLE row=" + row.getClass().getName()
                + " before=" + before + " after=" + after
                + " flipped=" + !String.valueOf(before).equals(String.valueOf(after))
                + " direct_press=" + pressed);
        System.out.println("P210_TOGGLE_SHOT screen=" + (client.field_1755 == null ? "null"
                : client.field_1755.getClass().getSimpleName()));
    }

    /** First entry of the screen's row list whose class is a Cloth boolean entry. */
    private static Object firstBooleanRow(class_437 screen) {
        Object children = childrenOf(screen);
        if (!(children instanceof List<?> list)) {
            return null;
        }
        for (Object child : list) {
            if (child == null) {
                continue;
            }
            Object rows = entryListOf(child);
            if (!(rows instanceof List<?> entries)) {
                continue;
            }
            for (Object entry : entries) {
                if (entry == null) {
                    continue;
                }
                String name = entry.getClass().getName();
                if (name.contains("BooleanListEntry") || name.contains("BooleanToggleBuilder")) {
                    return entry;
                }
            }
        }
        return null;
    }

    /** {@code BooleanListEntry.getValue()} (or any getValue() on the class chain). */
    private static Object valueOf(Object entry) {
        for (Class<?> type = entry.getClass(); type != null; type = type.getSuperclass()) {
            try {
                Method m = type.getDeclaredMethod("getValue");
                m.setAccessible(true);
                return m.invoke(entry);
            } catch (NoSuchMethodException ignored) {
                // keep walking up
            } catch (Throwable t) {
                return "!" + t.getClass().getSimpleName();
            }
        }
        return "?";
    }

    /** The entry's ON/OFF button: the first {@code class_4185} field, named {@code buttonWidget}. */
    private static Object buttonOf(Object entry) {
        Object fallback = null;
        for (Class<?> type = entry.getClass(); type != null; type = type.getSuperclass()) {
            for (Field field : type.getDeclaredFields()) {
                if (field.getType() != net.minecraft.class_4185.class) {
                    continue;
                }
                try {
                    field.setAccessible(true);
                    Object value = field.get(entry);
                    if (value == null) {
                        continue;
                    }
                    if (field.getName().contains("buttonWidget")) {
                        return value;
                    }
                    if (fallback == null) {
                        fallback = value;
                    }
                } catch (Throwable ignored) {
                    // unreadable field: try the next one
                }
            }
        }
        return fallback;
    }

    /** x, y, width, height of a widget as ints, or null when it cannot be read. */
    private static int[] boxOf(Object widget) {
        try {
            int x = (int) Math.round(num(callValue(widget, "method_46426")));
            int y = (int) Math.round(num(callValue(widget, "method_46427")));
            int w = (int) Math.round(num(callValue(widget, "method_25368")));
            int h = (int) Math.round(num(callValue(widget, "method_25364")));
            return new int[] {x, y, w, h};
        } catch (Throwable t) {
            return null;
        }
    }

    private static double num(Object value) {
        if (value instanceof Number n) {
            return n.doubleValue();
        }
        throw new IllegalStateException("not a number: " + value);
    }

    private static Object callValue(Object target, String name) {
        for (Class<?> type = target.getClass(); type != null; type = type.getSuperclass()) {
            try {
                Method m = type.getDeclaredMethod(name);
                m.setAccessible(true);
                return m.invoke(target);
            } catch (NoSuchMethodException ignored) {
                // keep walking up
            } catch (Throwable t) {
                throw new IllegalStateException(name + ": " + t, t);
            }
        }
        throw new IllegalStateException("no such method: " + name);
    }

    private static Object childrenOf(class_437 screen) {        try {
            Field field = class_437.class.getDeclaredField("field_22786");
            field.setAccessible(true);
            return field.get(screen);
        } catch (Throwable t) {
            return null;
        }
    }

    /** {@code EntryListWidget.children()} is class_350.method_25396; looked up by walking the class
     * chain so an override that is not public still resolves. */
    /** x, y, width, height, scroll, maxScroll of a widget, by intermediary names. */
    private static String geom(Object widget) {
        String[] names = {"method_46426", "method_46427", "method_25368", "method_25364",
                "method_25341", "method_25331"};
        StringBuilder sb = new StringBuilder("(");
        for (int i = 0; i < names.length; i++) {
            if (i > 0) {
                sb.append(',');
            }
            sb.append(call(widget, names[i]));
        }
        return sb.append(')').toString();
    }

    private static String call(Object target, String name) {
        for (Class<?> type = target.getClass(); type != null; type = type.getSuperclass()) {
            try {
                Method m = type.getDeclaredMethod(name);
                m.setAccessible(true);
                return String.valueOf(m.invoke(target));
            } catch (NoSuchMethodException ignored) {
                // keep walking up
            } catch (Throwable t) {
                return "!" + t.getClass().getSimpleName();
            }
        }
        return "-";
    }

    private static Object entryListOf(Object child) {        for (Class<?> type = child.getClass(); type != null; type = type.getSuperclass()) {
            try {
                Method m = type.getDeclaredMethod("method_25396");
                m.setAccessible(true);
                return m.invoke(child);
            } catch (NoSuchMethodException ignored) {
                // keep walking up
            } catch (Throwable t) {
                System.out.println("P210_ENTRIES_FAILED class=" + child.getClass().getName()
                        + " error=" + t);
                return null;
            }
        }
        return null;
    }
}
