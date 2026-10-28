package p203.mixin;

import net.fabricmc.fabric.api.networking.v1.ServerPlayNetworking;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import top.mcbridge1201.bridge.BalmNetworkingBridge;

import java.util.function.BiConsumer;

/**
 * Secondary stamp on the serverbound Balm receiver, to separate "the packet arrived in tick N" from
 * "the state was written in tick N".
 *
 * <p>This is a lambda inside the bridge ({@code registerServerbound} hands Fabric a
 * {@code BiConsumer<Payload, Context>}), so the target is a synthetic method name. {@code require}
 * is 0 on purpose: the name is compiler-generated, and a rename upstream must not turn this
 * optional stamp into a hard failure. If it never fires, {@link p203.ConcurrentProbe} still has the
 * mutation stamp, and the run says so instead of pretending it measured the packet.
 */
@Mixin(targets = "top.mcbridge1201.bridge.BalmNetworkingBridge")
public class BalmBridgeMixin {
    @Inject(method = "lambda$registerServerbound$1", at = @At("HEAD"), require = 0)
    private static void p203$serverbound(BiConsumer<Object, Object> handler,
                                         BalmNetworkingBridge.Payload<?> payload,
                                         ServerPlayNetworking.Context context, CallbackInfo ci) {
        Object value = payload == null ? null : payload.value();
        p203.ConcurrentProbe.noteServerbound(
                value == null ? "?" : value.getClass().getName(),
                System.currentTimeMillis());
    }
}
