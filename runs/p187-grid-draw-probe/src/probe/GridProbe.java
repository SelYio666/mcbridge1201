package probe;

import java.util.List;
import java.util.Optional;

import net.blay09.mods.balm.mixin.AbstractContainerScreenAccessor;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.fabricmc.fabric.api.client.rendering.v1.HudRenderCallback;
import net.minecraft.class_1735;
import net.minecraft.class_1792;
import net.minecraft.class_1799;
import net.minecraft.class_1802;
import net.minecraft.class_1836;
import net.minecraft.class_2561;
import net.minecraft.class_2960;
import net.minecraft.class_332;
import net.minecraft.class_465;
import net.minecraft.class_490;
import net.minecraft.class_5632;
import net.minecraft.class_7923;
import net.minecraft.class_9288;
import net.minecraft.class_9326;
import net.minecraft.class_9334;
import net.minecraft.class_9779;

/**
 * p187 client probe. Builds a shulker box with a real ContainerComponent, puts it in the hotbar,
 * opens the inventory (mouse hover is too flaky to drive from the harness), and then renders the
 * shulker's REAL tooltip through the REAL pipeline every HUD frame at a fixed position: getTooltip
 * -> SnapshotStore -> getTooltipData (mod mixin + registry provider) -> DrawContext.drawTooltip ->
 * PreviewTooltipComponent -> BasePreviewRenderer. The tracer mixins on BasePreviewRenderer and the
 * mod's ItemStackMixin log how far the draw gets.
 */
public final class GridProbe implements ClientModInitializer {
    private int ticks;
    private boolean opened;
    private boolean logged;
    private class_1799 box;
    private class_1799 serverBox;
    private int hudFrames;
    private boolean hudStarted;

    @Override
    public void onInitializeClient() {
        ClientTickEvents.END_CLIENT_TICK.register(client -> {
            if (client.field_1724 == null) {
                return;
            }
            ticks++;
            if (!opened && ticks > 40 && client.field_1755 == null) {
                class_1792 shulker = class_7923.field_41178
                        .method_10223(class_2960.method_60655("minecraft", "shulker_box"));
                class_1799 stack = new class_1799(shulker, 1);
                class_9288 container = class_9288.method_57493(
                        List.of(new class_1799(class_1802.field_8477, 5)));
                class_9326 components = class_9326.method_57841()
                        .method_57854(class_9334.field_49622, container)
                        .method_57852();
                stack.method_57366(components);
                client.field_1724.method_31548().method_5447(0, stack);
                this.box = stack;
                client.method_1507(new class_490(client.field_1724));
                opened = true;
                System.out.println("GRID_INV_OPEN tick=" + ticks);
            }
            if (opened && !logged && client.field_1755 instanceof class_465<?> screen) {
                var accessor = (AbstractContainerScreenAccessor) screen;
                double scale = client.method_22683().method_4495();
                System.out.println("GRID_SCREEN left=" + accessor.getLeftPos()
                        + " top=" + accessor.getTopPos() + " scale=" + scale);
                for (int i = 0; i < client.field_1724.field_7512.field_7761.size(); i++) {
                    class_1735 slot = client.field_1724.field_7512.field_7761.get(i);
                    class_1799 stack = slot.method_7677();
                    if (!stack.method_7960() && stack.method_7909() == class_7923.field_41178
                            .method_10223(class_2960.method_60655("minecraft", "shulker_box"))) {
                        System.out.println("GRID_SLOT index=" + i
                                + " x=" + slot.field_7873 + " y=" + slot.field_7872
                                + " count=" + stack.method_7947()
                                + " map=" + stack.method_57380());
                        break;
                    }
                }
                logged = true;
            }
            // Track the SERVER-synced shulker (placed via /item replace): it arrives with its own
            // CONTAINER component; when one shows up in a hotbar slot the HUD tooltip switches to
            // it so the real server-item path (p110) is exercised too.
            if (opened && ticks % 10 == 0) {
                for (int slot = 1; slot < 9; slot++) {
                    class_1799 stack = client.field_1724.method_31548().method_5438(slot);
                    if (stack.method_7960()
                            || stack.method_7909() != class_7923.field_41178
                                    .method_10223(class_2960.method_60655("minecraft", "shulker_box"))) {
                        continue;
                    }
                    Object component = readContainer(stack);
                    if (component instanceof class_9288 container && countNonAir(container) > 0) {
                        if (serverBox != stack) {
                            serverBox = stack;
                            System.out.println("GRID_SERVERBOX slot=" + slot
                                    + " nonAir=" + countNonAir(container));
                        }
                        break;
                    }
                }
            }
        });
        HudRenderCallback.EVENT.register((context, tickCounter) -> {
            class_1799 source = serverBox != null ? serverBox : box;
            if (source == null) {
                return;
            }
            if (!hudStarted) {
                hudStarted = true;
                System.out.println("GRID_HUD_START source="
                        + (source == serverBox ? "server" : "client"));
            }
            hudFrames++;
            if (source == box) {
                // The server inventory sync applies component patches to the very same stack
                // object, wiping the client-side CONTAINER value; re-apply it every frame before
                // building the tooltip (the server-synced box is refreshed by the server).
                class_9288 container = class_9288.method_57493(
                        List.of(new class_1799(class_1802.field_8477, 5)));
                class_9326 components = class_9326.method_57841()
                        .method_57854(class_9334.field_49622, container)
                        .method_57852();
                box.method_57366(components);
            }
            if (hudFrames % 100 == 1) {
                System.out.println("GRID_HUD frame=" + hudFrames
                        + " source=" + (source == serverBox ? "server" : "client")
                        + " nonAir=" + (readContainer(source) instanceof class_9288 c
                                ? countNonAir(c) : -1));
            }
            List<class_2561> lines = source.method_7950(class_1792.class_9635.field_51353,
                    clientPlayer(), class_1836.field_41071);
            Optional<class_5632> data = source.method_32347();
            if (hudFrames % 100 == 1) {
                System.out.println("GRID_HUD frame=" + hudFrames
                        + " lines=" + lines.size()
                        + " data=" + (data.isPresent()
                                ? data.get().getClass().getName() + "/"
                                        + (data.get() instanceof com.misterpemodder.shulkerboxtooltip.impl.tooltip.PreviewTooltipData d
                                                ? d.provider().getClass().getName()
                                                : "-")
                                : "empty"));
            }
            class_332 draw = context;
            draw.method_51437(net.minecraft.class_310.method_1551().field_1772, lines, data, 24, 24);
        });
    }


    private static Object readContainer(class_1799 stack) {
        return stack.method_57353().method_57829(class_9334.field_49622);
    }

    private static int countNonAir(class_9288 container) {
        int nonAir = 0;
        for (class_1799 stack : container.method_59714()) {
            if (!stack.method_7960()) {
                nonAir++;
            }
        }
        return nonAir;
    }

    private static net.minecraft.class_1657 clientPlayer() {
        return net.minecraft.class_310.method_1551().field_1724;
    }
}
