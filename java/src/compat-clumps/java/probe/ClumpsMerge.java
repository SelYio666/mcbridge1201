package probe;

import java.lang.reflect.Field;
import java.util.ArrayList;
import java.util.List;

import net.fabricmc.api.ModInitializer;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;
import net.minecraft.class_1297;
import net.minecraft.class_1303;
import net.minecraft.class_3218;

/**
 * Companion bridge for the converted Clumps 12.0.0.4.
 *
 * <p>The converter removed MixinExperienceOrb (load-bearing), so converted Clumps no longer merges
 * orbs. This module re-implements Clumps' merge on the server tick: orbs within a 2 block radius are
 * combined by writing the summed value into the survivor and discarding the other orb.
 *
 * <p>Vanilla canMerge is deliberately not used: 1.21.1 only merges orbs that have the same value and
 * the same 40-tick age phase, which is exactly the restriction Clumps removes. Vanilla merge() is
 * not used either — it does not add values.
 *
 * <p>Install this jar next to the converted Clumps jar. It is server-side; no client install is
 * required.
 */
public final class ClumpsMerge implements ModInitializer {
    private static final double MERGE_RADIUS_SQ = 4.0;

    private Field valueField;
    private int ticks;

    @Override
    public void onInitialize() {
        try {
            valueField = class_1303.class.getDeclaredField("field_6159");
            valueField.setAccessible(true);
        } catch (ReflectiveOperationException e) {
            throw new RuntimeException("experience orb value field is missing", e);
        }
        ServerTickEvents.END_SERVER_TICK.register(server -> {
            if (++ticks % 20 != 0) {
                return;
            }
            for (class_3218 world : server.method_3738()) {
                List<class_1303> orbs = new ArrayList<>();
                for (class_1297 e : world.method_27909()) {
                    if (e instanceof class_1303 orb) {
                        orbs.add(orb);
                    }
                }
                boolean[] dead = new boolean[orbs.size()];
                for (int i = 0; i < orbs.size(); i++) {
                    if (dead[i]) {
                        continue;
                    }
                    for (int j = i + 1; j < orbs.size(); j++) {
                        if (dead[j]) {
                            continue;
                        }
                        class_1303 a = orbs.get(i);
                        class_1303 b = orbs.get(j);
                        double dx = a.method_23317() - b.method_23317();
                        double dy = a.method_23318() - b.method_23318();
                        double dz = a.method_23321() - b.method_23321();
                        if (dx * dx + dy * dy + dz * dz > MERGE_RADIUS_SQ) {
                            continue;
                        }
                        try {
                            int sum = a.method_5919() + b.method_5919();
                            valueField.setInt(a, sum < 0 ? Integer.MAX_VALUE : sum);
                        } catch (IllegalAccessException e) {
                            throw new RuntimeException("orb value write failed", e);
                        }
                        b.method_31472();
                        dead[j] = true;
                    }
                }
            }
        });
    }
}
