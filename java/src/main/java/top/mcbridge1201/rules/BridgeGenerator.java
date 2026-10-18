package top.mcbridge1201.rules;

import org.objectweb.asm.ClassWriter;
import org.objectweb.asm.MethodVisitor;
import org.objectweb.asm.Opcodes;

/**
 * Generates the small runtime bridge classes that rules redirect into.
 *
 * <p>Hand-written bytecode (ASM) instead of javac: the bridge only needs a constructor
 * call against target-version types, and generating it keeps the tool independent from a
 * game classpath at build time.
 */
public final class BridgeGenerator {
    private BridgeGenerator() {}

    public static final String ITEM_PREDICATE_ANY = "top/mcbridge1201/bridge/ItemPredicateAny";
    public static final String ITEM_PREDICATE_ANY_DESC = "()Lnet/minecraft/class_2073;";

    /**
     * 1.20.1 {@code ItemPredicate.ANY} matched every stack. 1.21.1 made ItemPredicate a
     * record without the constant, so the equivalent is an empty predicate:
     * {@code new ItemPredicate(Optional.empty(), MinMaxBounds.Ints.ANY,
     * DataComponentPredicate.EMPTY, Map.of())}.
     */
    public static byte[] itemPredicateAny() {
        ClassWriter cw = new ClassWriter(ClassWriter.COMPUTE_MAXS);
        cw.visit(Opcodes.V17, Opcodes.ACC_PUBLIC | Opcodes.ACC_FINAL | Opcodes.ACC_SUPER,
                ITEM_PREDICATE_ANY, null, "java/lang/Object", null);

        MethodVisitor init = cw.visitMethod(Opcodes.ACC_PRIVATE, "<init>", "()V", null, null);
        init.visitCode();
        init.visitVarInsn(Opcodes.ALOAD, 0);
        init.visitMethodInsn(Opcodes.INVOKESPECIAL, "java/lang/Object", "<init>", "()V", false);
        init.visitInsn(Opcodes.RETURN);
        init.visitMaxs(0, 0);
        init.visitEnd();

        MethodVisitor any = cw.visitMethod(Opcodes.ACC_PUBLIC | Opcodes.ACC_STATIC, "any",
                ITEM_PREDICATE_ANY_DESC, null, null);
        any.visitCode();
        any.visitTypeInsn(Opcodes.NEW, "net/minecraft/class_2073");
        any.visitInsn(Opcodes.DUP);
        any.visitMethodInsn(Opcodes.INVOKESTATIC, "java/util/Optional", "empty",
                "()Ljava/util/Optional;", false);
        any.visitFieldInsn(Opcodes.GETSTATIC, "net/minecraft/class_2096$class_2100", "field_9708",
                "Lnet/minecraft/class_2096$class_2100;");
        any.visitFieldInsn(Opcodes.GETSTATIC, "net/minecraft/class_9329", "field_49597",
                "Lnet/minecraft/class_9329;");
        any.visitMethodInsn(Opcodes.INVOKESTATIC, "java/util/Map", "of", "()Ljava/util/Map;", true);
        any.visitMethodInsn(Opcodes.INVOKESPECIAL, "net/minecraft/class_2073", "<init>",
                "(Ljava/util/Optional;Lnet/minecraft/class_2096$class_2100;Lnet/minecraft/class_9329;Ljava/util/Map;)V",
                false);
        any.visitInsn(Opcodes.ARETURN);
        any.visitMaxs(0, 0);
        any.visitEnd();

        cw.visitEnd();
        return cw.toByteArray();
    }
}
