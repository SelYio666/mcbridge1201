package top.mcbridge1201;

import org.junit.jupiter.api.Test;
import org.objectweb.asm.ClassReader;
import org.objectweb.asm.ClassWriter;
import org.objectweb.asm.MethodVisitor;
import org.objectweb.asm.Opcodes;
import top.mcbridge1201.rules.BridgeGenerator;
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

/** Pins the "prefer supplied CodecDispatch over the generated fallback" rule. */
class JarPatcherCodecDispatchTest {

    private static final String CALLER = "test/CodecCaller";
    private static final String DESC = "(Lcom/mojang/serialization/Codec;"
            + "Ljava/util/function/Function;Ljava/util/function/Function;)"
            + "Lcom/mojang/serialization/Codec;";

    private static byte[] caller() {
        ClassWriter cw = new ClassWriter(ClassWriter.COMPUTE_MAXS);
        cw.visit(Opcodes.V17, Opcodes.ACC_PUBLIC | Opcodes.ACC_SUPER, CALLER, null,
                "java/lang/Object", null);
        MethodVisitor m = cw.visitMethod(Opcodes.ACC_PUBLIC | Opcodes.ACC_STATIC, "call", DESC, null, null);
        m.visitCode();
        m.visitVarInsn(Opcodes.ALOAD, 0);
        m.visitVarInsn(Opcodes.ALOAD, 1);
        m.visitVarInsn(Opcodes.ALOAD, 2);
        m.visitMethodInsn(Opcodes.INVOKESTATIC, BridgeGenerator.CODEC_DISPATCH, "dispatch", DESC, false);
        m.visitInsn(Opcodes.ARETURN);
        m.visitMaxs(0, 0);
        m.visitEnd();
        cw.visitEnd();
        return cw.toByteArray();
    }

    private static byte[] suppliedBridge() {
        ClassWriter cw = new ClassWriter(ClassWriter.COMPUTE_MAXS);
        cw.visit(Opcodes.V17, Opcodes.ACC_PUBLIC | Opcodes.ACC_SUPER,
                BridgeGenerator.CODEC_DISPATCH, null, "java/lang/Object", null);
        MethodVisitor m = cw.visitMethod(Opcodes.ACC_PUBLIC | Opcodes.ACC_STATIC, "dispatch", DESC, null, null);
        m.visitCode();
        m.visitInsn(Opcodes.ACONST_NULL);
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
    void suppliedCodecDispatchIsEmbeddedInsteadOfGenerated() throws Exception {
        Path dir = Path.of("build", "test-tmp", "codec-dispatch");
        Files.createDirectories(dir);
        Path in = dir.resolve("in.jar");
        Path out = dir.resolve("out.jar");
        Map<String, byte[]> entries = new LinkedHashMap<>();
        entries.put(CALLER + ".class", caller());
        writeJar(in, entries);

        RuleSet rs = new RuleSet();
        RuleSet.MethodRedirect r = new RuleSet.MethodRedirect();
        r.id = "codec.dispatch.test";
        r.sourceOwner = BridgeGenerator.CODEC_DISPATCH;
        r.sourceName = "dispatch";
        r.sourceDesc = DESC;
        r.sourceOpcode = 184;
        r.bridgeClass = BridgeGenerator.CODEC_DISPATCH;
        r.bridgeMethod = "dispatch";
        r.bridgeDesc = DESC;
        rs.methodRedirects.add(r);

        Map<String, byte[]> bridges = new LinkedHashMap<>();
        byte[] supplied = suppliedBridge();
        bridges.put(BridgeGenerator.CODEC_DISPATCH, supplied);
        JarPatcher.Result res = JarPatcher.patch(in, out, rs, null, bridges);

        assertEquals(1, res.applied().get("codec.dispatch.test"));
        assertTrue(res.externalBridges().contains(BridgeGenerator.CODEC_DISPATCH));
        try (ZipFile zf = new ZipFile(out.toFile())) {
            byte[] actual = zf.getInputStream(zf.getEntry(BridgeGenerator.CODEC_DISPATCH + ".class")).readAllBytes();
            assertEquals(new ClassReader(supplied).getClassName(), new ClassReader(actual).getClassName());
            assertFalse(zf.getEntry(BridgeGenerator.CODEC_DISPATCH + "$Adapter.class") != null,
                    "generated adapter must not be embedded when the javac class is supplied");
        }
    }
}
