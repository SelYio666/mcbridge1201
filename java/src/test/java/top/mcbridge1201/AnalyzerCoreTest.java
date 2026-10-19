package top.mcbridge1201;

import org.junit.jupiter.api.Test;
import org.objectweb.asm.ClassReader;
import org.objectweb.asm.tree.ClassNode;
import top.mcbridge1201.analyze.Analyzer;
import top.mcbridge1201.index.ClassInfo;
import top.mcbridge1201.index.TargetIndex;
import top.mcbridge1201.index.TinyMappings;
import top.mcbridge1201.rules.BridgeGenerator;
import top.mcbridge1201.scan.ArtifactScanner;

import java.io.ByteArrayInputStream;
import java.nio.charset.StandardCharsets;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.*;

/** Pins the two pieces of logic the damage numbers depend on. */
class AnalyzerCoreTest {

    private static TinyMappings mappings(String tiny) {
        try {
            return TinyMappings.read(new ByteArrayInputStream(tiny.getBytes(StandardCharsets.UTF_8)));
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }

    @Test
    void remapsDescriptionsThroughClassMapIncludingArraysAndInnerClasses() {
        TinyMappings m = mappings("""
                tiny\t2\t0\tofficial\tintermediary
                c\ta\tnet/minecraft/class_1
                c\ta$b\tnet/minecraft/class_1$class_2
                """);
        assertEquals("Lnet/minecraft/class_1;", m.remapDesc("La;"));
        assertEquals("[Lnet/minecraft/class_1;", m.remapDesc("[La;"));
        assertEquals("(Lnet/minecraft/class_1;[Lnet/minecraft/class_1$class_2;)V",
                m.remapDesc("(La;[La$b;)V"));
        assertEquals("Ljava/lang/String;", m.remapDesc("Ljava/lang/String;"));
    }

    @Test
    void resolvesInheritedMembersAndDistinguishesAbsenceKinds() {
        TargetIndex idx = new TargetIndex("test");
        ClassInfo base = new ClassInfo("net/minecraft/class_1");
        base.superName = "java/lang/Object";
        base.addMethod("method_1", "()V");
        base.addMethod("method_2", "(I)V");
        ClassInfo sub = new ClassInfo("net/minecraft/class_2");
        sub.superName = "net/minecraft/class_1";
        idx.classes.put(base.name, base);
        idx.classes.put(sub.name, sub);

        assertEquals(TargetIndex.Kind.OK, idx.resolveMethod("net/minecraft/class_2", "method_1", "()V").kind());
        assertEquals(TargetIndex.Kind.DESC_MISMATCH, idx.resolveMethod("net/minecraft/class_1", "method_2", "(J)V").kind());
        assertEquals(TargetIndex.Kind.MISSING_MEMBER, idx.resolveMethod("net/minecraft/class_1", "method_3", "()V").kind());
        assertEquals(TargetIndex.Kind.MISSING_CLASS, idx.resolveMethod("net/minecraft/class_9", "method_1", "()V").kind());
        // java.lang.Object members are not in the index but are still valid
        assertEquals(TargetIndex.Kind.OK, idx.resolveMethod("net/minecraft/class_1", "hashCode", "()I").kind());
    }

    @Test
    void reportsMixinInjectionTargetsMissingInTheTargetIndex() {
        TargetIndex mc = new TargetIndex("test");
        ClassInfo target = new ClassInfo("net/minecraft/class_14");
        target.superName = "java/lang/Object";
        target.addMethod("method_59", "()V");
        mc.classes.put(target.name, target);

        ArtifactScanner.Artifact a = new ArtifactScanner.Artifact();
        a.file = "synthetic.jar";
        a.loader = "fabric";
        ArtifactScanner.MixinInfo mi = new ArtifactScanner.MixinInfo();
        mi.configName = "test.mixins.json";
        mi.targets.add("net/minecraft/class_14");
        ArtifactScanner.Injection ok = new ArtifactScanner.Injection();
        ok.annotation = "Inject";
        ok.targetName = "method_59";
        ok.targetDesc = "()V";
        ArtifactScanner.Injection missing = new ArtifactScanner.Injection();
        missing.annotation = "Inject";
        missing.targetName = "method_60";
        missing.targetDesc = "()V";
        mi.injections.add(ok);
        mi.injections.add(missing);
        ArtifactScanner.Injection atMissing = new ArtifactScanner.Injection();
        atMissing.annotation = "Inject";
        atMissing.targetName = "method_59";
        atMissing.targetDesc = "()V";
        atMissing.atValue = "INVOKE";
        atMissing.atTargetOwner = "net/minecraft/class_14";
        atMissing.atTargetName = "method_99";
        atMissing.atTargetDesc = "()V";
        mi.injections.add(atMissing);
        a.mixins.add(mi);

        Analyzer.Result r = new Analyzer(mc, new TargetIndex("api"), "fabric").analyze(a);
        assertEquals(3, r.mixinInjectionCount);
        assertEquals(1, r.mixinAtTargetCount);
        assertEquals(2, r.unresolvedMixinInjections.size());
        assertTrue(r.unresolvedMixinInjections.stream().anyMatch(s -> s.contains("method_60")));
        assertTrue(r.unresolvedMixinInjections.stream().anyMatch(s -> s.contains("method_99")));
    }

    @Test
    void codecDispatchGenerationIncludesNullResultGuard() {
        var generated = BridgeGenerator.generate(Set.of(BridgeGenerator.CODEC_DISPATCH));
        byte[] guard = generated.get(BridgeGenerator.CODEC_DISPATCH_GUARD);
        assertNotNull(guard, "guard must be emitted with CodecDispatch");
        ClassNode cn = new ClassNode();
        new ClassReader(guard).accept(cn, 0);
        assertTrue(cn.interfaces.contains("com/mojang/serialization/MapCodec$ResultFunction"));
        assertNotNull(cn.methods.stream().filter(m -> m.name.equals("apply")).findFirst().orElse(null));
        assertNotNull(cn.methods.stream().filter(m -> m.name.equals("coApply")).findFirst().orElse(null));
    }

    @Test
    void unindexedNonJdkAncestorMakesResolutionUnknownNotMissing() {
        TargetIndex idx = new TargetIndex("test");
        ClassInfo c = new ClassInfo("net/minecraft/class_3");
        c.superName = "some/library/Base";
        idx.classes.put(c.name, c);
        assertEquals(TargetIndex.Kind.UNKNOWN, idx.resolveMethod("net/minecraft/class_3", "custom", "()V").kind());
    }

    @Test
    void prefersFabricMetadataWhenEntrypointsArePresent() throws Exception {
        // The host %TEMP% is not writable for this process; keep the fixture under build/.
        java.nio.file.Path dir = java.nio.file.Files.createTempDirectory(
                java.nio.file.Path.of("build"), "scanner-");
        java.nio.file.Path jar = dir.resolve("multi-loader.jar");
        try (var zos = new java.util.zip.ZipOutputStream(java.nio.file.Files.newOutputStream(jar))) {
            put(zos, "fabric.mod.json", """
                    {"schemaVersion":1,"id":"multi","version":"1.0.0",
                     "entrypoints":{"main":["example.Main"]},"depends":{}}""");
            put(zos, "META-INF/mods.toml", "modLoader=\"javafml\"\n[[mods]]\nmodId=\"multi\"\n");
        }
        ArtifactScanner.Artifact a = ArtifactScanner.scan(jar);
        java.nio.file.Files.deleteIfExists(jar);
        java.nio.file.Files.deleteIfExists(dir);
        assertEquals("fabric", a.loader);
        assertTrue(a.multiLoader);
    }

    private static void put(java.util.zip.ZipOutputStream zos, String name, String text) throws Exception {
        zos.putNextEntry(new java.util.zip.ZipEntry(name));
        zos.write(text.getBytes(StandardCharsets.UTF_8));
        zos.closeEntry();
    }
}
