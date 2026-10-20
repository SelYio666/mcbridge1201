package top.mcbridge1201.bridge;

import java.lang.reflect.Field;
import java.lang.reflect.Method;

import net.minecraft.class_332;

/**
 * Replacement body for ModListWidget.method_25311 (the custom list renderer).
 *
 * <p>The original body draws a textured background through 1.20.1 RenderSystem/Shader calls
 * (class_289.method_1349 and friends) that no longer exist in 1.21.1 and cannot be forwarded.
 * This version draws a plain translucent row background with DrawContext and then asks each entry
 * to render itself through the still-present Entry.method_25343 hook, so the list stays usable.
 */
public final class ModMenuListRenderBridge {
    private ModMenuListRenderBridge() {
    }

    public static void renderList(Object list, class_332 context, int mouseX, int mouseY, float delta) {
        try {
            Class<?> type = list.getClass();
            int count = (int) invoke(type, list, "method_25340");
            int left = (int) invoke(type, list, "method_25342");
            int width = (int) invoke(type, list, "method_25368");
            int height = (int) invoke(type, list, "method_25364");
            int itemHeight = field(type, "field_22741").getInt(list);
            int rowWidth = Math.max(0, width - 8);
            for (int i = 0; i < count; i++) {
                int top = (int) invoke(type, list, "method_25337", i);
                int bottom = top + itemHeight;
                if (bottom < 0 || top > height) {
                    continue;
                }
                boolean hovered = mouseX >= left && mouseX < left + rowWidth
                        && mouseY >= top && mouseY < bottom;
                context.method_25294(left, top, left + rowWidth, bottom, 0x80000000);
                Object entry = invoke(type, list, "method_25326", i);
                Method render = method(entry.getClass(), "method_25343", class_332.class,
                        int.class, int.class, int.class, int.class, int.class, int.class, int.class,
                        boolean.class, float.class);
                render.invoke(entry, context, i, left, top, rowWidth, itemHeight, mouseX, mouseY,
                        hovered, delta);
            }
        } catch (ReflectiveOperationException e) {
            throw new RuntimeException("Mod Menu list render failed", e);
        }
    }

    private static Object invoke(Class<?> type, Object target, String name, Object... args)
            throws ReflectiveOperationException {
        Class<?>[] types = new Class<?>[args.length];
        for (int i = 0; i < args.length; i++) {
            types[i] = args[i] instanceof Integer ? int.class : args[i].getClass();
        }
        return method(type, name, types).invoke(target, args);
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
