package com.teamresourceful.resourcefullib.common.networking.fabric;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

import net.fabricmc.fabric.api.networking.v1.PayloadTypeRegistry;
import net.minecraft.class_2540;
import net.minecraft.class_2960;
import net.minecraft.class_8710;
import net.minecraft.class_9129;
import net.minecraft.class_9139;

/**
 * Server-safe half of the ResourcefulLib raw-channel port.
 *
 * <p>This class must never reference client-only types: it is used by the dedicated-server side
 * ({@code sendToPlayer} / {@code registerC2SPacket}) as well as by the client helper. The payload
 * type, codec and channel location live here so both sides agree, while
 * {@link FabricClientPacketHelper} keeps the {@code ClientPlayNetworking} calls.
 */
final class RawChannel {
    private static final Map<class_2960, class_8710.class_9154<RawPayload>> IDS =
            new ConcurrentHashMap<>();

    private RawChannel() {}

    static class_2960 location(class_2960 channel, class_2960 id) {
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
