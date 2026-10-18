package top.mcbridge1201.remap;

import org.objectweb.asm.ClassReader;
import org.objectweb.asm.ClassVisitor;
import org.objectweb.asm.ClassWriter;
import org.objectweb.asm.FieldVisitor;
import org.objectweb.asm.MethodVisitor;
import org.objectweb.asm.Opcodes;
import org.objectweb.asm.commons.ClassRemapper;
import org.objectweb.asm.commons.Remapper;
import top.mcbridge1201.index.TinyMappings;

import java.io.BufferedOutputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Enumeration;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;
import java.util.zip.ZipOutputStream;

/**
 * Real jar remapper: rewrites class/member names through a tiny v2 mapping and
 * keeps method bodies intact.
 *
 * <p>Two differences from naive remapping, both learned from a real crash:
 * <ul>
 *   <li>member names are propagated through the class hierarchy, because intermediary
 *       does not list every server-side override while the interface is mapped;</li>
 *   <li>no zipfs is used (ZipOutputStream only): on this host {@code Files.isWritable}
 *       is false for every workspace path, so zipfs opens jars read-only.</li>
 * </ul>
 */
public final class JarRemapper {
    private final TinyMappings mappings;

    public JarRemapper(TinyMappings mappings) {
        this.mappings = mappings;
    }

    public void remap(Path in, Path out) throws IOException {
        Files.createDirectories(out.toAbsolutePath().getParent());
        Map<String, byte[]> entries = readEntries(in);
        Hierarchy hierarchy = scanHierarchy(entries);
        resolveNames(hierarchy);
        resolveLambdas(hierarchy);

        try (ZipOutputStream zos = new ZipOutputStream(new BufferedOutputStream(Files.newOutputStream(out)))) {
            int classes = 0;
            for (Map.Entry<String, byte[]> entry : entries.entrySet()) {
                String name = entry.getKey();
                byte[] data = entry.getValue();
                if (name.endsWith(".class")) {
                    String mapped = mappings.className(name.substring(0, name.length() - 6));
                    ClassReader cr = new ClassReader(data);
                    ClassWriter cw = new ClassWriter(0);
                    cr.accept(new ClassRemapper(cw, new MappingRemapper(mappings, hierarchy)), 0);
                    put(zos, mapped + ".class", cw.toByteArray());
                    classes++;
                } else {
                    put(zos, name, data);
                }
            }
            zos.finish();
            System.out.printf("remapped %d classes: %s -> %s (propagated=%d, lambdas=%d)%n",
                    classes, in.getFileName(), out.getFileName(),
                    hierarchy.resolvedMethods.size(), hierarchy.lambdaNames.size());
        }
    }

    private static Map<String, byte[]> readEntries(Path in) throws IOException {
        Map<String, byte[]> entries = new LinkedHashMap<>();
        try (ZipFile zf = new ZipFile(in.toFile())) {
            Enumeration<? extends ZipEntry> en = zf.entries();
            while (en.hasMoreElements()) {
                ZipEntry e = en.nextElement();
                if (e.isDirectory()) continue;
                String name = e.getName();
                // signatures are invalid after remapping; drop them (original stays untouched)
                if (name.startsWith("META-INF/") && (name.endsWith(".SF") || name.endsWith(".RSA")
                        || name.endsWith(".DSA") || name.endsWith(".EC"))) {
                    continue;
                }
                entries.put(name, readAll(zf.getInputStream(e)));
            }
        }
        return entries;
    }

    private static Hierarchy scanHierarchy(Map<String, byte[]> entries) {
        Hierarchy h = new Hierarchy();
        for (Map.Entry<String, byte[]> e : entries.entrySet()) {
            if (!e.getKey().endsWith(".class")) continue;
            new ClassReader(e.getValue()).accept(new ClassVisitor(Opcodes.ASM9) {
                private String owner;
                private String currentMethod;

                @Override
                public void visit(int version, int access, String name, String sig, String superName, String[] interfaces) {
                    owner = name;
                    h.add(name, superName, interfaces);
                }

                @Override
                public MethodVisitor visitMethod(int access, String name, String desc, String sig, String[] ex) {
                    h.addMethod(owner, name, desc, access);
                    currentMethod = name;
                    return new MethodVisitor(Opcodes.ASM9) {
                        @Override
                        public void visitInvokeDynamicInsn(String indyName, String indyDesc,
                                                           org.objectweb.asm.Handle bsm, Object... args) {
                            recordLambda(h, indyName, indyDesc, bsm, args);
                            super.visitInvokeDynamicInsn(indyName, indyDesc, bsm, args);
                        }
                    };
                }

                @Override
                public FieldVisitor visitField(int access, String name, String desc, String sig, Object value) {
                    h.addField(owner, name, desc);
                    return null;
                }
            }, ClassReader.SKIP_DEBUG | ClassReader.SKIP_FRAMES);
        }
        return h;
    }

    /**
     * A lambda's implementing method must carry the functional interface's mapped name.
     * Hierarchy propagation cannot see this: the implementation lives in a host class that
     * does not implement the interface.
     */
    private static void recordLambda(Hierarchy h, String indyName, String indyDesc,
                                     org.objectweb.asm.Handle bsm, Object[] args) {
        if (bsm == null || !bsm.getOwner().equals("java/lang/invoke/LambdaMetafactory")) return;
        if (!bsm.getName().equals("metafactory") && !bsm.getName().equals("altMetafactory")) return;
        if (args.length < 2) return;
        if (!(args[0] instanceof org.objectweb.asm.Type samType)) return;
        if (!(args[1] instanceof org.objectweb.asm.Handle impl)) return;
        String iface = org.objectweb.asm.Type.getReturnType(indyDesc).getInternalName();
        h.pendingLambdas.add(new String[]{
                impl.getOwner(), impl.getName(), impl.getDesc(),
                iface, indyName, samType.getDescriptor()});
    }

    /**
     * Decide the final name for every declared method once, so static/private helpers are
     * never propagated onto an interface method name (that produces duplicate methods).
     */
    private void resolveNames(Hierarchy h) {
        for (Hierarchy.Node n : h.nodes.values()) {
            for (Map.Entry<String, Integer> e : n.methods.entrySet()) {
                int sp = e.getKey().indexOf(' ');
                String name = e.getKey().substring(0, sp);
                String desc = e.getKey().substring(sp + 1);
                if (name.startsWith("<")) continue;
                String key = n.name + "#" + name + "#" + desc;
                String direct = mappings.methodNames.get(key);
                if (direct != null) {
                    h.resolvedMethods.put(key, direct);
                    continue;
                }
                int access = e.getValue();
                boolean isStaticOrPrivate = (access & (Opcodes.ACC_STATIC | Opcodes.ACC_PRIVATE)) != 0;
                if (isStaticOrPrivate) continue;
                for (String sup : h.supertypes(n.name)) {
                    if (sup.equals(n.name)) continue;
                    String via = mappings.methodNames.get(sup + "#" + name + "#" + desc);
                    if (via != null) {
                        h.resolvedMethods.put(key, via);
                        break;
                    }
                }
            }
        }
    }

    /** Resolve each lambda implementation method to the mapped name of its interface SAM. */
    private void resolveLambdas(Hierarchy h) {
        for (String[] p : h.pendingLambdas) {
            String mapped = mappings.methodNames.get(p[3] + "#" + p[4] + "#" + p[5]);
            if (mapped == null) {
                for (String sup : h.supertypes(p[3])) {
                    if (sup.equals(p[3])) continue;
                    mapped = mappings.methodNames.get(sup + "#" + p[4] + "#" + p[5]);
                    if (mapped != null) break;
                }
            }
            if (mapped != null) {
                h.lambdaNames.put(p[0] + "#" + p[1] + "#" + p[2], mapped);
                h.indyNames.put(p[3] + "#" + p[4], mapped);
                if (System.getenv("MCB_DEBUG") != null) {
                    System.out.printf("lambda indy %s.%s -> %s (impl %s.%s%s)%n",
                            p[3], p[4], mapped, p[0], p[1], p[2]);
                }
            }
        }
    }

    private static void put(ZipOutputStream zos, String name, byte[] data) throws IOException {
        ZipEntry ne = new ZipEntry(name);
        ne.setTime(0L); // deterministic output
        zos.putNextEntry(ne);
        zos.write(data);
        zos.closeEntry();
    }

    private static byte[] readAll(InputStream in) throws IOException {
        ByteArrayOutputStream bos = new ByteArrayOutputStream();
        in.transferTo(bos);
        return bos.toByteArray();
    }

    /** Maps names using the mapping tables; descriptors arrive in the source namespace. */
    private static final class MappingRemapper extends Remapper {
        private final TinyMappings m;
        private final Hierarchy h;

        MappingRemapper(TinyMappings m, Hierarchy h) {
            this.m = m;
            this.h = h;
        }

        @Override
        public String map(String internalName) {
            return m.className(internalName);
        }

        @Override
        public String mapMethodName(String owner, String name, String descriptor) {
            if (name.startsWith("<")) return name;
            String resolved = h.resolvedMethods.get(owner + "#" + name + "#" + descriptor);
            if (resolved != null) return resolved;
            String direct = m.methodNames.get(owner + "#" + name + "#" + descriptor);
            if (direct != null) return direct;
            for (String sup : h.supertypes(owner)) {
                if (sup.equals(owner)) continue;
                String via = m.methodNames.get(sup + "#" + name + "#" + descriptor);
                if (via != null) return via;
            }
            return name;
        }

        /**
         * LambdaMetafactory takes the SAM name from the invokedynamic NAME, not from the
         * interface. Leaving it unmapped makes the generated class implement the old name
         * while the remapped interface declares the new one (AbstractMethodError).
         */
        @Override
        public String mapInvokeDynamicMethodName(String name, String descriptor) {
            String iface;
            try {
                iface = org.objectweb.asm.Type.getReturnType(descriptor).getInternalName();
            } catch (RuntimeException e) {
                return name;
            }
            String mapped = h.indyNames.get(iface + "#" + name);
            return mapped == null ? name : mapped;
        }

        @Override
        public String mapFieldName(String owner, String name, String descriptor) {
            String direct = m.fieldNames.get(owner + "#" + name + "#" + descriptor);
            if (direct != null) return direct;
            // A field reference may use a subclass as owner while the field is declared in
            // a superclass; propagate only when the owner does not declare it itself.
            Hierarchy.Node n = h.get(owner);
            if (n != null && n.fields.contains(name + descriptor)) return name;
            for (String sup : h.supertypes(owner)) {
                if (sup.equals(owner)) continue;
                String via = m.fieldNames.get(sup + "#" + name + "#" + descriptor);
                if (via != null) return via;
            }
            return name;
        }
    }
}
