package top.mcbridge1201.bridge;

import net.minecraft.class_1269;

/**
 * 1.21.4 bridge for {@code InteractionResult}'s constant fields.
 *
 * <p>In 1.20.1/{@code class_1269} these fields are declared as {@code class_1269} itself. 1.21.4
 * turns them into records that {@code implement class_1269} - a subtype, but a <em>different
 * descriptor</em>, and JVMS 5.4.3.2 resolves a field by name AND descriptor. So the old
 * {@code GETSTATIC ... : Lclass_1269;} fails with {@code NoSuchFieldError} even though the value
 * would have been assignable (measured in {@code JvmResolutionTest}, runs/p255).
 *
 * <p>Each accessor re-reads the target field and widens it back to {@code class_1269}, so the call
 * site keeps the descriptor it was compiled against. Method names are intentionally the
 * intermediary field names: what each constant <em>means</em> (SUCCESS / CONSUME / PASS / FAIL)
 * was not re-verified for 1.21.4, and naming a conversion after a guess is how a bridge starts
 * lying.
 */
public final class InteractionResultBridge1214 {
    private InteractionResultBridge1214() {}

    public static class_1269 field5811() {
        return class_1269.field_5811;
    }

    public static class_1269 field5812() {
        return class_1269.field_5812;
    }

    public static class_1269 field21466() {
        return class_1269.field_21466;
    }
}
