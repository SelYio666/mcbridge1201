package top.mcbridge1201.bridge;

import net.minecraft.class_2960;

/** Replacement for the removed {@code new Identifier(String)} constructor. */
public final class IdentifierBridge {
    private IdentifierBridge() {
    }

    public static class_2960 of(String value) {
        int colon = value.indexOf(':');
        if (colon >= 0) {
            return class_2960.method_60655(value.substring(0, colon), value.substring(colon + 1));
        }
        return class_2960.method_60655("minecraft", value);
    }
}
