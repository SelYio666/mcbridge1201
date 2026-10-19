package top.mcbridge1201.bridge;

import net.minecraft.class_332;
import net.minecraft.class_437;

/**
 * 1.20.1 {@code Screen.renderBackground(DrawContext)} bridge.
 *
 * <p>1.21.1 replaced the one-argument method with
 * {@code renderBackground(DrawContext, int, int, float)} (mouse x/y and partial tick), so mod
 * screens that still call the old shape hit {@code NoSuchMethodError}. The bridge forwards to the
 * new method with neutral parameters.
 */
public final class ScreenRenderBridge {
    private ScreenRenderBridge() {}

    public static void renderBackground(class_437 screen, class_332 context) {
        screen.method_25420(context, 0, 0, 0.0f);
    }
}
