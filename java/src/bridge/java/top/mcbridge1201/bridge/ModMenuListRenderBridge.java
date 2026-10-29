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
 *     entry.drawBorder(ctx, i, y, x, width, height, mouseX, mouseY, hovered, delta)
 *     entry.render    (ctx, i, y, x, width, height, mouseX, mouseY, hovered, delta)
 * </pre>
 *
 * <p>ModMenu's {@code ModListEntry.render} reads its parameters in that order - the second int after
 * the index is {@code y}, the third is {@code x} - so passing them the other way round puts every
 * row somewhere else on screen. That was the p205 defect: the row backdrop was painted (it uses the
 * same left/top values the loop already had) while the icon and the name went missing.
 */
public final class ModMenuListRenderBridge {
    /** Off by default: the bridge is shipped in release jars and must not chatter. */
    private static final boolean DEBUG = Boolean.getBoolean("mcbridge.listrender.debug");
    private static final java.util.Set<String> ANNOUNCED = new java.util.HashSet<>();

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
            int rowHeight = Math.max(1, itemHeight - 4);
            if (DEBUG && ANNOUNCED.add(type.getName())) {
                System.out.println("P205_LIST class=" + type.getSimpleName() + " count=" + count
                        + " left=" + left + " rowWidth=" + rowWidth
                        + " itemHeight=" + itemHeight + " rows=" + widgetTop + ".." + widgetBottom
                        + " mouse=" + mouseX + "," + mouseY
                        + " firstEntry=" + (count > 0
                        ? invoke(type, list, "method_25326", 0).getClass().getName() : "none"));
            }
            for (int i = 0; i < count; i++) {
                int top = (int) invoke(type, list, "method_25337", i);
                int bottom = top + itemHeight;
                if (bottom < widgetTop || top > widgetBottom) {
                    continue;
                }
                Object entry = invoke(type, list, "method_25326", i);
                boolean isHovered = Objects.equals(entry, hovered);
                // The old shader backdrop is what is being replaced; this keeps a row band so the
                // list is still legible against the blurred screen background.
                context.method_25294(left, top, left + rowWidth, bottom, 0x80000000);
                entryCall(entry, "method_49568", context, i, top, left, rowWidth, rowHeight,
                        mouseX, mouseY, isHovered, delta);
                entryCall(entry, "method_25343", context, i, top, left, rowWidth, rowHeight,
                        mouseX, mouseY, isHovered, delta);
            }
        } catch (ReflectiveOperationException e) {
            throw new RuntimeException("Mod Menu list render failed", e);
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
}
