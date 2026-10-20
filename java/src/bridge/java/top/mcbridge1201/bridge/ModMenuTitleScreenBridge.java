package top.mcbridge1201.bridge;

import java.lang.reflect.Field;

import net.minecraft.class_2561;
import net.minecraft.class_332;
import net.minecraft.class_437;
import net.minecraft.class_442;

/** Mod Menu 7.2.2 title/list screen adaptations for 1.21.1. */
public final class ModMenuTitleScreenBridge {
    private ModMenuTitleScreenBridge() {
    }

    public static class_2561 titleText() {
        try {
            Field f = class_442.class.getDeclaredField("field_32271");
            f.setAccessible(true);
            return (class_2561) f.get(null);
        } catch (ReflectiveOperationException e) {
            throw new RuntimeException("TitleScreen.field_32271 is not accessible", e);
        }
    }

    /**
     * 1.20.1 Screen.renderBackground(DrawContext) became
     * renderBackground(DrawContext, int mouseX, int mouseY, float delta) in 1.21.1
     * (class_437.method_25420). The background does not need the pointer position, so the
     * converted call is forwarded with neutral coordinates.
     */
    public static void renderBackground(class_437 screen, class_332 context) {
        screen.method_25420(context, 0, 0, 0.0f);
    }
}
