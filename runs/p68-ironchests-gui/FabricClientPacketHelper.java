package com.teamresourceful.resourcefullib.common.networking.fabric;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

import com.teamresourceful.resourcefullib.common.networking.base.Packet;
import com.teamresourceful.resourcefullib.common.networking.base.PacketContext;
import com.teamresourceful.resourcefullib.common.networking.base.PacketHandler;
import io.netty.buffer.Unpooled;
import net.fabricmc.fabric.api.client.networking.v1.ClientPlayNetworking;
import net.fabricmc.fabric.api.networking.v1.PayloadTypeRegistry;
import net.minecraft.class_2540;
import net.minecraft.class_2960;
import net.minecraft.class_8710;
import net.minecraft.class_9129;
import net.minecraft.class_9139;

/**
 * 1.21.1 payload port of ResourcefulLib 2.0.6's client channel helper.
 *
 * <p>Same contract as the original but with the corrected channel location
 * ({@code namespace:channelPath/packetPath}; the previous port produced an invalid
 * {@code namespace/namespace:path/path}) and package-visible payload helpers so the server half can
 * share one payload type and one {@code RawPayload} class.
 */
public final class FabricClientPacketHelper {
    private static final Map<class_2960, class_8710.class_9154<RawPayload>> IDS = new ConcurrentHashMap<>();

    private FabricClientPacketHelper() {}

    public static <T extends Packet<T>> void clientOnlyRegister(class_2960 channel,
                                                                PacketHandler<T> handler) {
        class_8710.class_9154<RawPayload> payloadId = idFor(channel);
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
        class_2960 location = createChannelLocation(channel, packet.getID());
        ClientPlayNetworking.send(new RawPayload(idFor(location), data));
    }

    static class_2960 createChannelLocation(class_2960 channel, class_2960 id) {
        return class_2960.method_60655(channel.method_12836(),
                channel.method_12832() + "/" + id.method_12832());
    }

    static synchronized class_8710.class_9154<RawPayload> idFor(class_2960 location) {
        class_8710.class_9154<RawPayload> existing = IDS.get(location);
        if (existing != null) {
            return existing;
        }
        class_8710.class_9154<RawPayload> payloadId = new class_8710.class_9154<>(location);
        class_9139<class_9129, RawPayload> codec = class_9139.method_56437(
                (buf, payload) -> buf.writeBytes(payload.data),
                buf -> new RawPayload(payloadId, readBytes(buf)));
        PayloadTypeRegistry.playS2C().register(payloadId, codec);
        PayloadTypeRegistry.playC2S().register(payloadId, codec);
        IDS.put(location, payloadId);
        return payloadId;
    }

    static byte[] readBytes(class_2540 buf) {
        byte[] data = new byte[buf.readableBytes()];
        buf.readBytes(data);
        return data;
    }

    static final class RawPayload implements class_8710 {
        final class_8710.class_9154<RawPayload> id;
        final byte[] data;

        RawPayload(class_8710.class_9154<RawPayload> id, byte[] data) {
            this.id = id;
            this.data = data;
        }

        @Override
        public class_8710.class_9154<? extends class_8710> method_56479() {
            return id;
        }
    }
}
