package top.mcbridge1201.bridge;

import net.minecraft.class_2960;

/**
 * Replacements for the one member of 1.20.1's {@code Screen} that Cloth Config still reads.
 *
 * <p>{@code ConfigBuilderImpl.<init>} does {@code this.defaultBackground = Screen.field_44669}, and
 * that constant is 1.20.1's {@code OPTIONS_BACKGROUND_TEXTURE} - the dirt background a screen paints
 * behind its own widgets. 1.21.1 removed it from {@code Screen} (the menu backdrop moved to
 * {@code textures/gui/menu_background.png} and is drawn through the shader path), so the read aborts
 * with {@code NoSuchFieldError} before Cloth Config has built anything. Mod Menu asks every mod for
 * its config screen while {@code ModsScreen} initialises, which is why four mods logged the same
 * stack once per screen open (runs/p204-wheel-input/client.log).
 *
 * <p>The value only feeds {@code AbstractConfigScreen.getBackgroundLocation()} →
 * {@code RenderSystem.setShaderTexture}, i.e. the texture behind the config rows. Returning the
 * 1.21.1 backdrop keeps that draw meaningful; it is not the original 1.20.1 bitmap, and
 * {@code runs/p210-cloth-config/} records what the surface actually looks like because of it.
 */
public final class ClothConfigBridge {
    private ClothConfigBridge() {
    }

    /** Stands in for the removed {@code Screen.OPTIONS_BACKGROUND_TEXTURE}. */
    public static class_2960 defaultBackground() {
        return class_2960.method_60655("minecraft", "textures/gui/menu_background.png");
    }
}
