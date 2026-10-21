package probe;

import io.netty.buffer.Unpooled;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.minecraft.class_1799;
import net.minecraft.class_2487;
import net.minecraft.class_2540;
import net.minecraft.class_2960;
import net.minecraft.class_7923;
import top.mcbridge1201.bridge.TrashSlotNbtBridge;

/** Runtime probe for the strict TrashSlot NBT bridge (ISSUE-01 regression). */
public final class StrictProbe implements ClientModInitializer {
    private int ticks;
    private boolean done;

    @Override
    public void onInitializeClient() {
        ClientTickEvents.END_CLIENT_TICK.register(client -> {
            ticks++;
            if (done || ticks % 40 != 0 || client.field_1724 == null) {
                return;
            }
            done = true;
            System.out.println("STRICT_READY tick=" + ticks);
            try {
                var item = class_7923.field_41178.method_10223(class_2960.method_60655("minecraft", "diamond"));
                var stack = new class_1799(item, 5);
                var buf = new class_2540(Unpooled.buffer());
                TrashSlotNbtBridge.writeItem(buf, stack);
                var back = TrashSlotNbtBridge.readItem(buf);
                boolean ok = back.method_7947() == 5 && back.method_7909() == item;
                System.out.println("STRICT_VALID " + (ok ? "OK" : "FAIL count=" + back.method_7947()));
            } catch (Throwable t) {
                System.out.println("STRICT_VALID_THREW " + t);
            }
            try {
                var empty = new class_2487();
                var s = TrashSlotNbtBridge.load(empty);
                System.out.println("STRICT_EMPTY " + (s.method_7960() ? "OK" : "FAIL"));
            } catch (Throwable t) {
                System.out.println("STRICT_EMPTY_THREW " + t);
            }
            try {
                var bad = new class_2487();
                bad.method_10582("id", "minecraft:definitely_not_real");
                bad.method_10582("count", "1");
                TrashSlotNbtBridge.load(bad);
                System.out.println("STRICT_INVALID_NOT_THROWN");
            } catch (IllegalStateException e) {
                System.out.println("STRICT_INVALID_THROWN");
            } catch (Throwable t) {
                System.out.println("STRICT_INVALID_OTHER " + t);
            }
            try {
                var bad2 = new class_2487();
                bad2.method_10582("id", "minecraft:diamond");
                bad2.method_10582("count", "5");
                bad2.method_10582("Slot", "0");
                var s2 = TrashSlotNbtBridge.load(bad2);
                System.out.println("STRICT_TYPED_NOT_THROWN count=" + s2.method_7947()
                        + " empty=" + s2.method_7960()
                        + " item=" + s2.method_7909());
            } catch (IllegalStateException e) {
                System.out.println("STRICT_TYPED_THROWN");
            } catch (Throwable t) {
                System.out.println("STRICT_TYPED_OTHER " + t);
            }
            System.out.println("STRICT_DONE");
        });
    }
}
