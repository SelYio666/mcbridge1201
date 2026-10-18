package top.mcbridge1201.bridge;

/**
 * Lithium 0.11.4 uses the 1.20.1 static {@code FriendlyByteBuf.getVarIntSize(int)} for the
 * serialized size of its palette. 1.21.1 moved this helper to {@code VarInt.getByteSize(int)};
 * CenturyBridge tombstoned the old call. This bridge restores the exact size computation.
 */
public final class LithiumVarIntBridge {
    private LithiumVarIntBridge() {}

    public static int getByteSize(int value) {
        return net.minecraft.class_8703.method_53015(value);
    }
}
