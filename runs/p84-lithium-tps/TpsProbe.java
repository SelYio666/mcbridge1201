package probe;

import java.util.Iterator;

import net.fabricmc.api.ModInitializer;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;
import net.minecraft.class_3218;
import net.minecraft.server.MinecraftServer;

/** Loads a 17x17 chunk area and reports the average TPS over a 60-second window. */
public final class TpsProbe implements ModInitializer {
    private int ticks;
    private long startNanos;
    private int startTick;

    @Override
    public void onInitialize() {
        ServerTickEvents.END_SERVER_TICK.register(server -> {
            ticks++;
            if (ticks == 20) {
                Iterator<class_3218> it = server.method_3738().iterator();
                class_3218 world = it.next();
                int cx = 0;
                int cz = 0;
                int loaded = 0;
                for (int dx = -8; dx <= 8; dx++) {
                    for (int dz = -8; dz <= 8; dz++) {
                        if (world.method_8497(cx + dx, cz + dz) != null) {
                            loaded++;
                        }
                    }
                }
                startNanos = System.nanoTime();
                startTick = ticks;
                System.out.println("TPS_START loaded=" + loaded + "/289");
            }
            if (ticks == 1220) {
                long elapsed = System.nanoTime() - startNanos;
                double tps = 1200.0 / (elapsed / 1_000_000_000.0);
                System.out.println("TPS_AVG tps=" + String.format(java.util.Locale.ROOT, "%.2f", tps)
                        + " ticks=" + (ticks - startTick)
                        + " seconds=" + String.format(java.util.Locale.ROOT, "%.2f",
                                elapsed / 1_000_000_000.0));
            }
        });
    }
}
