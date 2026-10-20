package top.mcbridge1201.bridge;

import net.minecraft.class_310;
import net.minecraft.class_353;
import net.minecraft.class_4667;

/**
 * Rebuilds the old OptionsList constructor call from Mod Menu's options screen.
 *
 * <p>1.20.1 OptionsList took (client, width, height, top, bottom, itemHeight); 1.21.1 takes
 * (client, width, OptionsSubScreen parent) and reads the parent's layout. ModMenuOptionsScreen is
 * itself an OptionsSubScreen and is already the current screen when it builds the list, so the
 * factory takes the parent from the client instead of inventing one.
 */
public final class ModMenuOptionsListBridge {
    private ModMenuOptionsListBridge() {
    }

    public static class_353 create(class_310 client, int width, int height, int top, int bottom,
                                   int itemHeight) {
        if (!(client.field_1755 instanceof class_4667 parent)) {
            throw new IllegalStateException("Mod Menu options list needs an OptionsSubScreen parent, got "
                    + (client.field_1755 == null ? "null" : client.field_1755.getClass().getName()));
        }
        return new class_353(client, width, parent);
    }
}
