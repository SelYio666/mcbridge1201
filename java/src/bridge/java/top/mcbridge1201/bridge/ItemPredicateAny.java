package top.mcbridge1201.bridge;

import java.util.Map;
import java.util.Optional;

import net.minecraft.class_2073;
import net.minecraft.class_2096.class_2100;
import net.minecraft.class_9329;

/** Source twin of the generated "match everything" predicate, for the javac bridge path. */
public final class ItemPredicateAny {
    private ItemPredicateAny() {}

    @SuppressWarnings({"unchecked", "rawtypes"})
    public static class_2073 any() {
        Map sub = Map.of();
        return new class_2073(Optional.empty(), class_2100.field_9708, class_9329.field_49597, sub);
    }
}
