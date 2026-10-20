package top.mcbridge1201.bridge;

import java.util.ArrayList;
import java.util.List;

import com.mojang.datafixers.util.Pair;

import net.minecraft.class_1293;
import net.minecraft.class_1792;
import net.minecraft.class_1799;
import net.minecraft.class_4174;
import net.minecraft.class_9334;

/**
 * AppleSkin 2.5.2 still reads food values through 1.20.4-era Item/FoodComponent methods that
 * CenturyBridge replaced with tombstones. In 1.21.1 food moved to the FOOD data component.
 */
public final class AppleSkinFoodBridge {
    private AppleSkinFoodBridge() {
    }

    public static boolean isFood(class_1792 item) {
        return foodComponent(item) != null;
    }

    public static class_4174 foodComponent(class_1792 item) {
        return new class_1799(item).method_57379(class_9334.field_50075, null);
    }

    public static boolean alwaysEdible(class_4174 food) {
        return food != null && food.comp_2493();
    }

    public static int hunger(class_4174 food) {
        return food == null ? 0 : food.comp_2491();
    }

    public static float saturation(class_4174 food) {
        return food == null ? 0.0f : food.comp_2492();
    }

    /** 1.20.1 FoodComponent.getStatusEffects() -> 1.21.1 status effect entries. */
    public static List<Pair<class_1293, Float>> statusEffects(class_4174 food) {
        List<Pair<class_1293, Float>> out = new ArrayList<>();
        if (food != null) {
            for (class_4174.class_9423 entry : food.comp_2495()) {
                out.add(Pair.of(entry.comp_2496(), entry.comp_2497()));
            }
        }
        return out;
    }
}
