package top.mcbridge1201.bridge;

import net.minecraft.class_2487;
import net.minecraft.class_2499;
import net.minecraft.class_2520;

/**
 * 1.20.1 code asks NbtCompound.contains(key, 9) to test "is a list". 1.21.1 changed the type check
 * to the element type, so the legacy call is false for a list of compounds. Keep the old meaning
 * for list checks.
 */
public final class NbtListCompatBridge {
    private NbtListCompatBridge() {
    }

    public static boolean contains(class_2487 nbt, String key, int type) {
        if (type == 9) {
            class_2520 value = nbt.method_10580(key);
            return value instanceof class_2499;
        }
        if (type == 99) {
            class_2520 value = nbt.method_10580(key);
            if (value == null) {
                return false;
            }
            int id = value.method_10711();
            return id >= 1 && id <= 6;
        }
        return nbt.method_10573(key, type);
    }
}
