package top.mcbridge1201;

import org.junit.jupiter.api.Test;
import org.objectweb.asm.ClassReader;
import org.objectweb.asm.ClassWriter;
import org.objectweb.asm.MethodVisitor;
import org.objectweb.asm.Opcodes;
import org.objectweb.asm.tree.*;
import top.mcbridge1201.rules.JarPatcher;
import top.mcbridge1201.rules.RuleSet;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;
import java.util.zip.ZipOutputStream;

import static org.junit.jupiter.api.Assertions.*;

/** Synthetic tests for mixin callback target adaptation (append, replace, refmap). */
class MixinCallbackAdaptationTest {

    private static final String CI = "Lorg/spongepowered/asm/mixin/injection/callback/CallbackInfo;";
    private static final String INJECT = "Lorg/spongepowered/asm/mixin/injection/Inject;";
    private static final String AT = "Lorg/spongepowered/asm/mixin/injection/At;";
    private static final String MIXIN = "test/MixinSynthetic";
    private static final String REFMAP = "mixins.test.refmap.json";

    private static byte[] mixinClass(String name, String desc, boolean useArg, String target) {
        ClassWriter cw = new ClassWriter(ClassWriter.COMPUTE_MAXS);
        cw.visit(Opcodes.V17, Opcodes.ACC_PUBLIC | Opcodes.ACC_SUPER, MIXIN, null, "java/lang/Object", null);
        MethodVisitor mv = cw.visitMethod(Opcodes.ACC_PRIVATE, name, desc, null, null);
        mv.visitCode();
        if (useArg) {
            mv.visitVarInsn(Opcodes.ALOAD, 0);
            mv.visitVarInsn(Opcodes.ALOAD, 2);
            mv.visitInsn(Opcodes.POP);
        }
        mv.visitInsn(Opcodes.RETURN);
        mv.visitMaxs(0, 0);
        mv.visitEnd();
        cw.visitEnd();
        byte[] raw = cw.toByteArray();

        ClassNode cn = new ClassNode();
        new ClassReader(raw).accept(cn, 0);
        MethodNode mn = cn.methods.get(0);
        LabelNode start = new LabelNode();
        LabelNode end = new LabelNode();
        mn.instructions.insert(start);
        mn.instructions.add(end);
        mn.parameters = new ArrayList<>();
        if (useArg) {
            mn.parameters.add(new ParameterNode("world", 0));
        } else {
            mn.parameters.add(new ParameterNode("path", 0));
        }
        mn.parameters.add(new ParameterNode("ci", 0));
        mn.localVariables = new ArrayList<>();
        mn.localVariables.add(new LocalVariableNode("this", "L" + MIXIN + ";", null, start, end, 0));
        int ciSlot = useArg ? 2 : 2;
        mn.localVariables.add(new LocalVariableNode("ci", CI, null, start, end, ciSlot));
        AnnotationNode inject = new AnnotationNode(INJECT);
        inject.values = new ArrayList<>();
        inject.values.add("method");
        inject.values.add(new ArrayList<>(List.of(target)));
        inject.values.add("at");
        AnnotationNode at = new AnnotationNode(AT);
        at.values = new ArrayList<>(List.of("value", "RETURN"));
        inject.values.add(at);
        mn.visibleAnnotations = new ArrayList<>(List.of(inject));
        ClassWriter out = new ClassWriter(0);
        cn.accept(out);
        return out.toByteArray();
    }

    private static void writeJar(Path path, Map<String, byte[]> entries) throws Exception {
        try (ZipOutputStream zos = new ZipOutputStream(Files.newOutputStream(path))) {
            for (var e : entries.entrySet()) {
                ZipEntry ze = new ZipEntry(e.getKey());
                ze.setTime(0L);
                zos.putNextEntry(ze);
                zos.write(e.getValue());
                zos.closeEntry();
            }
        }
    }

    private static ClassNode readClass(Path jar, String name) throws Exception {
        try (ZipFile zf = new ZipFile(jar.toFile())) {
            byte[] bytes = zf.getInputStream(zf.getEntry(name + ".class")).readAllBytes();
            ClassNode cn = new ClassNode();
            new ClassReader(bytes).accept(cn, 0);
            return cn;
        }
    }

    private static String injectTarget(MethodNode mn) {
        for (AnnotationNode an : mn.visibleAnnotations) {
            if (!INJECT.equals(an.desc)) continue;
            for (int i = 0; i + 1 < an.values.size(); i += 2) {
                if ("method".equals(an.values.get(i))) {
                    return (String) ((List<?>) an.values.get(i + 1)).get(0);
                }
            }
        }
        return null;
    }

    @Test
    void appendModeShiftsLocalsAndRewritesInjectTarget() throws Exception {
        Path dir = Path.of("build", "test-tmp", "mixin-append");
        Files.createDirectories(dir);
        Path in = dir.resolve("in.jar");
        Path out = dir.resolve("out.jar");
        String oldDesc = "(Lnet/minecraft/class_1937;" + CI + ")V";
        String newDesc = "(Lnet/minecraft/class_1937;Lnet/minecraft/class_2394;" + CI + ")V";
        Map<String, byte[]> entries = new LinkedHashMap<>();
        entries.put(MIXIN + ".class", mixinClass("init", oldDesc, true,
                "<init>(Lnet/minecraft/world/World;)V"));
        writeJar(in, entries);

        RuleSet rs = new RuleSet();
        RuleSet.MixinCallbackAdaptation a = new RuleSet.MixinCallbackAdaptation();
        a.id = "synthetic.append";
        a.mixinClass = MIXIN;
        a.callbackMethod = "init";
        a.oldCallbackDesc = oldDesc;
        a.newCallbackDesc = newDesc;
        a.insertSlot = 2;
        a.addedParamDescs = List.of("Lnet/minecraft/class_2394;");
        a.addedParamNames = List.of("particle");
        a.oldTargetDescriptor = "<init>(Lnet/minecraft/world/World;)V";
        a.newTargetDescriptor = "<init>(Lnet/minecraft/class_1937;)V";
        rs.mixinCallbackAdaptations.add(a);

        JarPatcher.patch(in, out, rs, null);
        ClassNode cn = readClass(out, MIXIN);
        MethodNode mn = cn.methods.get(0);
        assertEquals(newDesc, mn.desc);
        assertEquals("<init>(Lnet/minecraft/class_1937;)V", injectTarget(mn));
        assertTrue(mn.parameters.stream().anyMatch(p -> "particle".equals(p.name)));
        LocalVariableNode ci = mn.localVariables.stream().filter(l -> "ci".equals(l.name)).findFirst().orElseThrow();
        assertEquals(3, ci.index);
        boolean sawShiftedCiLoad = false;
        for (AbstractInsnNode insn = mn.instructions.getFirst(); insn != null; insn = insn.getNext()) {
            if (insn instanceof VarInsnNode v && v.getOpcode() == Opcodes.ALOAD && v.var == 3) {
                sawShiftedCiLoad = true;
            }
        }
        assertTrue(sawShiftedCiLoad, "CallbackInfo load must shift from slot 2 to 3");
    }

    @Test
    void replaceModeRewritesDescriptorAndDropsStaleMetadata() throws Exception {
        Path dir = Path.of("build", "test-tmp", "mixin-replace");
        Files.createDirectories(dir);
        Path in = dir.resolve("in.jar");
        Path out = dir.resolve("out.jar");
        String oldDesc = "(Ljava/nio/file/Path;" + CI + ")V";
        String newDesc = "(Lnet/minecraft/class_9172;" + CI + ")V";
        Map<String, byte[]> entries = new LinkedHashMap<>();
        entries.put(MIXIN + ".class", mixinClass("init", oldDesc, false, "<init>"));
        writeJar(in, entries);

        RuleSet rs = new RuleSet();
        RuleSet.MixinCallbackAdaptation a = new RuleSet.MixinCallbackAdaptation();
        a.id = "synthetic.replace";
        a.mixinClass = MIXIN;
        a.callbackMethod = "init";
        a.oldCallbackDesc = oldDesc;
        a.newCallbackDesc = newDesc;
        a.replace = true;
        rs.mixinCallbackAdaptations.add(a);

        JarPatcher.patch(in, out, rs, null);
        MethodNode mn = readClass(out, MIXIN).methods.get(0);
        assertEquals(newDesc, mn.desc);
        assertNull(mn.parameters);
        assertTrue(mn.localVariables == null || mn.localVariables.isEmpty());
        assertTrue(mn.maxLocals >= 3);
        assertEquals("<init>", injectTarget(mn));
    }

    @Test
    void refmapEntryIsRewrittenTogetherWithCallback() throws Exception {
        Path dir = Path.of("build", "test-tmp", "mixin-refmap");
        Files.createDirectories(dir);
        Path in = dir.resolve("in.jar");
        Path out = dir.resolve("out.jar");
        String oldDesc = "(Ljava/nio/file/Path;" + CI + ")V";
        String newDesc = "(Lnet/minecraft/class_9172;" + CI + ")V";
        Map<String, byte[]> entries = new LinkedHashMap<>();
        entries.put(MIXIN + ".class", mixinClass("init", oldDesc, false, "<init>"));
        entries.put(REFMAP, ("{\"mappings\":{\"" + MIXIN + "\":{\"<init>\":\"old\"}}}")
                .getBytes(StandardCharsets.UTF_8));
        writeJar(in, entries);

        RuleSet rs = new RuleSet();
        RuleSet.MixinCallbackAdaptation a = new RuleSet.MixinCallbackAdaptation();
        a.id = "synthetic.refmap";
        a.mixinClass = MIXIN;
        a.callbackMethod = "init";
        a.oldCallbackDesc = oldDesc;
        a.newCallbackDesc = newDesc;
        a.replace = true;
        a.refmap = REFMAP;
        a.refmapKey = "<init>";
        a.refmapValue = "Ltest/Target;<init>()V";
        rs.mixinCallbackAdaptations.add(a);

        JarPatcher.patch(in, out, rs, null);
        try (ZipFile zf = new ZipFile(out.toFile())) {
            String json = new String(zf.getInputStream(zf.getEntry(REFMAP)).readAllBytes(), StandardCharsets.UTF_8);
            com.google.gson.JsonObject root = com.google.gson.JsonParser.parseString(json).getAsJsonObject();
            assertEquals("Ltest/Target;<init>()V", root.getAsJsonObject("mappings")
                    .getAsJsonObject(MIXIN).get("<init>").getAsString());
        }
    }
}
