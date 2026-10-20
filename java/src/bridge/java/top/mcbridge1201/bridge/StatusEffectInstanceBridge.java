package top.mcbridge1201.bridge;

import net.minecraft.class_1291;
import net.minecraft.class_1293;
import net.minecraft.class_1657;
import net.minecraft.class_2960;
import net.minecraft.class_7923;

/** 1.21.1 stores the effect as a RegistryEntry; legacy code expects the StatusEffect itself. */
public final class StatusEffectInstanceBridge {
    private StatusEffectInstanceBridge() {
    }

    public static class_1291 effectType(class_1293 instance) {
        return instance.method_5579().comp_349();
    }

    /** StatusEffects.HUNGER is a RegistryEntry constant on 1.21.1; legacy code wanted the effect. */
    public static class_1291 hunger() {
        return class_7923.field_41174.method_10223(class_2960.method_60655("minecraft", "hunger"));
    }

    public static class_1291 poison() {
        return class_7923.field_41174.method_10223(class_2960.method_60655("minecraft", "poison"));
    }

    public static class_1291 wither() {
        return class_7923.field_41174.method_10223(class_2960.method_60655("minecraft", "wither"));
    }

    /** hasStatusEffect now takes a RegistryEntry; compare by the unwrapped effect instead. */
    public static boolean hasStatusEffect(class_1657 player, class_1291 effect) {
        for (class_1293 instance : player.method_6026()) {
            if (instance.method_5579().comp_349() == effect) {
                return true;
            }
        }
        return false;
    }
}
