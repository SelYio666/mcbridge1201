package top.mcbridge1201.bridge;

import net.minecraft.class_1767;

/**
 * 1.21.1 re-used {@code DyeColor.method_7787} for an int colour, while 1.20.x callers expect the
 * old {@code float[]} components. This unwraps RGB (0xRRGGBB) into the legacy array.
 */
public final class DyeColorBridge {
    private DyeColorBridge() {
    }

    public static float[] legacyComponents(class_1767 color) {
        int rgb = color.method_7787();
        return new float[]{
                ((rgb >> 16) & 0xFF) / 255.0f,
                ((rgb >> 8) & 0xFF) / 255.0f,
                (rgb & 0xFF) / 255.0f,
        };
    }
}
