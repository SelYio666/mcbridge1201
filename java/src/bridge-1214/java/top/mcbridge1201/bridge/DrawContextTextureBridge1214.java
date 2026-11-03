package top.mcbridge1201.bridge;

import net.minecraft.class_2960;
import net.minecraft.class_332;
import net.minecraft.class_1921;

/**
 * 1.21.4 nine-slice bridge for the 1.20.1 {@code DrawContext.drawNineSlicedTexture} call.
 *
 * <p>Same contract as the 1.21.1 bridge ({@code DrawContextTextureBridge.drawNineSliced}): a
 * 1.20.1 mod asks for a nine-sliced texture with twelve ints, and later versions have no such
 * helper, so the nine patches are emitted here.
 *
 * <p>What changed in 1.21.4 - and why this class exists instead of reusing the 1.21.1 one:
 * {@code class_332.method_25293} gained a {@code Function<Identifier, RenderType>} as its first
 * parameter and moved {@code u}/{@code v} in front of {@code width}/{@code height}:
 *
 * <pre>
 * 1.21.1: blit(            id, x, y, width, height, u, v, regionW, regionH, texW, texH)
 * 1.21.4: blit(renderType, id, x, y, u,         v, width, height, regionW, regionH, texW, texH, color)
 * </pre>
 *
 * <p>{@code class_1921.method_62277} is 1.21.4's {@code RenderType.guiTextured(Identifier)}: the
 * GUI-textured resolver the vanilla code passes for a plain texture blit. {@code -1} is the
 * untinted colour.
 */
public final class DrawContextTextureBridge1214 {
    private DrawContextTextureBridge1214() {}

    public static void drawNineSliced(class_332 context, class_2960 texture,
                                      int x, int y, int width, int height,
                                      int left, int top, int right, int bottom,
                                      int textureWidth, int textureHeight,
                                      int u, int v) {
        int centerWidth = textureWidth - left - right;
        int centerHeight = textureHeight - top - bottom;
        if (width < left + right || height < top + bottom
                || centerWidth <= 0 || centerHeight <= 0) {
            blit(context, texture, x, y, width, height, u, v,
                    textureWidth, textureHeight, textureWidth, textureHeight);
            return;
        }

        int destCenterWidth = width - left - right;
        int destCenterHeight = height - top - bottom;

        blit(context, texture, x, y, left, top,
                u, v, left, top, textureWidth, textureHeight);
        blit(context, texture, x + width - right, y, right, top,
                u + textureWidth - right, v, right, top, textureWidth, textureHeight);
        blit(context, texture, x, y + height - bottom, left, bottom,
                u, v + textureHeight - bottom, left, bottom, textureWidth, textureHeight);
        blit(context, texture, x + width - right, y + height - bottom, right, bottom,
                u + textureWidth - right, v + textureHeight - bottom,
                right, bottom, textureWidth, textureHeight);

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

        blit(context, texture, x + left, y + top, destCenterWidth, destCenterHeight,
                u + left, v + top, centerWidth, centerHeight, textureWidth, textureHeight);
    }

    private static void blit(class_332 context, class_2960 texture,
                             int x, int y, int width, int height,
                             int u, int v, int regionWidth, int regionHeight,
                             int textureWidth, int textureHeight) {
        // 1.21.4 argument order: resolver, texture, x, y, u, v, width, height, region..., -1 tint.
        context.method_25293(class_1921::method_62277, texture, x, y, (float) u, (float) v,
                width, height, regionWidth, regionHeight, textureWidth, textureHeight, -1);
    }
}
