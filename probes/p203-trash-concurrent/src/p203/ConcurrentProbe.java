package p203;

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
 * p203 server probe: two players, one shared seed, and a per-packet tick stamp.
 *
 * <p>The claim under test is about the server, not about the clients: two trash operations
 * issued concurrently must arrive in the same server tick and stay isolated. So the interesting
 * measurement is taken here, where the tick counter is authoritative. {@link p203.mixin.PacketMixin}
 * calls {@link #notePacket} for every serverbound custom payload; this class stamps it with the
 * probe's own server-tick counter and prints it.
 *
 * <p>Seeds are deliberately different (A=5, B=4) and the two actions are deliberately different
 * (A deletes everything, B takes exactly one), so cross-talk is visible: a leaked packet would
 * move the wrong player's number to the wrong value.
 */
public final class ConcurrentProbe implements ModInitializer {
    public static final String USER_A = "GridUser";
    public static final String USER_B = "TrashB";

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
            System.out.println("P203_JOIN name=" + name + " total=" + joined.size());
        });
        ServerPlayConnectionEvents.DISCONNECT.register((handler, server) -> {
            class_3222 player = handler.method_32311();
            System.out.println("P203_LEAVE name=" + player.method_7334().getName());
        });
        ServerTickEvents.END_SERVER_TICK.register(server -> {
            ticks++;
            if (joined.size() < 2) {
                return;
            }
            if (!seeded && ticks >= 40) {
                seeded = true;
                seedingFlag = true;
                TrashHelper.setTrashItem(joined.get(USER_A), new class_1799(class_1802.field_8477, 5));
                TrashHelper.setTrashItem(joined.get(USER_B), new class_1799(class_1802.field_8477, 4));
                seedingFlag = false;
                System.out.println("P203_SEED tick=" + ticks + " " + USER_A + "=5 " + USER_B + "=4");
            }
            if (seeded && ticks % 20 == 0) {
                for (Map.Entry<String, class_3222> entry : joined.entrySet()) {
                    System.out.println("P203_SERVER tick=" + ticks + " user=" + entry.getKey()
                            + " trash=" + describe(TrashHelper.getTrashItem(entry.getValue())));
                }
            }
        });
        System.out.println("P203_SERVER_PROBE ready");
    }

    /** Called from the packet mixin, before the mod sees the payload. */
    public static void notePacket(String user, String channel, String payloadClass,
                                  long wallMillis) {
        System.out.println("P203_PKT thread=" + Thread.currentThread().getName()
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
        System.out.println("P203_S2C thread=" + Thread.currentThread().getName()
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
        System.out.println("P203_SET side=" + side
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
