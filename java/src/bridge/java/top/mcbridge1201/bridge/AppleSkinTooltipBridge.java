package top.mcbridge1201.bridge;

import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.List;

import net.fabricmc.fabric.api.client.item.v1.ItemTooltipCallback;
import net.minecraft.class_1657;
import net.minecraft.class_1799;
import net.minecraft.class_1836;
import net.minecraft.class_2561;

/**
 * AppleSkin 2.5.2 added its tooltip lines through a mixin on the old
 * {@code ItemStack.getTooltip(PlayerEntity, TooltipType)}; that method no longer exists on 1.21.1,
 * so the conversion dropped the mixin entry. This bridge keeps the mod's tooltip handler and
 * registers it through Fabric's current {@code ItemTooltipCallback}.
 */
public final class AppleSkinTooltipBridge {
    private static Object handler;
    private static Method onItemTooltip;

    private AppleSkinTooltipBridge() {
    }

    public static void init() {
        try {
            Class<?> handlerClass = Class.forName("squeek.appleskin.client.TooltipOverlayHandler");
            handler = handlerClass.getDeclaredConstructor().newInstance();
            Field instance = handlerClass.getDeclaredField("INSTANCE");
            instance.setAccessible(true);
            instance.set(null, handler);
            onItemTooltip = handlerClass.getMethod("onItemTooltip", class_1799.class, class_1657.class,
                    class_1836.class, List.class);
            ItemTooltipCallback.EVENT.register(AppleSkinTooltipBridge::onTooltip);
        } catch (Throwable t) {
            t.printStackTrace();
        }
    }

    private static void onTooltip(class_1799 stack, net.minecraft.class_1792.class_9635 context,
                                  class_1836 type, List<class_2561> lines) {
        if (handler == null || onItemTooltip == null) {
            return;
        }
        class_1657 player = net.minecraft.class_310.method_1551().field_1724;
        if (player == null) {
            return;
        }
        try {
            onItemTooltip.invoke(handler, stack, player, type, lines);
        } catch (Throwable t) {
            t.printStackTrace();
        }
    }
}
