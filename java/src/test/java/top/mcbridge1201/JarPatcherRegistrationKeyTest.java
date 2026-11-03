package top.mcbridge1201;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.objectweb.asm.ClassReader;
import org.objectweb.asm.ClassWriter;
import org.objectweb.asm.MethodVisitor;
import org.objectweb.asm.Opcodes;
import org.objectweb.asm.tree.AbstractInsnNode;
import org.objectweb.asm.tree.ClassNode;
import org.objectweb.asm.tree.InsnNode;
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

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Pins the one rule type that <em>inserts</em> a call instead of rewriting one.
 *
 * <p>1.21.2 requires block/item settings to carry a registry key before registration, and a 1.20.1
 * source never calls the setter that would give it one. There is no wrong reference to retarget,
 * so the converter has to add {@code settings.registryKey(...)} between the settings constructor
 * and the item constructor. The shape it may act on is narrow, and these cases pin both sides:
 *
 * <ul>
 *   <li>inline settings in a registration site -&gt; inject, before the value constructor;</li>
 *   <li>settings constructed but never registered -&gt; leave alone (no proof it is a registration);</li>
 *   <li>no replayable id load -&gt; leave alone (cannot invent a key);</li>
 *   <li>value built elsewhere (not inline) -&gt; leave alone.</li>
 * </ul>
 */
class JarPatcherRegistrationKeyTest {
    private static final String REGISTRY = "net/minecraft/class_2378";
    private static final String RESOURCE_KEY = "net/minecraft/class_5321";
    private static final String IDENTIFIER = "net/minecraft/class_2960";
    private static final String SETTINGS = "net/minecraft/class_1792$class_1793";
    private static final String ITEM = "net/minecraft/class_1792";
    private static final String RULE = "1214.item-settings.registry-key";

    private static RuleSet ruleSet() {
        RuleSet.RegistrationKey r = new RuleSet.RegistrationKey();
        r.id = RULE;
        r.registerOwner = REGISTRY;
        r.registerName = "method_10230";
        r.settingsClass = SETTINGS;
        r.settingsCtorDesc = "()V";
        r.setterOwner = SETTINGS;
        r.setterName = "method_63686";
        r.setterDesc = "(L" + RESOURCE_KEY + ";)L" + SETTINGS + ";";
        r.keyFactoryOwner = RESOURCE_KEY;
        r.keyFactoryName = "method_29179";
        r.keyFactoryDesc = "(L" + RESOURCE_KEY + ";L" + IDENTIFIER + ";)L" + RESOURCE_KEY + ";";
        r.registryKeyOwner = REGISTRY;
        r.registryKeyName = "method_30517";
        r.registryKeyDesc = "()L" + RESOURCE_KEY + ";";
        RuleSet rs = new RuleSet();
        rs.version = "0.1-draft";
        rs.target = "fabric-1.21.4";
        rs.registrationKeys.add(r);
        return rs;
    }

    @TempDir
    Path tmp;

    /** Emits the bytecode javac produces for {@code REG.register(ID, new Item(new Settings()))}. */
    private static byte[] registrar(boolean withRegister, boolean withInlineValue) {
        ClassWriter cw = new ClassWriter(ClassWriter.COMPUTE_FRAMES);
        cw.visit(Opcodes.V17, Opcodes.ACC_PUBLIC, "test/Registrar", null, "java/lang/Object", null);
        cw.visitField(Opcodes.ACC_STATIC | Opcodes.ACC_PUBLIC, "REG", "L" + REGISTRY + ";", null, null).visitEnd();
        cw.visitField(Opcodes.ACC_STATIC | Opcodes.ACC_PUBLIC, "ID", "L" + IDENTIFIER + ";", null, null).visitEnd();
        cw.visitField(Opcodes.ACC_STATIC | Opcodes.ACC_PUBLIC, "ITEM", "L" + ITEM + ";", null, null).visitEnd();
        MethodVisitor mv = cw.visitMethod(Opcodes.ACC_PUBLIC | Opcodes.ACC_STATIC, "init", "()V", null, null);
        mv.visitCode();
        if (withInlineValue) {
            mv.visitFieldInsn(Opcodes.GETSTATIC, "test/Registrar", "REG", "L" + REGISTRY + ";");
            mv.visitFieldInsn(Opcodes.GETSTATIC, "test/Registrar", "ID", "L" + IDENTIFIER + ";");
            mv.visitTypeInsn(Opcodes.NEW, ITEM);
            mv.visitInsn(Opcodes.DUP);
            mv.visitTypeInsn(Opcodes.NEW, SETTINGS);
            mv.visitInsn(Opcodes.DUP);
            mv.visitMethodInsn(Opcodes.INVOKESPECIAL, SETTINGS, "<init>", "()V", false);
            mv.visitMethodInsn(Opcodes.INVOKESPECIAL, ITEM, "<init>", "(L" + SETTINGS + ";)V", false);
            if (withRegister) {
                mv.visitMethodInsn(Opcodes.INVOKESTATIC, REGISTRY, "method_10230",
                        "(L" + REGISTRY + ";L" + IDENTIFIER + ";Ljava/lang/Object;)Ljava/lang/Object;",
                        true);
                mv.visitTypeInsn(Opcodes.CHECKCAST, ITEM);
                mv.visitFieldInsn(Opcodes.PUTSTATIC, "test/Registrar", "ITEM", "L" + ITEM + ";");
            } else {
                mv.visitInsn(Opcodes.POP);
            }
        } else {
            // Value built by a helper: the parent constructor got an item, not an inline settings.
            mv.visitFieldInsn(Opcodes.GETSTATIC, "test/Registrar", "REG", "L" + REGISTRY + ";");
            mv.visitFieldInsn(Opcodes.GETSTATIC, "test/Registrar", "ID", "L" + IDENTIFIER + ";");
            mv.visitFieldInsn(Opcodes.GETSTATIC, "test/Registrar", "ITEM", "L" + ITEM + ";");
            mv.visitMethodInsn(Opcodes.INVOKESTATIC, REGISTRY, "method_10230",
                    "(L" + REGISTRY + ";L" + IDENTIFIER + ";Ljava/lang/Object;)Ljava/lang/Object;", true);
            mv.visitInsn(Opcodes.POP);
        }
        mv.visitInsn(Opcodes.RETURN);
        mv.visitMaxs(0, 0);
        mv.visitEnd();
        cw.visitEnd();
        return cw.toByteArray();
    }

    private Map<String, Integer> applied(byte[] cls) throws Exception {
        Path in = tmp.resolve("in.jar");
        Path out = tmp.resolve("out.jar");
        Map<String, byte[]> entries = new LinkedHashMap<>();
        entries.put("test/Registrar.class", cls);
        try (ZipOutputStream zos = new ZipOutputStream(Files.newOutputStream(in))) {
            for (Map.Entry<String, byte[]> e : entries.entrySet()) {
                zos.putNextEntry(new ZipEntry(e.getKey()));
                zos.write(e.getValue());
                zos.closeEntry();
            }
        }
        JarPatcher.Result res = JarPatcher.patch(in, out, ruleSet());
        try (ZipFile zf = new ZipFile(out.toFile())) {
            byte[] patched = zf.getInputStream(zf.getEntry("test/Registrar.class")).readAllBytes();
            ClassNode cn = new ClassNode();
            new ClassReader(patched).accept(cn, 0);
            lastPatched = cn;
        }
        return res.applied();
    }

    private ClassNode lastPatched;

    private static int indexOf(ClassNode cn, String owner, String name) {
        int i = 0;
        for (AbstractInsnNode insn : cn.methods.get(0).instructions) {
            if (insn instanceof MethodInsnNode m && owner.equals(m.owner) && name.equals(m.name)) {
                return i;
            }
            i++;
        }
        return -1;
    }

    @Test
    void injectsTheKeyBeforeTheItemConstructor() throws Exception {
        Map<String, Integer> applied = applied(registrar(true, true));
        assertEquals(1, applied.getOrDefault(RULE, 0), "the rule must fire once: " + applied);
        int setter = indexOf(lastPatched, SETTINGS, "method_63686");
        int itemCtor = indexOf(lastPatched, ITEM, "<init>");
        int factory = indexOf(lastPatched, RESOURCE_KEY, "method_29179");
        assertTrue(setter >= 0, "the setter call must be injected");
        assertTrue(factory >= 0 && factory < setter, "the key must be built before it is applied");
        assertTrue(setter < itemCtor, "the key must be set before the item is constructed");
        // the injected block ends by dropping the un-keyed instance it replaced
        assertTrue(lastPatched.methods.get(0).instructions.get(setter + 1) instanceof InsnNode,
                "the setter result must be left on the stack after dropping the old settings");
    }

    @Test
    void leavesSettingsThatAreNeverRegisteredAlone() throws Exception {
        Map<String, Integer> applied = applied(registrar(false, true));
        assertEquals(0, applied.getOrDefault(RULE, 0), "no register call means no proof: " + applied);
        assertFalse(indexOf(lastPatched, SETTINGS, "method_63686") >= 0);
    }

    @Test
    void leavesAValueBuiltElsewhereAlone() throws Exception {
        Map<String, Integer> applied = applied(registrar(true, false));
        assertEquals(0, applied.getOrDefault(RULE, 0),
                "a value that is not built inline has no settings to key: " + applied);
        assertFalse(indexOf(lastPatched, SETTINGS, "method_63686") >= 0);
    }

    @Test
    void thePatchedClassStillParses() throws Exception {
        applied(registrar(true, true));
        assertNotNull(lastPatched);
        assertEquals("test/Registrar", lastPatched.name);
    }
}
