package top.mcbridge1201;

import org.junit.jupiter.api.Test;
import top.mcbridge1201.index.ClassInfo;
import top.mcbridge1201.index.TargetIndex;
import top.mcbridge1201.index.TinyMappings;

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
    void unindexedNonJdkAncestorMakesResolutionUnknownNotMissing() {
        TargetIndex idx = new TargetIndex("test");
        ClassInfo c = new ClassInfo("net/minecraft/class_3");
        c.superName = "some/library/Base";
        idx.classes.put(c.name, c);
        assertEquals(TargetIndex.Kind.UNKNOWN, idx.resolveMethod("net/minecraft/class_3", "custom", "()V").kind());
    }
}
