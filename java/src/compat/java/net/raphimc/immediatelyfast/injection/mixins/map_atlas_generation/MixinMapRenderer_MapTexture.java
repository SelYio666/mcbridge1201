package net.raphimc.immediatelyfast.injection.mixins.map_atlas_generation;

import net.minecraft.class_1011;
import net.minecraft.class_1043;
import net.minecraft.class_1060;
import net.minecraft.class_22;
import net.minecraft.class_2960;
import net.minecraft.class_330;
import net.minecraft.class_3620;
import net.minecraft.class_4588;
import net.raphimc.immediatelyfast.ImmediatelyFast;
import net.raphimc.immediatelyfast.feature.map_atlas_generation.MapAtlasTexture;
import net.raphimc.immediatelyfast.injection.interfaces.IMapRenderer;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Mutable;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.Redirect;
import org.spongepowered.asm.mixin.injection.Slice;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/**
 * 1.21.1 port of ImmediatelyFast's per-map texture redirect.
 *
 * <p>Deltas vs the 1.20.4 version:
 * <ul>
 *   <li>{@code method_1777}'s slice now ends at {@code class_4588.method_60803(I)} because
 *       {@code class_4588.method_1344()} was removed in 1.21.1;</li>
 *   <li>the 1.20.4 version builds its dummy texture with {@code net.lenni0451.reflect.Objects
 *       .allocate(...)}. This port does not depend on the nested Reflect jar: it lazily creates a
 *       real 1x1 {@code NativeImageBackedTexture} that is never registered, uploaded, read or
 *       closed, which is all the unused placeholder needs;</li>
 *   <li>the constructor's map id is captured in a {@code @Inject} at HEAD instead of a MixinExtras
 *       {@code @Local} sugar, so no extra runtime dependency is needed;</li>
 *   <li>one marker is logged when a map is bound to an atlas slot (evidence).</li>
 * </ul>
 *
 * <p>The dummy is only assigned to {@code field_2048} until the texture-manager redirect sets that
 * field to {@code null}; the real atlas texture is drawn through {@link MapAtlasTexture}.
 */
@Mixin(targets = "net.minecraft.class_330$class_331", priority = 1100)
public abstract class MixinMapRenderer_MapTexture {
    @Shadow
    private class_22 field_2046;
    @Mutable
    @Shadow
    @Final
    private class_1043 field_2048;
    @Shadow
    @Final
    class_330 field_2047;
    @Unique
    private static class_1043 immediatelyFast$dummyTexture;
    @Unique
    private int immediatelyFast$mapId;
    @Unique
    private int immediatelyFast$atlasX;
    @Unique
    private int immediatelyFast$atlasY;
    @Unique
    private MapAtlasTexture immediatelyFast$atlasTexture;

    @Unique
    private static class_1043 immediatelyFast$dummyTexture() {
        if (immediatelyFast$dummyTexture == null) {
            immediatelyFast$dummyTexture = new class_1043(1, 1, true);
        }
        return immediatelyFast$dummyTexture;
    }

    /**
     * Capture the constructor argument; 1.21.1 made the id a {@code MapId} at the renderer level
     * but {@code MapTexture}'s constructor still receives the plain int id.
     *
     * <p>1.21.1's inner constructor stores its outer reference before the {@code super()} call, so
     * Mixin's {@code HEAD} is "before super" and rejects an instance handler. Inject immediately
     * after the super constructor instead: the map id argument is still available and {@code this}
     * is usable.
     */
    @Inject(method = "<init>", at = @At(value = "INVOKE",
            target = "Ljava/lang/Object;<init>()V", shift = At.Shift.AFTER))
    private void immediatelyFast$captureMapId(class_330 mapRenderer, int id, class_22 state, CallbackInfo ci) {
        this.immediatelyFast$mapId = id;
    }

    @Redirect(method = "<init>", at = @At(value = "NEW", target = "(IIZ)Lnet/minecraft/class_1043;"))
    private class_1043 initAtlasParametersAndDontAllocateTexture(int width, int height, boolean useMipmaps) {
        int id = this.immediatelyFast$mapId;
        int packedLocation = ((IMapRenderer) this.field_2047).immediatelyFast$getAtlasMapping(id);
        if (packedLocation == -1) {
            ImmediatelyFast.LOGGER.warn("Map " + id + " is not in an atlas");
            return new class_1043(width, height, useMipmaps);
        }
        this.immediatelyFast$atlasX = (packedLocation >> 8 & 0xFF) * 128;
        this.immediatelyFast$atlasY = (packedLocation & 0xFF) * 128;
        this.immediatelyFast$atlasTexture =
                ((IMapRenderer) this.field_2047).immediatelyFast$getMapAtlasTexture(packedLocation >> 16);
        if (this.immediatelyFast$atlasTexture == null) {
            throw new IllegalStateException("getMapAtlasTexture returned null for packedLocation "
                    + packedLocation + " (map " + id + ")");
        }
        System.out.println("[mcbridge-port] map-atlas texture map=" + id + " packed=" + packedLocation
                + " atlas=" + (packedLocation >> 16));
        return immediatelyFast$dummyTexture();
    }

    @Redirect(method = "<init>", at = @At(value = "INVOKE",
            target = "Lnet/minecraft/class_1060;method_4617(Ljava/lang/String;Lnet/minecraft/class_1043;)Lnet/minecraft/class_2960;"))
    private class_2960 getAtlasTextureIdentifier(class_1060 textureManager, String id, class_1043 texture) {
        if (this.immediatelyFast$atlasTexture != null) {
            this.field_2048 = null;
            class_2960 identifier = this.immediatelyFast$atlasTexture.getIdentifier();
            System.out.println("[mcbridge-port] map-atlas bind map=" + id + " texture=" + identifier);
            return identifier;
        }
        return textureManager.method_4617(id, texture);
    }

    @Inject(method = "method_1776", at = @At("HEAD"), cancellable = true)
    private void updateAtlasTexture(CallbackInfo ci) {
        if (this.immediatelyFast$atlasTexture != null) {
            ci.cancel();
            class_1043 atlasTexture = this.immediatelyFast$atlasTexture.getTexture();
            class_1011 atlasImage = atlasTexture.method_4525();
            if (atlasImage == null) {
                throw new IllegalStateException("Atlas texture has already been closed");
            }
            for (int x = 0; x < 128; ++x) {
                for (int y = 0; y < 128; ++y) {
                    int i = x + y * 128;
                    atlasImage.method_4305(this.immediatelyFast$atlasX + x, this.immediatelyFast$atlasY + y,
                            class_3620.method_38480(this.field_2046.field_122[i]));
                }
            }
            atlasTexture.method_23207();
            atlasImage.method_4312(0, this.immediatelyFast$atlasX, this.immediatelyFast$atlasY,
                    this.immediatelyFast$atlasX, this.immediatelyFast$atlasY, 128, 128, false, false);
        }
    }

    @Redirect(method = "method_1777", at = @At(value = "INVOKE",
            target = "Lnet/minecraft/class_4588;method_22913(FF)Lnet/minecraft/class_4588;"),
            slice = @Slice(from = @At(value = "INVOKE",
                    target = "Lnet/minecraft/class_4588;method_22918(Lorg/joml/Matrix4f;FFF)Lnet/minecraft/class_4588;",
                    ordinal = 0),
                    to = @At(value = "INVOKE",
                            target = "Lnet/minecraft/class_4588;method_60803(I)Lnet/minecraft/class_4588;",
                            ordinal = 3)))
    private class_4588 drawAtlasTexture(class_4588 instance, float u, float v) {
        if (this.immediatelyFast$atlasTexture != null) {
            if (u == 0.0f && v == 1.0f) {
                u = (float) this.immediatelyFast$atlasX / 4096.0f;
                v = (float) (this.immediatelyFast$atlasY + 128) / 4096.0f;
            } else if (u == 1.0f && v == 1.0f) {
                u = (float) (this.immediatelyFast$atlasX + 128) / 4096.0f;
                v = (float) (this.immediatelyFast$atlasY + 128) / 4096.0f;
            } else if (u == 1.0f && v == 0.0f) {
                u = (float) (this.immediatelyFast$atlasX + 128) / 4096.0f;
                v = (float) this.immediatelyFast$atlasY / 4096.0f;
            } else if (u == 0.0f && v == 0.0f) {
                u = (float) this.immediatelyFast$atlasX / 4096.0f;
                v = (float) this.immediatelyFast$atlasY / 4096.0f;
            }
        }
        return instance.method_22913(u, v);
    }

    @Inject(method = "close", at = @At("HEAD"), cancellable = true)
    private void dontCloseDummyTexture(CallbackInfo ci) {
        if (this.immediatelyFast$atlasTexture != null) {
            ci.cancel();
        }
    }
}
