package com.teamresourceful.resourcefullib.common.networking.fabric;

import com.teamresourceful.resourcefullib.common.networking.base.Packet;
import com.teamresourceful.resourcefullib.common.networking.base.PacketContext;
import com.teamresourceful.resourcefullib.common.networking.base.PacketHandler;
import io.netty.buffer.Unpooled;
import net.fabricmc.fabric.api.client.networking.v1.ClientPlayNetworking;
import net.minecraft.class_2540;
import net.minecraft.class_2960;
import net.minecraft.class_8710;

/**
 * 1.21.1 payload port of ResourcefulLib 2.0.6's client channel helper.
 *
 * <p>Only client-side registration/sending lives here. Payload type, codec and channel location are
 * in {@link RawChannel} so a dedicated server can load that half without touching
 * {@code ClientPlayNetworking}.
 */
public final class FabricClientPacketHelper {
    private FabricClientPacketHelper() {}

    public static <T extends Packet<T>> void clientOnlyRegister(class_2960 channel,
                                                                PacketHandler<T> handler) {
        class_8710.class_9154<RawChannel.RawPayload> payloadId = RawChannel.idFor(channel);
        ClientPlayNetworking.registerGlobalReceiver(payloadId, (payload, context) -> {
            class_2540 buf = new class_2540(Unpooled.wrappedBuffer(payload.data));
            T packet = handler.decode(buf);
            PacketContext packetContext = handler.handle(packet);
            context.client().execute(() ->
                    packetContext.apply(context.player(), context.client().field_1687));
        });
    }

    public static <T extends Packet<T>> void sendToServerClientOnly(class_2960 channel, T packet) {
        class_2540 buf = new class_2540(Unpooled.buffer());
        packet.getHandler().encode(packet, buf);
        byte[] data = new byte[buf.readableBytes()];
        buf.readBytes(data);
        class_2960 location = RawChannel.location(channel, packet.getID());
        ClientPlayNetworking.send(new RawChannel.RawPayload(RawChannel.idFor(location), data));
    }
}
