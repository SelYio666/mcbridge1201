package top.mcbridge1201.bridge;

import net.minecraft.class_1304;
import net.minecraft.class_1309;
import net.minecraft.class_1799;

/**
 * 1.20.1 LivingEntity.broadcastBreakEvent(EquipmentSlot) -> 1.21.1
 * LivingEntity.onEquippedItemBroken(Item, EquipmentSlot).
 *
 * Both bodies are the same broadcast: level().broadcastEntityEvent(this, (byte) slotEventId) -
 * the 1.21.1 version adds an Item parameter that its own body never reads (verified by
 * disassembling btn.a(Lcul;Lbsy;)V), so the bridge fills it with the item currently equipped
 * in that slot, which is exactly what the 1.20.1 caller would have broadcast for.
 *
 * Mods reference the method through a subclass receiver (VeinMiner calls Player.method_20235),
 * so the bridge takes the receiver as a LivingEntity - INVOKESTATIC accepts the subclass.
 *
 * Suggested by tools/suggest_rules.py (broadcastbreakevent.callsite) for VeinMiner 2.0.7;
 * the suggester's declaration-class fallback found the call is an instance method declared on
 * LivingEntity even though the mod's constant pool names Player as the owner.
 */
public final class LivingEntityBroadcastBreakEvent {
    private LivingEntityBroadcastBreakEvent() {
    }

    public static void adapt(class_1309 entity, class_1304 slot) {
        class_1799 stack = entity.method_6118(slot);
        entity.method_20235(stack.method_7909(), slot);
    }
}
