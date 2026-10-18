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
        public String mixinClass;
        public int declaredClasses;
        public final List<String> targets = new ArrayList<>();
        public final List<Injection> injections = new ArrayList<>();
        public Map<String, String> refmap = Map.of();
    }

    /** One @Inject/@Redirect/... target method declared by a mixin handler. */
    public static final class Injection {
        public String annotation;
        public String rawTarget;
        public String targetOwner;
        public String targetName;
        public String targetDesc;
        public String atValue;
        public String atTargetOwner;
        public String atTargetName;
        public String atTargetDesc;
        public boolean atTargetField;
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
                Map<String, Map<String, String>> refmaps = readRefmap(zf, o);
                for (String side : List.of("mixins", "client", "server")) {
                    if (!o.has(side) || !o.get(side).isJsonArray()) continue;
                    for (JsonElement el : o.getAsJsonArray(side)) {
                        MixinInfo mi = new MixinInfo();
                        mi.configName = cfg + ":" + side;
                        mi.declaredClasses = 1;
                        String cls = el.getAsString();
                        String internal = (pkg.isEmpty() ? cls : pkg + "." + cls).replace('.', '/');
                        a.ownClasses.add(internal);
                        MixinInfo parsed = mixinInfo(zf, internal);
                        mi.mixinClass = internal;
                        mi.refmap = refmaps.getOrDefault(internal, Map.of());
                        mi.targets.addAll(parsed.targets);
                        mi.injections.addAll(parsed.injections);
                        for (Injection inj : mi.injections) resolveRefmapTarget(inj, mi);
                        a.mixins.add(mi);
                    }
                }
            }
        } catch (IOException ex) {
            a.errors.add("mixin config: " + ex.getMessage());
        }
    }

    private static Map<String, Map<String, String>> readRefmap(ZipFile zf, JsonObject config)
            throws IOException {
        if (!config.has("refmap") || !config.get("refmap").isJsonPrimitive()) return Map.of();
        String name = config.get("refmap").getAsString();
        ZipEntry e = zf.getEntry(name);
        if (e == null) return Map.of();
        JsonObject root = GSON.fromJson(new String(zf.getInputStream(e).readAllBytes(),
                StandardCharsets.UTF_8), JsonObject.class);
        if (root == null || !root.has("mappings") || !root.get("mappings").isJsonObject()) {
            return Map.of();
        }
        Map<String, Map<String, String>> out = new HashMap<>();
        for (var entry : root.getAsJsonObject("mappings").entrySet()) {
            if (!entry.getValue().isJsonObject()) continue;
            Map<String, String> values = new HashMap<>();
            for (var v : entry.getValue().getAsJsonObject().entrySet()) {
                if (v.getValue().isJsonPrimitive()) values.put(v.getKey(), v.getValue().getAsString());
            }
            out.put(entry.getKey(), values);
        }
        return out;
    }

    private static void resolveRefmapTarget(Injection inj, MixinInfo mi) {
        if (inj.rawTarget == null || mi.refmap.isEmpty()) return;
        String mapped = mi.refmap.get(inj.rawTarget);
        if (mapped == null) {
            for (String t : mi.targets) {
                mapped = mi.refmap.get("L" + t + ";" + inj.rawTarget);
                if (mapped != null) break;
            }
        }
        if (mapped == null) return;
        int paren = mapped.indexOf('(');
        if (paren < 0) return;
        String head = mapped.substring(0, paren);
        String desc = mapped.substring(paren);
        int semi = head.lastIndexOf(';');
        if (semi > 0) {
            String owner = head.substring(0, semi);
            if (owner.startsWith("L")) owner = owner.substring(1);
            inj.targetOwner = owner;
            head = head.substring(semi + 1);
        } else {
            int dot = head.lastIndexOf('.');
            if (dot >= 0) head = head.substring(dot + 1);
        }
        if (!head.isBlank()) {
            inj.targetName = head;
            inj.targetDesc = desc;
        }
    }

    private static final Set<String> INJECTION_ANNOTATIONS = Set.of(
            "Lorg/spongepowered/asm/mixin/injection/Inject;",
            "Lorg/spongepowered/asm/mixin/injection/Redirect;",
            "Lorg/spongepowered/asm/mixin/injection/ModifyConstant;",
            "Lorg/spongepowered/asm/mixin/injection/ModifyVariable;",
            "Lorg/spongepowered/asm/mixin/injection/ModifyArg;",
            "Lorg/spongepowered/asm/mixin/injection/ModifyArgs;",
            "Lorg/spongepowered/asm/mixin/injection/ModifyExpressionValue;",
            "Lorg/spongepowered/asm/mixin/injection/ModifyReturnValue;",
            "Lorg/spongepowered/asm/mixin/injection/WrapOperation;",
            "Lorg/spongepowered/asm/mixin/injection/WrapWithCondition;");

    private static MixinInfo mixinInfo(ZipFile zf, String internal) throws IOException {
        MixinInfo info = new MixinInfo();
        ZipEntry e = zf.getEntry(internal + ".class");
        if (e == null) return info;
        new ClassReader(zf.getInputStream(e)).accept(new ClassVisitor(Opcodes.ASM9) {
            @Override
            public AnnotationVisitor visitAnnotation(String desc, boolean visible) {
                if (!"Lorg/spongepowered/asm/mixin/Mixin;".equals(desc)) return null;
                return new AnnotationVisitor(Opcodes.ASM9) {
                    @Override
                    public void visit(String name, Object value) {
                        if ("targets".equals(name) && value instanceof String s) {
                            info.targets.add(s.replace('.', '/'));
                        } else if ("value".equals(name) && value instanceof org.objectweb.asm.Type t) {
                            info.targets.add(t.getInternalName());
                        }
                    }

                    @Override
                    public AnnotationVisitor visitArray(String name) {
                        if (!"targets".equals(name)) return null;
                        return new AnnotationVisitor(Opcodes.ASM9) {
                            @Override
                            public void visit(String n, Object value) {
                                if (value instanceof String s) info.targets.add(s.replace('.', '/'));
                            }
                        };
                    }
                };
            }

            @Override
            public MethodVisitor visitMethod(int access, String name, String descriptor,
                                             String signature, String[] exceptions) {
                return new MethodVisitor(Opcodes.ASM9) {
                    @Override
                    public AnnotationVisitor visitAnnotation(String desc, boolean visible) {
                        if (!INJECTION_ANNOTATIONS.contains(desc)) return null;
                        String annotation = desc.substring(desc.lastIndexOf('/') + 1, desc.length() - 1);
                        List<Injection> created = new ArrayList<>();
                        Injection pendingAt = new Injection();
                        return new AnnotationVisitor(Opcodes.ASM9) {
                            @Override
                            public void visit(String n, Object value) {
                                if ("method".equals(n) && value instanceof String s) {
                                    addMethod(created, annotation, s, pendingAt);
                                }
                            }

                            @Override
                            public AnnotationVisitor visitArray(String n) {
                                if ("method".equals(n)) {
                                    return new AnnotationVisitor(Opcodes.ASM9) {
                                        @Override
                                        public void visit(String ignored, Object value) {
                                            if (value instanceof String s) {
                                                addMethod(created, annotation, s, pendingAt);
                                            }
                                        }
                                    };
                                }
                                if ("at".equals(n)) {
                                    return new AnnotationVisitor(Opcodes.ASM9) {
                                        @Override
                                        public AnnotationVisitor visitAnnotation(String ignored, String atDesc) {
                                            return atVisitor(pendingAt, created);
                                        }
                                    };
                                }
                                return null;
                            }

                            @Override
                            public AnnotationVisitor visitAnnotation(String n, String atDesc) {
                                return "at".equals(n) ? atVisitor(pendingAt, created) : null;
                            }

                            @Override
                            public void visitEnd() {
                                info.injections.addAll(created);
                            }
                        };
                    }
                };
            }
        }, ClassReader.SKIP_CODE);
        return info;
    }

    private static void addMethod(List<Injection> created, String annotation, String spec,
                                  Injection pendingAt) {
        if (spec == null) return;
        Injection inj = new Injection();
        inj.annotation = annotation;
        parseMethodSpec(inj, spec);
        if (inj.targetName == null) return;
        copyAt(inj, pendingAt);
        created.add(inj);
    }

    private static AnnotationVisitor atVisitor(Injection pendingAt, List<Injection> created) {
        Injection tmp = new Injection();
        return new AnnotationVisitor(Opcodes.ASM9) {
            @Override
            public void visit(String n, Object value) {
                if ("value".equals(n) && value instanceof String s) {
                    tmp.atValue = s;
                } else if ("target".equals(n) && value instanceof String s) {
                    parseAtTarget(tmp, s);
                }
            }

            @Override
            public void visitEnd() {
                copyAt(pendingAt, tmp);
                for (Injection inj : created) copyAt(inj, tmp);
            }
        };
    }

    private static void copyAt(Injection to, Injection from) {
        to.atValue = from.atValue;
        to.atTargetOwner = from.atTargetOwner;
        to.atTargetName = from.atTargetName;
        to.atTargetDesc = from.atTargetDesc;
        to.atTargetField = from.atTargetField;
    }

    private static void parseMethodSpec(Injection inj, String spec) {
        if (spec == null) return;
        String s = spec.trim();
        if (s.isEmpty()) return;
        int paren = s.indexOf('(');
        String namePart = paren < 0 ? s : s.substring(0, paren);
        String desc = paren < 0 ? null : s.substring(paren);
        int semi = namePart.lastIndexOf(';');
        if (semi >= 0) namePart = namePart.substring(semi + 1);
        int dot = namePart.lastIndexOf('.');
        if (dot >= 0) namePart = namePart.substring(dot + 1);
        if (namePart.isBlank()) return;
        inj.rawTarget = s;
        inj.targetName = namePart;
        inj.targetDesc = desc;
    }

    private static void parseAtTarget(Injection inj, String target) {
        if (target == null) return;
        String s = target.trim();
        if (s.isEmpty()) return;
        int semi = s.indexOf(';');
        String rest = s;
        if (semi > 0) {
            String owner = s.substring(0, semi);
            if (owner.startsWith("L")) owner = owner.substring(1);
            inj.atTargetOwner = owner;
            rest = s.substring(semi + 1);
        }
        int paren = rest.indexOf('(');
        int colon = rest.indexOf(':');
        if (colon > 0 && (paren < 0 || colon < paren)) {
            inj.atTargetField = true;
            inj.atTargetName = rest.substring(0, colon);
            inj.atTargetDesc = rest.substring(colon + 1);
        } else {
            inj.atTargetName = paren < 0 ? rest : rest.substring(0, paren);
            inj.atTargetDesc = paren < 0 ? null : rest.substring(paren);
        }
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
