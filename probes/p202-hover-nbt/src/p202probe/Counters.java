package p202probe;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;

/**
 * Shared counters: the draw mixins write, the probe reads. Kept out of the mixin classes so the
 * probe never has to load a mixin class by name (mixins are only valid on their target).
 */
public final class Counters {
    /** Number of non-empty stacks the client found inside the CONTAINER component. */
    public static int NBT_STACKS;
    /** Number of distinct component maps among those stacks (heterogeneity, computed not claimed). */
    public static int NBT_DISTINCT;

    public static int DRAW_ITEMS_CALLS;
    public static int DRAW_ITEM_CALLS;
    public static volatile String LAST_TYPE = "none";

    /** One key per drawItem call: index + item + count + component map. */
    public static final Set<String> DRAWN_KEYS = Collections.synchronizedSet(new LinkedHashSet<>());
    /** Component maps only, so distinct payloads can be counted. */
    public static final Set<String> DRAWN_DISTINCT =
            Collections.synchronizedSet(new LinkedHashSet<>());
    /** Same, but empty stacks excluded: the grid pads unused cells with air. */
    public static final Set<String> DRAWN_DISTINCT_NONAIR =
            Collections.synchronizedSet(new LinkedHashSet<>());
    /** Item ids drawn, non-empty only. */
    public static final Set<String> DRAWN_ITEMS =
            Collections.synchronizedSet(new LinkedHashSet<>());
    public static final List<String> DRAWN_ORDER =
            Collections.synchronizedList(new ArrayList<>());

    private Counters() {
    }
}
