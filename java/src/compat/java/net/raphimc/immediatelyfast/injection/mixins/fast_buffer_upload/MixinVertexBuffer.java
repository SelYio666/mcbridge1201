package net.raphimc.immediatelyfast.injection.mixins.fast_buffer_upload;

import com.mojang.blaze3d.systems.RenderSystem;
import java.nio.ByteBuffer;
import net.minecraft.class_291;
import net.raphimc.immediatelyfast.ImmediatelyFast;
import org.lwjgl.opengl.GL15C;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Redirect;

/**
 * 1.21.1 port of ImmediatelyFast's dynamic vertex-buffer upload fast path.
 *
 * <p>The 1.21.1 class has an extra index upload entry point,
 * {@code method_60829(class_9799$class_9800)}, alongside
 * {@code method_43443(class_9801$class_4574, ByteBuffer)}; both are redirected. The logic is
 * upstream: for dynamic buffers only ({@code usage != 35044}), reuse a buffer that is at least as
 * large as the new data via {@code glBufferSubData} instead of reallocating with
 * {@code glBufferData}. Static buffers always reallocate.
 *
 * <p>The counter/log is evidence-only and low volume: it proves the fast path actually ran
 * (the class can apply while never taking the sub-data branch).
 */
@Mixin(value = class_291.class, priority = 500)
public abstract class MixinVertexBuffer {
    @Unique
    private static long immediatelyFast$fastUploads;
    @Unique
    private int immediatelyFast$vertexBufferSize;
    @Unique
    private int immediatelyFast$indexBufferSize;

    @Unique
    private static void immediatelyFast$noteFastUpload(int target, int usage, int size) {
        immediatelyFast$fastUploads++;
        if (immediatelyFast$fastUploads <= 3 || immediatelyFast$fastUploads % 1000 == 0) {
            System.out.println("[mcbridge-port] fast-buffer-upload subdata count="
                    + immediatelyFast$fastUploads + " target=" + target
                    + " usage=" + usage + " size=" + size);
        }
    }

    @Redirect(method = "method_43442", at = @At(value = "INVOKE",
            target = "Lcom/mojang/blaze3d/systems/RenderSystem;glBufferData(ILjava/nio/ByteBuffer;I)V"))
    private void optimizeVertexDataUploading(int target, ByteBuffer data, int usage) {
        if (!ImmediatelyFast.runtimeConfig.fast_buffer_upload || usage == 35044
                || data.remaining() > this.immediatelyFast$vertexBufferSize) {
            this.immediatelyFast$vertexBufferSize = data.remaining();
            RenderSystem.glBufferData(target, data, usage);
        } else {
            immediatelyFast$noteFastUpload(target, usage, data.remaining());
            GL15C.glBufferSubData(target, 0L, data);
        }
    }

    @Redirect(method = {
            "method_60829(Lnet/minecraft/class_9799$class_9800;)V",
            "method_43443(Lnet/minecraft/class_9801$class_4574;Ljava/nio/ByteBuffer;)Lcom/mojang/blaze3d/systems/RenderSystem$class_5590;"
    }, at = @At(value = "INVOKE",
            target = "Lcom/mojang/blaze3d/systems/RenderSystem;glBufferData(ILjava/nio/ByteBuffer;I)V"))
    private void optimizeIndexDataUploading(int target, ByteBuffer data, int usage) {
        if (!ImmediatelyFast.runtimeConfig.fast_buffer_upload || usage == 35044
                || data.remaining() > this.immediatelyFast$indexBufferSize) {
            this.immediatelyFast$indexBufferSize = data.remaining();
            RenderSystem.glBufferData(target, data, usage);
        } else {
            immediatelyFast$noteFastUpload(target, usage, data.remaining());
            GL15C.glBufferSubData(target, 0L, data);
        }
    }
}
