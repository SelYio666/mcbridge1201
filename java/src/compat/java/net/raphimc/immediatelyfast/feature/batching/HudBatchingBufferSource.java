package net.raphimc.immediatelyfast.feature.batching;

import java.util.SequencedMap;
import net.minecraft.class_1921;
import net.minecraft.class_4588;
import net.minecraft.class_9799;
import net.raphimc.immediatelyfast.feature.core.BatchableBufferSource;

/**
 * 1.21.1 port of ImmediatelyFast's HudBatchingBufferSource.
 *
 * <p>Simplified versus upstream 1.6.15: no per-lighting-state RenderLayer wrapping for item
 * rendering (LightingState/Iris left out). HUD quads are still batched per RenderLayer; only
 * the item-lighting variants are not split. The public toggles are kept because the HUD mixins
 * call them.
 */
public class HudBatchingBufferSource extends BatchableBufferSource {

    private boolean renderingItem;
    private boolean renderingItemDecorations;
    private boolean currentlyDrawing;

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
        // item lighting variants are not split in this port; all layers go through the
        // batched path unchanged
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
    }

    @Override
    public void drawDirect(class_1921 layer) {
        boolean prev = this.currentlyDrawing;
        this.currentlyDrawing = true;
        try {
            super.drawDirect(layer);
        } finally {
            this.currentlyDrawing = prev;
        }
    }
}
