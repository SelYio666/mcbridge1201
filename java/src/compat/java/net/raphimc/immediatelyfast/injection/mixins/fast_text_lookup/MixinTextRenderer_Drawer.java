package net.raphimc.immediatelyfast.injection.mixins.fast_text_lookup;

import java.lang.reflect.Field;
import java.lang.reflect.Method;
import net.minecraft.class_1921;
import net.minecraft.class_287;
import net.minecraft.class_2960;
import net.minecraft.class_327;
import net.minecraft.class_377;
import net.minecraft.class_4588;
import net.minecraft.class_4597;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Redirect;

/**
 * 1.21.1 port of the text-drawer fast path. The 1.20.4 version called
 * BufferBuilder.method_22893 to test "still building"; 1.21.1 keeps that state in the private
 * boolean field_1556 (upstream uses an access widener). We read it via cached reflection.
 * class_327.method_27526 is private too, so the font-storage lookup also uses reflection.
 */
@Mixin(targets = "net.minecraft.class_327$class_5232")
public abstract class MixinTextRenderer_Drawer {

    private static final Field BUILDING;
    private static final Method GET_FONT_STORAGE;

    static {
        try {
            BUILDING = class_287.class.getDeclaredField("field_1556");
            BUILDING.setAccessible(true);
            GET_FONT_STORAGE = class_327.class.getDeclaredMethod("method_27526", class_2960.class);
            GET_FONT_STORAGE.setAccessible(true);
        } catch (ReflectiveOperationException exc) {
            throw new ExceptionInInitializerError(exc);
        }
    }

    @Unique
    private class_1921 immediatelyFast$lastRenderLayer;
    @Unique
    private class_4588 immediatelyFast$lastVertexConsumer;
    @Unique
    private class_2960 immediatelyFast$lastFont;
    @Unique
    private class_377 immediatelyFast$lastFontStorage;

    @Redirect(method = {"accept"},
              at = @At(value = "INVOKE",
                       target = "Lnet/minecraft/class_4597;getBuffer(Lnet/minecraft/class_1921;)Lnet/minecraft/class_4588;"))
    private class_4588 reduceGetBufferCalls(class_4597 instance, class_1921 renderLayer) {
        class_4588 last = this.immediatelyFast$lastVertexConsumer;
        boolean isBufferInvalid = false;
        if (last instanceof class_287 builder) {
            try {
                isBufferInvalid = !BUILDING.getBoolean(builder);
            } catch (IllegalAccessException exc) {
                isBufferInvalid = true;
            }
        }
        if (!isBufferInvalid && this.immediatelyFast$lastRenderLayer == renderLayer) {
            return last;
        }
        this.immediatelyFast$lastRenderLayer = renderLayer;
        this.immediatelyFast$lastVertexConsumer = instance.getBuffer(renderLayer);
        return this.immediatelyFast$lastVertexConsumer;
    }

    @Redirect(method = {"accept"},
              at = @At(value = "INVOKE",
                       target = "Lnet/minecraft/class_327;method_27526(Lnet/minecraft/class_2960;)Lnet/minecraft/class_377;"))
    private class_377 reduceGetFontStorageCalls(class_327 instance, class_2960 id) {
        if (this.immediatelyFast$lastFont == id) {
            return this.immediatelyFast$lastFontStorage;
        }
        this.immediatelyFast$lastFont = id;
        try {
            this.immediatelyFast$lastFontStorage = (class_377) GET_FONT_STORAGE.invoke(instance, id);
        } catch (ReflectiveOperationException exc) {
            throw new RuntimeException("font storage lookup failed", exc);
        }
        return this.immediatelyFast$lastFontStorage;
    }
}
