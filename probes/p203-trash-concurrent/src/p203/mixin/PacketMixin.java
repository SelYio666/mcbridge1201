package p203.mixin;

import net.minecraft.class_2817;
import net.minecraft.class_3244;
import net.minecraft.class_8710;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/**
 * Stamps every serverbound custom payload with the server tick it was drained on.
 *
 * <p>The tick counter belongs to the probe and is incremented at the end of every server tick, so
 * two log lines carrying the same number really did land in the same tick. This is the only way to
 * say "concurrent" instead of "close together": wall-clock timestamps alone cannot, because a
 * 2 ms gap can still straddle a tick boundary and a 40 ms gap can still sit inside one.
 *
 * <p>Target: {@code ServerPlayNetworkHandler.onCustomPayload(CustomPayloadC2SPacket)}. Verified
 * against the intermediary jar this project builds with — {@code class_3244} declares
 * {@code public void method_52392(class_2817)}, and {@code class_2817.comp_1647()} is the payload.
 */
@Mixin(class_3244.class)
public abstract class PacketMixin {
    static {
        // If this line never appears, the config was not loaded at all and every P203_PKT line
        // being absent means "mixin missing", not "no packets".
        System.out.println("P203_MIXIN_STATIC_INIT");
    }

    @Inject(method = "method_52392", at = @At("HEAD"))
    private void p203$stamp(class_2817 packet, CallbackInfo ci) {
        class_3244 self = (class_3244) (Object) this;
        if (self.field_14140 == null) {
            return;
        }
        class_8710 payload = packet.comp_1647();
        String channel;
        try {
            channel = payload.method_56479().comp_2242().toString();
        } catch (RuntimeException e) {
            channel = "?";
        }
        p203.ConcurrentProbe.notePacket(
                self.field_14140.method_7334().getName(),
                channel,
                payload.getClass().getName(),
                System.currentTimeMillis());
    }
}
