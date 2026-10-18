package top.mcbridge1201.bridge;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;

import net.minecraft.class_1792;
import net.minecraft.class_2073;
import net.minecraft.class_2096.class_2100;
import net.minecraft.class_2960;
import net.minecraft.class_6880;
import net.minecraft.class_6885;
import net.minecraft.class_7923;
import net.minecraft.class_9329;

/**
 * Registry-aware replacement for ItemPredicate.fromJson (compiled against the 1.21.1
 * intermediary stub and embedded by the patch step).
 *
 * <p>The 1.21.1 ItemPredicate codec parses "items" as a HolderSet and needs a registry
 * context, so parsing with JsonOps alone fails (observed: {"items":["minecraft:dirt"]}).
 * This bridge builds the predicate from BuiltInRegistries.ITEM instead, so single and
 * multi item lists both keep their filtering semantics.
 */
public final class ItemPredicateFromJson {
    private ItemPredicateFromJson() {}

    @SuppressWarnings({"unchecked", "rawtypes"})
    public static class_2073 fromJson(JsonElement json) {
        try {
            if (json != null && json.isJsonObject()) {
                JsonObject o = json.getAsJsonObject();
                JsonElement items = o.get("items");
                if (items != null) {
                    List<String> ids = new ArrayList<>();
                    if (items.isJsonArray()) {
                        JsonArray arr = items.getAsJsonArray();
                        for (JsonElement e : arr) ids.add(e.getAsString());
                    } else {
                        ids.add(items.getAsString());
                    }
                    List<class_6880<class_1792>> holders = new ArrayList<>();
                    for (String id : ids) {
                        class_1792 item = class_7923.field_41178.method_10223(parse(id));
                        if (item == null) {
                            System.err.println("[mcbridge1201] ItemPredicate.fromJson: unknown item " + id);
                            continue;
                        }
                        holders.add(class_7923.field_41178.method_40269(item));
                    }
                    if (!holders.isEmpty()) {
                        class_6885<class_1792> set = class_6885.method_40242(holders);
                        Map sub = Map.of();
                        return new class_2073(Optional.of(set), class_2100.field_9708,
                                class_9329.field_49597, sub);
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
