package p204probe.mixin;

import net.minecraft.class_350;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Accessor;

/**
 * EntryListWidget's row height. Vanilla's mouseScrolled moves the list by exactly half a row per
 * wheel notch (method_25401: scroll -= amount * itemHeight / 2), so this number is the prediction
 * the harness's staircase (12, 24, 36, clamp) is checked against - the probe never writes it.
 */
@Mixin(class_350.class)
public interface ListAccessor {
    @Accessor("field_22741")
    int p204$itemHeight();
}
