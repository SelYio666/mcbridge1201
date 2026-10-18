package top.mcbridge1201;

import org.junit.jupiter.api.Test;
import org.objectweb.asm.AnnotationVisitor;
import org.objectweb.asm.ClassWriter;
import org.objectweb.asm.MethodVisitor;
import org.objectweb.asm.Opcodes;
import top.mcbridge1201.scan.ArtifactScanner;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

import static org.junit.jupiter.api.Assertions.*;

/** Pins the mixin injection-target extraction used by the static analysis. */
class MixinInjectionScanTest {

    private static byte[] syntheticMixin() {
        ClassWriter cw = new ClassWriter(0);
        cw.visit(Opcodes.V17, Opcodes.ACC_PUBLIC | Opcodes.ACC_SUPER, "test/TestMixin",
                null, "java/lang/Object", null);
        AnnotationVisitor mixin = cw.visitAnnotation("Lorg/spongepowered/asm/mixin/Mixin;", true);
        mixin.visit("targets", "net.minecraft.class_14");
        mixin.visitEnd();

        MethodVisitor mv = cw.visitMethod(Opcodes.ACC_PRIVATE, "handler", "()V", null, null);
        mv.visitCode();
        AnnotationVisitor inject = mv.visitAnnotation(
                "Lorg/spongepowered/asm/mixin/injection/Inject;", true);
        inject.visit("method", "method_59()V");
        inject.visitEnd();
        mv.visitInsn(Opcodes.RETURN);
        mv.visitMaxs(0, 1);
        mv.visitEnd();
        cw.visitEnd();
        return cw.toByteArray();
    }

    @Test
    void extractsMixinTargetAndInjectionDescriptor() throws Exception {
        Path dir = Path.of("build", "test-tmp", "mixin-inject");
        Files.createDirectories(dir);
        Path jar = dir.resolve("mixin.jar");
        Map<String, byte[]> entries = new LinkedHashMap<>();
        entries.put("test.mixins.json", ("{\"package\":\"test\",\"mixins\":[\"TestMixin\"]}")
                .getBytes(StandardCharsets.UTF_8));
        entries.put("test/TestMixin.class", syntheticMixin());
        try (ZipOutputStream zos = new ZipOutputStream(Files.newOutputStream(jar))) {
            for (Map.Entry<String, byte[]> e : entries.entrySet()) {
                ZipEntry ze = new ZipEntry(e.getKey());
                ze.setTime(0L);
                zos.putNextEntry(ze);
                zos.write(e.getValue());
                zos.closeEntry();
            }
        }

        ArtifactScanner.Artifact a = ArtifactScanner.scan(jar);
        assertEquals(1, a.mixins.size());
        ArtifactScanner.MixinInfo mi = a.mixins.get(0);
        assertEquals(1, mi.targets.size());
        assertEquals("net/minecraft/class_14", mi.targets.get(0));
        assertEquals(1, mi.injections.size());
        ArtifactScanner.Injection inj = mi.injections.get(0);
        assertEquals("Inject", inj.annotation);
        assertEquals("method_59", inj.targetName);
        assertEquals("()V", inj.targetDesc);
    }
}
