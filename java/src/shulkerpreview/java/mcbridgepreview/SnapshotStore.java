package mcbridgepreview;

import java.util.Collections;
import java.util.Map;
import java.util.WeakHashMap;

import net.minecraft.class_1799;

/**
 * Snapshot store for the shulker preview path. The stack that reaches getTooltipData can be a
 * stripped copy of the hovered stack, so the companion snapshots every stack at the start of
 * getTooltip and the provider prefers the snapshot's component over the live stack's. Lives in
 * the non-mixin package because mixin classes must not be referenced from ordinary code.
 */
public final class SnapshotStore {
    private static final Map<class_1799, class_1799> SNAPSHOTS =
            Collections.synchronizedMap(new WeakHashMap<>());

    private SnapshotStore() {
    }

    public static void put(class_1799 live, class_1799 snapshot) {
        SNAPSHOTS.put(live, snapshot);
    }

    public static class_1799 get(class_1799 live) {
        return SNAPSHOTS.get(live);
    }
}
