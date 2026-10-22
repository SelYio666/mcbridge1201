package net.raphimc.immediatelyfast.feature.core;

import it.unimi.dsi.fastutil.objects.Object2ObjectSortedMaps;
import it.unimi.dsi.fastutil.objects.Reference2ObjectLinkedOpenHashMap;
import it.unimi.dsi.fastutil.objects.ReferenceLinkedOpenHashSet;
import it.unimi.dsi.fastutil.objects.ReferenceSet;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.IdentityHashMap;
import java.util.List;
import java.util.Map;
import java.util.SequencedMap;
import java.util.Set;
import net.minecraft.class_1921;
import net.minecraft.class_287;
import net.minecraft.class_4588;
import net.minecraft.class_4597;
import net.minecraft.class_9799;
import net.minecraft.class_9801;

/**
 * 1.21.1 port of ImmediatelyFast's BatchableBufferSource.
 *
 * <p>Differences from the 1.20.4 original and from upstream 1.6.15:
 * <ul>
 *   <li>no Iris integration (Iris stays untested);</li>
 *   <li>no BufferAllocatorPool: each non-layer buffer owns a fresh ByteBufferBuilder which is
 *       closed after the draw (the batching behaviour is unchanged, only allocation reuse is
 *       omitted);</li>
 *   <li>layer ordering keeps only the translucent-last rule, not the entity-texture special
 *       cases (horse/wolf/villager) - those only change z-fighting order for entities.</li>
 * </ul>
 *
 * <p>{@code class_4598.method_60893} and {@code class_287.field_52071} are private in 1.21.1;
 * upstream widens them. This port uses reflection instead of an access widener.
 */
public class BatchableBufferSource extends class_4597.class_4598 implements AutoCloseable {

    private static final class_9799 FALLBACK_BUFFER = new class_9799(0);
    private static final Method DRAW_LAYER;
    private static final Field BUILDER_ALLOCATOR;
    private static final Field CURRENT_ALLOCATOR;

    static {
        try {
            DRAW_LAYER = class_4597.class_4598.class.getDeclaredMethod(
                    "method_60893", class_1921.class, class_287.class);
            DRAW_LAYER.setAccessible(true);
            BUILDER_ALLOCATOR = class_287.class.getDeclaredField("field_52071");
            BUILDER_ALLOCATOR.setAccessible(true);
            CURRENT_ALLOCATOR = class_4597.class_4598.class.getDeclaredField("field_52156");
            CURRENT_ALLOCATOR.setAccessible(true);
        } catch (ReflectiveOperationException exc) {
            throw new ExceptionInInitializerError(exc);
        }
    }

    /** debug/evidence counter: how many buffers actually went through the batched draw path */
    public static long batchedDraws;
    /** per-source counter for evidence (HUD vs item-model vs item-overlay) */
    public long draws;

    protected final Map<class_1921, ReferenceSet<class_287>> pendingBuffers =
            new Reference2ObjectLinkedOpenHashMap<>();
    protected final Set<class_1921> activeLayers = new ReferenceLinkedOpenHashSet<>();
    protected boolean drawFallbackLayersFirst = false;
    private final Map<class_287, class_9799> ownedAllocators = new IdentityHashMap<>();

    @SuppressWarnings({"unchecked", "rawtypes"})
    public BatchableBufferSource() {
        this((SequencedMap) Object2ObjectSortedMaps.emptyMap());
    }

    public BatchableBufferSource(SequencedMap<class_1921, class_9799> layerBuffers) {
        this(FALLBACK_BUFFER, layerBuffers);
    }

    public BatchableBufferSource(class_9799 fallbackBuffer,
                                 SequencedMap<class_1921, class_9799> layerBuffers) {
        super(fallbackBuffer, layerBuffers);
    }

    @Override
    public class_4588 getBuffer(class_1921 layer) {
        class_287 bufferBuilder;
        boolean hasBufferForRenderLayer = layer.method_43332() && this.pendingBuffers.containsKey(layer);
        if (!layer.method_43332()) {
            bufferBuilder = this.newBuffer(layer);
            this.field_52158 = layer;
        } else if (hasBufferForRenderLayer) {
            bufferBuilder = this.pendingBuffers.get(layer).iterator().next();
        } else if (this.field_20953.containsKey(layer)) {
            bufferBuilder = new class_287(this.field_20953.get(layer),
                    layer.method_23033(), layer.method_23031());
        } else {
            bufferBuilder = this.newBuffer(layer);
            this.field_52158 = layer;
        }
        if (hasBufferForRenderLayer) {
            if (this.activeLayers.contains(layer)) {
                this.activeLayers.remove(layer);
                this.activeLayers.add(layer);
            }
        } else {
            ReferenceSet<class_287> set = this.pendingBuffers.computeIfAbsent(
                    layer, key -> new ReferenceLinkedOpenHashSet<>());
            set.add(bufferBuilder);
            this.activeLayers.add(layer);
        }
        return bufferBuilder;
    }

    private class_287 newBuffer(class_1921 layer) {
        class_9799 allocator = new class_9799(256);
        class_287 builder = new class_287(allocator, layer.method_23033(), layer.method_23031());
        this.ownedAllocators.put(builder, allocator);
        return builder;
    }

    @Override
    public void method_37104() {
        this.field_52158 = null;
        this.drawFallbackLayersFirst = false;
        List<class_1921> sorted = new ArrayList<>(this.activeLayers.size());
        for (class_1921 layer : this.activeLayers) {
            if (!this.field_20953.containsKey(layer)) {
                sorted.add(layer);
            }
        }
        if (sorted.isEmpty()) {
            return;
        }
        sorted.sort(Comparator.comparingInt(this::getLayerOrder));
        for (class_1921 layer : sorted) {
            this.method_22994(layer);
        }
    }

    @Override
    public void method_22993() {
        if (this.activeLayers.isEmpty()) {
            this.close();
            return;
        }
        this.method_37104();
        for (class_1921 layer : new ArrayList<>(this.field_20953.keySet())) {
            this.method_22994(layer);
        }
    }

    @Override
    public void method_22994(class_1921 layer) {
        if (this.drawFallbackLayersFirst) {
            this.method_37104();
        }
        this.drawDirect(layer);
    }

    @Override
    public void close() {
        this.field_52158 = null;
        this.drawFallbackLayersFirst = false;
        for (ReferenceSet<class_287> set : this.pendingBuffers.values()) {
            for (class_287 builder : set) {
                try {
                    class_9801 built = builder.method_60794();
                    if (built != null) {
                        built.close();
                    }
                } catch (RuntimeException ignored) {
                    // nothing was written; just release the allocation
                }
                this.releaseOwned(builder);
            }
        }
        this.activeLayers.clear();
        this.pendingBuffers.clear();
        this.ownedAllocators.clear();
    }

    public void drawDirect(class_1921 layer) {
        this.activeLayers.remove(layer);
        ReferenceSet<class_287> buffers = this.pendingBuffers.remove(layer);
        if (buffers != null) {
            for (class_287 builder : buffers) {
                class_9799 prevAllocator = null;
                try {
                    prevAllocator = (class_9799) CURRENT_ALLOCATOR.get(this);
                    class_9799 builderAllocator = (class_9799) BUILDER_ALLOCATOR.get(builder);
                    if (builderAllocator != null) {
                        CURRENT_ALLOCATOR.set(this, builderAllocator);
                    }
                    DRAW_LAYER.invoke(this, layer, builder);
                    batchedDraws++;
                    this.draws++;
                } catch (ReflectiveOperationException exc) {
                    throw new RuntimeException("batched draw failed for " + layer, exc);
                } finally {
                    try {
                        CURRENT_ALLOCATOR.set(this, prevAllocator);
                    } catch (IllegalAccessException ignored) {
                        // best effort restore
                    }
                    this.releaseOwned(builder);
                }
            }
        }
        if (this.field_52158 == layer) {
            this.field_52158 = null;
        }
    }

    private void releaseOwned(class_287 builder) {
        class_9799 allocator = this.ownedAllocators.remove(builder);
        if (allocator != null) {
            allocator.close();
        } else {
            // buffers created with the superclass' per-layer allocator: release via reflection
            try {
                class_9799 fieldAllocator = (class_9799) BUILDER_ALLOCATOR.get(builder);
                if (fieldAllocator != null && fieldAllocator != FALLBACK_BUFFER
                        && fieldAllocator != this.field_52156) {
                    fieldAllocator.close();
                }
            } catch (IllegalAccessException ignored) {
                // best effort only
            }
        }
    }

    public boolean hasActiveLayers() {
        return !this.activeLayers.isEmpty();
    }

    protected int getLayerOrder(class_1921 layer) {
        if (layer == null) {
            return Integer.MAX_VALUE;
        }
        return layer.method_60894() ? 100000000 : 0;
    }
}
