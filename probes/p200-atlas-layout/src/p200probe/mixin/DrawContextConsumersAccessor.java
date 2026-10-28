package p200probe.mixin;

import net.minecraft.class_332;
import net.minecraft.class_4597;

import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Accessor;

/**
 * Test-only accessor: the p200 probe needs the DrawContext's vertex consumers to call the public
 * MapRenderer.render (method_1773) inside a HUD frame.
 */
@Mixin(class_332.class)
public interface DrawContextConsumersAccessor {
    @Accessor("field_44658")
    net.minecraft.class_4597.class_4598 mcbridge$field_44658();
}
