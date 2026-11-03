package top.mcbridge1201.bridge;

import net.minecraft.class_2741;
import net.minecraft.class_2769;

/**
 * 1.21.4 bridge for {@code BlockStateProperties}' direction properties.
 *
 * <p>1.20.1 declares them as {@code DirectionProperty} ({@code class_2753}). 1.21.4 **deletes that
 * class** and declares the same fields as {@code EnumProperty<Direction>} ({@code class_2754}),
 * so the old {@code GETSTATIC ... : Lclass_2753;} fails twice over: the descriptor no longer
 * matches, and the type it names does not exist.
 *
 * <p>A bridge cannot declare a return type that is gone, so these accessors return the common
 * supertype {@code Property} ({@code class_2769}). That is sound here because every read in the
 * sample is consumed as a {@code Property} - {@code BlockState#has(Property)} and
 * {@code Property#equals} - and both remain in 1.21.4. It is checked rather than assumed: the
 * evidence run scans every reference to {@code class_2753} before patching, and the patch itself
 * recomputes stack map frames, so no frame keeps pointing at the deleted class.
 *
 * <p>If a caller needed something {@code DirectionProperty}-specific, this bridge would not be
 * enough - that would be a real port, not a redirect.
 */
public final class BlockStatePropertiesBridge1214 {
    private BlockStatePropertiesBridge1214() {}

    /** {@code BlockStateProperties.FACING} (1.20.1: {@code class_2753}, 1.21.4: {@code class_2754}). */
    public static class_2769 field12481() {
        return class_2741.field_12481;
    }

    /** The other direction property ({@code HORIZONTAL_FACING}). */
    public static class_2769 field12525() {
        return class_2741.field_12525;
    }
}
