package probe.mixin;

import net.minecraft.class_312;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Accessor;

/** Test-only setter access to the raw mouse fields (in-game aiming, see p191). */
@Mixin(class_312.class)
public interface MouseAccessor {
    @Accessor("field_1795")
    void mcbridge$setRawX(double x);

    @Accessor("field_1794")
    void mcbridge$setRawY(double y);
}
