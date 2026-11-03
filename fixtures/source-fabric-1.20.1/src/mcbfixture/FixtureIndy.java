package mcbfixture;

import java.util.List;
import java.util.function.Supplier;
import java.util.stream.Collectors;

/**
 * invokedynamic coverage: a lambda that captures an argument, a method reference, an indy string
 * concatenation and a stream chain. Conversion paths that rewrite call sites or method bodies have
 * to keep the bootstrap methods and their argument lists intact.
 */
public final class FixtureIndy {
    private FixtureIndy() {
    }

    public static Supplier<String> lazyPath(net.minecraft.class_2960 id) {
        return () -> id.method_12832();
    }

    public static List<String> labels(List<net.minecraft.class_1799> stacks) {
        return stacks.stream().map(FixtureIndy::label).collect(Collectors.toList());
    }

    private static String label(net.minecraft.class_1799 stack) {
        return "stack:" + stack.method_7947();
    }

    public static String describe(List<String> labels) {
        return String.join(",", labels);
    }
}
