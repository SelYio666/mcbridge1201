package net.raphimc.immediatelyfast.injection.mixins.core;

import java.util.SequencedMap;
import net.minecraft.class_1921;
import net.minecraft.class_4597;
import net.minecraft.class_9799;
import net.raphimc.immediatelyfast.ImmediatelyFast;
import net.raphimc.immediatelyfast.feature.batching.SimpleImmediate;
import net.raphimc.immediatelyfast.feature.core.BatchableBufferSource;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Overwrite;

/**
 * 1.21.1 port of the VertexConsumerProvider factory mixin.
 *
 * <p>The 1.20.4 descriptor was (Map&lt;RenderLayer, BufferBuilder&gt;, BufferAllocator); 1.21.1 is
 * (SequencedMap&lt;RenderLayer, ByteBufferBuilder&gt;, ByteBufferBuilder). Upstream returns a plain
 * Immediate for the "disable universal batching" path; we return SimpleImmediate because the
 * protected Immediate constructor would need an access widener.
 */
@Mixin(class_4597.class)
public interface MixinVertexConsumerProvider {

    @Overwrite
    static class_4597.class_4598 method_22992(SequencedMap<class_1921, class_9799> layerBuffers,
                                              class_9799 fallbackBuffer) {
        if (ImmediatelyFast.config.debug_only_and_not_recommended_disable_universal_batching) {
            return new SimpleImmediate(fallbackBuffer, layerBuffers);
        }
        return new BatchableBufferSource(fallbackBuffer, layerBuffers);
    }
}
