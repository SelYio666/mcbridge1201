package net.raphimc.immediatelyfast.feature.batching;

import it.unimi.dsi.fastutil.objects.Object2ObjectLinkedOpenHashMap;
import java.lang.reflect.Field;
import java.util.SequencedMap;
import net.minecraft.class_1921;
import net.minecraft.class_332;
import net.minecraft.class_4597;
import net.minecraft.class_9799;

/**
 * 1.21.1 port of ImmediatelyFast's BatchingBuffers, keeping the public shape the 1.20.4
 * mixins call (FILL_CONSUMER/TEXTURE_CONSUMER/... and no-arg begin/end/force methods) while
 * the batching itself runs on 1.21.1 BufferBuilder/ByteBufferBuilder via
 * HudBatchingBufferSource.
 *
 * <p>Simplified versus upstream 1.6.15: item-lighting variants and Iris are not ported; the
 * HUD/item batches are kept as separate sources so draw order is still grouped.
 */
public class BatchingBuffers {

    public static class_4597 FILL_CONSUMER = null;
    public static class_4597 TEXTURE_CONSUMER = null;
    public static class_4597 TEXT_CONSUMER = null;
    public static class_4597 ITEM_MODEL_CONSUMER = null;
    public static class_4597 ITEM_OVERLAY_CONSUMER = null;

    private static final HudBatchingBufferSource HUD_BATCH = newBatch();
    private static final HudBatchingBufferSource DEBUG_HUD_BATCH = newBatch();
    private static final HudBatchingBufferSource ITEM_MODEL_BATCH = newBatch();
    private static final HudBatchingBufferSource ITEM_OVERLAY_BATCH = newBatch();

    private static class_4597 PREV_FILL_CONSUMER = null;
    private static class_4597 PREV_TEXT_CONSUMER = null;
    private static class_4597 PREV_TEXTURE_CONSUMER = null;

    private static final Field DRAW_CONTEXT_CONSUMERS;
    private static boolean isHudBatching;
    private static boolean loggedBegin;
    private static long lastLogTime;
    private static long lastLoggedDraws;

    static {
        try {
            DRAW_CONTEXT_CONSUMERS = class_332.class.getDeclaredField("field_44658");
            DRAW_CONTEXT_CONSUMERS.setAccessible(true);
        } catch (ReflectiveOperationException exc) {
            throw new ExceptionInInitializerError(exc);
        }
    }

    @SuppressWarnings({"rawtypes", "unchecked"})
    private static SequencedMap<class_1921, class_9799> emptyLayerBuffers() {
        return (SequencedMap) new Object2ObjectLinkedOpenHashMap();
    }

    private static HudBatchingBufferSource newBatch() {
        return new HudBatchingBufferSource(new class_9799(786432), emptyLayerBuffers());
    }

    public static void beginHudBatching() {
        beginHudBatching(HUD_BATCH);
    }

    public static void beginDebugHudBatching() {
        beginHudBatching(DEBUG_HUD_BATCH);
    }

    public static void beginHudBatching(HudBatchingBufferSource batch) {
        if (batch.hasActiveLayers()) {
            batch.close();
        }
        FILL_CONSUMER = batch;
        TEXTURE_CONSUMER = batch;
        TEXT_CONSUMER = batch;
        beginItemModelBatching();
        beginItemOverlayBatching();
        isHudBatching = true;
        if (!loggedBegin) {
            loggedBegin = true;
            System.out.println("[mcbridge-port] hud batching begin");
        }
    }

    public static void endHudBatching() {
        endHudBatching(HUD_BATCH);
    }

    public static void endDebugHudBatching() {
        endHudBatching(DEBUG_HUD_BATCH);
    }

    public static void endHudBatching(HudBatchingBufferSource batch) {
        FILL_CONSUMER = null;
        TEXTURE_CONSUMER = null;
        TEXT_CONSUMER = null;
        batch.method_22993();
        endItemModelBatching();
        endItemOverlayBatching();
        isHudBatching = ITEM_MODEL_CONSUMER != null || ITEM_OVERLAY_CONSUMER != null;
        long total = net.raphimc.immediatelyfast.feature.core.BatchableBufferSource.batchedDraws;
        long now = System.currentTimeMillis();
        if (total != lastLoggedDraws && now - lastLogTime > 2000
                && Boolean.getBoolean("mcbridge.bench")) {
            lastLogTime = now;
            lastLoggedDraws = total;
            int fps = -1;
            try {
                fps = net.minecraft.class_310.method_1551().method_47599();
            } catch (Throwable ignored) {
                // not on the client thread / client not ready
            }
            System.out.println("[mcbridge-port] batched-draws total=" + total
                    + " hud=" + HUD_BATCH.draws
                    + " itemModel=" + ITEM_MODEL_BATCH.draws
                    + " itemOverlay=" + ITEM_OVERLAY_BATCH.draws
                    + " fps=" + fps);
        }
    }

    public static boolean isHudBatching() {
        return isHudBatching || FILL_CONSUMER != null || TEXTURE_CONSUMER != null
                || TEXT_CONSUMER != null || ITEM_MODEL_CONSUMER != null
                || ITEM_OVERLAY_CONSUMER != null;
    }

    public static boolean hasDataToDraw() {
        return HUD_BATCH.hasActiveLayers() || DEBUG_HUD_BATCH.hasActiveLayers()
                || ITEM_MODEL_BATCH.hasActiveLayers() || ITEM_OVERLAY_BATCH.hasActiveLayers();
    }

    public static void forceDrawBuffers() {
        HUD_BATCH.method_22993();
        DEBUG_HUD_BATCH.method_22993();
        ITEM_MODEL_BATCH.method_22993();
        ITEM_OVERLAY_BATCH.method_22993();
    }

    private static void beginItemModelBatching() {
        if (ITEM_MODEL_BATCH.hasActiveLayers()) {
            ITEM_MODEL_BATCH.close();
        }
        ITEM_MODEL_CONSUMER = ITEM_MODEL_BATCH;
    }

    private static void endItemModelBatching() {
        ITEM_MODEL_CONSUMER = null;
        ITEM_MODEL_BATCH.method_22993();
    }

    private static void beginItemOverlayBatching() {
        if (ITEM_OVERLAY_BATCH.hasActiveLayers()) {
            ITEM_OVERLAY_BATCH.close();
        }
        ITEM_OVERLAY_CONSUMER = ITEM_OVERLAY_BATCH;
    }

    private static void endItemOverlayBatching() {
        ITEM_OVERLAY_CONSUMER = null;
        ITEM_OVERLAY_BATCH.method_22993();
    }

    public static void beginItemOverlayRendering() {
        if (ITEM_OVERLAY_CONSUMER != null) {
            PREV_FILL_CONSUMER = FILL_CONSUMER;
            PREV_TEXT_CONSUMER = TEXT_CONSUMER;
            PREV_TEXTURE_CONSUMER = TEXTURE_CONSUMER;
            FILL_CONSUMER = ITEM_OVERLAY_CONSUMER;
            TEXT_CONSUMER = ITEM_OVERLAY_CONSUMER;
            TEXTURE_CONSUMER = ITEM_OVERLAY_CONSUMER;
        }
    }

    public static void endItemOverlayRendering() {
        if (ITEM_OVERLAY_CONSUMER != null) {
            FILL_CONSUMER = PREV_FILL_CONSUMER;
            TEXT_CONSUMER = PREV_TEXT_CONSUMER;
            TEXTURE_CONSUMER = PREV_TEXTURE_CONSUMER;
        }
    }

    // keep the DrawContext-based helpers used by the 1.21.1 upstream shape; harmless for the
    // 1.20.4 mixins and used by our own tests/debugging
    public static void runBatched(class_332 drawContext, Runnable runnable) {
        drawContext.method_51452();
        class_4597 prev = swapConsumers(drawContext, HUD_BATCH);
        boolean prevFlag = isHudBatching;
        isHudBatching = true;
        try {
            beginHudBatching(HUD_BATCH);
            runnable.run();
            drawContext.method_51452();
        } finally {
            endHudBatching(HUD_BATCH);
            swapConsumers(drawContext, prev);
            isHudBatching = prevFlag;
        }
    }

    public static class_4597 beginHudBatching(class_332 drawContext) {
        drawContext.method_51452();
        class_4597 prev = swapConsumers(drawContext, HUD_BATCH);
        beginHudBatching(HUD_BATCH);
        return prev;
    }

    public static void endHudBatching(class_332 drawContext, class_4597 prev) {
        drawContext.method_51452();
        endHudBatching(HUD_BATCH);
        swapConsumers(drawContext, prev);
    }

    private static class_4597 swapConsumers(class_332 drawContext, class_4597 next) {
        try {
            class_4597 prev = (class_4597) DRAW_CONTEXT_CONSUMERS.get(drawContext);
            DRAW_CONTEXT_CONSUMERS.set(drawContext, next);
            return prev;
        } catch (IllegalAccessException exc) {
            throw new RuntimeException("cannot swap DrawContext vertex consumers", exc);
        }
    }

    /** Same shape as upstream: a RenderLayer wrapper that also re-applies lighting state. */
    public static class WrappedRenderLayer extends class_1921 {
        public WrappedRenderLayer(class_1921 renderLayer, Runnable additionalStartAction,
                                  Runnable additionalEndAction) {
            super("immediatelyfast_lit_" + System.identityHashCode(renderLayer) + "_"
                            + System.identityHashCode(additionalStartAction),
                    renderLayer.method_23031(),
                    renderLayer.method_23033(), renderLayer.method_22722(),
                    renderLayer.method_23037(), renderLayer.method_60894(),
                    () -> {
                        renderLayer.method_23516();
                        additionalStartAction.run();
                    },
                    () -> {
                        renderLayer.method_23518();
                        additionalEndAction.run();
                    });
        }
    }
}
