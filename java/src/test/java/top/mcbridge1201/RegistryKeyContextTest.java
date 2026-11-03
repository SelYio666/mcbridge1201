package top.mcbridge1201;

import org.junit.jupiter.api.Test;

import java.lang.reflect.Field;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.net.URL;
import java.net.URLClassLoader;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;
import java.util.function.Supplier;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.junit.jupiter.api.Assumptions.assumeTrue;

/**
 * Checks the one thing that would corrupt items rather than merely look wrong: the lifetime of the
 * pending registry id in {@code RegistryKeyContext}.
 *
 * <p>The context is a ThreadLocal set around a mod's supplier call. If it leaks, the NEXT
 * registration gets the previous mod's id - so these cases are about cleanup, not about whether a
 * key is produced:
 *
 * <ul>
 *   <li>visible while the supplier runs, gone afterwards;</li>
 *   <li>gone even when the supplier throws (the whole reason the set is inside try/finally);</li>
 *   <li>nested registrations see the inner id and restore the outer one, instead of clearing;</li>
 *   <li>two threads do not see each other's context.</li>
 * </ul>
 *
 * <p>It loads the compiled bridge plus the 1.21.4 stub through a URLClassLoader, so it needs
 * {@code work/targets/fabric-1.21.4/bridges} and the stub; without them it skips rather than
 * pretending.
 */
class RegistryKeyContextTest {
    private static final String BRIDGE = "top.mcbridge1201.bridge.RegistryKeyContext";

    @FunctionalInterface
    interface Checked<T> {
        T get() throws Exception;
    }

    private static <T> Supplier<T> unchecked(Checked<T> body) {
        return () -> {
            try {
                return body.get();
            } catch (RuntimeException e) {
                throw e;
            } catch (Exception e) {
                throw new RuntimeException(e);
            }
        };
    }

    private static Path bridgeDir() {
        for (Path p : new Path[]{Path.of("..", "work", "targets", "fabric-1.21.4", "bridges"),
                Path.of("work", "targets", "fabric-1.21.4", "bridges")}) {
            if (Files.isDirectory(p)) {
                return p;
            }
        }
        return null;
    }

    private static Path stub() {
        for (Path p : new Path[]{Path.of("..", "work", "target", "client-1.21.4-intermediary.jar"),
                Path.of("work", "target", "client-1.21.4-intermediary.jar")}) {
            if (Files.isRegularFile(p)) {
                return p;
            }
        }
        return null;
    }

    /** Every jar under work/target/libs-1214 - class_2378 extends Keyable, which lives in DFU. */
    private static List<URL> libUrls() throws Exception {
        List<URL> urls = new ArrayList<>();
        for (Path base : new Path[]{Path.of("..", "work", "target", "libs-1214"),
                Path.of("work", "target", "libs-1214")}) {
            if (!Files.isDirectory(base)) {
                continue;
            }
            try (var walk = Files.walk(base)) {
                walk.filter(p -> p.toString().endsWith(".jar"))
                        .forEach(p -> {
                            try {
                                urls.add(p.toUri().toURL());
                            } catch (Exception ignored) {
                                // unreadable path: skip it, the test will fail loudly if needed
                            }
                        });
            }
            if (!urls.isEmpty()) {
                return urls;
            }
        }
        return urls;
    }

    private static boolean available() {
        return bridgeDir() != null && stub() != null;
    }

    private static final class Ctx {
        final Class<?> bridge;
        final Object registry;
        final Method getWithKey;
        final ThreadLocal<?> pending;

        Ctx() throws Exception {
            List<URL> all = new ArrayList<>(libUrls());
            all.add(bridgeDir().toUri().toURL());
            all.add(stub().toUri().toURL());
            ClassLoader cl = new URLClassLoader(all.toArray(new URL[0]),
                    ClassLoader.getPlatformClassLoader());
            bridge = cl.loadClass(BRIDGE);
            // A Registry instance is not needed to test the ThreadLocal: only settings() reads it,
            // and this test never calls that. BuiltInRegistries cannot even be initialised here
            // (it needs a running game), which is why an earlier version of this test failed with
            // ExceptionInInitializerError.
            registry = null;
            getWithKey = bridge.getMethod("getWithKey", Supplier.class,
                    cl.loadClass("net.minecraft.class_2378"), cl.loadClass("net.minecraft.class_2960"));
            Field f = bridge.getDeclaredField("PENDING");
            f.setAccessible(true);
            pending = (ThreadLocal<?>) f.get(null);
        }

        Object id(String path) throws Exception {
            Class<?> identifier = Class.forName("net.minecraft.class_2960", true,
                    bridge.getClassLoader());
            // 1.21.4 made the constructor private; method_60655 is Identifier.of(namespace, path).
            return identifier.getMethod("method_60655", String.class, String.class)
                    .invoke(null, "compatprobe", path);
        }

        /** Runs one supplier inside the context and returns what the context looked like there. */
        Object run(Object id, Supplier<Object> supplier) throws Exception {
            try {
                return getWithKey.invoke(null, supplier, registry, id);
            } catch (InvocationTargetException e) {
                Throwable cause = e.getCause();
                if (cause instanceof RuntimeException re) {
                    throw re;
                }
                throw new RuntimeException(cause);
            }
        }
    }

    private static String currentId(Object pendingValue) {
        if (pendingValue == null) {
            return null;
        }
        try {
            Method id = pendingValue.getClass().getDeclaredMethod("id");
            id.setAccessible(true);
            Object identifier = id.invoke(pendingValue);
            Method path = identifier.getClass().getMethod("method_12832");
            return (String) path.invoke(identifier);
        } catch (Exception e) {
            return "<unreadable: " + e + ">";
        }
    }

    @Test
    void contextIsVisibleDuringTheSupplierAndClearedAfter() throws Exception {
        assumeTrue(available(), "needs the compiled bridge and the 1.21.4 stub");
        Ctx ctx = new Ctx();
        AtomicReference<String> during = new AtomicReference<>();
        ctx.run(ctx.id("alpha"), () -> {
            during.set(currentId(ctx.pending.get()));
            return null;
        });
        assertEquals("alpha", during.get(), "the supplier must see the pending id");
        assertNull(ctx.pending.get(), "the context must be gone after the call");
    }

    @Test
    void contextIsClearedWhenTheSupplierThrows() throws Exception {
        assumeTrue(available(), "needs the compiled bridge and the 1.21.4 stub");
        Ctx ctx = new Ctx();
        try {
            ctx.run(ctx.id("beta"), () -> {
                throw new RuntimeException("supplier failed");
            });
        } catch (RuntimeException expected) {
            assertEquals("supplier failed", expected.getMessage());
        }
        assertNull(ctx.pending.get(), "a throwing supplier must not leak the context");
    }

    @Test
    void nestedRegistrationRestoresTheOuterContext() throws Exception {
        assumeTrue(available(), "needs the compiled bridge and the 1.21.4 stub");
        Ctx ctx = new Ctx();
        List<String> seen = new ArrayList<>();
        ctx.run(ctx.id("outer"), unchecked(() -> {
            seen.add("outer:" + currentId(ctx.pending.get()));
            ctx.run(ctx.id("inner"), unchecked(() -> {
                seen.add("inner:" + currentId(ctx.pending.get()));
                return null;
            }));
            seen.add("restored:" + currentId(ctx.pending.get()));
            return null;
        }));
        assertEquals(List.of("outer:outer", "inner:inner", "restored:outer"), seen,
                "the inner call must restore the outer id, not clear it");
        assertNull(ctx.pending.get());
    }

    @Test
    void anotherThreadDoesNotSeeTheContext() throws Exception {
        assumeTrue(available(), "needs the compiled bridge and the 1.21.4 stub");
        Ctx ctx = new Ctx();
        AtomicReference<Object> seenByOtherThread = new AtomicReference<>("never ran");
        ctx.run(ctx.id("main_thread"), unchecked(() -> {
            Thread other = new Thread(() -> seenByOtherThread.set(ctx.pending.get()));
            other.start();
            other.join(5000);
            return null;
        }));
        // The context belongs to the thread that registered; a second thread must see nothing,
        // which is what stops two mods initialising in parallel from swapping registry ids.
        assertNull(seenByOtherThread.get(),
                "another thread must not see this thread's context, saw: " + seenByOtherThread.get());
    }
}
