package top.mcbridge1201.bridge;

import net.minecraft.class_332;
import net.minecraft.class_437;

/**
 * Cloth Config's config screen calls its own {@code method_25434(DrawContext)} to paint the
 * backdrop. That method overrode 1.20.1's {@code Screen.renderBackground(DrawContext)}; 1.21.1
 * changed the parent to {@code renderBackground(DrawContext, int, int, float)}
 * ({@code class_437.method_25420}), so the override no longer compiles against anything - the class
 * still carries it and still calls it, and the JVM reports
 * {@code NoSuchMethodError: ClothConfigScreen.method_25434(class_332)} on the first frame.
 *
 * <p>The call is forwarded to the current entry point with neutral pointer coordinates: a backdrop
 * does not use them. Found only after the option rows started rendering - the same call site was
 * unreachable while the list was renamed out of the render path
 * (runs/p210-cloth-config/after/client.log).
 */
public final class ClothConfigScreenBridge {
    private ClothConfigScreenBridge() {
    }

    public static void renderBackground(class_437 screen, class_332 context) {
        screen.method_25420(context, 0, 0, 0.0f);
    }
}
