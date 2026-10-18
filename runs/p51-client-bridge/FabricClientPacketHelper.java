package com.teamresourceful.resourcefullib.common.networking.fabric;

import com.teamresourceful.resourcefullib.common.networking.base.Packet;
import com.teamresourceful.resourcefullib.common.networking.base.PacketContext;
import com.teamresourceful.resourcefullib.common.networking.base.PacketHandler;
import io.netty.buffer.Unpooled;
import net.fabricmc.fabric.api.client.networking.v1.ClientPlayNetworking;
import net.fabricmc.fabric.api.networking.v1.PayloadTypeRegistry;
import net.minecraft.class_2540;
import net.minecraft.class_2960;
import net.minecraft.class_8710;
import net.minecraft.class_9139;

import java.util.HashMap;
import java.util.Map;

/**
 * Replacement for ResourcefulLib 2.0.6's client helper, which still uses the removed
 * ClientPlayNetworking.PlayChannelHandler / Identifier API. The payload body is carried
 * verbatim so the old ResourcefulLib PacketHandler codec keeps working.
 */
public final class FabricClientPacketHelper {
    private static final Map<class_2960, class_8710.class_9154<RawPayload>> IDS = new HashMap<>();

    private FabricClientPacketHelper() {
    }

    public static <T extends Packet<T>> void clientOnlyRegister(class_2960 id, PacketHandler<T> handler) {
        class_8710.class_9154<RawPayload> payloadId = idFor(id);
        ClientPlayNetworking.registerGlobalReceiver(payloadId, (payload, context) -> {
            class_2540 buf = new class_2540(Unpooled.wrappedBuffer(payload.data));
            Packet<T> packet = handler.decode(buf);
            PacketContext ctx = handler.handle((T) packet);
            context.client().execute(() -> ctx.apply(context.player(), context.client().field_1687));
        });
    }

    public static <T extends Packet<T>> void sendToServerClientOnly(class_2960 channel, T packet) {
        class_2540 buf = new class_2540(Unpooled.buffer());
        packet.getHandler().encode(packet, buf);
        byte[] data = new byte[buf.readableBytes()];
        buf.readBytes(data);
        class_2960 id = createChannelLocation(channel, packet.getID());
        ClientPlayNetworking.send(new RawPayload(idFor(id), data));
    }

    private static class_2960 createChannelLocation(class_2960 a, class_2960 b) {
        return class_2960.method_60655(a.method_12836() + "/" + b.method_12836(),
                a.method_12832() + "/" + b.method_12832());
    }

    private static synchronized class_8710.class_9154<RawPayload> idFor(class_2960 id) {
        class_8710.class_9154<RawPayload> existing = IDS.get(id);
        if (existing != null) return existing;
        class_8710.class_9154<RawPayload> payloadId = new class_8710.class_9154<>(id);
        class_9139<class_2540, RawPayload> codec = class_9139.method_56437(
                (buf, payload) -> buf.writeBytes(payload.data),
                buf -> {
                    byte[] data = new byte[buf.readableBytes()];
                    buf.readBytes(data);
                    return new RawPayload(payloadId, data);
                });
        PayloadTypeRegistry.playS2C().register(payloadId, codec);
        PayloadTypeRegistry.playC2S().register(payloadId, codec);
        IDS.put(id, payloadId);
        return payloadId;
    }

    private static final class RawPayload implements class_8710 {
        private final class_8710.class_9154<RawPayload> id;
        private final byte[] data;

        private RawPayload(class_8710.class_9154<RawPayload> id, byte[] data) {
            this.id = id;
            this.data = data;
        }

        @Override
        public class_8710.class_9154<? extends class_8710> method_56479() {
            return id;
        }
    }
}
