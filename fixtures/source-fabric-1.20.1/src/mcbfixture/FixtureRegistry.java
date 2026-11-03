package mcbfixture;

import net.minecraft.class_1792;
import net.minecraft.class_2378;
import net.minecraft.class_2960;
import net.minecraft.class_7923;

/**
 * Registration, and the two constructors that 1.21.1 changes shape:
 * {@code new Identifier(ns, path)} becomes a private constructor plus {@code Identifier.of},
 * and {@code new Item(Item.Settings)} keeps its shape but its superclass chain does not.
 *
 * <p>Written against the 1.20.1 intermediary names on purpose: a Fabric mod jar references the
 * intermediary namespace, so this is the real input shape rather than a Yarn-side approximation.
 */
public final class FixtureRegistry {
    public static final class_2960 PROBE_ID = new class_2960("mcbfixture", "probe_item");
    public static class_1792 PROBE_ITEM;

    private FixtureRegistry() {
    }

    public static void bootstrap() {
        PROBE_ITEM = class_2378.method_10230(class_7923.field_41178, PROBE_ID,
                new class_1792(new class_1792.class_1793()));
    }
}
