package top.mcbridge1201;

import org.junit.jupiter.api.Test;
import org.objectweb.asm.ClassReader;
import org.objectweb.asm.ClassWriter;
import org.objectweb.asm.MethodVisitor;
import org.objectweb.asm.Opcodes;
import org.objectweb.asm.tree.ClassNode;
import top.mcbridge1201.rules.JarPatcher;
import top.mcbridge1201.rules.RuleSet;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;
import java.util.zip.ZipOutputStream;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests the {@code onlyIfExtends} gate on {@link RuleSet.MethodRename}.
 *
 * <p>The gate exists because a wildcard rename has to know what it is renaming <em>for</em>.
 * 1.21.1 made {@code ClickableWidget.render} final and moved the override point to
 * {@code renderWidget}, so every subclass that declares {@code method_25394} must be renamed - but
 * Cloth Config's list widget only implements {@code Renderable} through {@code class_362}, and
 * <em>still needs</em> {@code method_25394} to be called at all. Renaming it there produced a list
 * with thirteen constructed rows and no pixels (runs/p210-cloth-config/after/client.log), which is
 * the defect these four cases pin down:
 *
 * <ul>
 *   <li>the direct parent is the gated type -&gt; rename,</li>
 *   <li>the gated type is three levels up -&gt; rename (the walk has to keep going),</li>
 *   <li>the parent is unrelated -&gt; do not rename (the {@code class_362} case),</li>
 *   <li>the chain leaves the jar and cannot be resolved -&gt; do not rename: not knowing an
 *       ancestor is not evidence of having it.</li>
 * </ul>
 */
class JarPatcherMethodRenameTest {

    private static final String OLD_NAME = "method_25394";
    private static final String NEW_NAME = "method_48579";
    private static final String DESC = "(Lnet/minecraft/class_332;IIF)V";
    private static final String GATE = "test/ClickableWidgetLike";
    private static final String RULE = "synthetic.render-override";

    private static RuleSet ruleSet() {
        RuleSet.MethodRename r = new RuleSet.MethodRename();
        r.id = RULE;
        r.owner = "*";
        r.oldName = OLD_NAME;
        r.oldDesc = DESC;
        r.newName = NEW_NAME;
        r.rewriteSuperCalls = false;
        r.onlyIfExtends = GATE;
        RuleSet rs = new RuleSet();
        rs.methodRenames.add(r);
        return rs;
    }

    /** A class with the renamed-in-question method and nothing else of interest. */
    private static byte[] declaring(String name, String superName) {
        ClassWriter cw = new ClassWriter(ClassWriter.COMPUTE_MAXS);
        cw.visit(Opcodes.V17, Opcodes.ACC_PUBLIC | Opcodes.ACC_SUPER, name, null, superName, null);
        MethodVisitor m = cw.visitMethod(Opcodes.ACC_PUBLIC, OLD_NAME, DESC, null, null);
        m.visitCode();
        m.visitInsn(Opcodes.RETURN);
        m.visitMaxs(0, 0);
        m.visitEnd();
        cw.visitEnd();
        return cw.toByteArray();
    }

    /** A plain class: exists only so an ancestor chain can point at it. */
    private static byte[] plain(String name, String superName) {
        ClassWriter cw = new ClassWriter(ClassWriter.COMPUTE_MAXS);
        cw.visit(Opcodes.V17, Opcodes.ACC_PUBLIC | Opcodes.ACC_SUPER, name, null, superName, null);
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

    private static JarPatcher.Result patch(Map<String, byte[]> classes, String caseName) throws Exception {
        Path dir = Path.of("build", "test-tmp", "method-rename", caseName);
        Files.createDirectories(dir);
        Path in = dir.resolve("in.jar");
        Path out = dir.resolve("out.jar");
        Map<String, byte[]> entries = new LinkedHashMap<>();
        for (Map.Entry<String, byte[]> e : classes.entrySet()) {
            entries.put(e.getKey() + ".class", e.getValue());
        }
        writeJar(in, entries);
        return JarPatcher.patch(in, out, ruleSet(), null, Map.of());
    }

    /** Methods of one class as it was written to the patched jar. */
    private static List<String> methodNames(String caseName, String className) throws Exception {
        Path out = Path.of("build", "test-tmp", "method-rename", caseName).resolve("out.jar");
        try (ZipFile zf = new ZipFile(out.toFile())) {
            byte[] bytes = zf.getInputStream(zf.getEntry(className + ".class")).readAllBytes();
            ClassNode cn = new ClassNode();
            new ClassReader(bytes).accept(cn, 0);
            return cn.methods.stream().map(m -> m.name).toList();
        }
    }

    @Test
    void renamesWhenTheDirectParentIsTheGatedType() throws Exception {
        // class_339 itself declares method_25394 in 1.20.1; a direct child hits the gate immediately.
        JarPatcher.Result res = patch(Map.of(
                "test/Child", declaring("test/Child", GATE),
                GATE, plain(GATE, "java/lang/Object")), "direct-parent");

        assertEquals(1, res.applied().get(RULE), "the rule must report one application");
        List<String> names = methodNames("direct-parent", "test/Child");
        assertTrue(names.contains(NEW_NAME), "the override must be renamed to the 1.21.1 hook");
        assertFalse(names.contains(OLD_NAME), "the old name must be gone");
    }

    @Test
    void renamesWhenTheGatedTypeIsThreeLevelsUp() throws Exception {
        // Real shape: TextFieldListEntry$1 -> TextFieldListEntry -> AbstractConfigListEntry ->
        // ... -> class_339. The walk cannot stop at the direct parent.
        JarPatcher.Result res = patch(Map.of(
                "test/Leaf", declaring("test/Leaf", "test/Middle"),
                "test/Middle", plain("test/Middle", "test/Upper"),
                "test/Upper", plain("test/Upper", GATE),
                GATE, plain(GATE, "java/lang/Object")), "three-levels");

        assertEquals(1, res.applied().get(RULE), "the rule must report one application");
        assertTrue(methodNames("three-levels", "test/Leaf").contains(NEW_NAME),
                "a gated ancestor three levels up still gates");
    }

    @Test
    void doesNotRenameUnderAnUnrelatedParent() throws Exception {
        // The class_362 case: this widget renders through Renderable/Tickable and keeps
        // method_25394, because that is still what 1.21.1 calls on it.
        JarPatcher.Result res = patch(Map.of(
                "test/ListWidget", declaring("test/ListWidget", "test/EntryListWidgetLike"),
                "test/EntryListWidgetLike", plain("test/EntryListWidgetLike", "java/lang/Object"),
                GATE, plain(GATE, "java/lang/Object")), "unrelated-parent");

        assertNull(res.applied().get(RULE), "no rename may be reported");
        List<String> names = methodNames("unrelated-parent", "test/ListWidget");
        assertTrue(names.contains(OLD_NAME), "the unrelated subclass keeps the method name");
        assertFalse(names.contains(NEW_NAME), "nothing may be renamed here");
    }

    @Test
    void doesNotRenameWhenTheAncestorCannotBeResolved() throws Exception {
        // The superclass is not in the jar and no --client-jar index was supplied, so the walk ends
        // on an unknown link. "Cannot tell" must not be read as "inherits".
        JarPatcher.Result res = patch(Map.of(
                "test/Orphan", declaring("test/Orphan", "test/NotInThisJar"),
                GATE, plain(GATE, "java/lang/Object")), "unresolvable-ancestor");

        assertNull(res.applied().get(RULE), "an unresolved chain must not gate a rename");
        assertTrue(methodNames("unresolvable-ancestor", "test/Orphan").contains(OLD_NAME),
                "the method keeps its name when the ancestry is unknown");
    }
}
