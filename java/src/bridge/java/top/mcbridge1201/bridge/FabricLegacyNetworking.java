package top.mcbridge1201.bridge;

import java.lang.reflect.Method;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

import io.netty.buffer.Unpooled;
import net.fabricmc.fabric.api.client.networking.v1.ClientPlayNetworking;
import net.fabricmc.fabric.api.networking.v1.PayloadTypeRegistry;
import net.fabricmc.fabric.api.networking.v1.ServerPlayNetworking;
import net.minecraft.class_2540;
import net.minecraft.class_2658;
import net.minecraft.class_2817;
import net.minecraft.class_2960;
import net.minecraft.class_310;
import net.minecraft.class_3222;
import net.minecraft.class_8710;
import net.minecraft.class_9129;
import net.minecraft.class_9139;

/**
 * Ports the 1.20.1 Fabric networking channel API onto 1.21.1 custom payloads.
 *
 * <p>Old mods call {@code ClientPlayNetworking.registerGlobalReceiver(Identifier, PlayChannelHandler)}
 * and {@code ServerPlayNetworking.send(player, Identifier, PacketByteBuf)}. The patch rules redirect
 * those call sites here. The client handler's legacy interface (removed from Fabric API in 1.21.1)
 * is provided by {@code net.fabricmc.fabric.api.client.networking.v1.ClientPlayNetworking$PlayChannelHandler}
 * from the embedded shim; this bridge only invokes its {@code receive} method reflectively, so it
 * compiles without that shim and works on both sides.
 */
public final class FabricLegacyNetworking {
    private static final Map<class_2960, class_8710.class_9154<RawPayload>> TYPES = new ConcurrentHashMap<>();
    private static final Map<class_2960, Object> LEGACY_HANDLERS = new ConcurrentHashMap<>();

    private FabricLegacyNetworking() {
    }

    private static synchronized class_8710.class_9154<RawPayload> type(class_2960 id) {
        class_8710.class_9154<RawPayload> existing = TYPES.get(id);
        if (existing != null) {
            return existing;
        }
        class_8710.class_9154<RawPayload> type = new class_8710.class_9154<>(id);
        class_9139<class_9129, RawPayload> codec = class_9139.method_56437(
                (buf, payload) -> buf.writeBytes(payload.data),
                buf -> {
                    byte[] data = new byte[buf.readableBytes()];
                    buf.readBytes(data);
                    return new RawPayload(type, data);
                });
        PayloadTypeRegistry.playS2C().register(type, codec);
        PayloadTypeRegistry.playC2S().register(type, codec);
        TYPES.put(id, type);
        return type;
    }

    /** Replacement for the old {@code new CustomPayloadC2SPacket(Identifier, PacketByteBuf)}. */
    public static class_2658 createClientPacket(class_2960 id, class_2540 buf) {
        byte[] data = new byte[buf.readableBytes()];
        buf.readBytes(data);
        return new class_2658(new RawPayload(type(id), data));
    }

    /** Replacement for the old {@code new ServerboundCustomPayloadPacket(Identifier, PacketByteBuf)}. */
    public static class_2817 createServerboundPacket(class_2960 id, class_2540 buf) {
        byte[] data = new byte[buf.readableBytes()];
        buf.readBytes(data);
        return new class_2817(new RawPayload(type(id), data));
    }

    /** Replacement for the old two-argument {@code registerGlobalReceiver(Identifier, handler)}. */
    public static boolean registerClientReceiver(class_2960 id, Object legacyHandler) {
        class_8710.class_9154<RawPayload> type = type(id);
        LEGACY_HANDLERS.put(id, legacyHandler);
        ClientPlayNetworking.registerGlobalReceiver(type, (payload, context) -> {
            try {
                receive(legacyHandler, context.client(), context.client().method_1562(),
                        new class_2540(Unpooled.wrappedBuffer(payload.data)),
                        context.responseSender());
            } catch (ReflectiveOperationException e) {
                throw new RuntimeException("legacy channel " + id + " handler failed", e);
            }
        });
        return true;
    }

    /** Replacement for the old {@code unregisterReceiver(Identifier)}; the caller pops the result. */
    public static Object unregisterClientReceiver(class_2960 id) {
        LEGACY_HANDLERS.remove(id);
        ClientPlayNetworking.unregisterReceiver(id);
        return null;
    }

    /** Replacement for the old {@code ServerPlayNetworking.registerReceiver(handler, id, handler)}. */
    public static boolean registerServerReceiver(net.minecraft.class_3244 networkHandler,
                                                 class_2960 id, Object legacyHandler) {
        class_8710.class_9154<RawPayload> type = type(id);
        ServerPlayNetworking.registerReceiver(networkHandler, type, (payload, context) -> {
            try {
                receiveServer(legacyHandler, context.server(), context.player(),
                        context.player().field_13987,
                        new class_2540(Unpooled.wrappedBuffer(payload.data)),
                        context.responseSender());
            } catch (ReflectiveOperationException e) {
                throw new RuntimeException("legacy C2S channel " + id + " handler failed", e);
            }
        });
        return true;
    }

    /** Replacement for the old {@code unregisterReceiver(handler, id)}; the caller pops the result. */
    public static Object unregisterServerReceiver(net.minecraft.class_3244 networkHandler, class_2960 id) {
        ServerPlayNetworking.unregisterReceiver(networkHandler, id);
        return null;
    }

    private static void receiveServer(Object handler, net.minecraft.server.MinecraftServer server,
                                      class_3222 player, net.minecraft.class_3244 networkHandler,
                                      class_2540 buf, Object sender) throws ReflectiveOperationException {
        for (Method m : handler.getClass().getMethods()) {
            if (m.getParameterCount() == 5 && m.getReturnType() == void.class) {
                m.setAccessible(true);
                m.invoke(handler, server, player, networkHandler, buf, sender);
                return;
            }
        }
        throw new NoSuchMethodException(handler.getClass().getName() + ".receive");
    }

    /** Replacement for the old {@code ServerPlayNetworking.send(player, id, buf)}. */
    public static void sendToPlayer(class_3222 player, class_2960 id, class_2540 buf) {
        byte[] data = new byte[buf.readableBytes()];
        buf.readBytes(data);
        ServerPlayNetworking.send(player, new RawPayload(type(id), data));
    }

    private static void receive(Object handler, class_310 client, Object networkHandler,
                                class_2540 buf, Object sender) throws ReflectiveOperationException {
        for (Method m : handler.getClass().getMethods()) {
            if (m.getParameterCount() == 4 && m.getReturnType() == void.class) {
                m.setAccessible(true);
                m.invoke(handler, client, networkHandler, buf, sender);
                return;
            }
        }
        throw new NoSuchMethodException(handler.getClass().getName() + ".receive");
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
