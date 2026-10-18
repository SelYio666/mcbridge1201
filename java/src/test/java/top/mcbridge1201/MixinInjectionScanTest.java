package top.mcbridge1201;

import org.junit.jupiter.api.Test;
import org.objectweb.asm.AnnotationVisitor;
import org.objectweb.asm.ClassWriter;
import org.objectweb.asm.MethodVisitor;
import org.objectweb.asm.Opcodes;
import top.mcbridge1201.scan.ArtifactScanner;

import java.io.ByteArrayOutputStream;
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

    private static byte[] syntheticMixin(String method) {
        return syntheticMixin(method, "Lnet/minecraft/class_14;method_59()V");
    }

    private static byte[] syntheticMixin(String method, String atTarget) {
        return syntheticMixin(new String[]{method}, atTarget);
    }

    private static byte[] syntheticMixin(String[] methods, String atTarget) {
        return syntheticMixin(methods, "INVOKE", atTarget);
    }

    private static byte[] syntheticMixin(String[] methods, String atValue, String atTarget) {
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
        if (methods.length == 1) {
            inject.visit("method", methods[0]);
        } else {
            AnnotationVisitor array = inject.visitArray("method");
            for (String method : methods) array.visit(null, method);
            array.visitEnd();
        }
        AnnotationVisitor at = inject.visitAnnotation(
                "at", "Lorg/spongepowered/asm/mixin/injection/At;");
        at.visit("value", atValue);
        at.visit("target", atTarget);
        at.visitEnd();
        inject.visitEnd();
        mv.visitInsn(Opcodes.RETURN);
        mv.visitMaxs(0, 1);
        mv.visitEnd();
        cw.visitEnd();
        return cw.toByteArray();
    }

    private static byte[] jarBytes(Map<String, byte[]> entries) throws Exception {
        ByteArrayOutputStream bos = new ByteArrayOutputStream();
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

    private static void writeJar(Path jar, Map<String, byte[]> entries) throws Exception {
        try (ZipOutputStream zos = new ZipOutputStream(Files.newOutputStream(jar))) {
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
    void extractsMixinTargetAndInjectionDescriptor() throws Exception {
        Path dir = Path.of("build", "test-tmp", "mixin-inject");
        Files.createDirectories(dir);
        Path jar = dir.resolve("mixin.jar");
        Map<String, byte[]> entries = new LinkedHashMap<>();
        entries.put("test.mixins.json", ("{\"package\":\"test\",\"mixins\":[\"TestMixin\"]}")
                .getBytes(StandardCharsets.UTF_8));
        entries.put("test/TestMixin.class", syntheticMixin("method_59()V"));
        writeJar(jar, entries);

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
        assertEquals("INVOKE", inj.atValue);
        assertEquals("net/minecraft/class_14", inj.atTargetOwner);
        assertEquals("method_59", inj.atTargetName);
        assertEquals("()V", inj.atTargetDesc);
    }

    @Test
    void mapsNamedInjectionTargetThroughRefmap() throws Exception {
        Path dir = Path.of("build", "test-tmp", "mixin-refmap");
        Files.createDirectories(dir);
        Path jar = dir.resolve("mixin.jar");
        Map<String, byte[]> entries = new LinkedHashMap<>();
        entries.put("test.mixins.json", ("{\"package\":\"test\",\"refmap\":\"test.refmap.json\","
                + "\"mixins\":[\"TestMixin\"]}").getBytes(StandardCharsets.UTF_8));
        entries.put("test.refmap.json", ("{\"mappings\":{\"test/TestMixin\":{"
                + "\"named()V\":\"Lnet/minecraft/class_14;method_59()V\","
                + "\"namedAt()V\":\"Lnet/minecraft/class_14;method_60()V\"}}}")
                .getBytes(StandardCharsets.UTF_8));
        entries.put("test/TestMixin.class", syntheticMixin("named()V", "namedAt()V"));
        writeJar(jar, entries);

        ArtifactScanner.Artifact a = ArtifactScanner.scan(jar);
        ArtifactScanner.Injection inj = a.mixins.get(0).injections.get(0);
        assertEquals("net/minecraft/class_14", inj.targetOwner);
        assertEquals("method_59", inj.targetName);
        assertEquals("()V", inj.targetDesc);
        assertEquals("net/minecraft/class_14", inj.atTargetOwner);
        assertEquals("method_60", inj.atTargetName);
        assertEquals("()V", inj.atTargetDesc);
    }

    @Test
    void keepsEveryMethodOfAnInjectionArray() throws Exception {
        Path dir = Path.of("build", "test-tmp", "mixin-multi-method");
        Files.createDirectories(dir);
        Path jar = dir.resolve("mixin.jar");
        Map<String, byte[]> entries = new LinkedHashMap<>();
        entries.put("test.mixins.json", ("{\"package\":\"test\","
                + "\"mixins\":[\"TestMixin\"]}").getBytes(StandardCharsets.UTF_8));
        entries.put("test/TestMixin.class", syntheticMixin(
                new String[]{"method_59()V", "method_60()V"}, "Lnet/minecraft/class_14;method_61()V"));
        writeJar(jar, entries);

        ArtifactScanner.Artifact a = ArtifactScanner.scan(jar);
        assertEquals(2, a.mixins.get(0).injections.size());
        assertEquals("method_59", a.mixins.get(0).injections.get(0).targetName);
        assertEquals("method_60", a.mixins.get(0).injections.get(1).targetName);
        assertEquals("method_61", a.mixins.get(0).injections.get(0).atTargetName);
        assertEquals("method_61", a.mixins.get(0).injections.get(1).atTargetName);
    }

    @Test
    void parsesFieldAtTarget() throws Exception {
        Path dir = Path.of("build", "test-tmp", "mixin-field-at");
        Files.createDirectories(dir);
        Path jar = dir.resolve("mixin.jar");
        Map<String, byte[]> entries = new LinkedHashMap<>();
        entries.put("test.mixins.json", ("{\"package\":\"test\","
                + "\"mixins\":[\"TestMixin\"]}").getBytes(StandardCharsets.UTF_8));
        entries.put("test/TestMixin.class", syntheticMixin(
                new String[]{"method_59()V"}, "FIELD",
                "Lnet/minecraft/class_14;field_99:Lnet/minecraft/class_1799;"));
        writeJar(jar, entries);

        ArtifactScanner.Artifact a = ArtifactScanner.scan(jar);
        ArtifactScanner.Injection inj = a.mixins.get(0).injections.get(0);
        assertTrue(inj.atTargetField);
        assertEquals("FIELD", inj.atValue);
        assertEquals("net/minecraft/class_14", inj.atTargetOwner);
        assertEquals("field_99", inj.atTargetName);
        assertEquals("Lnet/minecraft/class_1799;", inj.atTargetDesc);
    }

    @Test
    void scansMixinConfigInsideNestedJar() throws Exception {
        Map<String, byte[]> nested = new LinkedHashMap<>();
        nested.put("nested.mixins.json", ("{\"package\":\"test\","
                + "\"mixins\":[\"TestMixin\"]}").getBytes(StandardCharsets.UTF_8));
        nested.put("test/TestMixin.class", syntheticMixin("method_59()V"));

        Path dir = Path.of("build", "test-tmp", "mixin-nested");
        Files.createDirectories(dir);
        Path jar = dir.resolve("outer.jar");
        Map<String, byte[]> entries = new LinkedHashMap<>();
        entries.put("fabric.mod.json", "{\"id\":\"outer\",\"version\":\"1\"}"
                .getBytes(StandardCharsets.UTF_8));
        entries.put("META-INF/jars/nested.jar", jarBytes(nested));
        writeJar(jar, entries);

        ArtifactScanner.Artifact a = ArtifactScanner.scan(jar);
        assertEquals(1, a.mixins.size());
        ArtifactScanner.MixinInfo mi = a.mixins.get(0);
        assertTrue(mi.configName.startsWith("META-INF/jars/nested.jar!/"));
        assertEquals("net/minecraft/class_14", mi.targets.get(0));
        assertEquals(1, mi.injections.size());
        assertEquals("method_59", mi.injections.get(0).targetName);
    }
}
