package p231;

import net.blay09.mods.trashslot.TrashHelper;
import net.fabricmc.api.ModInitializer;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;
import net.fabricmc.fabric.api.networking.v1.ServerPlayConnectionEvents;
import net.fabricmc.loader.api.FabricLoader;
import net.minecraft.class_1799;
import net.minecraft.class_1802;
import net.minecraft.class_3222;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * p231 server probe: four players behind a latency proxy, one seed each, and per-write stamps.
 *
 * <p>p203 proved same-tick isolation for two players on loopback. This round extends the same
 * measurement to four players, each in its own game directory, all connecting through a userspace
 * TCP proxy that delays every chunk by the configured amount in each direction (the harness passes
 * the delay via {@code -Dp231.delayMs} so the run log states the injected latency next to the
 * measured one). Cross-talk stays visible because the four operations and seeds differ:
 * A deletes 5, B takes one from 4, C takes one from 3, D deletes 2. A leaked packet either writes
 * the wrong value for a user or leaves one user without its write, and both fail the verdict.
 *
 * <p>Seeds are overridable with {@code -Dp231.seed.<name>} but default to 5/4/3/2 so the run and
 * the probe agree without extra wiring.
 */
public final class QuadProbe implements ModInitializer {
    private static final Map<String, Integer> SEEDS = new LinkedHashMap<>();

    static {
        SEEDS.put("GridUser", Integer.getInteger("p231.seed.GridUser", 5));
        SEEDS.put("TrashB", Integer.getInteger("p231.seed.TrashB", 4));
        SEEDS.put("TrashC", Integer.getInteger("p231.seed.TrashC", 3));
        SEEDS.put("TrashD", Integer.getInteger("p231.seed.TrashD", 2));
    }

    private static final Map<String, class_3222> joined = new LinkedHashMap<>();
    private static volatile int ticks;
    private static boolean seeded;
    private static boolean seedingFlag;

    @Override
    public void onInitialize() {
        if (FabricLoader.getInstance().getEnvironmentType() != net.fabricmc.api.EnvType.SERVER) {
            return;
        }
        ServerPlayConnectionEvents.JOIN.register((handler, sender, server) -> {
            class_3222 player = handler.method_32311();
            String name = player.method_7334().getName();
            joined.put(name, player);
            System.out.println("P231_JOIN name=" + name + " total=" + joined.size());
        });
        ServerPlayConnectionEvents.DISCONNECT.register((handler, server) -> {
            class_3222 player = handler.method_32311();
            System.out.println("P231_LEAVE name=" + player.method_7334().getName());
        });
        ServerTickEvents.END_SERVER_TICK.register(server -> {
            ticks++;
            if (joined.size() < SEEDS.size()) {
                return;
            }
            if (!seeded && ticks >= 40) {
                seeded = true;
                seedingFlag = true;
                StringBuilder seededLine = new StringBuilder();
                for (Map.Entry<String, Integer> entry : SEEDS.entrySet()) {
                    class_3222 player = joined.get(entry.getKey());
                    if (player == null) {
                        continue;
                    }
                    TrashHelper.setTrashItem(player,
                            new class_1799(class_1802.field_8477, entry.getValue()));
                    seededLine.append(" ").append(entry.getKey()).append("=")
                            .append(entry.getValue());
                }
                seedingFlag = false;
                System.out.println("P231_SEED tick=" + ticks + seededLine);
            }
            if (seeded && ticks % 20 == 0) {
                for (Map.Entry<String, class_3222> entry : joined.entrySet()) {
                    System.out.println("P231_SERVER tick=" + ticks + " user=" + entry.getKey()
                            + " trash=" + describe(TrashHelper.getTrashItem(entry.getValue())));
                }
            }
        });
        System.out.println("P231_SERVER_PROBE ready users=" + SEEDS.keySet());
    }

    /** Called from the packet mixin, before the mod sees the payload. */
    public static void notePacket(String user, String channel, String payloadClass,
                                  long wallMillis) {
        System.out.println("P231_PKT thread=" + Thread.currentThread().getName()
                + " user=" + user
                + " tick=" + ticks
                + " wall=" + wallMillis
                + " channel=" + channel
                + " payload=" + payloadClass);
    }

    /** Server tick this probe is currently inside; stamped onto every state mutation. */
    public static int ticks() {
        return ticks;
    }

    public static void noteServerbound(String messageClass, long wallMillis) {
        System.out.println("P231_S2C thread=" + Thread.currentThread().getName()
                + " tick=" + ticks
                + " wall=" + wallMillis
                + " message=" + messageClass);
    }

    /** True while the probe itself is seeding, so the seed is not read as a player operation. */
    public static boolean seeding() {
        return seedingFlag;
    }

    public static void noteTrashMutation(String side, String user, class_1799 stack,
                                         long wallMillis) {
        System.out.println("P231_SET side=" + side
                + " thread=" + Thread.currentThread().getName()
                + " tick=" + ("SERVER".equals(side) ? ticks : -1)
                + " wall=" + wallMillis
                + " seeding=" + seedingFlag
                + " user=" + user
                + " stack=" + describe(stack));
    }

    public static String describe(class_1799 stack) {
        if (stack == null || stack.method_7960()) {
            return "empty";
        }
        return stack.method_7909() + "x" + stack.method_7947();
    }
}
