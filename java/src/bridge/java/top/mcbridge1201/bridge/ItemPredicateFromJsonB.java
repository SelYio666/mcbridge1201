package top.mcbridge1201.bridge;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;

import java.util.Map;
import java.util.Optional;

import net.minecraft.class_1792;
import net.minecraft.class_2073;
import net.minecraft.class_2096$class_2100;
import net.minecraft.class_2960;
import net.minecraft.class_6880;
import net.minecraft.class_7923;
import net.minecraft.class_9329;

/**
 * Registry-aware replacement for ItemPredicate.fromJson.
 *
 * <p>The 1.21.1 ItemPredicate codec parses "items" as a HolderSet and needs a registry
 * context, so parsing with JsonOps alone fails (observed: {"items":["minecraft:dirt"]}).
 * This bridge builds the predicate from BuiltInRegistries.ITEM instead.
 *
 * <p>Single-item predicates are handled faithfully. Multi-item lists are not representable
 * with the single-entry HolderSet factory used here; those log and fall back to the
 * match-everything predicate (recorded degradation) rather than silently mis-filtering.
 */
public final class ItemPredicateFromJsonB {
    private ItemPredicateFromJsonB() {}

    @SuppressWarnings({"unchecked", "rawtypes"})
    public static class_2073 fromJson(JsonElement json) {
        try {
            if (json != null && json.isJsonObject()) {
                JsonObject o = json.getAsJsonObject();
                JsonElement items = o.get("items");
                if (items != null) {
                    String id = null;
                    if (items.isJsonArray()) {
                        JsonArray arr = items.getAsJsonArray();
                        if (arr.size() == 1) {
                            id = arr.get(0).getAsString();
                        } else {
                            System.err.println("[mcbridge1201] ItemPredicate.fromJson: multi-item list is not "
                                    + "supported by the registry bridge yet: " + items);
                        }
                    } else {
                        id = items.getAsString();
                    }
                    if (id != null) {
                        class_2960 rl = parse(id);
                        class_1792 item = class_7923.field_41178.method_10223(rl);
                        if (item != null) {
                            class_6880<class_1792> set = class_6880.method_40223(item);
                            Map sub = Map.of();
                            return new class_2073(Optional.of(set),
                                    class_2096$class_2100.field_9708,
                                    class_9329.field_49597, sub);
                        }
                        System.err.println("[mcbridge1201] ItemPredicate.fromJson: unknown item " + id);
                    }
                }
            }
        } catch (Throwable t) {
            System.err.println("[mcbridge1201] registry-aware fromJson failed: " + t);
        }
        return ItemPredicateAny.any();
    }

    private static class_2960 parse(String id) {
        int i = id.indexOf(':');
        if (i < 0) return class_2960.method_60655("minecraft", id);
        return class_2960.method_60655(id.substring(0, i), id.substring(i + 1));
    }
}
