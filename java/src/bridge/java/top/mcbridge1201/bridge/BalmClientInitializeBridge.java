package top.mcbridge1201.bridge;

import net.blay09.mods.balm.api.EmptyLoadContext;
import net.blay09.mods.balm.api.client.BalmClient;

/**
 * Call-site bridge for trashslot 15.1.5's client initializer against native Balm 21.x:
 *
 * <p>trashslot calls the 1.20.1-era {@code BalmClient.initialize(String, Runnable)}; Balm 21
 * requires a {@code BalmRuntimeLoadContext}. The mod itself is the only initializer here, so the
 * empty load context is the equivalent context.
 */
public final class BalmClientInitializeBridge {
    private BalmClientInitializeBridge() {}

    public static void initialize(String modId, Runnable initializer) {
        BalmClient.initialize(modId, EmptyLoadContext.INSTANCE, initializer);
    }
}
