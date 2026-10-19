package top.mcbridge1201.bridge;

import java.lang.reflect.Field;

import net.minecraft.class_2561;
import net.minecraft.class_442;

/** Mod Menu 7.2.2 compares a button label with TitleScreen.field_32271, which became private. */
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
}
