package top.mcbridge1201.bridge;

import java.util.HashMap;
import java.util.Map;

import net.minecraft.class_1792;
import net.minecraft.class_1799;
import net.minecraft.class_1887;
import net.minecraft.class_1890;
import net.minecraft.class_2680;
import net.minecraft.class_9304;

/** FallingTree tombstone bridges: enchantment map and mining speed. */
public final class FallingTreeBridge {
    private FallingTreeBridge() {
    }

    /** 1.20.1 EnchantmentHelper.get(ItemStack) -> Map<Enchantment,Integer>. */
    public static Map<class_1887, Integer> enchantments(class_1799 stack) {
        Map<class_1887, Integer> out = new HashMap<>();
        class_9304 component = class_1890.method_57532(stack);
        if (component != null) {
            for (var entry : component.method_57539()) {
                out.put(entry.getKey().comp_349(), entry.getIntValue());
            }
        }
        return out;
    }

    /** 1.20.1 Item.getMiningSpeedMultiplier(ItemStack, BlockState); renamed to method_58404. */
    public static float miningSpeed(class_1792 item, class_1799 stack, class_2680 state) {
        return item.method_58404(stack, state);
    }

    /** 1.20.1 ItemStack.damage(int, LivingEntity, Consumer); 1.21.1 uses damage(int, LivingEntity, EquipmentSlot). */
    public static void damage(class_1799 stack, int amount, net.minecraft.class_1309 entity,
                              java.util.function.Consumer<net.minecraft.class_1792> unused) {
        stack.method_7970(amount, entity, net.minecraft.class_1304.field_6174);
    }
}
