package top.mcbridge1201.bridge;

import net.minecraft.class_2960;

/** Replacements for the removed Identifier constructors. */
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

    /** The two-argument constructor became private in 1.21.1; the factory is the public path. */
    public static class_2960 of(String namespace, String path) {
        return class_2960.method_60655(namespace, path);
    }
}
