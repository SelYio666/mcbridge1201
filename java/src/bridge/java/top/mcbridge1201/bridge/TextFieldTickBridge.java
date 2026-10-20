package top.mcbridge1201.bridge;

import net.minecraft.class_342;

/**
 * Replacement for the removed 1.20.1 TextFieldWidget.tick() (class_342.method_1865).
 *
 * <p>That method only incremented the cursor-blink counter (field_2107). 1.21.1 removed the tick
 * method because the cursor blink is now derived from real time inside the widget rendering, so
 * there is no state left to advance. The bridge exists so converted call sites link; it has no
 * observable behaviour to preserve.
 */
public final class TextFieldTickBridge {
    private TextFieldTickBridge() {
    }

    public static void tick(class_342 field) {
        // Nothing to advance: 1.21.1 computes the blink phase from wall-clock time.
    }
}
