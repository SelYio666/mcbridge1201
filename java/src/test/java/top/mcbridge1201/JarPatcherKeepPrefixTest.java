package top.mcbridge1201;

import org.junit.jupiter.api.Test;
import org.objectweb.asm.ClassReader;
import org.objectweb.asm.ClassWriter;
import org.objectweb.asm.Label;
import org.objectweb.asm.MethodVisitor;
import org.objectweb.asm.Opcodes;
import org.objectweb.asm.tree.AbstractInsnNode;
import org.objectweb.asm.tree.ClassNode;
import org.objectweb.asm.tree.FieldInsnNode;
import org.objectweb.asm.tree.MethodInsnNode;
import org.objectweb.asm.tree.MethodNode;
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

/**
 * Tests the {@code keepPrefixBeforeTombstones} body redirect: the half of a method that still works
 * must survive, and only the half that calls removed API is replaced.
 *
 * <p>This exists because Mod Menu's description panel lost its rows when the whole body was
 * replaced - the row building and the crash were in the same method (runs/p206-modmenu-select/).
 * The positive case below is shaped like that method: real work guarded by a branch, then a jump to
 * a tail block that calls a tombstone stub.
 */
class JarPatcherKeepPrefixTest {

    private static final String OWNER = "test/SyntheticPanel";
    private static final String BRIDGE = "test/PanelBridge";
    private static final String RULE = "synthetic.keep-prefix";
    private static final String DESC = "(Ljava/lang/Object;)V";

    private static RuleSet ruleSet() {
        RuleSet.BodyRedirect r = new RuleSet.BodyRedirect();
        r.id = RULE;
        r.owner = OWNER;
        r.name = "render";
        r.desc = DESC;
        r.bridgeClass = BRIDGE;
        r.bridgeMethod = "renderPanel";
        r.bridgeDesc = DESC;
        r.keepPrefixBeforeTombstones = true;
        RuleSet rs = new RuleSet();
        rs.bodyRedirects.add(r);
        return rs;
    }

    /**
     * Shape of the real method: read state, branch to the tail on one outcome, otherwise record the
     * selection, and in both cases fall into the tail that uses removed API.
     */
    private static byte[] syntheticPanel(boolean jumpIntoTheTail) {
        ClassWriter cw = new ClassWriter(ClassWriter.COMPUTE_MAXS);
        cw.visit(Opcodes.V17, Opcodes.ACC_PUBLIC | Opcodes.ACC_SUPER, OWNER, null, "java/lang/Object", null);
        cw.visitField(Opcodes.ACC_PUBLIC, "col", "I", null, null).visitEnd();
        cw.visitField(Opcodes.ACC_PUBLIC, "last", "Ljava/lang/Object;", null, null).visitEnd();

        MethodVisitor m = cw.visitMethod(Opcodes.ACC_PUBLIC, "render", DESC, null, null);
        m.visitCode();
        Label tail = new Label();      // the kept prefix always arrives here
        Label insideTail = new Label(); // only used by the negative case
        if (jumpIntoTheTail) {
            // A retained branch that lands after the cut: keeping the prefix would jump into code
            // that no longer exists, so the patcher must refuse instead of emitting a bad class.
            // The label above the tail still exists because the first branch targets it.
            m.visitVarInsn(Opcodes.ALOAD, 1);
            m.visitJumpInsn(Opcodes.IFNULL, tail);
        } else {
            m.visitVarInsn(Opcodes.ALOAD, 1);
            m.visitJumpInsn(Opcodes.IFNULL, tail);
        }
        m.visitVarInsn(Opcodes.ALOAD, 0);
        m.visitIntInsn(Opcodes.BIPUSH, 7);
        m.visitFieldInsn(Opcodes.PUTFIELD, OWNER, "col", "I");
        if (jumpIntoTheTail) {
            m.visitJumpInsn(Opcodes.GOTO, insideTail);
        }
        m.visitVarInsn(Opcodes.ALOAD, 0);
        m.visitVarInsn(Opcodes.ALOAD, 1);
        m.visitFieldInsn(Opcodes.PUTFIELD, OWNER, "last", "Ljava/lang/Object;");
        m.visitLabel(tail);
        m.visitMethodInsn(Opcodes.INVOKESTATIC, "centurybridge/gen/Tombstones_synthetic_1_0", "t1",
                "()Ljava/lang/Object;", false);
        m.visitVarInsn(Opcodes.ASTORE, 2);
        m.visitLabel(insideTail);
        m.visitVarInsn(Opcodes.ALOAD, 2);
        m.visitMethodInsn(Opcodes.INVOKESTATIC, "centurybridge/gen/Tombstones_synthetic_1_0", "t2",
                "(Ljava/lang/Object;)V", false);
        m.visitInsn(Opcodes.RETURN);
        m.visitMaxs(0, 0);
        m.visitEnd();
        cw.visitEnd();
        return cw.toByteArray();
    }

    /** A method with no tombstone reference at all: there is no boundary to find. */
    private static byte[] syntheticPanelWithoutTombstone() {
        ClassWriter cw = new ClassWriter(ClassWriter.COMPUTE_MAXS);
        cw.visit(Opcodes.V17, Opcodes.ACC_PUBLIC | Opcodes.ACC_SUPER, OWNER, null, "java/lang/Object", null);
        MethodVisitor m = cw.visitMethod(Opcodes.ACC_PUBLIC, "render", DESC, null, null);
        m.visitCode();
        m.visitInsn(Opcodes.RETURN);
        m.visitMaxs(0, 0);
        m.visitEnd();
        cw.visitEnd();
        return cw.toByteArray();
    }

    private static byte[] dummyBridge() {
        ClassWriter cw = new ClassWriter(ClassWriter.COMPUTE_MAXS);
        cw.visit(Opcodes.V17, Opcodes.ACC_PUBLIC | Opcodes.ACC_FINAL | Opcodes.ACC_SUPER, BRIDGE, null,
                "java/lang/Object", null);
        MethodVisitor m = cw.visitMethod(Opcodes.ACC_PUBLIC | Opcodes.ACC_STATIC, "renderPanel", DESC, null, null);
        m.visitCode();
        m.visitInsn(Opcodes.RETURN);
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

    private static JarPatcher.Result patch(byte[] panel, Path dir) throws Exception {
        Files.createDirectories(dir);
        Path in = dir.resolve("in.jar");
        Path out = dir.resolve("out.jar");
        Map<String, byte[]> entries = new LinkedHashMap<>();
        entries.put(OWNER + ".class", panel);
        writeJar(in, entries);
        Map<String, byte[]> bridges = new LinkedHashMap<>();
        bridges.put(BRIDGE, dummyBridge());
        return JarPatcher.patch(in, out, ruleSet(), null, bridges);
    }

    private static MethodNode renderMethod(Path dir) throws Exception {
        try (ZipFile zf = new ZipFile(dir.resolve("out.jar").toFile())) {
            byte[] bytes = zf.getInputStream(zf.getEntry(OWNER + ".class")).readAllBytes();
            ClassNode cn = new ClassNode();
            new ClassReader(bytes).accept(cn, 0);
            for (MethodNode mn : cn.methods) {
                if (mn.name.equals("render") && mn.desc.equals(DESC)) {
                    return mn;
                }
            }
        }
        fail("render method missing from the patched class");
        return null;
    }

    @Test
    void keepsTheWorkingPrefixAndReplacesOnlyTheTombstoneTail() throws Exception {
        Path dir = Path.of("build", "test-tmp", "keep-prefix");
        JarPatcher.Result res = patch(syntheticPanel(false), dir);

        assertEquals(1, res.applied().get(RULE), "the redirect must report exactly one application");
        assertTrue(res.externalBridges().contains(BRIDGE), "the javac bridge must be embedded");

        MethodNode mn = renderMethod(dir);
        boolean writesCol = false;
        boolean writesLast = false;
        boolean callsBridge = false;
        int tombstoneRefs = 0;
        AbstractInsnNode lastReal = null;
        for (AbstractInsnNode insn = mn.instructions.getFirst(); insn != null; insn = insn.getNext()) {
            if (insn instanceof FieldInsnNode f && f.owner.equals(OWNER) && f.getOpcode() == Opcodes.PUTFIELD) {
                if (f.name.equals("col")) writesCol = true;
                if (f.name.equals("last")) writesLast = true;
            }
            if (insn instanceof MethodInsnNode m) {
                if (m.owner.startsWith("centurybridge/gen/")) tombstoneRefs++;
                if (m.owner.equals(BRIDGE) && m.name.equals("renderPanel")) callsBridge = true;
            }
            if (insn.getOpcode() != -1) lastReal = insn;
        }
        assertTrue(writesCol, "the prefix's field write is the side effect that must survive");
        assertTrue(writesLast, "the second field write lives between the branch and the cut");
        assertTrue(callsBridge, "the tail must be replaced by the bridge call");
        assertEquals(0, tombstoneRefs, "no removed-API call may survive the patch");
        assertNotNull(lastReal);
        assertEquals(Opcodes.RETURN, lastReal.getOpcode(), "the bridge call must be followed by return");
    }

    @Test
    void refusesWhenKeptCodeJumpsIntoTheReplacedTail() {
        IllegalArgumentException e = assertThrows(IllegalArgumentException.class,
                () -> patch(syntheticPanel(true), Path.of("build", "test-tmp", "keep-prefix-bad-jump")));
        assertTrue(e.getMessage().contains("jumps past the cut"), e.getMessage());
    }

    @Test
    void refusesWhenThereIsNoTombstoneReference() {
        IllegalArgumentException e = assertThrows(IllegalArgumentException.class,
                () -> patch(syntheticPanelWithoutTombstone(), Path.of("build", "test-tmp", "keep-prefix-none")));
        assertTrue(e.getMessage().contains("no reference to centurybridge/gen/"), e.getMessage());
    }
}
