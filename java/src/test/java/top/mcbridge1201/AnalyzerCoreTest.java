package top.mcbridge1201;

import org.junit.jupiter.api.Test;
import top.mcbridge1201.analyze.Analyzer;
import top.mcbridge1201.index.ClassInfo;
import top.mcbridge1201.index.TargetIndex;
import top.mcbridge1201.index.TinyMappings;
import top.mcbridge1201.scan.ArtifactScanner;

import java.io.ByteArrayInputStream;
import java.nio.charset.StandardCharsets;

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
        a.mixins.add(mi);

        Analyzer.Result r = new Analyzer(mc, new TargetIndex("api"), "fabric").analyze(a);
        assertEquals(2, r.mixinInjectionCount);
        assertEquals(1, r.unresolvedMixinInjections.size());
        assertTrue(r.unresolvedMixinInjections.get(0).contains("method_60"));
    }

    @Test
    void unindexedNonJdkAncestorMakesResolutionUnknownNotMissing() {
        TargetIndex idx = new TargetIndex("test");
        ClassInfo c = new ClassInfo("net/minecraft/class_3");
        c.superName = "some/library/Base";
        idx.classes.put(c.name, c);
        assertEquals(TargetIndex.Kind.UNKNOWN, idx.resolveMethod("net/minecraft/class_3", "custom", "()V").kind());
    }
}
