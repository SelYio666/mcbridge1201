package probe;

import net.fabricmc.api.ModInitializer;
import net.fabricmc.fabric.api.command.v2.CommandRegistrationCallback;
import net.minecraft.class_1304;
import net.minecraft.class_1309;
import net.minecraft.class_1588;
import net.minecraft.class_1799;
import net.minecraft.class_2561;
import net.minecraft.class_3218;
import net.minecraft.class_2168;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.mojang.brigadier.builder.LiteralArgumentBuilder;

import top.mcbridge1201.bridge.ItemStackHurtAndBreakLegacy;
import top.mcbridge1201.bridge.LivingEntityBroadcastBreakEvent;

/**
 * Runtime probe for the two VeinMiner bridges added in p255. Registers /mcbridge-probe:
 * it finds a summoned zombie (holding a diamond pickaxe) in the overworld, calls the
 * bridges on it and prints assertions to the server log - no client is needed.
 *
 * The bridge classes are loaded from the patched VeinMiner jar that ships in the same
 * mods folder, so this exercises the exact embedded bytecode the patch produces.
 */
public class VeinBridgeProbe implements ModInitializer {
    public static final Logger LOG = LoggerFactory.getLogger("mcbridge-vein-probe");

    @Override
    public void onInitialize() {
        CommandRegistrationCallback.EVENT.register((dispatcher, registryAccess, environment) ->
            dispatcher.register(LiteralArgumentBuilder.<class_2168>literal("mcbridge-probe").executes(ctx -> {
                class_3218 world = ctx.getSource().method_9225();
                class_1588 zombie = null;
                int total = 0;
                for (Object o : world.method_27909()) {
                    total++;
                    if (o instanceof class_1588 z && z.method_6047().method_7947() > 0) {
                        zombie = z;
                        break;
                    }
                }
                LOG.info("PROBE_ENTS total={}", total);
                LOG.info("PROBE_ENTS total={}", total);
                if (zombie == null) {
                    LOG.error("PROBE_RESULT fail=no-zombie");
                    return 0;
                }
                class_1799 stack = zombie.method_6047();
                if (stack.method_7947() == 0) {
                    LOG.error("PROBE_RESULT fail=no-held-item");
                    return 0;
                }
                int beforeDamage = stack.method_7919();
                int beforeCount = stack.method_7947();
                int maxDamage = stack.method_7936();

                // 1. hurt below the max: damage rises, stack survives, 1.20.1 consumer gets the ENTITY
                int[] hurtCalls = {0};
                Object[] hurtArg = {null};
                ItemStackHurtAndBreakLegacy.adapt(stack, 100, zombie, e -> {
                    hurtCalls[0]++;
                    hurtArg[0] = e;
                });
                int afterDamage = stack.method_7919();
                int countAfterHurt = stack.method_7947();
                LOG.info("PROBE_HURT before={} after={} maxDamage={} count={} consumerCalls={} consumerGotEntity={}",
                        beforeDamage, afterDamage, maxDamage, stack.method_7947(), hurtCalls[0], hurtArg[0] == zombie);

                // 2. hurt far past the max: stack breaks (count drops), consumer fires again
                int[] breakCalls = {0};
                Object[] breakArg = {null};
                ItemStackHurtAndBreakLegacy.adapt(stack, maxDamage * 2, zombie, e -> {
                    breakCalls[0]++;
                    breakArg[0] = e;
                });
                LOG.info("PROBE_BREAK countBefore={} countAfter={} consumerCalls={} consumerGotEntity={}",
                        beforeCount, stack.method_7947(), breakCalls[0], breakArg[0] == zombie);

                // 3. broadcastBreakEvent -> onEquippedItemBroken: must not throw
                LivingEntityBroadcastBreakEvent.adapt(zombie, class_1304.field_6173);
                LOG.info("PROBE_BROADCAST ok");

                // 1.20.1 semantics: the consumer fires ONLY when the item actually broke.
                boolean pass = afterDamage == beforeDamage + 100 && countAfterHurt == beforeCount
                        && hurtCalls[0] == 0
                        && breakCalls[0] == 1 && breakArg[0] == zombie && stack.method_7947() == beforeCount - 1;
                LOG.info("PROBE_RESULT pass={}", pass);
                return pass ? 1 : 0;
            })));
    }
}
