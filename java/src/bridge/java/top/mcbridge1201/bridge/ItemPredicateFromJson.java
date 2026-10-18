package top.mcbridge1201.bridge;

import com.google.gson.JsonElement;
import com.mojang.serialization.DynamicOps;
import java.lang.reflect.Field;
import net.minecraft.class_2073;
import net.minecraft.class_2378;
import net.minecraft.class_5455;
import net.minecraft.class_6903;
import net.minecraft.class_7923;

public final class ItemPredicateFromJson {
    private ItemPredicateFromJson() {}

    @SuppressWarnings({"unchecked", "rawtypes"})
    public static class_2073 fromJson(JsonElement json) {
        try {
            Field f = class_7923.class.getDeclaredField("field_41170");
            f.setAccessible(true);
            Object registries = f.get(null);
            var access = class_5455.method_40302((class_2378) registries);
            DynamicOps<JsonElement> ops = class_6903.method_46632((DynamicOps) com.mojang.serialization.JsonOps.INSTANCE, access);
            var result = class_2073.field_45754.parse(ops, json);
            if (result.result().isPresent()) {
                return (class_2073) result.result().get();
            }
            System.err.println("[mcbridge1201] ItemPredicate.fromJson: codec rejected " + json + " -> " + result.error().map(Object::toString).orElse("?"));
        } catch (Throwable t) {
            System.err.println("[mcbridge1201] registry-aware fromJson failed: " + t);
        }
        return ItemPredicateAny.any();
    }
}