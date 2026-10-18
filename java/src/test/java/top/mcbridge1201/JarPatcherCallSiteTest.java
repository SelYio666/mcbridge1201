package top.mcbridge1201;

import org.junit.jupiter.api.Test;
import org.objectweb.asm.ClassReader;
import org.objectweb.asm.ClassWriter;
import org.objectweb.asm.MethodVisitor;
import org.objectweb.asm.Opcodes;
import org.objectweb.asm.tree.AbstractInsnNode;
import org.objectweb.asm.tree.ClassNode;
import org.objectweb.asm.tree.MethodInsnNode;
import top.mcbridge1201.rules.JarPatcher;
import top.mcbridge1201.rules.RuleSet;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;
import java.util.zip.ZipOutputStream;

import static org.junit.jupiter.api.Assertions.*;

/** End-to-end (synthetic jar) test of call-site rewriting plus javac-bridge embedding. */
class JarPatcherCallSiteTest {

    private static final String OWNER = "net/minecraft/class_14";
    private static final String NAME = "method_59";
    private static final String OLD_DESC =
            "(Lnet/minecraft/class_1922;Lnet/minecraft/class_2338$class_2339;Lnet/minecraft/class_7;)"
                    + "Lnet/minecraft/class_7;";
    private static final String BRIDGE = "top/mcbridge1201/bridge/WalkNodeEvaluatorCheckNeighbourBlocks";

    private static RuleSet ruleSet() {
        RuleSet.CallSiteAdaptation a = new RuleSet.CallSiteAdaptation();
        a.id = "synthetic.call-site";
        a.sourceOwner = OWNER;
        a.sourceName = NAME;
        a.sourceDesc = OLD_DESC;
        a.sourceOpcode = 184;
        a.targetOwner = OWNER;
        a.targetName = NAME;
        a.targetDesc = "(Lnet/minecraft/class_9316;IIILnet/minecraft/class_7;)Lnet/minecraft/class_7;";
        a.bridgeClass = BRIDGE;
        a.bridgeMethod = "checkNeighbourBlocks";
        a.bridgeDesc = OLD_DESC;
        RuleSet rs = new RuleSet();
        rs.callSiteAdaptations.add(a);
        return rs;
    }

    private static byte[] syntheticCaller() {
        ClassWriter cw = new ClassWriter(ClassWriter.COMPUTE_MAXS);
        cw.visit(Opcodes.V17, Opcodes.ACC_PUBLIC | Opcodes.ACC_FINAL | Opcodes.ACC_SUPER,
                "test/SyntheticCaller", null, "java/lang/Object", null);
        MethodVisitor m = cw.visitMethod(Opcodes.ACC_PUBLIC | Opcodes.ACC_STATIC, "call",
                OLD_DESC, null, null);
        m.visitCode();
        m.visitVarInsn(Opcodes.ALOAD, 0);
        m.visitVarInsn(Opcodes.ALOAD, 1);
        m.visitVarInsn(Opcodes.ALOAD, 2);
        m.visitMethodInsn(Opcodes.INVOKESTATIC, OWNER, NAME, OLD_DESC, false);
        m.visitInsn(Opcodes.ARETURN);
        m.visitMaxs(0, 0);
        m.visitEnd();
        cw.visitEnd();
        return cw.toByteArray();
    }

    private static byte[] dummyBridge() {
        ClassWriter cw = new ClassWriter(ClassWriter.COMPUTE_MAXS);
        cw.visit(Opcodes.V17, Opcodes.ACC_PUBLIC | Opcodes.ACC_FINAL | Opcodes.ACC_SUPER,
                BRIDGE, null, "java/lang/Object", null);
        MethodVisitor m = cw.visitMethod(Opcodes.ACC_PUBLIC | Opcodes.ACC_STATIC, "checkNeighbourBlocks",
                OLD_DESC, null, null);
        m.visitCode();
        m.visitVarInsn(Opcodes.ALOAD, 2);
        m.visitInsn(Opcodes.ARETURN);
        m.visitMaxs(0, 0);
        m.visitEnd();
        cw.visitEnd();
        return cw.toByteArray();
    }

    private static void writeJar(Path path, Map<String, byte[]> entries) throws Exception {
        try (ZipOutputStream zos = new ZipOutputStream(Files.newOutputStream(path))) {
            for (Map.Entry<String, byte[]> e : entries.entrySet()) {
                ZipEntry ze = new ZipEntry(e.getKey());
                ze.setTime(0L);
                zos.putNextEntry(ze);
                zos.write(e.getValue());
                zos.closeEntry();
            }
        }
    }

    @Test
    void rewritesExactInvocationAndEmbedsCompiledBridge() throws Exception {
        Path dir = Path.of("build", "test-tmp", "callsite");
        Files.createDirectories(dir);
        Path in = dir.resolve("in.jar");
        Path out = dir.resolve("out.jar");
        Map<String, byte[]> entries = new LinkedHashMap<>();
        entries.put("test/SyntheticCaller.class", syntheticCaller());
        writeJar(in, entries);

        Map<String, byte[]> bridges = new LinkedHashMap<>();
        bridges.put(BRIDGE, dummyBridge());
        JarPatcher.Result res = JarPatcher.patch(in, out, ruleSet(), null, bridges);

        assertEquals(1, res.applied().get("synthetic.call-site"));
        assertTrue(res.externalBridges().contains(BRIDGE));

        try (ZipFile zf = new ZipFile(out.toFile())) {
            assertNotNull(zf.getEntry(BRIDGE + ".class"), "compiled bridge must be embedded");
            byte[] bytes = zf.getInputStream(zf.getEntry("test/SyntheticCaller.class")).readAllBytes();
            ClassNode cn = new ClassNode();
            new ClassReader(bytes).accept(cn, 0);
            MethodInsnNode call = null;
            for (var mn : cn.methods) {
                for (AbstractInsnNode insn = mn.instructions.getFirst(); insn != null; insn = insn.getNext()) {
                    if (insn instanceof MethodInsnNode mi) call = mi;
                }
            }
            assertNotNull(call);
            assertEquals(BRIDGE, call.owner);
            assertEquals("checkNeighbourBlocks", call.name);
            assertEquals(OLD_DESC, call.desc);
        }
    }

    @Test
    void embedsBridgeInsideNestedJarThatUsesIt() throws Exception {
        Path dir = Path.of("build", "test-tmp", "callsite-nested");
        Files.createDirectories(dir);
        Path in = dir.resolve("in.jar");
        Path out = dir.resolve("out.jar");

        byte[] nestedJar = jarBytes(Map.of("test/SyntheticCaller.class", syntheticCaller()));
        Map<String, byte[]> entries = new LinkedHashMap<>();
        entries.put("META-INF/jars/nested.jar", nestedJar);
        writeJar(in, entries);

        Map<String, byte[]> bridges = new LinkedHashMap<>();
        bridges.put(BRIDGE, dummyBridge());
        JarPatcher.Result res = JarPatcher.patch(in, out, ruleSet(), null, bridges);

        assertEquals(1, res.applied().get("synthetic.call-site"));
        assertEquals(1, res.nestedJars());
        assertTrue(res.externalBridges().contains(BRIDGE));

        try (ZipFile zf = new ZipFile(out.toFile())) {
            // The bridge is needed only by the nested jar, so it must not leak to the top level.
            assertNull(zf.getEntry(BRIDGE + ".class"));
            byte[] nested = zf.getInputStream(zf.getEntry("META-INF/jars/nested.jar")).readAllBytes();
            Map<String, byte[]> nestedEntries = readJar(nested);
            assertNotNull(nestedEntries.get(BRIDGE + ".class"),
                    "nested jar must carry its own bridge copy");
            ClassNode cn = new ClassNode();
            new ClassReader(nestedEntries.get("test/SyntheticCaller.class")).accept(cn, 0);
            MethodInsnNode call = null;
            for (var mn : cn.methods) {
                for (AbstractInsnNode insn = mn.instructions.getFirst(); insn != null; insn = insn.getNext()) {
                    if (insn instanceof MethodInsnNode mi) call = mi;
                }
            }
            assertNotNull(call);
            assertEquals(BRIDGE, call.owner);
        }
    }

    private static byte[] jarBytes(Map<String, byte[]> entries) throws Exception {
        java.io.ByteArrayOutputStream bos = new java.io.ByteArrayOutputStream();
        try (ZipOutputStream zos = new ZipOutputStream(bos)) {
            for (Map.Entry<String, byte[]> e : entries.entrySet()) {
                ZipEntry ze = new ZipEntry(e.getKey());
                ze.setTime(0L);
                zos.putNextEntry(ze);
                zos.write(e.getValue());
                zos.closeEntry();
            }
        }
        return bos.toByteArray();
    }

    private static Map<String, byte[]> readJar(byte[] bytes) throws Exception {
        Map<String, byte[]> entries = new LinkedHashMap<>();
        try (java.util.zip.ZipInputStream zis =
                     new java.util.zip.ZipInputStream(new java.io.ByteArrayInputStream(bytes))) {
            ZipEntry ze;
            while ((ze = zis.getNextEntry()) != null) {
                if (!ze.isDirectory()) entries.put(ze.getName(), zis.readAllBytes());
            }
        }
        return entries;
    }

    @Test
    void rejectsUnknownBridgeInsteadOfEmittingDanglingCall() throws Exception {
        Path dir = Path.of("build", "test-tmp", "callsite-missing");
        Files.createDirectories(dir);
        Path in = dir.resolve("in.jar");
        Path out = dir.resolve("out.jar");
        Map<String, byte[]> entries = new LinkedHashMap<>();
        entries.put("test/SyntheticCaller.class", syntheticCaller());
        writeJar(in, entries);

        IllegalArgumentException ex = assertThrows(IllegalArgumentException.class,
                () -> JarPatcher.patch(in, out, ruleSet(), null, Map.of()));
        assertTrue(ex.getMessage().contains(BRIDGE));
    }
}
