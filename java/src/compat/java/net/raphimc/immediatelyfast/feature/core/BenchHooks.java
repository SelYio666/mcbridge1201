package net.raphimc.immediatelyfast.feature.core;

/** Tiny holder for benchmark instrumentation shared by mixins (kept top-level: Mixin may merge
 * nested classes of interface mixins, which breaks their binary names). */
public final class BenchHooks {
    public static long lastFpsLog;

    private BenchHooks() {
    }
}
