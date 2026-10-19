package top.mcbridge1201.bridge;

import net.minecraft.class_2960;
import net.minecraft.class_332;

/**
 * 1.20.1 {@code DrawContext.drawNineSlicedTexture(...)} bridge.
 *
 * <p>1.21.1 removed the nine-slice helper. IronChests' {@code GeneratedScreenRenderer} calls the
 * 12-int overload:
 *
 * <pre>
 * drawNineSlicedTexture(texture, x, y, width, height,
 *                       left=4, top=4, right=4, bottom=4,
 *                       centerWidth=256, centerHeight=256, u=0, v=0)
 * </pre>
 *
 * <p>The bridge reproduces the nine patches with 1.21.1's full {@code blit}
 * ({@code method_25293}). {@code centerWidth/centerHeight} are the texture dimensions, so the
 * stretchable center is {@code centerWidth - left - right} by {@code centerHeight - top - bottom}.
 */
public final class DrawContextTextureBridge {
    private DrawContextTextureBridge() {}

    public static void drawNineSliced(class_332 context, class_2960 texture,
                                      int x, int y, int width, int height,
                                      int left, int top, int right, int bottom,
                                      int textureWidth, int textureHeight,
                                      int u, int v) {
        int centerWidth = textureWidth - left - right;
        int centerHeight = textureHeight - top - bottom;
        if (width < left + right || height < top + bottom
                || centerWidth <= 0 || centerHeight <= 0) {
            // Degenerate box: fall back to a single stretched draw of the whole texture region.
            blit(context, texture, x, y, width, height, u, v,
                    textureWidth, textureHeight, textureWidth, textureHeight);
            return;
        }

        int destCenterWidth = width - left - right;
        int destCenterHeight = height - top - bottom;

        // corners
        blit(context, texture, x, y, left, top,
                u, v, left, top, textureWidth, textureHeight);
        blit(context, texture, x + width - right, y, right, top,
                u + textureWidth - right, v, right, top, textureWidth, textureHeight);
        blit(context, texture, x, y + height - bottom, left, bottom,
                u, v + textureHeight - bottom, left, bottom, textureWidth, textureHeight);
        blit(context, texture, x + width - right, y + height - bottom, right, bottom,
                u + textureWidth - right, v + textureHeight - bottom,
                right, bottom, textureWidth, textureHeight);

        // edges
        blit(context, texture, x + left, y, destCenterWidth, top,
                u + left, v, centerWidth, top, textureWidth, textureHeight);
        blit(context, texture, x + left, y + height - bottom, destCenterWidth, bottom,
                u + left, v + textureHeight - bottom,
                centerWidth, bottom, textureWidth, textureHeight);
        blit(context, texture, x, y + top, left, destCenterHeight,
                u, v + top, left, centerHeight, textureWidth, textureHeight);
        blit(context, texture, x + width - right, y + top, right, destCenterHeight,
                u + textureWidth - right, v + top,
                right, centerHeight, textureWidth, textureHeight);

        // center
        blit(context, texture, x + left, y + top, destCenterWidth, destCenterHeight,
                u + left, v + top, centerWidth, centerHeight, textureWidth, textureHeight);
    }

    private static void blit(class_332 context, class_2960 texture,
                             int x, int y, int width, int height,
                             int u, int v, int regionWidth, int regionHeight,
                             int textureWidth, int textureHeight) {
        context.method_25293(texture, x, y, width, height, u, v,
                regionWidth, regionHeight, textureWidth, textureHeight);
    }
}
