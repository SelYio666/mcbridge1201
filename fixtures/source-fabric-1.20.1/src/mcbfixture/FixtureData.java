package mcbfixture;

import net.minecraft.class_1799;
import net.minecraft.class_2487;

/**
 * Item NBT read/write. 1.20.5 adds a RegistryWrapper.WrapperLookup parameter to these methods,
 * which is one of the first breaks a 1.20.1 source hits on the way to 1.21.x. The fixture keeps
 * the 1.20.1 one-argument shape so a conversion either adapts the signature or fails loudly.
 */
public final class FixtureData {
    private FixtureData() {
    }

    /** Returns a copy of the stack's tag, or an empty tag: a read must not mutate the source stack. */
    public static class_2487 snapshot(class_1799 stack) {
        class_2487 tag = stack.method_7969();
        return tag == null ? new class_2487() : tag.method_10553();
    }

    public static boolean isEmpty(class_1799 stack) {
        return stack.method_7960();
    }
}
