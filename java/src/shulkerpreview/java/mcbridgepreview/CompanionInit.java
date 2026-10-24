package mcbridgepreview;

import com.misterpemodder.shulkerboxtooltip.api.provider.PreviewProvider;
import com.misterpemodder.shulkerboxtooltip.api.provider.PreviewProviderRegistry;
import com.misterpemodder.shulkerboxtooltip.impl.provider.PreviewProviderRegistryImpl;

import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.minecraft.class_1792;
import net.minecraft.class_2960;
import net.minecraft.class_7923;

/**
 * Registers the component-first shulker provider over the converted mod's own one. The mod fills
 * the registry from its plugin plugins while its own init runs, which happens after this mod's
 * entrypoint, so the actual registration is deferred to the first client tick — entrypoints are
 * all done by then and the registry is needed only at tooltip time. The registry locks itself
 * outside the mod's own registration window, so unlock around the register call; one register
 * call covers all 17 shulker items because registering the same provider instance twice throws.
 */
public final class CompanionInit implements ClientModInitializer {
    private static final String[] SHULKER_ITEMS = {
            "shulker_box", "white_shulker_box", "orange_shulker_box", "magenta_shulker_box",
            "light_blue_shulker_box", "yellow_shulker_box", "lime_shulker_box", "pink_shulker_box",
            "gray_shulker_box", "light_gray_shulker_box", "cyan_shulker_box", "purple_shulker_box",
            "blue_shulker_box", "brown_shulker_box", "green_shulker_box", "red_shulker_box",
            "black_shulker_box",
    };
    private boolean registered;

    @Override
    public void onInitializeClient() {
        ClientTickEvents.END_CLIENT_TICK.register(client -> {
            if (registered || client.field_1724 == null) {
                return;
            }
            registered = true;
            registerProvider();
        });
    }

    private void registerProvider() {
        PreviewProviderRegistry registry = PreviewProviderRegistry.getInstance();
        class_1792 box = class_7923.field_41178
                .method_10223(class_2960.method_60655("minecraft", "shulker_box"));
        if (box == null) {
            System.out.println("SBT_REGISTRY shulker item not found");
            return;
        }
        PreviewProvider delegate = registry.get(box);
        if (delegate == null) {
            System.out.println("SBT_REGISTRY no delegate provider");
            return;
        }
        class_1792[] items = new class_1792[SHULKER_ITEMS.length];
        int count = 0;
        for (String name : SHULKER_ITEMS) {
            class_1792 item = class_7923.field_41178
                    .method_10223(class_2960.method_60655("minecraft", name));
            if (item != null) {
                items[count++] = item;
            }
        }
        PreviewProviderRegistryImpl impl = (PreviewProviderRegistryImpl) registry;
        impl.setLocked(false);
        try {
            registry.register(class_2960.method_60655("sbtpreview", "component_shulker"),
                    new ComponentPreviewProvider(delegate),
                    java.util.Arrays.copyOf(items, count));
            System.out.println("SBT_REGISTRY delegate=" + delegate.getClass().getName()
                    + " registered=" + count + " now=" + registry.get(box).getClass().getName());
        } catch (RuntimeException e) {
            System.out.println("SBT_REGISTRY register failed: " + e);
        } finally {
            impl.setLocked(true);
        }
    }
}
