package top.mcbridge1201.index;

import org.objectweb.asm.ClassReader;
import org.objectweb.asm.ClassVisitor;
import org.objectweb.asm.FieldVisitor;
import org.objectweb.asm.MethodVisitor;
import org.objectweb.asm.Opcodes;

import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Enumeration;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;

/** Builds {@link TargetIndex} instances from a Minecraft client jar (via intermediary) and from API jars. */
public final class IndexBuilder {
    private IndexBuilder() {}

    /** Index the obfuscated client jar, translating names and descriptors to intermediary. */
    public static TargetIndex minecraft(Path clientJar, TinyMappings mappings) throws IOException {
        TargetIndex idx = new TargetIndex("intermediary");
        try (ZipFile zf = new ZipFile(clientJar.toFile())) {
            Enumeration<? extends ZipEntry> en = zf.entries();
            while (en.hasMoreElements()) {
                ZipEntry e = en.nextElement();
                if (e.isDirectory() || !e.getName().endsWith(".class")) continue;
                try (InputStream in = zf.getInputStream(e)) {
                    indexClass(in, idx, mappings);
                }
            }
        }
        return idx;
    }

    /** Index a jar whose names are already final (Fabric API, loader, third-party libraries). */
    public static void apiJar(Path jar, TargetIndex idx) throws IOException {
        try (ZipFile zf = new ZipFile(jar.toFile())) {
            Enumeration<? extends ZipEntry> en = zf.entries();
            while (en.hasMoreElements()) {
                ZipEntry e = en.nextElement();
                String n = e.getName();
                if (e.isDirectory()) continue;
                if (n.endsWith(".class")) {
                    try (InputStream in = zf.getInputStream(e)) {
                        indexClass(in, idx, null);
                    }
                } else if (n.startsWith("META-INF/jars/") && n.endsWith(".jar")) {
                    byte[] nested = zf.getInputStream(e).readAllBytes();
                    apiJarBytes(nested, idx);
                }
            }
        }
    }

    /** Index an in-memory nested jar (no temp files: the host temp dir is not always writable). */
    private static void apiJarBytes(byte[] jarBytes, TargetIndex idx) throws IOException {
        try (java.util.zip.ZipInputStream zin = new java.util.zip.ZipInputStream(new java.io.ByteArrayInputStream(jarBytes))) {
            java.util.zip.ZipEntry e;
            while ((e = zin.getNextEntry()) != null) {
                if (e.isDirectory()) continue;
                String n = e.getName();
                if (n.endsWith(".class")) {
                    indexClass(new java.io.ByteArrayInputStream(zin.readAllBytes()), idx, null);
                } else if (n.startsWith("META-INF/jars/") && n.endsWith(".jar")) {
                    apiJarBytes(zin.readAllBytes(), idx);
                }
            }
        }
    }

    private static void indexClass(InputStream in, TargetIndex idx, TinyMappings mappings) throws IOException {
        ClassReader cr = new ClassReader(in);
        String rawName = cr.getClassName();
        String name = mappings == null ? rawName : mappings.className(rawName);
        ClassInfo ci = new ClassInfo(name);
        if (mappings == null) {
            ci.superName = cr.getSuperName();
            ci.interfaces = java.util.List.of(cr.getInterfaces());
        }
        cr.accept(new ClassVisitor(Opcodes.ASM9) {
            @Override
            public void visit(int version, int access, String n, String signature, String superName, String[] interfaces) {
                if (mappings != null) {
                    ci.superName = superName == null ? null : mappings.className(superName);
                    ci.interfaces = interfaces == null ? java.util.List.of()
                            : java.util.Arrays.stream(interfaces).map(mappings::className).toList();
                }
                ci.isInterface = (access & Opcodes.ACC_INTERFACE) != 0;
            }

            @Override
            public MethodVisitor visitMethod(int access, String n, String d, String sig, String[] ex) {
                String mn = n;
                String md = d;
                if (mappings != null) {
                    String mapped = mappings.methodNames.get(rawName + "#" + n + "#" + d);
                    mn = mapped != null ? mapped : n;
                    ci.syntheticMissingMapping |= mapped == null && !n.startsWith("<") && rawName.length() <= 2;
                    md = mappings.remapDesc(d);
                }
                ci.addMethod(mn, md);
                return null;
            }

            @Override
            public FieldVisitor visitField(int access, String n, String d, String sig, Object value) {
                String fn = n;
                String fd = d;
                if (mappings != null) {
                    String mapped = mappings.fieldNames.get(rawName + "#" + n + "#" + d);
                    fn = mapped != null ? mapped : n;
                    fd = mappings.remapDesc(d);
                }
                ci.addField(fn, fd);
                return null;
            }
        }, ClassReader.SKIP_CODE | ClassReader.SKIP_DEBUG | ClassReader.SKIP_FRAMES);
        idx.classes.put(ci.name, ci);
    }
}
