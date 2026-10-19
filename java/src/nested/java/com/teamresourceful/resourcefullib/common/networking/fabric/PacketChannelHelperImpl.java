package com.teamresourceful.resourcefullib.common.networking.fabric;

import com.teamresourceful.resourcefullib.common.networking.base.Packet;
import com.teamresourceful.resourcefullib.common.networking.base.PacketHandler;
import io.netty.buffer.Unpooled;
import net.fabricmc.api.EnvType;
import net.fabricmc.fabric.api.networking.v1.ServerPlayNetworking;
import net.fabricmc.loader.api.FabricLoader;
import net.minecraft.class_1657;
import net.minecraft.class_2540;
import net.minecraft.class_2960;
import net.minecraft.class_3222;
import net.minecraft.class_8710;

/**
 * 1.21.1 payload port of ResourcefulLib 2.0.6's Fabric channel helper.
 *
 * <p>The 1.20.1 build registered and sent through the raw channel API
 * ({@code ServerPlayNetworking.registerGlobalReceiver(Identifier, PlayChannelHandler)} and
 * {@code ServerPlayNetworking.send(ServerPlayer, Identifier, PacketByteBuf)}), which 1.21.1 removed.
 * Packets are wrapped in {@link RawChannel.RawPayload}; the server-safe {@link RawChannel} holds the
 * payload type and codec, and the client-only {@link FabricClientPacketHelper} is only touched when
 * {@code FabricLoader} reports a client environment.
 */
public class PacketChannelHelperImpl {
    public PacketChannelHelperImpl() {}

    public static void registerChannel(class_2960 channel, int version) {
        // 1.21.1 registers payload types lazily in RawChannel.idFor.
    }

    public static <T extends Packet<T>> void registerS2CPacket(class_2960 channel, class_2960 id,
                                                               PacketHandler<T> handler, Class<T> type) {
        if (FabricLoader.getInstance().getEnvironmentType() == EnvType.CLIENT) {
            FabricClientPacketHelper.clientOnlyRegister(RawChannel.location(channel, id), handler);
        }
    }

    public static <T extends Packet<T>> void registerC2SPacket(class_2960 channel, class_2960 id,
                                                               PacketHandler<T> handler, Class<T> type) {
        class_2960 location = RawChannel.location(channel, id);
        class_8710.class_9154<RawChannel.RawPayload> payloadId = RawChannel.idFor(location);
        ServerPlayNetworking.registerGlobalReceiver(payloadId, (payload, context) -> {
            class_2540 buf = new class_2540(Unpooled.wrappedBuffer(payload.data));
            T packet = handler.decode(buf);
            context.server().execute(() -> handler.handle(packet)
                    .apply(context.player(), context.player().method_37908()));
        });
    }

    public static <T extends Packet<T>> void sendToServer(class_2960 channel, T packet) {
        if (FabricLoader.getInstance().getEnvironmentType() == EnvType.CLIENT) {
            FabricClientPacketHelper.sendToServerClientOnly(channel, packet);
        }
    }

    public static <T extends Packet<T>> void sendToPlayer(class_2960 channel, T packet,
                                                          class_1657 player) {
        if (!(player instanceof class_3222 serverPlayer)) {
            return;
        }
        class_2540 buf = new class_2540(Unpooled.buffer());
        packet.getHandler().encode(packet, buf);
        byte[] data = new byte[buf.readableBytes()];
        buf.readBytes(data);
        class_2960 location = RawChannel.location(channel, packet.getID());
        ServerPlayNetworking.send(serverPlayer,
                new RawChannel.RawPayload(RawChannel.idFor(location), data));
    }
}
