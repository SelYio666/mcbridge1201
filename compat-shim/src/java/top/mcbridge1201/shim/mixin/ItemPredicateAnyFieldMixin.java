package top.mcbridge1201.shim.mixin;

import java.util.Map;
import java.util.Optional;

import net.minecraft.class_2073;
import net.minecraft.class_2096.class_2100;
import net.minecraft.class_9329;

import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/**
 * Runtime shim for the 1.20.1 {@code ItemPredicate.ANY} constant (intermediary
 * class_2073.field_9640), which 1.21.1 removed when ItemPredicate became a record.
 *
 * 1.20.1 mods patch every GETSTATIC of this field through the {@code itempredicate.any.static-field}
 * fieldRedirect rule; this shim is the rule-free alternative: Mixin re-adds the missing static
 * field to class_2073 itself, initialized to the exact empty-predicate shape the bridge builds
 * (Optional.empty() items, MinMaxBounds.Ints.ANY, DataComponentPredicate.EMPTY, empty Map) - an
 * empty ItemPredicate matches every stack, which is what the 1.20.1 constant meant.
 *
 * Built by tools/build_compat_shim.py; the jar stays in work/, never in the repository.
 */
@Mixin(class_2073.class)
public abstract class ItemPredicateAnyFieldMixin {
    // public static on purpose: foreign GETSTATIC sites need a public member with this exact
    // name. Mixin rejects non-private static fields, so tools/build_compat_shim.py marks the
    // COMPILED field ACC_SYNTHETIC (validateField skips synthetic; field resolution ignores it).
    public static class_2073 field_9640;

    @Inject(method = "<clinit>", at = @At("TAIL"))
    private static void mcbridge$addLegacyAny(CallbackInfo ci) {
        field_9640 = new class_2073(Optional.empty(), class_2100.field_9708, class_9329.field_49597, Map.of());
    }
}
