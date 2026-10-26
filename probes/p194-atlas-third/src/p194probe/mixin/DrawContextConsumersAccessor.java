package p194probe.mixin;

import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Accessor;

import net.minecraft.class_332;
import net.minecraft.class_4597;

/**
 * Test-only accessor: the p194 probe needs the DrawContext's vertex consumers to call the public
 * MapRenderer.draw (method_1773) for map 1/1025/2049 inside one HUD frame.
 */
@Mixin(class_332.class)
public interface DrawContextConsumersAccessor {
    @Accessor("field_44658")
    net.minecraft.class_4597.class_4598 mcbridge$field_44658();
}
