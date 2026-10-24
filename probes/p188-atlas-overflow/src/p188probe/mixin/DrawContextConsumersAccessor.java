package p188probe.mixin;

import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Accessor;

import net.minecraft.class_332;
import net.minecraft.class_4597;

/**
 * Test-only accessor: the p188 probe needs the DrawContext's vertex consumers to call the public
 * MapRenderer.draw (method_1773) for the overflow map (1025) inside a HUD frame.
 */
@Mixin(class_332.class)
public interface DrawContextConsumersAccessor {
    @Accessor("field_44658")
    net.minecraft.class_4597.class_4598 mcbridge$field_44658();
}
