package probe.mixin;

import net.minecraft.class_312;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Accessor;

/**
 * Test-only setter access to the game's raw mouse fields: on this machine the OS cursor moves
 * are not picked up by the game window (RES_MOUSE pinned at the window centre across whole
 * runs), so the probe drives the in-game mouse state directly for the p191 aiming phases.
 */
@Mixin(class_312.class)
public interface MouseAccessor {
    @Accessor("field_1795")
    void mcbridge$setRawX(double x);

    @Accessor("field_1794")
    void mcbridge$setRawY(double y);
}
