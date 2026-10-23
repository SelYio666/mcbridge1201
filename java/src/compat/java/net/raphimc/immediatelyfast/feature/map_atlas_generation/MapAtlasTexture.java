package net.raphimc.immediatelyfast.feature.map_atlas_generation;

import net.minecraft.class_1043;
import net.minecraft.class_1060;
import net.minecraft.class_2960;
import net.minecraft.class_310;

/**
 * 1.21.1 port of ImmediatelyFast's map atlas texture.
 *
 * <p>Deltas vs the 1.20.4 version: Identifier(String,String) is now a static factory
 * (class_2960.method_60655) and the TextureManager register/unregister calls are unchanged
 * (class_1060.method_4616/method_4615). NativeImage(int,int,boolean) still exists.
 */
public class MapAtlasTexture implements AutoCloseable {
    public static final int ATLAS_SIZE = 4096;
    public static final int MAP_SIZE = 128;
    public static final int MAPS_PER_ATLAS = 1024;

    private final int id;
    private final class_2960 identifier;
    private final class_1043 texture;
    private int mapCount;
    private boolean closed;

    public MapAtlasTexture(int id) {
        this.id = id;
        this.identifier = class_2960.method_60655("immediatelyfast", "map_atlas/" + id);
        this.texture = new class_1043(ATLAS_SIZE, ATLAS_SIZE, true);
        this.textureManager().method_4616(this.identifier, this.texture);
    }

    private class_1060 textureManager() {
        return class_310.method_1551().method_1531();
    }

    public int getNextMapLocation() {
        if (this.mapCount >= MAPS_PER_ATLAS) {
            return -1;
        }
        byte atlasX = (byte) (this.mapCount % 32);
        byte atlasY = (byte) (this.mapCount / 32);
        this.mapCount++;
        return this.id << 16 | atlasX << 8 | atlasY;
    }

    public int getId() {
        return this.id;
    }

    public class_2960 getIdentifier() {
        return this.identifier;
    }

    public class_1043 getTexture() {
        return this.texture;
    }

    /**
     * A map texture can still be referenced by a HeldItemRenderer frame that was already queued
     * when the world exit clears the atlas. {@code updateAtlasTexture} must not write into the
     * closed NativeImage (1.21.1 throws "Image is not allocated").
     */
    public boolean isClosed() {
        return this.closed;
    }

    @Override
    public void close() {
        if (this.closed) {
            return;
        }
        this.closed = true;
        System.out.println("[mcbridge-port] map-atlas close id=" + this.id);
        this.texture.close();
        this.textureManager().method_4615(this.identifier);
    }
}
