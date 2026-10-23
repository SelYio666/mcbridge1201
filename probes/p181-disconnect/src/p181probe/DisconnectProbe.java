package p181probe;

import net.fabricmc.api.ClientModInitializer;
import net.minecraft.class_310;

/**
 * Test-only client probe: after a delay, disconnect the integrated server normally.
 *
 * <p>The p181 lifecycle test cannot use {@code /stop} from a datapack function (the integrated
 * server's command tree has no stop command and functions run at permission level 2). This probe
 * calls {@code MinecraftClient.method_18096(null, false)} on the render thread, which runs
 * {@code GameRenderer.method_3203 -> MapRenderer.method_1771}; that is exactly the map-atlas
 * clear/close path under test.
 */
public final class DisconnectProbe implements ClientModInitializer {
    private static final long DELAY_MS = 30_000L;

    @Override
    public void onInitializeClient() {
        Thread thread = new Thread(() -> {
            try {
                Thread.sleep(DELAY_MS);
            } catch (InterruptedException ignored) {
                return;
            }
            class_310 client = class_310.method_1551();
            System.out.println("[p181-probe] requesting client stop");
            // method_1592 clears the run-loop flag; the main loop then runs method_1519 (cleanup),
            // including GameRenderer/MapRenderer close. This is a normal shutdown between frames,
            // unlike calling disconnect() from the in-frame task queue.
            client.method_18859(client::method_1592);
        }, "p181-disconnect");
        thread.setDaemon(true);
        thread.start();
    }
}
