package top.mcbridge1201;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
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
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;
import java.util.zip.ZipOutputStream;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Pins the rule type that inserts a call instead of replacing one.
 *
 * <p>It exists for a shape the other rules cannot express: "tell a bridge something before the
 * callee runs". The concrete case is ResourcefulLib evaluating a mod's {@code Supplier} inside
 * {@code FabricRegistryEntry.of} with the registry id sitting in a local (runs/p258).
 *
 * <p>What must hold, and is checked here: the insertion lands before the matched call, it is
 * stack-neutral (the argument it pushes is exactly what the bridge consumes), a rule with no
 * local slot is skipped rather than emitting a broken sequence, and a method with two matching
 * calls gets two insertions - not zero, not four.
 */
class JarPatcherInsertBeforeCallTest {
    private static final String SUPPLIER = "java/util/function/Supplier";
    private static final String CTX = "test/Ctx";
    private static final String RULE = "synthetic.set-context";

    private static RuleSet ruleSet(int loadLocal) {
        RuleSet.InsertBeforeCall r = new RuleSet.InsertBeforeCall();
        r.id = RULE;
        r.matchOwner = SUPPLIER;
        r.matchName = "get";
        r.matchDesc = "()Ljava/lang/Object;";
        r.matchOpcode = Opcodes.INVOKEINTERFACE;
        r.loadLocal = loadLocal;
        r.loadKind = "aload";
        r.bridgeClass = CTX;
        r.bridgeMethod = "set";
        r.bridgeDesc = "(Ljava/lang/String;)V";
        RuleSet rs = new RuleSet();
        rs.version = "0.1-draft";
        rs.target = "fabric-1.21.4";
        rs.insertBeforeCalls.add(r);
        return rs;
    }

    @TempDir
    Path tmp;

    /** {@code static Object of(Supplier s, String id) { s.get(); s.get(); return null; }} */
    private static byte[] withCalls(int howMany) {
        ClassWriter cw = new ClassWriter(ClassWriter.COMPUTE_FRAMES);
        cw.visit(Opcodes.V17, Opcodes.ACC_PUBLIC, "test/Entry", null, "java/lang/Object", null);
        MethodVisitor mv = cw.visitMethod(Opcodes.ACC_PUBLIC | Opcodes.ACC_STATIC, "of",
                "(L" + SUPPLIER + ";Ljava/lang/String;)Ljava/lang/Object;", null, null);
        mv.visitCode();
        for (int i = 0; i < howMany; i++) {
            mv.visitVarInsn(Opcodes.ALOAD, 0);
            mv.visitMethodInsn(Opcodes.INVOKEINTERFACE, SUPPLIER, "get", "()Ljava/lang/Object;", true);
            mv.visitInsn(Opcodes.POP);
        }
        mv.visitInsn(Opcodes.ACONST_NULL);
        mv.visitInsn(Opcodes.ARETURN);
        mv.visitMaxs(0, 0);
        mv.visitEnd();
        cw.visitEnd();
        return cw.toByteArray();
    }

    private ClassNode lastPatched;

    private Map<String, Integer> patch(byte[] cls, int loadLocal) throws Exception {
        Path in = tmp.resolve("in.jar");
        Path out = tmp.resolve("out.jar");
        try (ZipOutputStream zos = new ZipOutputStream(Files.newOutputStream(in))) {
            zos.putNextEntry(new ZipEntry("test/Entry.class"));
            zos.write(cls);
            zos.closeEntry();
        }
        JarPatcher.Result res = JarPatcher.patch(in, out, ruleSet(loadLocal));
        try (ZipFile zf = new ZipFile(out.toFile())) {
            byte[] patched = zf.getInputStream(zf.getEntry("test/Entry.class")).readAllBytes();
            ClassNode cn = new ClassNode();
            new ClassReader(patched).accept(cn, 0);
            lastPatched = cn;
        }
        return res.applied();
    }

    /** Offsets (in instruction order) of every instruction matching the predicate. */
    private List<Integer> positions(String owner, String name) {
        List<Integer> out = new ArrayList<>();
        int i = 0;
        for (AbstractInsnNode insn : lastPatched.methods.get(0).instructions) {
            if (insn instanceof MethodInsnNode m && owner.equals(m.owner) && name.equals(m.name)) {
                out.add(i);
            }
            i++;
        }
        return out;
    }

    @Test
    void insertsBeforeTheMatchedCall() throws Exception {
        Map<String, Integer> applied = patch(withCalls(1), 1);
        assertEquals(1, applied.getOrDefault(RULE, 0), "one match, one insertion: " + applied);
        List<Integer> bridge = positions(CTX, "set");
        List<Integer> supplierGet = positions(SUPPLIER, "get");
        assertEquals(1, bridge.size(), "the bridge call must be present");
        assertEquals(1, supplierGet.size());
        assertTrue(bridge.get(0) < supplierGet.get(0), "insertion must precede the matched call");
    }

    @Test
    void pushesTheDeclaredLocalBeforeTheBridge() throws Exception {
        patch(withCalls(1), 1);
        List<Integer> bridge = positions(CTX, "set");
        List<AbstractInsnNode> instructions = new ArrayList<>();
        for (AbstractInsnNode insn : lastPatched.methods.get(0).instructions) {
            instructions.add(insn);
        }
        AbstractInsnNode before = instructions.get(bridge.get(0) - 1);
        assertTrue(before instanceof org.objectweb.asm.tree.VarInsnNode v
                        && v.getOpcode() == Opcodes.ALOAD && v.var == 1,
                "the argument the bridge consumes must be the declared local: " + before);
    }

    @Test
    void twoMatchesGetTwoInsertions() throws Exception {
        Map<String, Integer> applied = patch(withCalls(2), 1);
        assertEquals(2, applied.getOrDefault(RULE, 0), "both call sites: " + applied);
        assertEquals(2, positions(CTX, "set").size(), "no duplicated insertion");
        assertEquals(2, positions(SUPPLIER, "get").size(), "the matched calls are still there");
    }

    @Test
    void aRuleWithoutALocalSlotIsSkipped() throws Exception {
        // loadLocal -1 is the default; emitting ALOAD -1 would produce an invalid class.
        Map<String, Integer> applied = patch(withCalls(1), -1);
        assertEquals(0, applied.getOrDefault(RULE, 0), "must not fire without a source: " + applied);
        assertTrue(positions(CTX, "set").isEmpty());
        assertNotNull(lastPatched);
    }
}
