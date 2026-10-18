package me.jellysquid.mods.lithium.mixin.world.chunk_access;

import java.util.concurrent.CompletableFuture;

import net.minecraft.class_2791;
import net.minecraft.class_2806;
import net.minecraft.class_3215;
import net.minecraft.class_9259;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Overwrite;
import org.spongepowered.asm.mixin.Shadow;
import top.mcbridge1201.bridge.ChunkAccessPump;

/**
 * Minimal 1.21.1 port of lithium's chunk-access overwrite.
 *
 * <p>The 1.20.1 mixin built its own ChunkHolderExtended future cache and called the removed
 * ChunkMap.method_17236 (Either&lt;Chunk, Unloaded&gt;). 1.21.1 already has the status-aware
 * ChunkResult future inside GenerationChunkHolder and the vanilla ServerChunkManager
 * method_14134; this port delegates to that method and converts ChunkResult to a chunk.
 *
 * <p>This keeps the mixin and its overwrite (no mixin strip) and keeps vanilla semantics. The
 * 1.20.1 multi-entry cache / off-thread fast path is not reimplemented; that optimization loss
 * is recorded in runs/p13-chunk-port/README.md.
 */
@Mixin(class_3215.class)
public abstract class ServerChunkManagerMixin {
    @Shadow
    private CompletableFuture<class_9259<class_2791>> method_14134(int x, int z,
                                                                  class_2806 status,
                                                                  boolean create) {
        throw new AssertionError("shadow");
    }

    @Overwrite
    public class_2791 method_12121(int x, int z, class_2806 status, boolean create) {
        CompletableFuture<class_9259<class_2791>> future = this.method_14134(x, z, status, create);
        if (!future.isDone()) {
            ChunkAccessPump.pump(this, future);
        }
        class_9259<class_2791> result = future.join();
        class_2791 chunk = result.method_57130(null);
        if (chunk == null && create) {
            throw new IllegalStateException(result.method_57129());
        }
        return chunk;
    }
}
