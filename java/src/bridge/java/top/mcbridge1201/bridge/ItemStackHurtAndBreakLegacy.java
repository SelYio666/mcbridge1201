package top.mcbridge1201.bridge;

import java.util.function.Consumer;

import net.minecraft.class_1309;
import net.minecraft.class_1799;
import net.minecraft.class_3218;
import net.minecraft.class_3222;

/**
 * 1.20.1 ItemStack.hurtAndBreak(int, LivingEntity, Consumer) -> 1.21.1
 * hurtAndBreak(int, ServerLevel, ServerPlayer, Consumer).
 *
 * Semantics transcribed from the 1.20.1 body (client-1.20.1 cfz.a(ILbfz;Ljava/util/function/Consumer;)V)
 * and the 1.21.1 body (cuq.a(ILaqu;Laqv;Ljava/util/function/Consumer;)V):
 *
 * - the 1.20.1 version no-ops on the client side and for creative players; the 1.21.1 four-arg
 *   no-ops for non-damageable stacks and for a creative SERVER player, and takes a
 *   {@code @Nullable} ServerPlayer (null = no durability criteria, no stats) - so non-player
 *   entities fall out of the same call with null, matching the 1.20.1 non-player path.
 * - the 1.20.1 consumer receives the LIVING ENTITY (Consumer&lt;T extends LivingEntity&gt;); the
 *   1.21.1 consumer receives the broken Item - the bridge rebinds it so the mod's 1.20.1
 *   lambda keeps receiving the entity it was compiled against.
 * - the enchantment-based amount reduction (Unbreaking) moved from ItemStack.hurt into the
 *   four-arg itself, so calling the four-arg keeps that behaviour.
 *
 * Not verified so far: the ServerPlayer branch (needs a real client; the probe in
 * runs/p255-vein-bridge verifies the null-player path end to end).
 *
 * Suggested by tools/suggest_rules.py (hurtandbreak.callsite, high confidence) for VeinMiner
 * 2.0.7; the runtime trigger is VeinMiner's damageItem during vein mining.
 */
@SuppressWarnings({"unchecked", "rawtypes"})
public final class ItemStackHurtAndBreakLegacy {
    private ItemStackHurtAndBreakLegacy() {
    }

    public static void adapt(class_1799 stack, int amount, class_1309 entity, Consumer onBroken) {
        // 1.20.1 returned early when entity.level() was client side; same shape here.
        if (entity.method_5770() instanceof class_3218 level) {
            class_3222 player = entity instanceof class_3222 serverPlayer ? serverPlayer : null;
            stack.method_7956(amount, level, player, item -> onBroken.accept(entity));
        }
    }
}
