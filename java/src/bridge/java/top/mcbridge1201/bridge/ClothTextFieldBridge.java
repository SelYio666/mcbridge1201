package top.mcbridge1201.bridge;

import net.minecraft.class_342;

/**
 * Replacements for the two {@code TextFieldWidget} calls Cloth Config makes with 1.20.1 signatures.
 *
 * <p>1.20.1: {@code setCursorToStart()} / {@code setCursor(int)}. 1.21.1 added a
 * {@code shiftKeyPressed} flag to both ({@code method_1870(Z)V} / {@code method_1883(IZ)V}), so the
 * old descriptors no longer link - Cloth's text-field cell constructor died on
 * {@code NoSuchMethodError: void net.minecraft.class_342.method_1870()} while AppleSkin's config
 * screen was being built (runs/p210-cloth-config/attempt1-field-only/client.log).
 *
 * <p>{@code false} is the old behaviour: no selection is being extended.
 */
public final class ClothTextFieldBridge {
    private ClothTextFieldBridge() {
    }

    public static void setCursorToStart(class_342 widget) {
        widget.method_1870(false);
    }

    public static void setCursor(class_342 widget, int cursor) {
        widget.method_1883(cursor, false);
    }
}
