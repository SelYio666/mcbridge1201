package probe;

import java.lang.reflect.Field;

import net.blay09.mods.balm.api.Balm;
import net.blay09.mods.balm.api.event.client.screen.ScreenKeyEvent;
import net.blay09.mods.trashslot.client.TrashSlotGuiHandler;
import net.blay09.mods.trashslot.client.TrashSlotSlot;
import net.blay09.mods.trashslot.client.gui.TrashSlotComponent;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.minecraft.class_1799;
import net.minecraft.class_1802;
import net.minecraft.class_437;
import net.minecraft.class_490;

public final class TrashEmptyKeyProbe implements ClientModInitializer {
    private int ticks;

    private static int field(class_437 screen, String name) {
        try {
            Field f = class_437.class.getDeclaredField(name);
            f.setAccessible(true);
            return f.getInt(screen);
        } catch (ReflectiveOperationException e) {
            return -1;
        }
    }

    @Override
    public void onInitializeClient() {
        Balm.getEvents().onEvent(ScreenKeyEvent.Press.Post.class,
                event -> System.out.println("KEY_EVENT screen=" + event.getScreen()
                        + " key=" + event.getKey()
                        + " scan=" + event.getScanCode()));
        ClientTickEvents.END_CLIENT_TICK.register(client -> {
            if (client.field_1724 == null) return;
            ticks++;
            if (ticks == 100) {
                client.method_1507(new class_490(client.field_1724));
                System.out.println("TRASH_OPEN screen=" + client.field_1755);
            }
            if (ticks == 140) {
                TrashSlotSlot trash = TrashSlotGuiHandler.getTrashSlot();
                if (trash != null) {
                    trash.method_7673(new class_1799(class_1802.field_8477, 5));
                }
                System.out.println("TRASH_SEED trash="
                        + (trash == null ? "null" : trash.method_7677()));
            }
            if (ticks == 160) {
                TrashSlotSlot trash = TrashSlotGuiHandler.getTrashSlot();
                TrashSlotComponent comp = TrashSlotGuiHandler.getTrashSlotComponent();
                if (trash != null) {
                    System.out.println("TRASH_SLOT f72=" + trash.field_7872
                            + " f73=" + trash.field_7873 + " f74=" + trash.field_7874);
                }
                if (client.field_1755 != null) {
                    System.out.println("TRASH_SCREEN w=" + client.field_1755.field_22789
                            + " h=" + client.field_1755.field_22790
                            + " left=" + field(client.field_1755, "field_2776")
                            + " top=" + field(client.field_1755, "field_2800"));
                }
                if (comp != null) {
                    int minX = Integer.MAX_VALUE;
                    int minY = Integer.MAX_VALUE;
                    int maxX = Integer.MIN_VALUE;
                    int maxY = Integer.MIN_VALUE;
                    for (int x = 0; x <= 640; x++) {
                        for (int y = 0; y <= 480; y++) {
                            if (comp.isInside(x, y)) {
                                minX = Math.min(minX, x);
                                minY = Math.min(minY, y);
                                maxX = Math.max(maxX, x);
                                maxY = Math.max(maxY, y);
                            }
                        }
                    }
                    System.out.println("TRASH_RECT l=" + minX + " t=" + minY
                            + " r=" + maxX + " b=" + maxY);
                }
            }
            if (ticks >= 200 && ticks % 40 == 0) {
                TrashSlotSlot trash = TrashSlotGuiHandler.getTrashSlot();
                System.out.println("TRASH_STATE tick=" + ticks
                        + " trash=" + (trash == null ? "null" : trash.method_7677()));
            }
        });
    }
}
