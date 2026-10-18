package top.mcbridge1201;

import com.google.gson.GsonBuilder;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import top.mcbridge1201.analyze.Analyzer;
import top.mcbridge1201.index.IndexBuilder;
import top.mcbridge1201.index.TargetIndex;
import top.mcbridge1201.index.TinyMappings;
import top.mcbridge1201.scan.ArtifactScanner;

import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.time.OffsetDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.stream.Stream;
import java.util.zip.ZipFile;

/**
 * P0 CLI: environment report and static cross-version damage analysis.
 * The plan/evidence JSON is the authoritative record; console output is a summary.
 */
public final class Main {
    static final String VERSION = "0.1.0";

    public static void main(String[] args) throws Exception {
        if (args.length == 0) {
            usage();
            System.exit(2);
        }
        switch (args[0]) {
            case "doctor" -> doctor(args);
            case "analyze" -> analyze(args);
            case "index-info" -> indexInfo(args);
            case "remap-jar" -> remapJar(args);
            case "patch" -> patchJar(args);
            case "patch-readonly" -> patchReadOnly(args);
            case "refs" -> dumpRefs(args);
            default -> {
                usage();
                System.exit(2);
            }
        }
    }

    private static void usage() {
        System.err.println("""
                mcbridge1201 0.1.0
                  doctor   [--json <file>]
                  analyze  --mods <dir> --client-jar <1.21.1 client.jar> --mappings <intermediary-1.21.1 tiny>
                           --api <jar> [--api <jar> ...] --target <version> [--target-loader fabric]
                           --out <plan.json> [--markdown <file>]
                  index-info --client-jar <jar> --mappings <tiny> --api <jar> [...]
                  remap-jar --in <obf.jar> --out <intermediary.jar> --mappings <tiny|mappings.jar>
                  patch    --in <jar> --out <jar> --rules <json> [--rules <json> ...]
                           [--client-jar <1.21.1 client.jar> --mappings <intermediary tiny>]
                           [--bridge-dir <javac output dir> ...]
                """);
    }

    private static Map<String, List<String>> flags(String[] args, int from) {
        Map<String, List<String>> m = new LinkedHashMap<>();
        for (int i = from; i < args.length; i++) {
            if (!args[i].startsWith("--")) continue;
            String k = args[i].substring(2);
            List<String> vals = m.computeIfAbsent(k, x -> new ArrayList<>());
            while (i + 1 < args.length && !args[i + 1].startsWith("--")) vals.add(args[++i]);
            m.put(k, vals);
        }
        return m;
    }

    private static String one(Map<String, List<String>> f, String k, String def) {
        List<String> v = f.get(k);
        return v == null || v.isEmpty() ? def : v.get(0);
    }

    private static void doctor(String[] args) throws IOException {
        Map<String, List<String>> f = flags(args, 1);
        JsonObject o = new JsonObject();
        o.addProperty("tool", "mcbridge1201");
        o.addProperty("toolVersion", VERSION);
        o.addProperty("generatedAt", now());
        o.addProperty("os", System.getProperty("os.name") + " " + System.getProperty("os.version"));
        o.addProperty("arch", System.getProperty("os.arch"));
        o.addProperty("javaVersion", System.getProperty("java.version"));
        o.addProperty("javaVendor", System.getProperty("java.vendor"));
        o.addProperty("javaHome", System.getProperty("java.home"));
        o.addProperty("fileEncoding", System.getProperty("file.encoding"));
        o.addProperty("cpus", Runtime.getRuntime().availableProcessors());
        o.addProperty("maxHeapBytes", Runtime.getRuntime().maxMemory());
        o.addProperty("prefix", "no GUI/client launch is attempted by this tool; it reports only");
        String out = one(f, "json", null);
        String text = new GsonBuilder().setPrettyPrinting().create().toJson(o);
        if (out != null) Files.writeString(Path.of(out), text + "\n", StandardCharsets.UTF_8);
        System.out.println(text);
    }

    private static TargetIndex unusedPlaceholder() { return null; }

    private static TinyMappings readMappings(Path mappingsJar) throws IOException {
        if (mappingsJar.toString().endsWith(".tiny")) {
            try (InputStream in = Files.newInputStream(mappingsJar)) {
                return TinyMappings.read(in);
            }
        }
        try (ZipFile zf = new ZipFile(mappingsJar.toFile())) {
            var e = zf.getEntry("mappings/mappings.tiny");
            if (e == null) throw new IOException("no mappings/mappings.tiny in " + mappingsJar);
            try (InputStream in = zf.getInputStream(e)) {
                return TinyMappings.read(in);
            }
        }
    }

    /** Real, body-preserving remap (official -> intermediary), used for target-game stubs. */
    private static void remapJar(String[] args) throws IOException {
        Map<String, List<String>> f = flags(args, 1);
        Path in = Path.of(require(f, "in"));
        Path out = Path.of(require(f, "out"));
        Path mappings = Path.of(require(f, "mappings"));
        long t0 = System.nanoTime();
        new top.mcbridge1201.remap.JarRemapper(readMappings(mappings)).remap(in, out);
        System.out.printf("wrote %s in %d ms (sha256 %s)%n",
                out, (System.nanoTime() - t0) / 1_000_000, ArtifactScanner.sha256(out));
    }

    private static void indexInfo(String[] args) throws IOException {
        Map<String, List<String>> f = flags(args, 1);
        Path clientJar = Path.of(require(f, "client-jar"));
        TinyMappings tm = readMappings(Path.of(require(f, "mappings")));
        TargetIndex idx = IndexBuilder.minecraft(clientJar, tm);
        for (String api : f.getOrDefault("api", List.of())) IndexBuilder.apiJar(Path.of(api), idx);
        System.out.printf("classes=%d methods=%d mappings=%d%n", idx.classCount(), idx.methodCount(), tm.classMap.size());
    }

    /** Instrument a tool copy: make one boolean method return false (local workaround only). */
    /** Debug helper: print the references collected from one class inside a jar. */
    private static void dumpRefs(String[] args) throws IOException {
        Map<String, List<String>> f = flags(args, 1);
        Path jar = Path.of(require(f, "jar"));
        String cls = require(f, "class").replace('.', '/');
        try (ZipFile zf = new ZipFile(jar.toFile())) {
            var e = zf.getEntry(cls + ".class");
            if (e == null) {
                System.err.println("class not found: " + cls);
                System.exit(2);
            }
            byte[] bytes = zf.getInputStream(e).readAllBytes();
            for (var r : top.mcbridge1201.scan.RefCollector.collect(bytes, cls)) {
                System.out.printf("%-6s %s %s %s%n", r.kind(), r.owner(),
                        r.name() == null ? "" : r.name(), r.desc() == null ? "" : r.desc());
            }
        }
    }

    /** Apply versioned transform rules (field redirects) and embed the bridge classes. */
    private static void patchJar(String[] args) throws IOException {
        Map<String, List<String>> f = flags(args, 1);
        Path in = Path.of(require(f, "in"));
        Path out = Path.of(require(f, "out"));
        List<String> rulePaths = f.getOrDefault("rules", List.of());
        if (rulePaths.isEmpty()) {
            System.err.println("missing --rules");
            System.exit(2);
        }
        var rules = new top.mcbridge1201.rules.RuleSet();
        for (String rp : rulePaths) {
            var part = top.mcbridge1201.rules.RuleSet.load(Path.of(rp));
            if (rules.version == null) rules.version = part.version;
            if (rules.target == null) rules.target = part.target;
            rules.fieldRedirects.addAll(part.fieldRedirects);
            rules.methodRedirects.addAll(part.methodRedirects);
            rules.callSiteAdaptations.addAll(part.callSiteAdaptations);
            rules.constructorRedirects.addAll(part.constructorRedirects);
            rules.signatureAdaptations.addAll(part.signatureAdaptations);
            rules.mixinCallbackAdaptations.addAll(part.mixinCallbackAdaptations);
            rules.mixinStrips.addAll(part.mixinStrips);
        }
        TargetIndex idx = null;
        String clientJar = one(f, "client-jar", null);
        String mappings = one(f, "mappings", null);
        if (clientJar != null && mappings != null) {
            idx = IndexBuilder.minecraft(Path.of(clientJar), readMappings(Path.of(mappings)));
            for (String lib : f.getOrDefault("lib", List.of())) {
                IndexBuilder.apiJar(Path.of(lib), idx);
            }
        }
        Map<String, byte[]> bridgeClasses = loadBridgeClasses(f.getOrDefault("bridge-dir", List.of()));
        var res = top.mcbridge1201.rules.JarPatcher.patch(in, out, rules, idx, bridgeClasses);
        System.out.printf("patched %s -> %s (classes changed=%d)%n", in.getFileName(), out.getFileName(), res.classes());
        res.applied().forEach((k, v) -> System.out.printf("  rule %s applied %d time(s)%n", k, v));
        System.out.printf("  bridges embedded: %s%n", res.bridges());
        System.out.printf("  javac bridges: %s%n", res.externalBridges());
        System.out.printf("  sha256 %s%n", ArtifactScanner.sha256(out));
    }

    /** Load javac output ({@code <dir>/top/.../Foo.class}) keyed by internal class name. */
    private static Map<String, byte[]> loadBridgeClasses(List<String> dirs) throws IOException {
        Map<String, byte[]> out = new LinkedHashMap<>();
        for (String dir : dirs) {
            Path root = Path.of(dir);
            if (!Files.isDirectory(root)) {
                throw new IOException("--bridge-dir is not a directory: " + root);
            }
            try (Stream<Path> s = Files.walk(root)) {
                for (Path p : s.filter(Files::isRegularFile)
                        .filter(p -> p.toString().endsWith(".class")).sorted().toList()) {
                    String rel = root.relativize(p).toString().replace('\\', '/');
                    String internal = rel.substring(0, rel.length() - ".class".length());
                    out.put(internal, Files.readAllBytes(p));
                }
            }
        }
        return out;
    }

    private static void patchReadOnly(String[] args) throws IOException {
        Map<String, List<String>> f = flags(args, 1);
        Path in = Path.of(require(f, "in"));
        Path out = Path.of(require(f, "out"));
        String cls = one(f, "class", "net/fabricmc/tinyremapper/FileSystemReference");
        String method = one(f, "method", "isReadOnly");
        top.mcbridge1201.remap.ReadOnlyGuardPatcher.patch(in, out, cls, method);
        System.out.printf("patched %s#%s in %s -> %s%n", cls, method, in.getFileName(), out.getFileName());
    }

    private static String require(Map<String, List<String>> f, String k) {
        String v = one(f, k, null);
        if (v == null) {
            System.err.println("missing --" + k);
            System.exit(2);
        }
        return v;
    }

    private static void analyze(String[] args) throws Exception {
        Map<String, List<String>> f = flags(args, 1);
        Path mods = Path.of(require(f, "mods"));
        Path clientJar = Path.of(require(f, "client-jar"));
        Path mappings = Path.of(require(f, "mappings"));
        List<Path> apiJars = f.getOrDefault("api", List.of()).stream().map(Path::of).toList();
        String target = one(f, "target", "1.21.1");
        String targetLoader = one(f, "target-loader", "fabric");
        Path out = Path.of(require(f, "out"));

        long t0 = System.nanoTime();
        TinyMappings tm = readMappings(mappings);
        TargetIndex mcIndex = IndexBuilder.minecraft(clientJar, tm);
        TargetIndex full = mcIndex;
        for (Path api : apiJars) IndexBuilder.apiJar(api, full);
        TargetIndex sourceIndex = null;
        TargetIndex sourceApiIndex = null;
        String srcJar = one(f, "source-client-jar", null);
        String srcMap = one(f, "source-mappings", null);
        if (srcJar != null && srcMap != null) {
            sourceIndex = IndexBuilder.minecraft(Path.of(srcJar), readMappings(Path.of(srcMap)));
            sourceApiIndex = new TargetIndex("fabric-api-source");
            for (String api : f.getOrDefault("source-api", List.of())) {
                IndexBuilder.apiJar(Path.of(api), sourceApiIndex);
            }
        }
        long indexMs = (System.nanoTime() - t0) / 1_000_000;

        Analyzer analyzer = new Analyzer(mcIndex, full, targetLoader, sourceIndex, sourceApiIndex);
        JsonObject plan = new JsonObject();
        plan.addProperty("schemaVersion", "0.1-draft");
        plan.addProperty("generatedAt", now());
        plan.addProperty("tool", "mcbridge1201 " + VERSION);
        plan.addProperty("note", "Static analysis only. No game was launched; static stage ANALYZED does not imply VERIFIED/BOOTED/CONTRACT_PASSED.");
        JsonObject targetObj = new JsonObject();
        targetObj.addProperty("minecraft", target);
        targetObj.addProperty("loader", targetLoader);
        targetObj.addProperty("clientJar", clientJar.toAbsolutePath().toString());
        targetObj.addProperty("clientJarSha256", ArtifactScanner.sha256(clientJar));
        targetObj.addProperty("mappings", mappings.toAbsolutePath().toString());
        targetObj.addProperty("mappingsSha256", ArtifactScanner.sha256(mappings));
        targetObj.addProperty("indexClasses", mcIndex.classCount());
        targetObj.addProperty("indexMembers", mcIndex.methodCount());
        targetObj.addProperty("indexBuildMs", indexMs);
        JsonArray apis = new JsonArray();
        for (Path p : apiJars) {
            JsonObject a = new JsonObject();
            a.addProperty("path", p.toAbsolutePath().toString());
            a.addProperty("sha256", ArtifactScanner.sha256(p));
            apis.add(a);
        }
        targetObj.add("apiJars", apis);
        plan.add("target", targetObj);

        List<Path> jars;
        try (Stream<Path> s = Files.walk(mods, 2)) {
            jars = s.filter(p -> p.toString().endsWith(".jar") && Files.isRegularFile(p)).sorted().toList();
        }
        JsonArray artifacts = new JsonArray();
        int blocked = 0, clean = 0, needsDep = 0;
        for (Path jar : jars) {
            ArtifactScanner.Artifact a = ArtifactScanner.scan(jar);
            Analyzer.Result r = analyzer.analyze(a);
            switch (r.verdict) {
                case "blocked_static" -> blocked++;
                case "needs_dependency" -> needsDep++;
                default -> clean++;
            }
            artifacts.add(toJson(a, r));
            System.out.printf("%-42s %-14s missingClass=%-4d missingMember=%-4d mismatch=%-3d apiMissing=%-3d external=%-3d%n",
                    a.file, r.verdict, r.counts.get("missingClass"), r.counts.get("missingMember"),
                    r.counts.get("descMismatch"), r.counts.get("missingApiClass"), r.external.size());
        }
        plan.add("artifacts", artifacts);
        JsonObject summary = new JsonObject();
        summary.addProperty("artifacts", artifacts.size());
        summary.addProperty("blockedStatic", blocked);
        summary.addProperty("needsDependency", needsDep);
        summary.addProperty("cleanStatic", clean);
        plan.add("summary", summary);

        Files.createDirectories(out.toAbsolutePath().getParent());
        Files.writeString(out, new GsonBuilder().setPrettyPrinting().create().toJson(plan) + "\n", StandardCharsets.UTF_8);
        String md = one(f, "markdown", null);
        if (md != null) {
            Files.writeString(Path.of(md), markdown(plan), StandardCharsets.UTF_8);
        }
        System.out.println("wrote " + out);
    }

    private static JsonObject toJson(ArtifactScanner.Artifact a, Analyzer.Result r) {
        JsonObject o = new JsonObject();
        o.addProperty("file", a.file);
        o.addProperty("sha256", a.sha256);
        o.addProperty("size", a.size);
        o.addProperty("loader", a.loader);
        JsonArray meta = new JsonArray();
        a.metadataFiles.forEach(meta::add);
        o.add("metadataFiles", meta);
        o.addProperty("modId", a.modId);
        o.addProperty("version", a.version);
        o.addProperty("displayName", a.displayName);
        o.addProperty("environment", a.environment);
        JsonObject deps = new JsonObject();
        a.depends.forEach(deps::addProperty);
        o.add("depends", deps);
        o.addProperty("classes", a.classCount);
        o.addProperty("classFileMajorMax", a.classFileVersionMax);
        o.addProperty("nestedJars", a.nestedJars.size());
        o.addProperty("signed", !a.signatureFiles.isEmpty());
        o.addProperty("accessWideners", a.accessWidenerCount);
        o.addProperty("verdict", r.verdict);
        o.addProperty("stage", "ANALYZED");
        JsonObject counts = new JsonObject();
        r.counts.forEach(counts::addProperty);
        counts.addProperty("externalPackages", r.external.size());
        o.add("counts", counts);
        o.add("missingClass", items(r.missingClass));
        o.add("missingMember", items(r.missingMember));
        o.add("descMismatch", items(r.descMismatch));
        o.add("missingApiClass", items(r.missingApiClass));
        o.add("missingApiMember", items(r.missingApiMember));
        o.add("wrongLoaderNamespace", items(r.wrongLoader));
        o.add("unmappedNamespace", items(r.unmappedNamespace));
        o.add("externalPackages", items(r.external));
        JsonObject mixins = new JsonObject();
        mixins.addProperty("configs", a.mixinConfigs.size());
        mixins.addProperty("classes", r.mixinClassCount);
        JsonArray mt = new JsonArray();
        r.unresolvedMixinTargets.forEach(mt::add);
        mixins.add("unresolvedTargets", mt);
        o.add("mixins", mixins);
        JsonArray notes = new JsonArray();
        r.notes.forEach(notes::add);
        o.add("notes", notes);
        return o;
    }

    private static JsonArray items(List<Analyzer.Item> items) {
        JsonArray arr = new JsonArray();
        for (Analyzer.Item i : items) {
            JsonObject o = new JsonObject();
            o.addProperty("owner", i.owner);
            if (i.name != null) o.addProperty("name", i.name);
            if (i.desc != null) o.addProperty("desc", i.desc);
            o.addProperty("kind", i.kind);
            o.addProperty("refs", i.refCount);
            if (i.sources != null) {
                JsonArray s = new JsonArray();
                i.sources.forEach(s::add);
                o.add("sources", s);
            }
            if (i.note != null) o.addProperty("note", i.note);
            if (i.presentInSource != null) o.addProperty("presentInSource", i.presentInSource);
            arr.add(o);
        }
        return arr;
    }

    private static String markdown(JsonObject plan) {
        StringBuilder sb = new StringBuilder();
        JsonObject t = plan.getAsJsonObject("target");
        sb.append("# Static damage matrix (generated)\n\n");
        sb.append("Target: ").append(t.get("minecraft").getAsString()).append(" / ")
                .append(t.get("loader").getAsString()).append("\n\n");
        sb.append("| artifact | loader | verdict | missing class | missing member | desc mismatch | api class | api member | unmapped ns refs | mixin targets unresolved |\n");
        sb.append("|---|---|---|---|---|---|---|---|---|---|\n");
        for (var el : plan.getAsJsonArray("artifacts")) {
            JsonObject a = el.getAsJsonObject();
            JsonObject c = a.getAsJsonObject("counts");
            sb.append("| ").append(a.get("file").getAsString()).append(" | ")
                    .append(a.get("loader").getAsString()).append(" | ")
                    .append(a.get("verdict").getAsString()).append(" | ")
                    .append(c.get("missingClass")).append(" | ")
                    .append(c.get("missingMember")).append(" | ")
                    .append(c.get("descMismatch")).append(" | ")
                    .append(c.get("missingApiClass")).append(" | ")
                    .append(c.get("missingApiMember")).append(" | ")
                    .append(c.get("unmappedNamespaceRefs")).append(" | ")
                    .append(c.get("mixinTargetsUnresolved")).append(" |\n");
        }
        sb.append("\nGenerated ").append(plan.get("generatedAt").getAsString())
                .append(" by ").append(plan.get("tool").getAsString()).append(".\n");
        return sb.toString();
    }

    private static String now() {
        return OffsetDateTime.now().format(DateTimeFormatter.ISO_OFFSET_DATE_TIME);
    }
}
