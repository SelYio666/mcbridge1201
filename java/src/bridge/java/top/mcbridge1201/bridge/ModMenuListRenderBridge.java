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
 *
 * <p>The description panel is the other shape of the same problem. {@code DescriptionListWidget}'s
 * render method builds its rows first and only then draws through the removed pipeline, so its body
 * is not replaced wholesale: the rule keeps everything up to the removed tail and appends
 * {@link #renderDescription}, which draws the panel backdrop, the already-built rows, and a
 * scrollbar. Nothing here rebuilds ModMenu's row list - that is still its own code.
 *
 * <p>Where the panel is drawn is read from the widget's 1.20.1 geometry fields (left/right/top/
 * bottom, written by {@code setLeftPos}) when a converted subclass keeps them, not from
 * {@code getX()}: in 1.21.1 that accessor belongs to ClickableWidget and never sees setLeftPos, so
 * the first version of this bridge drew the panel at x=0 - on top of the mod list, which is painted
 * afterwards - while the screen had placed it at x=328.
 */
public final class ModMenuListRenderBridge {
    /** Off by default: the bridge is shipped in release jars and must not chatter. */
    private static final boolean DEBUG = Boolean.getBoolean("mcbridge.listrender.debug");
    /** Entry count last reported per list class: the description panel starts empty and fills in
     * when a mod is selected, so its line has to be printed again on the change, not once. */
    private static final java.util.Map<String, Integer> LAST_COUNT = new java.util.HashMap<>();
    private static final java.util.Set<String> HIGHLIGHT_ANNOUNCED = new java.util.HashSet<>();
    private static final java.util.Set<String> PANEL_ANNOUNCED = new java.util.HashSet<>();
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
    /** Replaces the removed textured panel backdrop of the description list. */
    private static final int PANEL_BACKDROP = 0x80000000;
    private static final int SCROLL_TRACK = 0x40000000;
    private static final int SCROLL_THUMB = 0xC0A0A0A0;

    private ModMenuListRenderBridge() {
    }

    /** ModListWidget.method_25311: rows on top of a flat band, no panel of their own. */
    public static void renderList(Object list, class_332 context, int mouseX, int mouseY, float delta) {
        try {
            draw(list, context, mouseX, mouseY, delta, false);
        } catch (ReflectiveOperationException e) {
            throw new RuntimeException("Mod Menu list render failed", e);
        }
    }

    /**
     * Tail of DescriptionListWidget's render, appended after its own row building. The widget is
     * one panel, not a list of bands: the backdrop goes behind all rows and the scrollbar is drawn
     * because the removed tail also drew it.
     */
    public static void renderDescription(Object list, class_332 context, int mouseX, int mouseY,
                                         float delta) {
        try {
            draw(list, context, mouseX, mouseY, delta, true);
        } catch (ReflectiveOperationException e) {
            throw new RuntimeException("Mod Menu description render failed", e);
        }
    }

    private static void draw(Object list, class_332 context, int mouseX, int mouseY, float delta,
                             boolean panel) throws ReflectiveOperationException {
        Class<?> type = list.getClass();
        int count = (int) invoke(type, list, "method_25340");
        int rowWidth = (int) invoke(type, list, "method_25322");
        int itemHeight = field(type, "field_22741").getInt(list);
        // Where the widget really is. 1.21.1's getX()/getY() come from ClickableWidget, and for a
        // converted 1.20.1 subclass they hold what its constructor passed - not what the screen
        // moved it to afterwards: Mod Menu sets the description panel's left with the 1.20.1
        // EntryListWidget.setLeftPos, which no longer exists and is kept by LegacyParentWidget in
        // field_19088. Reading that pair first is the difference between drawing the panel over the
        // mod list (x = 0) and drawing it where the screen put it (x = 328 on a 640 wide GUI).
        // The mod list keeps the vanilla accessors so the geometry p205/p206 measured does not move.
        int boxLeft;
        int boxRight;
        int boxTop;
        int boxBottom;
        boolean legacy = panel && fieldOrNull(type, "field_19088") != null;
        if (legacy) {
            boxLeft = field(type, "field_19088").getInt(list);
            boxRight = field(type, "field_19087").getInt(list);
            boxTop = field(type, "field_19085").getInt(list);
            boxBottom = field(type, "field_19086").getInt(list);
        } else {
            boxLeft = (int) invoke(type, list, "method_46426");
            boxRight = boxLeft + field(type, "field_22758").getInt(list);
            boxTop = (int) invoke(type, list, "method_46427");
            boxBottom = (int) invoke(type, list, "method_55443");
        }
        // 1.20.1 EntryListWidget.getRowLeft(): the row area is centred in the widget, plus 2 px.
        int left = legacy ? (boxLeft + boxRight) / 2 - rowWidth / 2 + 2
                : (int) invoke(type, list, "method_25342");
        int widgetTop = boxTop;
        int widgetBottom = boxBottom;
        Object hovered = invoke(type, list, "method_25308", (double) mouseX, (double) mouseY);
        boolean focused = (boolean) invoke(type, list, "method_25370");
        int rowHeight = Math.max(1, itemHeight - 4);
        Integer previousCount = DEBUG ? LAST_COUNT.put(type.getName(), count) : null;
        if (DEBUG && (previousCount == null || previousCount != count)) {
            System.out.println("P205_LIST class=" + type.getSimpleName() + " count=" + count
                    + " left=" + left + " rowWidth=" + rowWidth
                    + " itemHeight=" + itemHeight + " rows=" + widgetTop + ".." + widgetBottom
                    + " mouse=" + mouseX + "," + mouseY
                    + " focused=" + focused
                    + " box=" + boxLeft + "," + widgetTop + "," + (boxRight - boxLeft)
                    + "," + (widgetBottom - widgetTop)
                    + " legacy=" + legacy + " getX=" + (int) invoke(type, list, "method_46426")
                    + " firstEntry=" + (count > 0
                    ? invoke(type, list, "method_25326", 0).getClass().getName() : "none"));
        }
        if (panel) {
            context.method_25294(boxLeft, widgetTop, boxRight, widgetBottom, PANEL_BACKDROP);
            if (DEBUG && PANEL_ANNOUNCED.add(type.getName())) {
                System.out.println("P207_PANEL class=" + type.getSimpleName()
                        + " box=" + boxLeft + "," + widgetTop + "," + (boxRight - boxLeft) + ","
                        + (widgetBottom - widgetTop) + " count=" + count
                        + " legacy=" + legacy + " rowLeft=" + left);
            }
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
            // list is still legible against the blurred screen background. The description panel
            // has one backdrop for all rows instead, so its text is not striped.
            if (!panel) {
                context.method_25294(left, top, left + rowWidth, bottom, 0x80000000);
            }
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
        if (panel) {
            drawScrollBar(list, context, boxLeft, boxRight, widgetTop, widgetBottom);
        }
        if (DEBUG) {
            Integer previous = LAST_SELECTED.put(type.getName(), selected);
            if (previous == null || previous != selected) {
                System.out.println("P205_SELECT class=" + type.getSimpleName()
                        + " selected=" + selected + " count=" + count
                        + " focused=" + focused);
            }
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

    /**
     * A plain scrollbar replacing {@code DescriptionListWidget.renderScrollBar}, which drew into a
     * 1.20.1 BufferBuilder. Geometry follows the vanilla numbers (2 px inset, 4 px of slack); the
     * colours are flat because the textured sprite is gone. It is an approximation, and it is only
     * drawn when there is something to scroll.
     */
    private static void drawScrollBar(Object list, class_332 context, int boxLeft, int boxRight,
                                      int widgetTop, int widgetBottom)
            throws ReflectiveOperationException {
        Class<?> type = list.getClass();
        double scroll = (double) invoke(type, list, "method_25341");
        int maxScroll = (int) invoke(type, list, "method_25331");
        int viewHeight = widgetBottom - widgetTop;
        if (maxScroll <= 0 || viewHeight < 12) {
            return;
        }
        int trackTop = widgetTop + 2;
        int trackHeight = viewHeight - 4;
        double visible = trackHeight / (double) (trackHeight + maxScroll);
        int thumbHeight = Math.max(16, (int) Math.round(trackHeight * visible));
        double ratio = Math.min(1.0, Math.max(0.0, scroll / (double) maxScroll));
        int thumbTop = trackTop + (int) Math.round((trackHeight - thumbHeight) * ratio);
        int x2 = boxRight - 2;
        int x1 = Math.max(boxLeft + 2, x2 - 6);
        context.method_25294(x1, trackTop, x2, trackTop + trackHeight, SCROLL_TRACK);
        context.method_25294(x1, thumbTop, x2, thumbTop + thumbHeight, SCROLL_THUMB);
        if (DEBUG) {
            System.out.println("P207_SCROLL class=" + type.getSimpleName()
                    + " scroll=" + scroll + " max=" + maxScroll
                    + " thumb=" + thumbTop + "+" + thumbHeight + " x=" + x1 + ".." + x2);
        }
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

    /** Same walk, but "absent" is an answer rather than an error: legacy fields are optional. */
    private static Field fieldOrNull(Class<?> type, String name) {
        for (Class<?> c = type; c != null; c = c.getSuperclass()) {
            try {
                Field f = c.getDeclaredField(name);
                f.setAccessible(true);
                return f;
            } catch (NoSuchFieldException ignored) {
                // keep walking up
            }
        }
        return null;
    }
}
