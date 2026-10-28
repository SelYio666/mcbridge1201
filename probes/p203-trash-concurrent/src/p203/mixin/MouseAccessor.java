package p203.mixin;

import net.minecraft.class_312;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Accessor;

/** Test-only setter access to the raw mouse fields (in-game aiming; same shape as p191/p192). */
@Mixin(class_312.class)
public interface MouseAccessor {
    @Accessor("field_1795")
    void p203$setRawX(double x);

    @Accessor("field_1794")
    void p203$setRawY(double y);
}
