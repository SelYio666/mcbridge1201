package top.mcbridge1201.bridge;

import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.concurrent.CompletableFuture;
import java.util.function.BooleanSupplier;

/**
 * Reflection bridge for the private executor field of ServerChunkManager.
 *
 * <p>The vanilla 1.21.1 getChunk path pumps the chunk task queue while waiting for the
 * ChunkResult future: {@code field_18809.method_18857(() -> future.isDone())}. The field's type
 * is a package-private nested class, so a mixin in another package cannot shadow it with the
 * exact descriptor. This helper reads the field and invokes the public queue method reflectively,
 * preserving the vanilla wait semantics without widening access.
 */
public final class ChunkAccessPump {
    private static final Method PUMP;

    static {
        try {
            Class<?> type = Class.forName("net.minecraft.class_3215$class_4212");
            PUMP = type.getMethod("method_18857", BooleanSupplier.class);
        } catch (ReflectiveOperationException e) {
            throw new ExceptionInInitializerError(e);
        }
    }

    private ChunkAccessPump() {}

    public static void pump(Object serverChunkManager, CompletableFuture<?> future) {
        try {
            Field field = null;
            for (Class<?> c = serverChunkManager.getClass(); c != null; c = c.getSuperclass()) {
                try {
                    field = c.getDeclaredField("field_18809");
                    break;
                } catch (NoSuchFieldException ignored) {
                    // inherited field: keep walking
                }
            }
            if (field == null) throw new NoSuchFieldException("field_18809");
            field.setAccessible(true);
            Object executor = field.get(serverChunkManager);
            PUMP.invoke(executor, (BooleanSupplier) future::isDone);
        } catch (ReflectiveOperationException e) {
            throw new RuntimeException("chunk-access pump failed", e);
        }
    }
}
