package p202probe.mixin;

import net.minecraft.class_312;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Accessor;

/**
 * READ-ONLY view of the two raw cursor fields Mouse keeps from the GLFW callback
 * (field_1795/field_1794). p191/p193/p197 WROTE these through an accessor to aim; p202 must not,
 * or the hover would be the probe's own doing.
 *
 * Reading them separates two very different failures:
 *   raw changed but Mouse.getX()/getY() did not  -> the callback arrived, tick() did not apply it
 *                                                   (window focus / paused gate)
 *   raw unchanged                               -> the window never saw a cursor event at all
 */
@Mixin(class_312.class)
public interface MouseReadAccessor {
    @Accessor("field_1795")
    double p202$rawX();

    @Accessor("field_1794")
    double p202$rawY();
}
