package top.mcbridge1201.scan;

import com.google.gson.Gson;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import org.objectweb.asm.AnnotationVisitor;
import org.objectweb.asm.ClassReader;
import org.objectweb.asm.ClassVisitor;
import org.objectweb.asm.MethodVisitor;
import org.objectweb.asm.Opcodes;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.*;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;

/**
 * Reads one mod jar: metadata, loader, mixin configuration, nested jars, signature
 * state and every symbolic reference made by its classes (including JiJ classes).
 */
public final class ArtifactScanner {
    public static final class RefAgg {
        public final Ref ref;
        public int count;
        public final List<String> sources = new ArrayList<>(2);
        public RefAgg(Ref ref) { this.ref = ref; }
        void hit(String source) {
            count++;
            if (sources.size() < 3 && !sources.contains(source)) sources.add(source);
        }
    }

    public static final class MixinInfo {
        public String configName;
        public int declaredClasses;
        public final List<String> targets = new ArrayList<>();
    }

    public static final class Artifact {
        public String file;
        public String sha256;
        public long size;
        public String loader = "unknown";
        public String modId;
        public String version;
        public String displayName;
        public String description;
        public String environment;
        public final Map<String, String> depends = new LinkedHashMap<>();
        public final List<String> nestedJars = new ArrayList<>();
        public final List<String> mixinConfigs = new ArrayList<>();
        public final List<MixinInfo> mixins = new ArrayList<>();
        public final List<String> signatureFiles = new ArrayList<>();
        public final Set<String> ownClasses = new LinkedHashSet<>();
        public final Map<String, RefAgg> refs = new LinkedHashMap<>();
        public int classCount;
        public int classFileVersionMax;
        public int accessWidenerCount;
        public final List<String> accessWideners = new ArrayList<>();
        public final List<String> entrypoints = new ArrayList<>();
        public final List<String> metadataFiles = new ArrayList<>();
        public final List<String> errors = new ArrayList<>();

        public int errorCount() {
            return errors.size();
        }
    }

    private static final Gson GSON = new Gson();

    public static Artifact scan(Path jar) throws IOException {
        Artifact a = new Artifact();
        a.file = jar.getFileName().toString();
        a.size = Files.size(jar);
        a.sha256 = sha256(jar);
        try (ZipFile zf = new ZipFile(jar.toFile())) {
            ZipEntry fmj = zf.getEntry("fabric.mod.json");
            ZipEntry toml = zf.getEntry("META-INF/mods.toml");
            ZipEntry neotoml = zf.getEntry("META-INF/neoforge.mods.toml");
            a.metadataFiles.addAll(java.util.stream.Stream.of(
                            fmj == null ? null : "fabric.mod.json",
                            toml == null ? null : "META-INF/mods.toml",
                            neotoml == null ? null : "META-INF/neoforge.mods.toml")
                    .filter(java.util.Objects::nonNull).toList());
            // Multi-loader jars ship both metadata files; the loader-specific one wins.
            if (neotoml != null) {
                a.loader = "neoforge";
                readModsToml(a, new String(zf.getInputStream(neotoml).readAllBytes(), StandardCharsets.UTF_8));
            } else if (toml != null) {
                a.loader = "forge";
                readModsToml(a, new String(zf.getInputStream(toml).readAllBytes(), StandardCharsets.UTF_8));
            } else if (fmj != null) {
                a.loader = "fabric";
                readFabricMeta(a, zf.getInputStream(fmj));
            } else if (zf.getEntry("META-INF/MANIFEST.MF") != null) {
                String mf = new String(zf.getInputStream(zf.getEntry("META-INF/MANIFEST.MF")).readAllBytes(), StandardCharsets.UTF_8);
                if (mf.contains("FMLModType") || mf.contains("FMLCorePlugin")) a.loader = "forge-coremod?";
            }
            if (fmj != null && !"fabric".equals(a.loader)) {
                // keep Fabric metadata available for mixed jars without overriding the loader
                readFabricMeta(a, zf.getInputStream(fmj));
            }
            var en = zf.entries();
            while (en.hasMoreElements()) {
                ZipEntry e = en.nextElement();
                if (e.isDirectory()) continue;
                String n = e.getName();
                if (n.startsWith("META-INF/") && (n.endsWith(".SF") || n.endsWith(".RSA") || n.endsWith(".DSA") || n.endsWith(".EC"))) {
                    a.signatureFiles.add(n);
                }
                if (n.endsWith(".class")) {
                    byte[] bytes = readAll(zf.getInputStream(e));
                    a.classCount++;
                    int major = ((bytes[6] & 0xff) << 8) | (bytes[7] & 0xff);
                    a.classFileVersionMax = Math.max(a.classFileVersionMax, major);
                    String internal = n.substring(0, n.length() - 6);
                    a.ownClasses.add(internal);
                    collectRefs(a, bytes, internal, false);
                } else if (n.startsWith("META-INF/jars/") && n.endsWith(".jar")) {
                    byte[] nested = readAll(zf.getInputStream(e));
                    a.nestedJars.add(n + " (" + nested.length + " bytes)");
                    scanNested(a, nested, n);
                } else if (n.endsWith(".mixins.json") || n.matches(".*\\.mixins\\.json")) {
                    if (!a.mixinConfigs.contains(n)) a.mixinConfigs.add(n);
                } else if (n.endsWith(".accesswidener") || n.endsWith(".accessWidener")) {
                    // .accesswidener is the standard suffix; also accept exact "accessWidener" entries
                }
                if (n.endsWith(".accesswidener")) {
                    a.accessWidenerCount++;
                    a.accessWideners.add(n);
                }
            }
        }
        finalizeScan(a, jar);
        return a;
    }

    private static void finalizeScan(Artifact a, Path jar) {
        readMixinConfig(a, jar);
    }

    private static void scanNested(Artifact a, byte[] bytes, String entryName) {
        try (java.util.zip.ZipInputStream zin =
                     new java.util.zip.ZipInputStream(new java.io.ByteArrayInputStream(bytes))) {
            java.util.zip.ZipEntry e;
            while ((e = zin.getNextEntry()) != null) {
                if (e.isDirectory() || !e.getName().endsWith(".class")) continue;
                byte[] cb = zin.readAllBytes();
                String internal = e.getName().substring(0, e.getName().length() - 6);
                a.ownClasses.add(internal);
                collectRefs(a, cb, internal + " [nested]", true);
            }
        } catch (IOException ex) {
            a.errors.add("nested jar " + entryName + ": " + ex.getMessage());
        }
    }

    private static void collectRefs(Artifact a, byte[] classBytes, String source, boolean nested) {
        try {
            var refs = RefCollector.collect(classBytes, source);
            for (Ref r : refs) {
                a.refs.computeIfAbsent(r.key(), k -> new RefAgg(r)).hit(source);
            }
        } catch (RuntimeException ex) {
            a.errors.add("class " + source + ": " + ex.getMessage());
        }
    }

    private static void readFabricMeta(Artifact a, InputStream in) throws IOException {
        JsonObject o = GSON.fromJson(new String(in.readAllBytes(), StandardCharsets.UTF_8), JsonObject.class);
        if (o == null) return;
        a.modId = str(o, "id");
        a.version = str(o, "version");
        a.displayName = o.has("name") ? str(o, "name") : a.modId;
        a.description = str(o, "description");
        if (o.has("environment")) a.environment = str(o, "environment");
        if (o.has("depends") && o.get("depends").isJsonObject()) {
            for (var e : o.getAsJsonObject("depends").entrySet()) {
                a.depends.put(e.getKey(), e.getValue().isJsonArray() ? e.getValue().toString() : e.getValue().getAsString());
            }
        }
        if (o.has("mixins") && o.get("mixins").isJsonArray()) {
            for (JsonElement e : o.getAsJsonArray("mixins")) {
                if (e.isJsonObject()) a.mixinConfigs.add(str(e.getAsJsonObject(), "config"));
                else a.mixinConfigs.add(e.getAsString());
            }
        }
        if (o.has("accessWidener")) {
            a.accessWidenerCount++;
            a.accessWideners.add(str(o, "accessWidener"));
        }
        if (o.has("entrypoints") && o.get("entrypoints").isJsonObject()) {
            for (var e : o.getAsJsonObject("entrypoints").entrySet()) {
                a.entrypoints.add(e.getKey() + "=" + e.getValue());
            }
        }
    }

    private static void readModsToml(Artifact a, String toml) {
        for (String raw : toml.split("\\R")) {
            String line = raw.trim();
            if (line.isEmpty() || line.startsWith("#")) continue;
            int eq = line.indexOf('=');
            if (eq < 0) continue;
            String k = line.substring(0, eq).trim().replace("\"", "");
            String v = line.substring(eq + 1).trim().replaceAll("^\"|\"$", "");
            switch (k) {
                case "modId" -> { if (a.modId == null) a.modId = v; }
                case "version" -> { if (a.version == null) a.version = v; }
                case "displayName" -> { if (a.displayName == null) a.displayName = v; }
                case "description" -> { if (a.description == null) a.description = v; }
                case "modLoader" -> a.depends.put("modLoader", v);
                case "loaderVersion" -> a.depends.put("loaderVersion", v);
                case "license" -> a.depends.put("license", v);
                default -> { }
            }
        }
    }

    private static String str(JsonObject o, String k) {
        return o.has(k) && !o.get(k).isJsonNull() ? o.get(k).getAsString() : null;
    }

    /** Read mixin configs to count declared mixin classes and their @Mixin targets. */
    public static void readMixinConfig(Artifact a, Path jar) {
        a.mixins.clear();
        try (ZipFile zf = new ZipFile(jar.toFile())) {
            for (String cfg : a.mixinConfigs) {
                if (cfg == null) continue;
                ZipEntry e = zf.getEntry(cfg);
                if (e == null) {
                    MixinInfo mi = new MixinInfo();
                    mi.configName = cfg;
                    a.mixins.add(mi);
                    continue;
                }
                JsonObject o = GSON.fromJson(new String(zf.getInputStream(e).readAllBytes(), StandardCharsets.UTF_8), JsonObject.class);
                if (o == null) continue;
                String pkg = o.has("package") ? str(o, "package") : "";
                for (String side : List.of("mixins", "client", "server")) {
                    if (!o.has(side) || !o.get(side).isJsonArray()) continue;
                    for (JsonElement el : o.getAsJsonArray(side)) {
                        MixinInfo mi = new MixinInfo();
                        mi.configName = cfg + ":" + side;
                        mi.declaredClasses = 1;
                        String cls = el.getAsString();
                        String internal = (pkg.isEmpty() ? cls : pkg + "." + cls).replace('.', '/');
                        a.ownClasses.add(internal);
                        mi.targets.addAll(mixinTargets(zf, internal));
                        a.mixins.add(mi);
                    }
                }
            }
        } catch (IOException ex) {
            a.errors.add("mixin config: " + ex.getMessage());
        }
    }

    private static List<String> mixinTargets(ZipFile zf, String internal) throws IOException {
        ZipEntry e = zf.getEntry(internal + ".class");
        if (e == null) return List.of();
        List<String> out = new ArrayList<>();
        new ClassReader(zf.getInputStream(e)).accept(new ClassVisitor(Opcodes.ASM9) {
            @Override
            public AnnotationVisitor visitAnnotation(String desc, boolean visible) {
                if (!"Lorg/spongepowered/asm/mixin/Mixin;".equals(desc)) return null;
                return new AnnotationVisitor(Opcodes.ASM9) {
                    @Override
                    public void visit(String name, Object value) {
                        if ("targets".equals(name) && value instanceof String s) {
                            out.add(s.replace('.', '/'));
                        } else if ("value".equals(name) && value instanceof org.objectweb.asm.Type t) {
                            out.add(t.getInternalName());
                        }
                    }

                    @Override
                    public AnnotationVisitor visitArray(String name) {
                        return this;
                    }
                };
            }
        }, ClassReader.SKIP_CODE);
        return out;
    }

    private static byte[] readAll(InputStream in) throws IOException {
        ByteArrayOutputStream bos = new ByteArrayOutputStream();
        in.transferTo(bos);
        return bos.toByteArray();
    }

    public static String sha256(Path p) throws IOException {
        try (InputStream in = Files.newInputStream(p)) {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            byte[] buf = new byte[1 << 20];
            int n;
            while ((n = in.read(buf)) > 0) md.update(buf, 0, n);
            StringBuilder sb = new StringBuilder();
            for (byte b : md.digest()) sb.append(String.format("%02x", b));
            return sb.toString();
        } catch (java.security.NoSuchAlgorithmException e) {
            throw new IllegalStateException(e);
        }
    }
}
