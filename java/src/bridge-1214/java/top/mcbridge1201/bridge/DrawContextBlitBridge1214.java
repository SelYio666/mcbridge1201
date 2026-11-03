package top.mcbridge1201.bridge;

import net.minecraft.class_1921;
import net.minecraft.class_2960;
import net.minecraft.class_332;

/**
 * 1.21.4 blit bridges for the two plain-texture flavours ironchests uses.
 *
 * <p>1.21.4's {@code class_332} blits take a {@code Function<Identifier, RenderType>} as their
 * first parameter, and the full overload also carries explicit region and texture sizes. The
 * 1.20.1 calls reaching this bridge are shorter:
 *
 * <pre>
 * 1.20.1 drawTexture(tex, x, y, u, v, w, h)                -&gt; method_25290(Lclass_2960;IIFFIIII)V
 * 1.20.1 drawTexture(tex, x, y, w, h, u, v)                -&gt; method_25302(Lclass_2960;IIIIII)V
 * </pre>
 *
 * <p>The seven-argument form is 1.20.1's convenience overload: it forwards to the full one with
 * region = the destination size and texture size = 256x256, which is exactly what
 * {@code blitSimple} reproduces. The nine-argument form already carries its own region, so it maps
 * one-to-one after the resolver is added.
 *
 * <p>Resolver: {@code class_1921.method_62277} = 1.21.4's {@code RenderType.guiTextured(Identifier)}.
 */
public final class DrawContextBlitBridge1214 {
    private DrawContextBlitBridge1214() {}

    /** 1.20.1 {@code drawTexture(tex, x, y, u, v, width, height)}. */
    public static void blit(class_332 context, class_2960 texture,
                            int x, int y, float u, float v, int width, int height,
                            int regionWidth, int regionHeight) {
        context.method_25290(class_1921::method_62277, texture, x, y, u, v,
                width, height, regionWidth, regionHeight);
    }

    /** 1.20.1 {@code drawTexture(tex, x, y, width, height, u, v)}: region = destination, 256^2 atlas. */
    public static void blitSimple(class_332 context, class_2960 texture,
                                  int x, int y, int width, int height, int u, int v) {
        context.method_25302(class_1921::method_62277, texture, x, y, (float) u, (float) v,
                width, height, width, height, 256, 256);
    }
}
