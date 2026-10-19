package top.mcbridge1201.bridge;

import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.util.stream.Stream;

import net.minecraft.class_1937;
import net.minecraft.class_2487;
import net.minecraft.class_2586;
import net.minecraft.class_7225;

/**
 * IronChests 1.20.1 sync-NBT bridge.
 *
 * <p>The 1.20.1 class had {@code readNbt(NbtCompound)} / {@code writeNbt(NbtCompound)}; 1.21.1 uses
 * the two-argument {@code readNbt(NbtCompound, HolderLookup.Provider)} /
 * {@code writeNbt(NbtCompound, HolderLookup.Provider)}. The conversion left one-argument calls in
 * {@code GenericChestBlockEntity.getSyncTag()} and {@code loadSyncTag(NbtCompound)} (and, on top of
 * that, swapped which of the two is called), so both call sites are redirected here.
 *
 * <p>The bridge uses reflection because the 1.21.1 two-argument methods are {@code protected} on
 * {@code BlockEntity} and only the mod's own overrides are public; this keeps the bridge free of a
 * compile-time dependency on the mod jar.
 */
public final class IronChestsNbtBridge {
    private IronChestsNbtBridge() {}

    /** {@code getSyncTag()} wants to serialise the entity into the tag. */
    public static void writeSyncTag(class_2586 entity, class_2487 tag) {
        // The converted class keeps the 1.20.1 method names but its bodies are swapped:
        // method_11007(NbtCompound, Provider) writes the inventory into the tag, while
        // method_11014(NbtCompound, Provider) clears and reads the inventory from the tag.
        invoke(entity, "method_11007", tag);
    }

    /** {@code loadSyncTag(tag)} wants to deserialise the tag into the entity. */
    public static void readSyncTag(class_2586 entity, class_2487 tag) {
        invoke(entity, "method_11014", tag);
    }

    private static void invoke(class_2586 entity, String name, class_2487 tag) {
        try {
            Method method = entity.getClass().getMethod(name, class_2487.class,
                    class_7225.class_7874.class);
            method.invoke(entity, tag, provider(entity));
        } catch (NoSuchMethodException | IllegalAccessException e) {
            throw new IllegalStateException("IronChests NBT bridge: " + name, e);
        } catch (InvocationTargetException e) {
            Throwable cause = e.getCause();
            if (cause instanceof RuntimeException runtime) throw runtime;
            if (cause instanceof Error error) throw error;
            throw new IllegalStateException(cause);
        }
    }

    private static class_7225.class_7874 provider(class_2586 entity) {
        class_1937 world = entity.method_10997();
        if (world != null) {
            return world.method_30349();
        }
        return class_7225.class_7874.method_46761(Stream.<class_7225.class_7226<?>>empty());
    }
}
