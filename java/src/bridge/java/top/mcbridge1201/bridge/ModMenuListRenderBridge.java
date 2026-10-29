package top.mcbridge1201.bridge;

import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.Objects;

import net.minecraft.class_332;

/**
 * Replacement body for ModListWidget.method_25311 (EntryListWidget.renderList).
 *
 * <p>The original body draws a textured background through 1.20.1 RenderSystem/Shader calls
 * (class_289.method_1349 and friends) that no longer exist in 1.21.1 and cannot be forwarded.
 * This version draws a plain translucent row background with DrawContext and then asks each entry
 * to render itself through the still-present Entry hooks, so the list stays usable.
 *
 * <p>The per-row call has to follow vanilla {@code EntryListWidget.renderList} exactly:
 *
 * <pre>
 *   left   = getRowLeft()    method_25342   x + width / 2 - getRowWidth() / 2 + 2
 *   right  = getRowWidth()   method_25322   220 unless a subclass overrides it
 *   height = itemHeight - 4  field_22741
 *   for each entry:
 *     y = getRowTop(i)       method_25337
 *     skip unless y + itemHeight &gt;= getY() and y &lt;= getBottom()
 *     hovered = (getEntryAtPosition(mouseX, mouseY) == entry)    method_25308
 *     if (isSelected(i)) drawSelection(ctx, y, width, height, hasFocus() ? -1 : -8355712, black)
 *     entry.drawBorder(ctx, i, y, x, width, height, mouseX, mouseY, hovered, delta)
 *     entry.render    (ctx, i, y, x, width, height, mouseX, mouseY, hovered, delta)
 * </pre>
 *
 * <p>Selection is drawn by {@code EntryListWidget.method_44398}, which the bridge cannot call through
 * the redirect (only the body of the replaced method is redirected) and which is protected, so it is
 * re-implemented here from its bytecode: two fills, a 2 px overhang above and below the row, and a
 * 1 px inset border. The colours are the vanilla pair - white while the list has focus, grey when it
 * does not - and black for the border. On top of that a translucent wash is added, because one white
 * pixel around a black interior is not a visible selection on this backdrop.
 *
 * <p>ModMenu's {@code ModListEntry.render} reads its parameters in that order - the second int after
 * the index is {@code y}, the third is {@code x} - so passing them the other way round puts every
 * row somewhere else on screen. That was the p205 defect: the row backdrop was painted (it uses the
 * same left/top values the loop already had) while the icon and the name went missing.
 */
public final class ModMenuListRenderBridge {
    /** Off by default: the bridge is shipped in release jars and must not chatter. */
    private static final boolean DEBUG = Boolean.getBoolean("mcbridge.listrender.debug");
    /** Entry count last reported per list class: the description panel starts empty and fills in
     * when a mod is selected, so its line has to be printed again on the change, not once. */
    private static final java.util.Map<String, Integer> LAST_COUNT = new java.util.HashMap<>();
    private static final java.util.Set<String> HIGHLIGHT_ANNOUNCED = new java.util.HashSet<>();
    /** Last selected row per list class, so a click can be reported once instead of every frame. */
    private static final java.util.Map<String, Integer> LAST_SELECTED = new java.util.HashMap<>();
    private static final int SELECTED_FOCUSED = 0xFFFFFFFF;
    private static final int SELECTED_UNFOCUSED = 0xFF808080;
    private static final int SELECTED_BORDER = 0xFF000000;
    /**
     * Deliberate deviation from vanilla: the outline alone is a single pixel, and against this
     * bridge's flat row band (the textured 1.20.1 backdrop is gone) it is practically invisible.
     * A translucent wash is laid over the row so the selection actually reads as selected.
     */
    private static final int SELECTED_WASH_FOCUSED = 0x40FFFFFF;
    private static final int SELECTED_WASH_IDLE = 0x24FFFFFF;

    private ModMenuListRenderBridge() {
    }

    public static void renderList(Object list, class_332 context, int mouseX, int mouseY, float delta) {
        try {
            Class<?> type = list.getClass();
            int count = (int) invoke(type, list, "method_25340");
            int left = (int) invoke(type, list, "method_25342");
            int rowWidth = (int) invoke(type, list, "method_25322");
            int itemHeight = field(type, "field_22741").getInt(list);
            int widgetTop = (int) invoke(type, list, "method_46427");
            int widgetBottom = (int) invoke(type, list, "method_55443");
            Object hovered = invoke(type, list, "method_25308", (double) mouseX, (double) mouseY);
            boolean focused = (boolean) invoke(type, list, "method_25370");
            int rowHeight = Math.max(1, itemHeight - 4);
            Integer previousCount = DEBUG ? LAST_COUNT.put(type.getName(), count) : null;
            if (DEBUG && (previousCount == null || previousCount != count)) {
                int boxX = (int) invoke(type, list, "method_46426");
                int boxWidth = field(type, "field_22758").getInt(list);
                System.out.println("P205_LIST class=" + type.getSimpleName() + " count=" + count
                        + " left=" + left + " rowWidth=" + rowWidth
                        + " itemHeight=" + itemHeight + " rows=" + widgetTop + ".." + widgetBottom
                        + " mouse=" + mouseX + "," + mouseY
                        + " focused=" + focused
                        + " box=" + boxX + "," + widgetTop + "," + boxWidth
                        + "," + (widgetBottom - widgetTop)
                        + " firstEntry=" + (count > 0
                        ? invoke(type, list, "method_25326", 0).getClass().getName() : "none"));
            }
            int selected = -1;
            for (int i = 0; i < count; i++) {
                int top = (int) invoke(type, list, "method_25337", i);
                int bottom = top + itemHeight;
                if (bottom < widgetTop || top > widgetBottom) {
                    continue;
                }
                Object entry = invoke(type, list, "method_25326", i);
                boolean isHovered = Objects.equals(entry, hovered);
                boolean isSelected = (boolean) invoke(type, list, "method_25332", i);
                if (isSelected) {
                    selected = i;
                }
                // The old shader backdrop is what is being replaced; this keeps a row band so the
                // list is still legible against the blurred screen background.
                context.method_25294(left, top, left + rowWidth, bottom, 0x80000000);
                if (isSelected) {
                    drawSelection(list, context, top, rowWidth, rowHeight,
                            focused ? SELECTED_FOCUSED : SELECTED_UNFOCUSED,
                            focused ? SELECTED_WASH_FOCUSED : SELECTED_WASH_IDLE);
                }
                entryCall(entry, "method_49568", context, i, top, left, rowWidth, rowHeight,
                        mouseX, mouseY, isHovered, delta);
                entryCall(entry, "method_25343", context, i, top, left, rowWidth, rowHeight,
                        mouseX, mouseY, isHovered, delta);
            }
            if (DEBUG) {
                Integer previous = LAST_SELECTED.put(type.getName(), selected);
                if (previous == null || previous != selected) {
                    System.out.println("P205_SELECT class=" + type.getSimpleName()
                            + " selected=" + selected + " count=" + count
                            + " focused=" + focused);
                }
            }
        } catch (ReflectiveOperationException e) {
            throw new RuntimeException("Mod Menu list render failed", e);
        }
    }

    /**
     * Re-implementation of {@code EntryListWidget.method_44398} from its bytecode: a filled band that
     * overhangs the row by 2 px on top and bottom, then a 1 px inset border. The list's own x/width
     * are read from the widget because the band is centred on it, not on the row's left edge.
     */
    private static void drawSelection(Object list, class_332 context, int y, int rowWidth,
                                      int rowHeight, int color, int wash)
            throws ReflectiveOperationException {
        Class<?> type = list.getClass();
        int listX = (int) invoke(type, list, "method_46426");
        int listWidth = field(type, "field_22758").getInt(list);
        int x1 = (listX + listWidth - rowWidth) / 2;
        int x2 = (listX + listWidth + rowWidth) / 2;
        if (DEBUG && HIGHLIGHT_ANNOUNCED.add(list.getClass().getName())) {
            System.out.println("P206_HIGHLIGHT class=" + list.getClass().getSimpleName()
                    + " x=" + x1 + ".." + x2 + " y=" + y + ".." + (y + rowHeight)
                    + " listX=" + listX + " listW=" + listWidth + " rowWidth=" + rowWidth
                    + " color=" + Integer.toHexString(color));
        }
        context.method_25294(x1, y - 2, x2, y + rowHeight + 2, color);
        context.method_25294(x1 + 1, y - 1, x2 - 1, y + rowHeight + 1, SELECTED_BORDER);
        context.method_25294(x1 + 1, y - 1, x2 - 1, y + rowHeight + 1, wash);
    }

    private static Object invoke(Class<?> type, Object target, String name, Object... args)
            throws ReflectiveOperationException {
        Class<?>[] types = new Class<?>[args.length];
        for (int i = 0; i < args.length; i++) {
            types[i] = args[i] instanceof Integer ? int.class
                    : args[i] instanceof Double ? double.class : args[i].getClass();
        }
        return method(type, name, types).invoke(target, args);
    }

    /** Entry.render / Entry.drawBorder: (context, index, y, x, width, height, mouseX, mouseY, hovered, delta). */
    private static void entryCall(Object entry, String name, class_332 context, int index,
                                  int y, int x, int width, int height, int mouseX, int mouseY,
                                  boolean hovered, float delta) throws ReflectiveOperationException {
        Method call = method(entry.getClass(), name, class_332.class,
                int.class, int.class, int.class, int.class, int.class, int.class, int.class,
                boolean.class, float.class);
        call.invoke(entry, context, index, y, x, width, height, mouseX, mouseY, hovered, delta);
    }

    private static Method method(Class<?> type, String name, Class<?>... parameterTypes)
            throws NoSuchMethodException {
        for (Class<?> c = type; c != null && c != Object.class; c = c.getSuperclass()) {
            try {
                Method m = c.getDeclaredMethod(name, parameterTypes);
                m.setAccessible(true);
                return m;
            } catch (NoSuchMethodException ignored) {
                // keep walking up
            }
        }
        throw new NoSuchMethodException(type.getName() + "." + name);
    }

    private static Field field(Class<?> type, String name) throws NoSuchFieldException {
        for (Class<?> c = type; c != null; c = c.getSuperclass()) {
            try {
                Field f = c.getDeclaredField(name);
                f.setAccessible(true);
                return f;
            } catch (NoSuchFieldException ignored) {
                // keep walking up
            }
        }
        throw new NoSuchFieldException(type.getName() + "." + name);
    }
}
