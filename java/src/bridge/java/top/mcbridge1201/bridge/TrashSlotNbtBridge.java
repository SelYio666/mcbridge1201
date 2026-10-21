package top.mcbridge1201.bridge;

import com.mojang.serialization.DataResult;
import com.mojang.serialization.DynamicOps;

import java.lang.reflect.Field;

import net.minecraft.class_1799;
import net.minecraft.class_2378;
import net.minecraft.class_2487;
import net.minecraft.class_2509;
import net.minecraft.class_2520;
import net.minecraft.class_2540;
import net.minecraft.class_5455;
import net.minecraft.class_6903;
import net.minecraft.class_7923;

/**
 * Replaces the four 1.20.1 ItemStack/NBT helpers that CenturyBridge tombstoned for trashslot:
 *
 * <ul>
 *   <li>{@code ItemStack.writeNbt(NbtCompound)} (method_7953)</li>
 *   <li>{@code ItemStack.fromNbt(NbtCompound)} (method_7915)</li>
 *   <li>{@code FriendlyByteBuf.writeItemStack(ItemStack)} (method_10793)</li>
 *   <li>{@code FriendlyByteBuf.readItemStack()} (method_10819)</li>
 * </ul>
 *
 * <p>1.20.5 moved item data into components; 1.21.1's ItemStack.CODEC is registry-aware. This
 * bridge builds a RegistryOps over the built-in registries and uses NbtOps, then writes/reads
 * the NBT through FriendlyByteBuf's remaining NBT methods. The packet format is internal to
 * trashslot (both sides are patched), so this is a valid replacement.
 */
public final class TrashSlotNbtBridge {
    private static volatile DynamicOps<class_2520> ops;

    private TrashSlotNbtBridge() {}

    @SuppressWarnings({"unchecked", "rawtypes"})
    private static DynamicOps<class_2520> ops() {
        DynamicOps<class_2520> local = ops;
        if (local != null) return local;
        synchronized (TrashSlotNbtBridge.class) {
            local = ops;
            if (local == null) {
                try {
                    Field f = class_7923.class.getDeclaredField("field_41170");
                    f.setAccessible(true);
                    Object registries = f.get(null);
                    var access = class_5455.method_40302((class_2378) registries);
                    local = class_6903.method_46632((DynamicOps) class_2509.field_11560, access);
                    ops = local;
                } catch (ReflectiveOperationException e) {
                    throw new ExceptionInInitializerError(e);
                }
            }
        }
        return local;
    }

    /** ItemStack.writeNbt: encode into the supplied compound and return it (fails loudly). */
    public static class_2487 save(class_1799 stack, class_2487 target) {
        DataResult<class_2520> result = class_1799.field_24671.encodeStart(ops(), stack);
        class_2520 encoded = result.result().orElse(null);
        if (!(encoded instanceof class_2487 compound)) {
            throw new IllegalStateException("[mcbridge1201] ItemStack encode failed: "
                    + result.error().map(Object::toString).orElse("no value"));
        }
        for (String key : compound.method_10541()) {
            target.method_10566(key, compound.method_10580(key));
        }
        return target;
    }

    /** ItemStack.fromNbt: parse from NBT; empty tag is legal empty, parse failure throws. */
    public static class_1799 load(class_2487 tag) {
        if (tag == null || tag.method_10541().isEmpty()) {
            return class_1799.field_8037;
        }
        DataResult<class_1799> result = class_1799.field_24671.parse(ops(), tag);
        if (result.result().isPresent()) {
            return result.result().get();
        }
        throw new IllegalStateException("[mcbridge1201] ItemStack decode failed: "
                + result.error().map(Object::toString).orElse("?"));
    }

    /** FriendlyByteBuf.writeItemStack: write the registry-aware ItemStack NBT (fails loudly). */
    public static class_2540 writeItem(class_2540 buf, class_1799 stack) {
        DataResult<class_2520> result = class_1799.field_24671.encodeStart(ops(), stack);
        class_2520 encoded = result.result().orElse(null);
        if (encoded == null) {
            throw new IllegalStateException("[mcbridge1201] ItemStack network encode failed: "
                    + result.error().map(Object::toString).orElse("?"));
        }
        buf.method_10794(encoded);
        return buf;
    }

    /** FriendlyByteBuf.readItemStack: read the NBT written by {@link #writeItem}. */
    public static class_1799 readItem(class_2540 buf) {
        return load(buf.method_10798());
    }
}
