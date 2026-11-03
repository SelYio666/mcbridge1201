package top.mcbridge1201.bridge;

import net.minecraft.class_1792;
import net.minecraft.class_2378;
import net.minecraft.class_2960;
import net.minecraft.class_5321;

import java.util.function.Supplier;

/**
 * Carries registration context across the supplier boundary, so a settings object built inside a
 * lambda can be given the registry key that 1.21.2+ requires.
 *
 * <p>The shape this exists for (measured in runs/p258): ResourcefulLib's
 * {@code FabricRegistryEntry.of(registry, id, supplier)} evaluates {@code supplier.get()} and then
 * registers the result, so the id is only known on the factory's stack - not inside the lambda that
 * builds {@code Item.Settings}.
 *
 * <p>The context is a ThreadLocal, and its lifetime is the whole risk: a leaked id would make the
 * NEXT registration use the wrong key, which corrupts items rather than looking wrong. So the
 * set/restore is entirely inside {@link #getWithKey}, in a {@code try/finally}, and the rule only
 * ever rewrites the supplier call into that method - there is no way for a patched class to set the
 * context and forget to clear it. Nested registrations restore the previous value instead of
 * clearing it.
 */
public final class RegistryKeyContext {
    private RegistryKeyContext() {}

    private record Pending(class_2378<?> registry, class_2960 id) {}

    private static final ThreadLocal<Pending> PENDING = new ThreadLocal<>();

    /**
     * Runs {@code supplier.get()} with the registry context set, restoring the previous context
     * afterwards - including when the supplier throws.
     */
    public static Object getWithKey(Supplier<?> supplier, class_2378<?> registry, class_2960 id) {
        Pending previous = PENDING.get();
        PENDING.set(new Pending(registry, id));
        try {
            return supplier.get();
        } finally {
            if (previous == null) {
                PENDING.remove();
            } else {
                PENDING.set(previous);
            }
        }
    }

    /**
     * Builds settings for whatever is being registered right now.
     *
     * <p>When a context is active the registry key is applied; when it is not, a plain settings
     * object is returned. That makes the rewrite unconditionally safe: a mod that registers some
     * item outside the wrapper still gets exactly the object it asked for.
     */
    @SuppressWarnings({"rawtypes", "unchecked"})
    public static class_1792.class_1793 settings() {
        class_1792.class_1793 settings = new class_1792.class_1793();
        Pending pending = PENDING.get();
        if (pending != null) {
            class_5321 registryKey = (class_5321) pending.registry().method_46765();
            class_5321 key = (class_5321) class_5321.method_29179(registryKey, pending.id());
            settings.method_63686(key);
        }
        return settings;
    }
}
