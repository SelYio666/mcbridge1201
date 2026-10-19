package top.mcbridge1201.bridge;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.BiConsumer;
import java.util.function.Function;

import net.blay09.mods.balm.api.network.BalmNetworking;
import net.fabricmc.fabric.api.client.networking.v1.ClientPlayNetworking;
import net.fabricmc.fabric.api.networking.v1.PayloadTypeRegistry;
import net.fabricmc.fabric.api.networking.v1.ServerPlayNetworking;
import net.minecraft.class_1657;
import net.minecraft.class_2540;
import net.minecraft.class_2960;
import net.minecraft.class_3222;
import net.minecraft.class_8710;
import net.minecraft.class_9129;
import net.minecraft.class_9139;

/**
 * Adapts the 1.20.1-era Balm networking registration to 1.21.1 Fabric payloads.
 *
 * <p>Old Balm: {@code registerServerboundPacket(Identifier, Class<T>, BiConsumer<FriendlyByteBuf,T>,
 * Function<FriendlyByteBuf,T>, BiConsumer<ServerPlayer,T>)}. 1.21.1 Balm 21 uses
 * {@code PacketType<T>} + {@code StreamCodec<RegistryFriendlyByteBuf,T>}. This bridge keeps the
 * old call shape by wrapping T in a CustomPayload and registering a StreamCodec that delegates to
 * the mod's existing encode/decode functions. Clientbound payload types are registered too, but
 * no client receiver is installed on a dedicated server (the client path is not exercised here).
 */
public final class BalmNetworkingBridge {
    private static final Map<Class<?>, Function<Object, class_8710>> SENDERS = new ConcurrentHashMap<>();
    private static final Map<Class<?>, Function<Object, class_8710>> SERVERBOUND_SENDERS = new ConcurrentHashMap<>();
    private static final ThreadLocal<class_3222> REPLY_PLAYER = new ThreadLocal<>();

    private BalmNetworkingBridge() {}

    public static <T> void registerServerbound(BalmNetworking self, class_2960 id, Class<T> type,
                                               BiConsumer<T, class_2540> writer,
                                               Function<class_2540, T> reader,
                                               BiConsumer<class_3222, T> handler) {
        Payload<T> descriptor = new Payload<>(id);
        class_8710.class_9154<Payload<T>> packetType = descriptor.method_56479();
        class_9139<class_9129, Payload<T>> codec = codec(writer, reader, descriptor);
        PayloadTypeRegistry.playC2S().register(packetType, codec);
        SERVERBOUND_SENDERS.put(type, value -> new Payload<>(packetType, type.cast(value)));
        ServerPlayNetworking.registerGlobalReceiver(packetType,
                (payload, context) -> {
                    REPLY_PLAYER.set(context.player());
                    try {
                        handler.accept(context.player(), payload.value());
                    } finally {
                        REPLY_PLAYER.remove();
                    }
                });
    }

    public static <T> void registerClientbound(BalmNetworking self, class_2960 id, Class<T> type,
                                               BiConsumer<T, class_2540> writer,
                                               Function<class_2540, T> reader,
                                               BiConsumer<net.minecraft.class_1657, T> handler) {
        Payload<T> descriptor = new Payload<>(id);
        class_8710.class_9154<Payload<T>> packetType = descriptor.method_56479();
        PayloadTypeRegistry.playS2C().register(packetType, codec(writer, reader, descriptor));
        SENDERS.put(type, value -> new Payload<>(packetType, type.cast(value)));
        if (isClient()) {
            try {
                Class<?> client = Class.forName("top.mcbridge1201.bridge.BalmNetworkingBridge$Client");
                client.getMethod("register", class_8710.class_9154.class, BiConsumer.class)
                        .invoke(null, packetType, handler);
            } catch (ReflectiveOperationException e) {
                throw new IllegalStateException("client payload receiver registration failed", e);
            }
        }
    }

    public static void sendTo(BalmNetworking self, class_1657 player, Object packet) {
        if (!(player instanceof class_3222 serverPlayer)) {
            throw new IllegalArgumentException("sendTo requires a ServerPlayer, got " + player);
        }
        Function<Object, class_8710> sender = SENDERS.get(packet.getClass());
        if (sender == null) {
            throw new IllegalArgumentException("unregistered Balm packet type: " + packet.getClass().getName());
        }
        ServerPlayNetworking.send(serverPlayer, sender.apply(packet));
    }

    /** Old Balm's client-to-server packet send; 1.21.1 Balm changed the erasure to CustomPayload. */
    public static void sendToServer(BalmNetworking self, Object packet) {
        Function<Object, class_8710> sender = SERVERBOUND_SENDERS.get(packet.getClass());
        if (sender == null) {
            throw new IllegalArgumentException("unregistered serverbound Balm packet type: "
                    + packet.getClass().getName());
        }
        ClientPlayNetworking.send(sender.apply(packet));
    }

    /** Old Balm's reply inside a serverbound handler; send back to the packet's sender. */
    public static void reply(BalmNetworking self, Object packet) {
        class_3222 player = REPLY_PLAYER.get();
        if (player == null) {
            throw new IllegalStateException("No context to reply to");
        }
        Function<Object, class_8710> sender = SENDERS.get(packet.getClass());
        if (sender == null) {
            throw new IllegalArgumentException("unregistered clientbound Balm packet type: "
                    + packet.getClass().getName());
        }
        ServerPlayNetworking.send(player, sender.apply(packet));
    }

    private static boolean isClient() {
        try {
            Class<?> loaderClass = Class.forName("net.fabricmc.loader.api.FabricLoader");
            Object loader = loaderClass.getMethod("getInstance").invoke(null);
            Object type = loader.getClass().getMethod("getEnvironmentType").invoke(loader);
            return "CLIENT".equals(String.valueOf(type));
        } catch (ReflectiveOperationException e) {
            return false;
        }
    }

    /** Loaded only on the client; kept nested so it is embedded with the bridge. */
    public static final class Client {
        private Client() {}

        public static <T> void register(class_8710.class_9154<Payload<T>> type,
                                        BiConsumer<net.minecraft.class_1657, T> handler) {
            ClientPlayNetworking.registerGlobalReceiver(type,
                    (payload, context) -> handler.accept(context.player(), payload.value()));
        }
    }

    private static <T> class_9139<class_9129, Payload<T>> codec(
            BiConsumer<T, class_2540> writer, Function<class_2540, T> reader, Payload<T> descriptor) {
        return class_9139.method_56437(
                (buf, payload) -> writer.accept(payload.value(), buf),
                buf -> {
                    T value = reader.apply(buf);
                    return descriptor.with(value);
                });
    }

    /** CustomPayload wrapper; the id is fixed by the PacketType created in the constructor. */
    public static final class Payload<T> implements class_8710 {
        private final class_8710.class_9154<Payload<T>> type;
        private final T value;

        @SuppressWarnings("unchecked")
        private Payload(class_2960 id) {
            this.type = new class_8710.class_9154<>(id);
            this.value = null;
        }

        private Payload(class_8710.class_9154<Payload<T>> type, T value) {
            this.type = type;
            this.value = value;
        }

        private Payload<T> with(T value) {
            return new Payload<>(type, value);
        }

        public T value() {
            return value;
        }

        @Override
        public class_8710.class_9154<Payload<T>> method_56479() {
            return type;
        }
    }
}
