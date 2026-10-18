package top.mcbridge1201.bridge;

import net.blay09.mods.balm.api.Balm;
import net.blay09.mods.balm.api.EmptyLoadContext;

/**
 * Call-site bridge for trashslot 15.1.5 against native Balm 21.x:
 *
 * <p>trashslot calls the 1.20.1-era {@code Balm.initialize(String, Runnable)}; Balm 21 replaced
 * it with {@code initialize(String, BalmRuntimeLoadContext, Runnable)}. The mod itself is the
 * only initializer here, so the empty load context is the equivalent context.
 */
public final class BalmInitializeBridge {
    private BalmInitializeBridge() {}

    public static void initialize(String modId, Runnable initializer) {
        Balm.initialize(modId, EmptyLoadContext.INSTANCE, initializer);
    }
}
