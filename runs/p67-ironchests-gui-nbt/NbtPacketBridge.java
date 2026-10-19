package top.mcbridge1201.bridge;

import net.minecraft.class_2487;
import net.minecraft.class_2520;
import net.minecraft.class_2540;

/**
 * 1.20.1 {@code PacketByteBuf.writeNbt(NbtCompound)} bridge.
 *
 * <p>1.21.1 keeps the method name but widens the parameter to {@code NbtElement}
 * ({@code class_2520}), so the old {@code (NbtCompound)PacketByteBuf} descriptor no longer links:
 *
 * <pre>
 * NoSuchMethodError: 'net.minecraft.class_2540 net.minecraft.class_2540.method_10794(class_2487)'
 * </pre>
 *
 * <p>{@code NbtCompound} extends {@code NbtElement}, so the bridge only widens the argument.
 */
public final class NbtPacketBridge {
    private NbtPacketBridge() {}

    public static class_2540 writeNbt(class_2540 buf, class_2487 tag) {
        return buf.method_10794((class_2520) tag);
    }
}
