package top.mcbridge1201.bridge;

import net.minecraft.class_2960;
import net.minecraft.class_332;

/**
 * 1.20.1 {@code DrawContext.drawTexture(...)} (12 ints) bridge.
 *
 * <p>1.21.1 split this into several overloads. IronChests' {@code GeneratedScreenRenderer} calls the
 * old shape with (x, y, width, height, u=4, v=4, regionWidth=4, regionHeight=4, textureWidth=256,
 * textureHeight=256, 0, 0); the first ten values map directly onto
 * {@code method_25293(Identifier, int, int, int, int, float, float, int, int, int, int)}. The two
 * trailing legacy ints have no 1.21.1 counterpart and are ignored.
 */
public final class DrawContextTextureBridge {
    private DrawContextTextureBridge() {}

    public static void drawTexture(class_332 context, class_2960 texture,
                                   int x, int y, int width, int height,
                                   int u, int v, int regionWidth, int regionHeight,
                                   int textureWidth, int textureHeight,
                                   int legacyA, int legacyB) {
        context.method_25293(texture, x, y, width, height, u, v,
                regionWidth, regionHeight, textureWidth, textureHeight);
    }
}
