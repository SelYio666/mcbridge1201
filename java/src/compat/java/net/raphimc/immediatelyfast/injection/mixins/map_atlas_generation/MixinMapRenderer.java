package net.raphimc.immediatelyfast.injection.mixins.map_atlas_generation;

import it.unimi.dsi.fastutil.ints.Int2IntMap;
import it.unimi.dsi.fastutil.ints.Int2IntOpenHashMap;
import it.unimi.dsi.fastutil.ints.Int2ObjectMap;
import it.unimi.dsi.fastutil.ints.Int2ObjectOpenHashMap;
import net.minecraft.class_22;
import net.minecraft.class_330;
import net.minecraft.class_9209;
import net.raphimc.immediatelyfast.feature.map_atlas_generation.MapAtlasTexture;
import net.raphimc.immediatelyfast.injection.interfaces.IMapRenderer;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

/**
 * 1.21.1 port of ImmediatelyFast's map atlas provider.
 *
 * <p>Deltas vs the 1.20.4 version: {@code MapRenderer.method_32601} takes a {@code MapId}
 * ({@code class_9209}) instead of an {@code int}; the map id is read through
 * {@code mapId.comp_2315()}. {@code method_1771} (clear) is unchanged.
 *
 * <p>The only local change is a one-line marker on atlas creation/assignment so a client run can
 * prove that the atlas path actually executed (style matches the other port markers).
 */
@Mixin(class_330.class)
public abstract class MixinMapRenderer implements IMapRenderer {
    @Unique
    private final Int2ObjectMap<MapAtlasTexture> immediatelyFast$mapAtlasTextures = new Int2ObjectOpenHashMap<>();
    @Unique
    private final Int2IntMap immediatelyFast$mapIdToAtlasMapping = new Int2IntOpenHashMap();

    @Inject(method = "method_1771", at = @At("RETURN"))
    private void clearMapAtlasTextures(CallbackInfo ci) {
        int atlases = this.immediatelyFast$mapAtlasTextures.size();
        for (MapAtlasTexture texture : this.immediatelyFast$mapAtlasTextures.values()) {
            texture.close();
        }
        this.immediatelyFast$mapAtlasTextures.clear();
        this.immediatelyFast$mapIdToAtlasMapping.clear();
        System.out.println("[mcbridge-port] map-atlas clear atlases=" + atlases);
    }

    @Inject(method = "method_32601", at = @At("HEAD"))
    private void createMapAtlasTexture(class_9209 mapId, class_22 state,
                                       CallbackInfoReturnable<class_330.class_331> cir) {
        int id = mapId.comp_2315();
        if (this.immediatelyFast$mapIdToAtlasMapping.containsKey(id)) {
            return;
        }
        // Same semantics as the upstream computeIfAbsent lambda, but explicit so the evidence
        // marker fires exactly once per map rather than on every lookup.
        int packedLocation = -1;
        for (MapAtlasTexture atlasTexture : this.immediatelyFast$mapAtlasTextures.values()) {
            packedLocation = atlasTexture.getNextMapLocation();
            if (packedLocation != -1) {
                break;
            }
        }
        if (packedLocation == -1) {
            MapAtlasTexture atlasTexture = new MapAtlasTexture(this.immediatelyFast$mapAtlasTextures.size());
            this.immediatelyFast$mapAtlasTextures.put(atlasTexture.getId(), atlasTexture);
            packedLocation = atlasTexture.getNextMapLocation();
            System.out.println("[mcbridge-port] map-atlas create id=" + atlasTexture.getId());
        }
        this.immediatelyFast$mapIdToAtlasMapping.put(id, packedLocation);
        System.out.println("[mcbridge-port] map-atlas assign map=" + id + " packed=" + packedLocation);
    }

    @Override
    public MapAtlasTexture immediatelyFast$getMapAtlasTexture(int id) {
        return this.immediatelyFast$mapAtlasTextures.get(id);
    }

    @Override
    public int immediatelyFast$getAtlasMapping(int mapId) {
        return this.immediatelyFast$mapIdToAtlasMapping.getOrDefault(mapId, -1);
    }
}
