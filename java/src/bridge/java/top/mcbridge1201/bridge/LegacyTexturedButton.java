package top.mcbridge1201.bridge;

import net.minecraft.class_2561;
import net.minecraft.class_2960;
import net.minecraft.class_310;
import net.minecraft.class_327;
import net.minecraft.class_332;
import net.minecraft.class_344;
import net.minecraft.class_4185;
import net.minecraft.class_8666;

/**
 * Keeps the 1.20.1 TexturedButtonWidget constructor and its texture-atlas drawing alive.
 *
 * <p>1.20.1 buttons were drawn from a sub-region (u/v/texWidth/texHeight) of an arbitrary texture
 * Identifier. 1.21.1 replaced that with WidgetSprites, which only supports whole GUI sprites. This
 * class accepts the old constructor arguments and re-implements the old drawing (texture quad plus
 * centred label) on top of the 1.21.1 widget, so icons keep their original look.
 */
public class LegacyTexturedButton extends class_344 {
    private final class_2960 texture;
    private final int u;
    private final int v;
    private final int vOffset;
    private final int texWidth;
    private final int texHeight;

    public LegacyTexturedButton(int x, int y, int width, int height, int u, int v, int vOffset,
                                class_2960 texture, int texWidth, int texHeight,
                                class_4185.class_4241 onPress, class_2561 message) {
        super(x, y, width, height, new class_8666(texture, texture), onPress, message);
        this.texture = texture;
        this.u = u;
        this.v = v;
        this.vOffset = vOffset;
        this.texWidth = texWidth;
        this.texHeight = texHeight;
    }

    /** Old constructor variant without a label (icon-only buttons). */
    public LegacyTexturedButton(int x, int y, int width, int height, int u, int v,
                                class_2960 texture, class_4185.class_4241 onPress) {
        this(x, y, width, height, u, v, 0, texture, 256, 256, onPress, class_2561.method_43470(""));
    }

    /** Old constructor variant with a hover v-offset but no label. */
    public LegacyTexturedButton(int x, int y, int width, int height, int u, int v, int vOffset,
                                class_2960 texture, class_4185.class_4241 onPress) {
        this(x, y, width, height, u, v, vOffset, texture, 256, 256, onPress,
                class_2561.method_43470(""));
    }

    /** Old constructor variant with texture size but no label. */
    public LegacyTexturedButton(int x, int y, int width, int height, int u, int v, int vOffset,
                                class_2960 texture, int texWidth, int texHeight,
                                class_4185.class_4241 onPress) {
        this(x, y, width, height, u, v, vOffset, texture, texWidth, texHeight, onPress,
                class_2561.method_43470(""));
    }

    /** Factory used by constructorRedirects for {@code new TexturedButtonWidget(...)} call sites. */
    public static class_344 create(int x, int y, int width, int height, int u, int v, int vOffset,
                                   class_2960 texture, int texWidth, int texHeight,
                                   class_4185.class_4241 onPress, class_2561 message) {
        return new LegacyTexturedButton(x, y, width, height, u, v, vOffset, texture, texWidth,
                texHeight, onPress, message);
    }

    @Override
    public void method_48579(class_332 context, int mouseX, int mouseY, float delta) {
        int x = method_46426();
        int y = method_46427();
        int width = method_25368();
        int height = method_25364();
        int vv = this.v + (method_25370() ? this.vOffset : 0);
        context.method_25290(this.texture, x, y, this.u, vv, width, height,
                this.texWidth, this.texHeight);
        class_2561 message = method_25369();
        class_327 font = class_310.method_1551().field_1772;
        int textWidth = font.method_27525(message);
        context.method_51439(font, message, x + (width - textWidth) / 2, y + (height - 8) / 2,
                0xFFFFFF, true);
    }
}
