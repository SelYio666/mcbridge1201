package top.mcbridge1201.bridge;

import java.util.List;

import net.minecraft.class_1730;
import net.minecraft.class_1792;
import net.minecraft.class_1799;
import net.minecraft.class_2487;
import net.minecraft.class_2499;
import net.minecraft.class_2520;
import net.minecraft.class_2960;
import net.minecraft.class_7923;
import net.minecraft.class_9288;
import net.minecraft.class_9334;

/**
 * ShulkerBoxTooltip 4.0.4 still reads the 1.20.x "BlockEntityTag.Items" NBT of a stack through
 * tombstones. 1.21.1 stores the same data in the CONTAINER component, but the mod's preview code
 * still expects the old compound shape, so this bridge renders the component back into that shape
 * and parses item compounds back into ItemStacks.
 */
public final class ShulkerBoxNbtBridge {
    private ShulkerBoxNbtBridge() {
    }

    public static class_2487 legacyBlockEntityTag(class_1799 stack, String key) {
        if (!"BlockEntityTag".equals(key)) {
            return null;
        }
        // method_57379(type, value) is ItemStack.set and would clear the component; read through
        // getComponents() (method_57353) instead.
        Object component = stack.method_57353().method_57829(class_9334.field_49622);
        if (!(component instanceof class_9288 container)) {
            return null;
        }
        class_2487 tag = new class_2487();
        class_2499 items = new class_2499();
        int slot = 0;
        for (class_1799 s : container.method_59714()) {
            if (s != null && !s.method_7960()) {
                class_2487 entry = new class_2487();
                entry.method_10569("Slot", slot);
                entry.method_10582("id",
                        class_7923.field_41178.method_10221(s.method_7909()).toString());
                entry.method_10569("Count", s.method_7947());
                items.add(entry);
            }
            slot++;
        }
        tag.method_10566("Items", items);
        return tag;
    }

    public static class_1799 legacyFromNbt(class_2487 compound) {
        String id = compound.method_10558("id");
        int count = compound.method_10550("Count");
        int colon = id.indexOf(':');
        class_2960 key = colon >= 0
                ? class_2960.method_60655(id.substring(0, colon), id.substring(colon + 1))
                : class_2960.method_60655("minecraft", id);
        class_1792 item = class_7923.field_41178.method_10223(key);
        return new class_1799(item, Math.max(1, count));
    }

    /** Kept for callers that used the old getNbt() to inspect anything but the container. */
    public static class_2487 legacyNbt(class_1799 stack) {
        return legacyBlockEntityTag(stack, "BlockEntityTag");
    }

    /** 1.21.1 has no ItemStack.setNbt(NbtCompound); the preview renderer only snapshots it. */
    public static void setLegacyNbt(class_1799 stack, class_2487 tag) {
    }

    /** 1.20.1 EnderChestInventory.writeNbt() -> Slot/id/Count list (1.21.1 needs RegistryOps). */
    public static class_2499 writeEnderChest(class_1730 inventory) {
        class_2499 items = new class_2499();
        for (int slot = 0; slot < inventory.method_5439(); slot++) {
            class_1799 stack = inventory.method_5438(slot);
            if (stack == null || stack.method_7960()) {
                continue;
            }
            class_2487 entry = new class_2487();
            entry.method_10569("Slot", slot);
            entry.method_10582("id",
                    class_7923.field_41178.method_10221(stack.method_7909()).toString());
            entry.method_10569("Count", stack.method_7947());
            items.add(entry);
        }
        return items;
    }

    /** 1.20.1 EnderChestInventory.readNbt(NbtList) -> fill the inventory from Slot/id/Count. */
    public static void readEnderChest(class_1730 inventory, class_2499 items) {
        for (class_2520 element : items) {
            if (!(element instanceof class_2487 entry)) {
                continue;
            }
            int slot = entry.method_10550("Slot");
            String id = entry.method_10558("id");
            int count = entry.method_10550("Count");
            int colon = id.indexOf(':');
            class_2960 key = colon >= 0
                    ? class_2960.method_60655(id.substring(0, colon), id.substring(colon + 1))
                    : class_2960.method_60655("minecraft", id);
            inventory.method_5447(slot,
                    new class_1799(class_7923.field_41178.method_10223(key), Math.max(1, count)));
        }
    }

    static List<class_1799> ignored() {
        return List.of();
    }
}
