package p202probe.mixin;

import net.minecraft.class_1735;
import net.minecraft.class_465;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Accessor;

/**
 * READ-ONLY access to HandledScreen.focusedSlot (field_2787, protected).
 *
 * The whole point of p202 is that the hover is produced by cursor movement arriving through the
 * window system; this accessor only observes the result. No setter is generated, so the probe
 * cannot set the hovered slot even by accident.
 */
@Mixin(class_465.class)
public interface HandledScreenAccessor {
    @Accessor("field_2787")
    class_1735 p202$focusedSlot();
}
