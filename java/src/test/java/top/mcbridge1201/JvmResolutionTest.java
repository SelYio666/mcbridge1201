package top.mcbridge1201;

import org.junit.jupiter.api.Test;
import org.objectweb.asm.ClassWriter;
import org.objectweb.asm.MethodVisitor;
import org.objectweb.asm.Opcodes;

import java.lang.reflect.InvocationTargetException;
import java.net.URL;
import java.net.URLClassLoader;
import java.nio.file.Files;
import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertInstanceOf;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.junit.jupiter.api.Assumptions.assumeTrue;

/**
 * Asks the JVM itself whether a stale descriptor still resolves.
 *
 * <p>The static analyser reports {@code descMismatch} when a member exists with a different
 * descriptor. A report is a claim; this test settles it. JVMS 5.4.3.2 (field resolution) and
 * 5.4.3.3 (method resolution) require the <em>name and descriptor</em> to match - a subtype is not
 * good enough at resolution time, even though the verifier would accept the value afterwards.
 *
 * <p>So this test builds tiny classes that reference the 1.20.1 descriptors and runs them against
 * the 1.21.4 stub:
 *
 * <ul>
 *   <li>old field descriptor -&gt; NoSuchFieldError,</li>
 *   <li>old method descriptor -&gt; NoSuchMethodError,</li>
 *   <li>the target descriptor -&gt; no linkage error (control).</li>
 * </ul>
 *
 * <p>It needs {@code work/target/client-1.21.4-intermediary.jar}; without it the test skips
 * instead of pretending. This is the only way in this repository to check runtime linkage without
 * launching Minecraft.
 */
class JvmResolutionTest {
    private static final String ITEM_RESULT = "net/minecraft/class_1269";
    private static final String SUCCESS_FIELD = "field_21466";
    private static final String PROPERTY = "net/minecraft/class_2769";
    private static final String VALUES_METHOD = "method_11898";

    private static Path stub() {
        for (Path candidate : new Path[]{
                Path.of("..", "work", "target", "client-1.21.4-intermediary.jar"),
                Path.of("work", "target", "client-1.21.4-intermediary.jar")}) {
            if (Files.isRegularFile(candidate)) {
                return candidate;
            }
        }
        return null;
    }

    private static final class ByteLoader extends ClassLoader {
        ByteLoader(URL stub) {
            super(new URLClassLoader(new URL[]{stub}, ClassLoader.getPlatformClassLoader()));
        }

        Class<?> define(String name, byte[] bytes) {
            return defineClass(name, bytes, 0, bytes.length);
        }
    }

    /** Builds a class whose {@code run()} performs one field or method reference. */
    private static byte[] probeField(String owner, String name, String desc) {
        ClassWriter cw = new ClassWriter(ClassWriter.COMPUTE_FRAMES);
        cw.visit(Opcodes.V17, Opcodes.ACC_PUBLIC, "probe/Run", null, "java/lang/Object", null);
        MethodVisitor mv = cw.visitMethod(Opcodes.ACC_PUBLIC | Opcodes.ACC_STATIC, "run", "()V",
                null, null);
        mv.visitCode();
        mv.visitFieldInsn(Opcodes.GETSTATIC, owner, name, desc);
        mv.visitInsn(Opcodes.POP);
        mv.visitInsn(Opcodes.RETURN);
        mv.visitMaxs(0, 0);
        mv.visitEnd();
        cw.visitEnd();
        return cw.toByteArray();
    }

    /**
     * {@code run(Object receiver)} casts to the owner and calls the member. Resolution happens
     * before the call, so a stale descriptor fails with NoSuchMethodError instead of a
     * NullPointerException - we pass null on purpose and look only at which error arrives.
     */
    private static byte[] probeMethod(String owner, String name, String desc) {
        ClassWriter cw = new ClassWriter(ClassWriter.COMPUTE_FRAMES);
        cw.visit(Opcodes.V17, Opcodes.ACC_PUBLIC, "probe/Run", null, "java/lang/Object", null);
        MethodVisitor mv = cw.visitMethod(Opcodes.ACC_PUBLIC | Opcodes.ACC_STATIC, "run",
                "(Ljava/lang/Object;)V", null, null);
        mv.visitCode();
        mv.visitVarInsn(Opcodes.ALOAD, 0);
        mv.visitTypeInsn(Opcodes.CHECKCAST, owner);
        mv.visitMethodInsn(Opcodes.INVOKEVIRTUAL, owner, name, desc, false);
        mv.visitInsn(Opcodes.POP);
        mv.visitInsn(Opcodes.RETURN);
        mv.visitMaxs(0, 0);
        mv.visitEnd();
        cw.visitEnd();
        return cw.toByteArray();
    }

    private static Throwable run(byte[] bytes) throws Exception {
        Path stub = stub();
        ByteLoader loader = new ByteLoader(stub.toUri().toURL());
        Class<?> cls = loader.define("probe.Run", bytes);
        try {
            try {
                cls.getMethod("run").invoke(null);
            } catch (NoSuchMethodException noArgs) {
                // The method probe takes a receiver; null is fine, resolution comes first.
                cls.getMethod("run", Object.class).invoke(null, (Object) null);
            }
            return null;
        } catch (InvocationTargetException e) {
            return e.getCause();
        }
    }

    @Test
    void staleFieldDescriptorFailsAtResolution() throws Exception {
        assumeTrue(stub() != null, "no 1.21.4 stub in work/target");
        // 1.20.1: field_21466 was declared as class_1269; 1.21.4 declares it as class_1269$class_9860.
        Throwable cause = run(probeField(ITEM_RESULT, SUCCESS_FIELD, "L" + ITEM_RESULT + ";"));
        assertInstanceOf(NoSuchFieldError.class, cause,
                "a field whose type changed must fail resolution, subtype or not: " + cause);
    }

    @Test
    void targetFieldDescriptorResolves() throws Exception {
        assumeTrue(stub() != null, "no 1.21.4 stub in work/target");
        // The 1.21.4 declaration of the same field.
        Throwable cause = run(probeField(ITEM_RESULT, SUCCESS_FIELD,
                "L" + ITEM_RESULT + "$class_9860;"));
        assertTrue(cause == null || !(cause instanceof NoSuchFieldError),
                "the target descriptor must resolve: " + cause);
    }

    @Test
    void staleMethodDescriptorFailsAtResolution() throws Exception {
        assumeTrue(stub() != null, "no 1.21.4 stub in work/target");
        // 1.20.1 Property#values returned Collection; 1.21.4 returns List. Same name, new descriptor.
        Throwable cause = run(probeMethod(PROPERTY, VALUES_METHOD, "()Ljava/util/Collection;"));
        assertInstanceOf(NoSuchMethodError.class, cause,
                "a method whose return type changed must fail resolution: " + cause);
    }

    @Test
    void targetMethodDescriptorResolves() throws Exception {
        assumeTrue(stub() != null, "no 1.21.4 stub in work/target");
        Throwable cause = run(probeMethod(PROPERTY, VALUES_METHOD, "()Ljava/util/List;"));
        assertTrue(cause == null || !(cause instanceof NoSuchMethodError),
                "the target descriptor must resolve: " + cause);
    }
}
