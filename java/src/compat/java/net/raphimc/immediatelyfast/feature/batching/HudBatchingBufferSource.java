package net.raphimc.immediatelyfast.feature.batching;

import it.unimi.dsi.fastutil.objects.Object2ObjectMap;
import it.unimi.dsi.fastutil.objects.Object2ObjectOpenHashMap;
import it.unimi.dsi.fastutil.objects.Reference2ObjectMap;
import it.unimi.dsi.fastutil.objects.Reference2ObjectOpenHashMap;
import it.unimi.dsi.fastutil.objects.ReferenceObjectImmutablePair;
import it.unimi.dsi.fastutil.objects.ReferenceObjectPair;
import it.unimi.dsi.fastutil.objects.ReferenceOpenHashSet;
import it.unimi.dsi.fastutil.objects.ReferenceSet;
import java.lang.reflect.Field;
import java.util.SequencedMap;
import java.util.Set;
import net.minecraft.class_1921;
import net.minecraft.class_4588;
import net.minecraft.class_4668;
import net.minecraft.class_9799;
import net.raphimc.immediatelyfast.feature.core.BatchableBufferSource;

/**
 * 1.21.1 port of ImmediatelyFast's HudBatchingBufferSource, now including the item-lighting
 * variants: while an item is being rendered, buffers are split per LightingState and drawn
 * through WrappedRenderLayer; item decorations swap the text layer to the GUI-textured one.
 */
public class HudBatchingBufferSource extends BatchableBufferSource {

    private static final Field LAYER_NAME;

    static {
        try {
            LAYER_NAME = class_4668.class.getDeclaredField("field_21363");
            LAYER_NAME.setAccessible(true);
        } catch (ReflectiveOperationException exc) {
            throw new ExceptionInInitializerError(exc);
        }
    }

    private static String layerName(class_1921 layer) {
        try {
            return String.valueOf(LAYER_NAME.get(layer));
        } catch (IllegalAccessException exc) {
            return "";
        }
    }

    private final Object2ObjectMap<ReferenceObjectPair<class_1921, LightingState>, class_1921>
            lightingRenderLayers = new Object2ObjectOpenHashMap<>();
    private final Reference2ObjectMap<class_1921, ReferenceSet<class_1921>> renderLayerMap =
            new Reference2ObjectOpenHashMap<>();
    private boolean renderingItem;
    private boolean renderingItemDecorations;
    private boolean currentlyDrawing;
    private static boolean lightingLogged;

    public HudBatchingBufferSource(class_9799 fallbackBuffer,
                                   SequencedMap<class_1921, class_9799> layerBuffers) {
        super(fallbackBuffer, layerBuffers);
    }

    public void setRenderingItem(boolean renderingItem) {
        this.renderingItem = renderingItem;
    }

    public void setRenderingItemDecorations(boolean renderingItemDecorations) {
        this.renderingItemDecorations = renderingItemDecorations;
    }

    public boolean isCurrentlyDrawing() {
        return this.currentlyDrawing;
    }

    @Override
    public class_4588 getBuffer(class_1921 layer) {
        if (layerName(layer).contains("glint")) {
            return super.getBuffer(layer);
        }
        if (this.renderingItem) {
            LightingState lightingState = LightingState.current();
            if (!lightingLogged) {
                lightingLogged = true;
                System.out.println("[mcbridge-port] item lighting variants active");
            }
            class_1921 newLayer = this.lightingRenderLayers.computeIfAbsent(
                    new ReferenceObjectImmutablePair<>(layer, lightingState),
                    key -> new BatchingBuffers.WrappedRenderLayer(
                            layer, lightingState::saveAndApply, lightingState::revert));
            this.renderLayerMap.computeIfAbsent(layer, key -> new ReferenceOpenHashSet<>())
                    .add(newLayer);
            return super.getBuffer(newLayer);
        }
        if (this.renderingItemDecorations && layer == class_1921.method_51785()) {
            return super.getBuffer(class_1921.method_51784());
        }
        return super.getBuffer(layer);
    }

    @Override
    public void method_22993() {
        boolean prev = this.currentlyDrawing;
        this.currentlyDrawing = true;
        try {
            super.method_22993();
        } finally {
            this.currentlyDrawing = prev;
        }
        this.lightingRenderLayers.clear();
        this.renderLayerMap.clear();
    }

    @Override
    public void drawDirect(class_1921 layer) {
        boolean prev = this.currentlyDrawing;
        this.currentlyDrawing = true;
        try {
            Set<class_1921> renderLayers = this.renderLayerMap.remove(layer);
            if (renderLayers != null) {
                for (class_1921 renderLayer : renderLayers) {
                    super.drawDirect(renderLayer);
                }
            } else {
                super.drawDirect(layer);
            }
        } finally {
            this.currentlyDrawing = prev;
        }
    }

    @Override
    public void close() {
        super.close();
        this.lightingRenderLayers.clear();
        this.renderLayerMap.clear();
    }
}
