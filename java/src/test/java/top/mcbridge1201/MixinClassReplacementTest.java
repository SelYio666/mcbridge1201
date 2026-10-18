package top.mcbridge1201;

import org.junit.jupiter.api.Test;
import org.objectweb.asm.ClassWriter;
import org.objectweb.asm.MethodVisitor;
import org.objectweb.asm.Opcodes;
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

/** A mixin implementation replacement must replace the target and embed its helpers. */
class MixinClassReplacementTest {

    private static byte[] clazz(String name, int value) {
        ClassWriter cw = new ClassWriter(ClassWriter.COMPUTE_MAXS);
        cw.visit(Opcodes.V17, Opcodes.ACC_PUBLIC | Opcodes.ACC_SUPER, name, null, "java/lang/Object", null);
        MethodVisitor mv = cw.visitMethod(Opcodes.ACC_PUBLIC | Opcodes.ACC_STATIC, "value", "()I", null, null);
        mv.visitCode();
        mv.visitIntInsn(Opcodes.BIPUSH, value);
        mv.visitInsn(Opcodes.IRETURN);
        mv.visitMaxs(0, 0);
        mv.visitEnd();
        cw.visitEnd();
        return cw.toByteArray();
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

    @Test
    void replacesTargetAndEmbedsHelpers() throws Exception {
        Path dir = Path.of("build", "test-tmp", "mixin-replacement");
        Files.createDirectories(dir);
        Path in = dir.resolve("in.jar");
        Path out = dir.resolve("out.jar");
        byte[] target = clazz("test/Target", 1);
        Map<String, byte[]> entries = new LinkedHashMap<>();
        entries.put("test/Target.class", target);
        writeJar(in, entries);

        byte[] replacement = clazz("test/Target", 2);
        byte[] helper = clazz("test/Helper", 3);
        Map<String, byte[]> bridgeClasses = new LinkedHashMap<>();
        bridgeClasses.put("test/Target", replacement);
        bridgeClasses.put("test/Helper", helper);

        RuleSet rs = new RuleSet();
        RuleSet.MixinClassReplacement r = new RuleSet.MixinClassReplacement();
        r.id = "synthetic.replace-class";
        r.targetClass = "test/Target";
        r.replacementClass = "test/Target";
        r.alsoEmbed = List.of("test/Helper");
        rs.mixinClassReplacements.add(r);

        JarPatcher.Result res = JarPatcher.patch(in, out, rs, null, bridgeClasses);
        assertEquals(1, res.applied().get(r.id));
        assertTrue(res.externalBridges().contains("test/Target"));
        assertTrue(res.externalBridges().contains("test/Helper"));

        try (ZipFile zf = new ZipFile(out.toFile())) {
            assertArrayEquals(replacement,
                    zf.getInputStream(zf.getEntry("test/Target.class")).readAllBytes());
            assertArrayEquals(helper,
                    zf.getInputStream(zf.getEntry("test/Helper.class")).readAllBytes());
        }
    }
}
