package top.mcbridge1201.rules;

import org.objectweb.asm.ClassWriter;
import org.objectweb.asm.MethodVisitor;
import org.objectweb.asm.Opcodes;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/**
 * Generates the small runtime bridge classes that rules redirect into.
 *
 * <p>Hand-written bytecode (ASM) instead of javac: the bridges only call target-version
 * types, and generating them keeps the tool independent from a game classpath at build time.
 */
public final class BridgeGenerator {
    private BridgeGenerator() {}

    public static final String ITEM_PREDICATE_ANY = "top/mcbridge1201/bridge/ItemPredicateAny";
    public static final String ITEM_PREDICATE_ANY_DESC = "()Lnet/minecraft/class_2073;";

    public static final String CODEC_DISPATCH = "top/mcbridge1201/bridge/CodecDispatch";
    public static final String CODEC_DISPATCH_ADAPTER = "top/mcbridge1201/bridge/CodecDispatch$Adapter";
    public static final String CODEC_DISPATCH_GUARD = "top/mcbridge1201/bridge/CodecDispatch$Guard";
    public static final String ITEM_PREDICATE_FROM_JSON = "top/mcbridge1201/bridge/ItemPredicateFromJson";
    public static final String IDENTIFIER_FACTORY = "top/mcbridge1201/bridge/IdentifierFactory";

    private static final String CODEC = "com/mojang/serialization/Codec";
    private static final String MAP_CODEC = "com/mojang/serialization/MapCodec";
    private static final String FUNCTION = "java/util/function/Function";

    /** Bridge classes this generator can emit. Everything else must be supplied as javac output. */
    public static boolean isGenerated(String name) {
        return ITEM_PREDICATE_ANY.equals(name)
                || CODEC_DISPATCH.equals(name)
                || ITEM_PREDICATE_FROM_JSON.equals(name)
                || IDENTIFIER_FACTORY.equals(name);
    }

    /** All classes that must be embedded when the given bridge names are used. */
    public static Map<String, byte[]> generate(Set<String> used) {
        Map<String, byte[]> out = new LinkedHashMap<>();
        if (used.contains(ITEM_PREDICATE_ANY)) {
            out.put(ITEM_PREDICATE_ANY, itemPredicateAny());
        }
        if (used.contains(CODEC_DISPATCH)) {
            out.put(CODEC_DISPATCH, codecDispatch());
            out.put(CODEC_DISPATCH_ADAPTER, codecDispatchAdapter());
            out.put(CODEC_DISPATCH_GUARD, codecDispatchGuard());
        }
        if (used.contains(ITEM_PREDICATE_FROM_JSON)) {
            out.put(ITEM_PREDICATE_FROM_JSON, itemPredicateFromJson());
            // the fromJson bridge falls back to the generated "any" predicate
            out.put(ITEM_PREDICATE_ANY, itemPredicateAny());
        }
        if (used.contains(IDENTIFIER_FACTORY)) {
            out.put(IDENTIFIER_FACTORY, identifierFactory());
        }
        for (String name : used) {
            if (!out.containsKey(name)) {
                throw new IllegalArgumentException("no generator for bridge " + name);
            }
        }
        return out;
    }

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

    /**
     * 1.21.1 changed {@code Codec.dispatch}'s second function from {@code Codec} to
     * {@code MapCodec}; old call sites return a Codec and crash with
     * {@code MapCodecCodec cannot be cast to MapCodec}. The bridge adapts the value
     * function with {@code MapCodec.assumeMapUnsafe}.
     */
    public static byte[] codecDispatch() {
        ClassWriter cw = new ClassWriter(ClassWriter.COMPUTE_MAXS);
        cw.visit(Opcodes.V17, Opcodes.ACC_PUBLIC | Opcodes.ACC_FINAL | Opcodes.ACC_SUPER,
                CODEC_DISPATCH, null, "java/lang/Object", null);

        MethodVisitor init = cw.visitMethod(Opcodes.ACC_PRIVATE, "<init>", "()V", null, null);
        init.visitCode();
        init.visitVarInsn(Opcodes.ALOAD, 0);
        init.visitMethodInsn(Opcodes.INVOKESPECIAL, "java/lang/Object", "<init>", "()V", false);
        init.visitInsn(Opcodes.RETURN);
        init.visitMaxs(0, 0);
        init.visitEnd();

        MethodVisitor m = cw.visitMethod(Opcodes.ACC_PUBLIC | Opcodes.ACC_STATIC, "dispatch",
                "(L" + CODEC + ";L" + FUNCTION + ";L" + FUNCTION + ";)L" + CODEC + ";", null, null);
        m.visitCode();
        m.visitVarInsn(Opcodes.ALOAD, 0);
        m.visitVarInsn(Opcodes.ALOAD, 1);
        m.visitTypeInsn(Opcodes.NEW, CODEC_DISPATCH_ADAPTER);
        m.visitInsn(Opcodes.DUP);
        m.visitVarInsn(Opcodes.ALOAD, 2);
        m.visitMethodInsn(Opcodes.INVOKESPECIAL, CODEC_DISPATCH_ADAPTER, "<init>",
                "(L" + FUNCTION + ";)V", false);
        m.visitMethodInsn(Opcodes.INVOKEINTERFACE, CODEC, "dispatch",
                "(L" + FUNCTION + ";L" + FUNCTION + ";)L" + CODEC + ";", true);
        m.visitInsn(Opcodes.ARETURN);
        m.visitMaxs(0, 0);
        m.visitEnd();

        cw.visitEnd();
        return cw.toByteArray();
    }

    /**
     * 1.20.1 {@code ItemPredicate.fromJson(JsonElement)} (static) was removed in 1.21.1.
     * Faithful reconstruction: parse the JSON with the target's ItemPredicate.CODEC using
     * JsonOps, exactly how the 1.20.1 implementation was written.
     */
    public static byte[] itemPredicateFromJson() {
        ClassWriter cw = new SafeClassWriter();
        cw.visit(Opcodes.V17, Opcodes.ACC_PUBLIC | Opcodes.ACC_FINAL | Opcodes.ACC_SUPER,
                ITEM_PREDICATE_FROM_JSON, null, "java/lang/Object", null);

        MethodVisitor init = cw.visitMethod(Opcodes.ACC_PRIVATE, "<init>", "()V", null, null);
        init.visitCode();
        init.visitVarInsn(Opcodes.ALOAD, 0);
        init.visitMethodInsn(Opcodes.INVOKESPECIAL, "java/lang/Object", "<init>", "()V", false);
        init.visitInsn(Opcodes.RETURN);
        init.visitMaxs(0, 0);
        init.visitEnd();

        MethodVisitor m = cw.visitMethod(Opcodes.ACC_PUBLIC | Opcodes.ACC_STATIC, "fromJson",
                "(Lcom/google/gson/JsonElement;)Lnet/minecraft/class_2073;", null, null);
        m.visitCode();
        m.visitFieldInsn(Opcodes.GETSTATIC, "net/minecraft/class_2073", "field_45754",
                "Lcom/mojang/serialization/Codec;");
        m.visitFieldInsn(Opcodes.GETSTATIC, "com/mojang/serialization/JsonOps", "INSTANCE",
                "Lcom/mojang/serialization/JsonOps;");
        m.visitVarInsn(Opcodes.ALOAD, 0);
        m.visitMethodInsn(Opcodes.INVOKEINTERFACE, "com/mojang/serialization/Codec", "parse",
                "(Lcom/mojang/serialization/DynamicOps;Ljava/lang/Object;)Lcom/mojang/serialization/DataResult;", true);
        m.visitMethodInsn(Opcodes.INVOKEINTERFACE, "com/mojang/serialization/DataResult", "result",
                "()Ljava/util/Optional;", true);
        m.visitVarInsn(Opcodes.ASTORE, 1);
        m.visitVarInsn(Opcodes.ALOAD, 1);
        m.visitMethodInsn(Opcodes.INVOKEVIRTUAL, "java/util/Optional", "isPresent", "()Z", false);
        var ok = new org.objectweb.asm.Label();
        m.visitJumpInsn(Opcodes.IFNE, ok);
        // VISIBLE diagnostic: a legacy predicate JSON that the 1.21.1 codec rejects must not
        // silently become a match-everything predicate without a log line.
        m.visitFieldInsn(Opcodes.GETSTATIC, "java/lang/System", "err", "Ljava/io/PrintStream;");
        m.visitVarInsn(Opcodes.ALOAD, 0);
        m.visitMethodInsn(Opcodes.INVOKEVIRTUAL, "com/google/gson/JsonElement", "toString",
                "()Ljava/lang/String;", false);
        m.visitMethodInsn(Opcodes.INVOKEVIRTUAL, "java/io/PrintStream", "println", "(Ljava/lang/String;)V", false);
        m.visitFieldInsn(Opcodes.GETSTATIC, "java/lang/System", "err", "Ljava/io/PrintStream;");
        m.visitLdcInsn("[mcbridge1201] ItemPredicate.fromJson: 1.21.1 codec rejected legacy JSON; "
                + "falling back to match-everything predicate (recorded degradation)");
        m.visitMethodInsn(Opcodes.INVOKEVIRTUAL, "java/io/PrintStream", "println", "(Ljava/lang/String;)V", false);
        m.visitMethodInsn(Opcodes.INVOKESTATIC, ITEM_PREDICATE_ANY, "any", ITEM_PREDICATE_ANY_DESC, false);
        m.visitInsn(Opcodes.ARETURN);
        m.visitLabel(ok);
        m.visitVarInsn(Opcodes.ALOAD, 1);
        m.visitMethodInsn(Opcodes.INVOKEVIRTUAL, "java/util/Optional", "get", "()Ljava/lang/Object;", false);
        m.visitTypeInsn(Opcodes.CHECKCAST, "net/minecraft/class_2073");
        m.visitInsn(Opcodes.ARETURN);
        m.visitMaxs(0, 0);
        m.visitEnd();

        cw.visitEnd();
        return cw.toByteArray();
    }

    /**
     * 1.21.1 made {@code Identifier(String,String)} private; the public factory is
     * {@code Identifier.of(namespace, path)}. Constructor redirects replace
     * {@code new Identifier(a,b)} with this call.
     */
    public static byte[] identifierFactory() {
        ClassWriter cw = new ClassWriter(ClassWriter.COMPUTE_MAXS);
        cw.visit(Opcodes.V17, Opcodes.ACC_PUBLIC | Opcodes.ACC_FINAL | Opcodes.ACC_SUPER,
                IDENTIFIER_FACTORY, null, "java/lang/Object", null);

        MethodVisitor init = cw.visitMethod(Opcodes.ACC_PRIVATE, "<init>", "()V", null, null);
        init.visitCode();
        init.visitVarInsn(Opcodes.ALOAD, 0);
        init.visitMethodInsn(Opcodes.INVOKESPECIAL, "java/lang/Object", "<init>", "()V", false);
        init.visitInsn(Opcodes.RETURN);
        init.visitMaxs(0, 0);
        init.visitEnd();

        MethodVisitor m = cw.visitMethod(Opcodes.ACC_PUBLIC | Opcodes.ACC_STATIC, "of",
                "(Ljava/lang/String;Ljava/lang/String;)Lnet/minecraft/class_2960;", null, null);
        m.visitCode();
        m.visitVarInsn(Opcodes.ALOAD, 0);
        m.visitVarInsn(Opcodes.ALOAD, 1);
        m.visitMethodInsn(Opcodes.INVOKESTATIC, "net/minecraft/class_2960", "method_60655",
                "(Ljava/lang/String;Ljava/lang/String;)Lnet/minecraft/class_2960;", false);
        m.visitInsn(Opcodes.ARETURN);
        m.visitMaxs(0, 0);
        m.visitEnd();

        cw.visitEnd();
        return cw.toByteArray();
    }

    private static byte[] codecDispatchAdapter() {
        ClassWriter cw = new SafeClassWriter();
        cw.visit(Opcodes.V17, Opcodes.ACC_PUBLIC | Opcodes.ACC_FINAL | Opcodes.ACC_SUPER,
                CODEC_DISPATCH_ADAPTER, null, "java/lang/Object", new String[]{FUNCTION});

        String mapCodecCodec = "com/mojang/serialization/MapCodec$MapCodecCodec";
        cw.visitField(Opcodes.ACC_PRIVATE | Opcodes.ACC_FINAL, "inner", "L" + FUNCTION + ";", null, null).visitEnd();

        MethodVisitor init = cw.visitMethod(Opcodes.ACC_PUBLIC, "<init>", "(L" + FUNCTION + ";)V", null, null);
        init.visitCode();
        init.visitVarInsn(Opcodes.ALOAD, 0);
        init.visitMethodInsn(Opcodes.INVOKESPECIAL, "java/lang/Object", "<init>", "()V", false);
        init.visitVarInsn(Opcodes.ALOAD, 0);
        init.visitVarInsn(Opcodes.ALOAD, 1);
        init.visitFieldInsn(Opcodes.PUTFIELD, CODEC_DISPATCH_ADAPTER, "inner", "L" + FUNCTION + ";");
        init.visitInsn(Opcodes.RETURN);
        init.visitMaxs(0, 0);
        init.visitEnd();

        MethodVisitor apply = cw.visitMethod(Opcodes.ACC_PUBLIC, "apply",
                "(Ljava/lang/Object;)Ljava/lang/Object;", null, null);
        apply.visitCode();
        apply.visitVarInsn(Opcodes.ALOAD, 0);
        apply.visitFieldInsn(Opcodes.GETFIELD, CODEC_DISPATCH_ADAPTER, "inner", "L" + FUNCTION + ";");
        apply.visitVarInsn(Opcodes.ALOAD, 1);
        apply.visitMethodInsn(Opcodes.INVOKEINTERFACE, FUNCTION, "apply",
                "(Ljava/lang/Object;)Ljava/lang/Object;", true);
        apply.visitVarInsn(Opcodes.ASTORE, 2);
        // MapCodecCodec already wraps a MapCodec: unwrap it instead of assuming.
        apply.visitVarInsn(Opcodes.ALOAD, 2);
        apply.visitTypeInsn(Opcodes.INSTANCEOF, mapCodecCodec);
        var fallback = new org.objectweb.asm.Label();
        apply.visitJumpInsn(Opcodes.IFEQ, fallback);
        apply.visitVarInsn(Opcodes.ALOAD, 2);
        apply.visitTypeInsn(Opcodes.CHECKCAST, mapCodecCodec);
        apply.visitMethodInsn(Opcodes.INVOKEVIRTUAL, mapCodecCodec, "codec",
                "()L" + MAP_CODEC + ";", false);
        apply.visitInsn(Opcodes.ARETURN);
        apply.visitLabel(fallback);
        apply.visitVarInsn(Opcodes.ALOAD, 2);
        apply.visitTypeInsn(Opcodes.CHECKCAST, CODEC);
        apply.visitMethodInsn(Opcodes.INVOKESTATIC, MAP_CODEC, "assumeMapUnsafe",
                "(L" + CODEC + ";)L" + MAP_CODEC + ";", false);
        // assumeMapUnsafe may report success(null); guard it into a decode error instead of
        // letting Optional.of(null) escape into DFU callers.
        apply.visitTypeInsn(Opcodes.NEW, CODEC_DISPATCH_GUARD);
        apply.visitInsn(Opcodes.DUP);
        apply.visitMethodInsn(Opcodes.INVOKESPECIAL, CODEC_DISPATCH_GUARD, "<init>", "()V", false);
        apply.visitMethodInsn(Opcodes.INVOKEVIRTUAL, MAP_CODEC, "mapResult",
                "(L" + MAP_CODEC + "$ResultFunction;)L" + MAP_CODEC + ";", false);
        apply.visitInsn(Opcodes.ARETURN);
        apply.visitMaxs(0, 0);
        apply.visitEnd();

        cw.visitEnd();
        return cw.toByteArray();
    }

    /** ResultFunction that rejects a null-successful decode from assumeMapUnsafe. */
    private static byte[] codecDispatchGuard() {
        ClassWriter cw = new ClassWriter(ClassWriter.COMPUTE_MAXS);
        cw.visit(Opcodes.V17, Opcodes.ACC_PUBLIC | Opcodes.ACC_FINAL | Opcodes.ACC_SUPER,
                CODEC_DISPATCH_GUARD, null, "java/lang/Object",
                new String[]{MAP_CODEC + "$ResultFunction"});

        MethodVisitor init = cw.visitMethod(Opcodes.ACC_PUBLIC, "<init>", "()V", null, null);
        init.visitCode();
        init.visitVarInsn(Opcodes.ALOAD, 0);
        init.visitMethodInsn(Opcodes.INVOKESPECIAL, "java/lang/Object", "<init>", "()V", false);
        init.visitInsn(Opcodes.RETURN);
        init.visitMaxs(0, 0);
        init.visitEnd();

        String dataResult = "com/mojang/serialization/DataResult";
        String resultFunction = MAP_CODEC + "$ResultFunction";
        MethodVisitor apply = cw.visitMethod(Opcodes.ACC_PUBLIC, "apply",
                "(Lcom/mojang/serialization/DynamicOps;Lcom/mojang/serialization/MapLike;"
                        + "L" + dataResult + ";)L" + dataResult + ";", null, null);
        apply.visitCode();
        var keep = new org.objectweb.asm.Label();
        apply.visitVarInsn(Opcodes.ALOAD, 3);
        apply.visitMethodInsn(Opcodes.INVOKEVIRTUAL, dataResult, "result",
                "()Ljava/util/Optional;", false);
        apply.visitMethodInsn(Opcodes.INVOKEVIRTUAL, "java/util/Optional", "isPresent", "()Z", false);
        apply.visitJumpInsn(Opcodes.IFEQ, keep);
        apply.visitVarInsn(Opcodes.ALOAD, 3);
        apply.visitMethodInsn(Opcodes.INVOKEVIRTUAL, dataResult, "result",
                "()Ljava/util/Optional;", false);
        apply.visitMethodInsn(Opcodes.INVOKEVIRTUAL, "java/util/Optional", "get",
                "()Ljava/lang/Object;", false);
        apply.visitJumpInsn(Opcodes.IFNONNULL, keep);
        apply.visitLdcInsn("null result from Codec.dispatch adapter");
        apply.visitMethodInsn(Opcodes.INVOKESTATIC, dataResult, "error",
                "(Ljava/lang/String;)L" + dataResult + ";", false);
        apply.visitInsn(Opcodes.ARETURN);
        apply.visitLabel(keep);
        apply.visitVarInsn(Opcodes.ALOAD, 3);
        apply.visitInsn(Opcodes.ARETURN);
        apply.visitMaxs(0, 0);
        apply.visitEnd();

        MethodVisitor co = cw.visitMethod(Opcodes.ACC_PUBLIC, "coApply",
                "(Lcom/mojang/serialization/DynamicOps;Ljava/lang/Object;"
                        + "Lcom/mojang/serialization/RecordBuilder;)"
                        + "Lcom/mojang/serialization/RecordBuilder;", null, null);
        co.visitCode();
        co.visitVarInsn(Opcodes.ALOAD, 3);
        co.visitInsn(Opcodes.ARETURN);
        co.visitMaxs(0, 0);
        co.visitEnd();

        cw.visitEnd();
        return cw.toByteArray();
    }

    /** Computes frames without resolving game types (they are not on this tool's classpath). */
    private static final class SafeClassWriter extends ClassWriter {
        SafeClassWriter() {
            super(ClassWriter.COMPUTE_FRAMES | ClassWriter.COMPUTE_MAXS);
        }

        @Override
        protected String getCommonSuperClass(String type1, String type2) {
            return "java/lang/Object";
        }
    }
}
