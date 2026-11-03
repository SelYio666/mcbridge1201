package top.mcbridge1201.profile;

import com.google.gson.Gson;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * A target profile freezes one exact conversion target as a configuration identity.
 *
 * <p>It records the source namespace and Java level, the target Minecraft/loader/API builds with
 * the SHA-256 of every index the conversion reads, the upstream engine commit, the ordered rule
 * package, the bridge ABI and the resource schema. It is <b>not</b> a support claim: whether a
 * concrete artifact converts correctly is decided by the per-artifact evidence in
 * {@code profiles/}, never by a profile file existing.
 *
 * <p>Validation is a hard gate with no silent defaults. A rule package built for another target,
 * a rule written in the wrong namespace, an index whose bytes do not match the frozen hash, a
 * bridge compiled above the target Java level or an incomplete rule package stops the conversion
 * before the output jar is created.
 */
public final class TargetProfile {
    public static final String SCHEMA = "target-profile-1";
    /** Schema versions this build understands. */
    public static final Set<String> SUPPORTED_SCHEMAS = Set.of(SCHEMA);
    /**
     * Bridge ABI this build embeds. Bumping it invalidates every compiled bridge and every cache
     * key: rule files address bridge classes by this contract, not by whatever javac produced.
     */
    public static final String BRIDGE_ABI = "mcbridge-bridge-1";

    public static final String SEVERITY_ERROR = "error";
    public static final String SEVERITY_WARNING = "warning";

    // --- schema ------------------------------------------------------------------------------

    /** One indexed file the pipeline reads, pinned by hash and by role. */
    public static final class Artifact {
        public String path;
        public String sha256;
        public Long size;
        public String role;
    }

    /** Where the converted input comes from: its namespace and Java level are part of the identity. */
    public static final class Source {
        public String minecraft;
        public String loader;
        public String namespace;
        public Integer javaMajor;
        public Integer classMajorMax;
        public String originalJarSha256;
        public String note;
    }

    /** The exact target environment. Every field is required. */
    public static final class Target {
        public String id;
        public String minecraft;
        public String loader;
        public String loaderVersion;
        public String fabricApi;
        public Integer javaMajor;
        public Integer classMajorMax;
        public String namespace;
        public String namespaceStrategy;
    }

    /** Indexes the conversion reads. Role names are fixed so a profile cannot point at the wrong file. */
    public static final class Indices {
        /** Client jar remapped to the target namespace: the javac classpath for bridge sources. */
        public Artifact bridgeStub;
        public Artifact clientJar;
        public Artifact mappings;
        public Artifact loader;
        public List<Artifact> api = new ArrayList<>();
        public List<Artifact> libs = new ArrayList<>();
        /**
         * A pinned closure file (JSON with a {@code classpath} array). Used when a target's compile
         * classpath is the whole library set rather than a handful of jars: listing 59 paths in the
         * profile would bury the identity fields, so the closure is one artifact with one hash.
         */
        public Artifact libClosure;
    }

    /** The locked upstream engine (CenturyBridge and friends) this pipeline segments with. */
    public static final class Engine {
        public String name;
        public String commit;
        public String artifactSha256;
        public String license;
        public String note;
    }

    /** Per-target output and cache locations; two targets must never share a directory. */
    public static final class Output {
        public String bridgeClasses;
        public String cache;
        public String convertedJars;
        public String reports;
    }

    /** How the plan is assembled: engine, ordered rules, bridge ABI. */
    public static final class Pipeline {
        public Engine engine;
        public List<String> ruleOrder = new ArrayList<>();
        public String bridgeAbi;
        public List<String> capabilities = new ArrayList<>();
        public Output output;
    }

    /** Resource/data schema the conversion may touch. */
    public static final class Resources {
        public Integer dataVersion;
        public Integer resourcePackFormat;
        public List<String> converters = new ArrayList<>();
        public String note;
    }

    /** What was actually exercised for this target. Absence here means "not verified", not "fine". */
    public static final class Verification {
        public String fixtureVersion;
        public List<String> testedScopes = new ArrayList<>();
        public List<String> knownGaps = new ArrayList<>();
        public String evidence;
    }

    public String schemaVersion;
    public String profileId;
    public String status;
    public String note;
    /** Explicitly refused targets: a conversion may not silently fall back to another version. */
    public List<String> refusesTargets = new ArrayList<>();
    public Source source;
    public Target target;
    public Indices indices;
    public Pipeline pipeline;
    public Resources resources;
    public Verification verification;

    // --- loading -----------------------------------------------------------------------------

    public static TargetProfile load(Path json) throws IOException {
        String text = Files.readString(json, StandardCharsets.UTF_8);
        return fromJson(text, json.toString());
    }

    public static TargetProfile fromJson(String text, String origin) throws IOException {
        JsonObject o;
        try {
            o = new Gson().fromJson(text, JsonObject.class);
        } catch (RuntimeException e) {
            throw new IOException(origin + ": not valid JSON (" + e.getMessage() + ")");
        }
        if (o == null) {
            throw new IOException(origin + ": empty profile");
        }
        TargetProfile p = new Gson().fromJson(o, TargetProfile.class);
        p.validateStructure(origin);
        return p;
    }

    /** Structure only: enough that later checks can rely on non-null fields. */
    private void validateStructure(String origin) throws IOException {
        if (schemaVersion == null || schemaVersion.isBlank()) {
            throw new IOException(origin + ": no schemaVersion");
        }
        if (!SUPPORTED_SCHEMAS.contains(schemaVersion)) {
            throw new IOException(origin + ": unsupported schemaVersion '" + schemaVersion
                    + "' (supported: " + SUPPORTED_SCHEMAS + ")");
        }
        if (profileId == null || profileId.isBlank()) {
            throw new IOException(origin + ": no profileId");
        }
        if (target == null) {
            throw new IOException(origin + ": no target block");
        }
        if (target.id == null || target.id.isBlank()) {
            throw new IOException(origin + ": target.id is required; it is the identity rules bind to");
        }
        if (target.minecraft == null || target.minecraft.isBlank()) {
            throw new IOException(origin + ": target.minecraft is required");
        }
        if (target.loader == null || target.loader.isBlank()) {
            throw new IOException(origin + ": target.loader is required");
        }
        if (target.namespace == null || target.namespace.isBlank()) {
            throw new IOException(origin + ": target.namespace is required");
        }
        if (target.javaMajor == null || target.javaMajor <= 0) {
            throw new IOException(origin + ": target.javaMajor is required");
        }
        if (target.classMajorMax == null || target.classMajorMax <= 0) {
            throw new IOException(origin + ": target.classMajorMax is required; a target must state the"
                    + " highest class file version it can load");
        }
        if (source == null) {
            throw new IOException(origin + ": no source block");
        }
        if (pipeline == null) {
            throw new IOException(origin + ": no pipeline block");
        }
        if (pipeline.bridgeAbi == null || pipeline.bridgeAbi.isBlank()) {
            throw new IOException(origin + ": pipeline.bridgeAbi is required");
        }
        if (indices == null) {
            throw new IOException(origin + ": no indices block");
        }
        if (refusesTargets == null) {
            refusesTargets = new ArrayList<>();
        }
        if (pipeline.ruleOrder == null) {
            pipeline.ruleOrder = new ArrayList<>();
        }
    }

    // --- validation --------------------------------------------------------------------------

    /** One finding. {@code code} is stable so tests and reports can assert on it. */
    public static final class Problem {
        public final String severity;
        public final String code;
        public final String message;

        public Problem(String severity, String code, String message) {
            this.severity = severity;
            this.code = code;
            this.message = message;
        }

        public boolean isError() {
            return SEVERITY_ERROR.equals(severity);
        }

        @Override
        public String toString() {
            return severity + " [" + code + "] " + message;
        }
    }

    /** Everything validation needs to look at, supplied by the caller (CLI or test). */
    public static final class Input {
        /** Repo root used to resolve relative index paths. Defaults to the working directory. */
        public Path root = Path.of("").toAbsolutePath();
        public List<Path> ruleFiles = new ArrayList<>();
        public List<Path> bridgeDirs = new ArrayList<>();
        /** Optional explicit index overrides: checked against the frozen hashes when given. */
        public Path clientJar;
        public Path mappings;
        public List<Path> apiJars = new ArrayList<>();
        public List<Path> libs = new ArrayList<>();
        /** When true a missing index file is a warning instead of an error (portable dry-run). */
        public boolean allowMissingIndices;
        /** When false the index bytes are not hashed (fast dry-run); missing files still fail. */
        public boolean verifyIndexHashes = true;
    }

    /**
     * Full gate. Errors mean "refuse to convert"; warnings mean "this is recorded but tolerated".
     *
     * @return findings in the order they were discovered, never null
     */
    public List<Problem> validate(Input in) throws IOException {
        List<Problem> out = new ArrayList<>();
        checkIdentity(out, in);
        Map<String, JsonObject> rules = loadRules(out, in);
        checkNamespaces(out, rules);
        checkRuleMetadata(out, rules);
        checkRuleOrder(out, rules);
        checkIndices(out, in);
        checkBridgeClassVersions(out, in);
        return out;
    }

    private void checkIdentity(List<Problem> out, Input in) {
        if (!BRIDGE_ABI.equals(pipeline.bridgeAbi)) {
            out.add(new Problem(SEVERITY_ERROR, "pipeline.bridge-abi",
                    "profile declares bridge ABI '" + pipeline.bridgeAbi + "' but this build embeds '"
                            + BRIDGE_ABI + "'; rule files address the bridge by ABI, so the whole"
                            + " rule package must be re-validated against the new one"));
        }
        if (pipeline.ruleOrder.isEmpty()) {
            out.add(new Problem(SEVERITY_ERROR, "pipeline.rule-order-empty",
                    "pipeline.ruleOrder is empty: an unordered rule package cannot be replayed,"
                            + " because rules that touch the same member apply in file order"));
        }
        String expected = target.loader + "-" + target.minecraft;
        if (!expected.equals(target.id)) {
            out.add(new Problem(SEVERITY_WARNING, "target.id-convention",
                    "target.id '" + target.id + "' does not follow the '<loader>-<minecraft>'"
                            + " convention ('" + expected + "'); identity checks stay exact but"
                            + " tooling that derives ids will misname this target"));
        }
        int derived = classMajorFor(target.javaMajor);
        if (derived > 0 && derived != target.classMajorMax) {
            out.add(new Problem(SEVERITY_ERROR, "target.class-major-inconsistent",
                    "target.classMajorMax=" + target.classMajorMax + " but Java " + target.javaMajor
                            + " produces class major " + derived
                            + "; a target that understates its class version will accept classes"
                            + " the runtime rejects"));
        }
        if (source.classMajorMax != null && source.classMajorMax > target.classMajorMax) {
            out.add(new Problem(SEVERITY_WARNING, "source.newer-than-target",
                    "source class major " + source.classMajorMax + " is above target "
                            + target.classMajorMax + "; every converted class must be downgraded and"
                            + " a plain remap will not do it"));
        }
    }

    /** Class major for a Java feature release (17 → 61, 21 → 65, 25 → 69). */
    public static int classMajorFor(int javaMajor) {
        if (javaMajor < 1) {
            return -1;
        }
        return javaMajor + 44;
    }

    private Map<String, JsonObject> loadRules(List<Problem> out, Input in) throws IOException {
        Map<String, JsonObject> byFile = new java.util.LinkedHashMap<>();
        Set<String> seenIds = new LinkedHashSet<>();
        for (Path p : in.ruleFiles) {
            JsonObject o;
            try {
                o = new Gson().fromJson(Files.readString(p, StandardCharsets.UTF_8), JsonObject.class);
            } catch (RuntimeException e) {
                out.add(new Problem(SEVERITY_ERROR, "rules.unparsable",
                        p + ": not valid JSON (" + e.getMessage() + ")"));
                continue;
            }
            if (o == null) {
                out.add(new Problem(SEVERITY_ERROR, "rules.unparsable", p + ": empty rule file"));
                continue;
            }
            String targetField = optString(o, "target");
            if (targetField == null || !targetField.equals(target.id)) {
                out.add(new Problem(SEVERITY_ERROR, "rules.target-mismatch",
                        p.getFileName() + " targets '" + targetField + "' but this profile is '"
                                + target.id + "'; converting an artifact with another target's rules"
                                + " applies member rewrites that do not exist there"));
            }
            String schema = optString(o, "schemaVersion");
            if (schema == null || !top.mcbridge1201.rules.RuleSet.SUPPORTED_SCHEMAS.contains(schema)) {
                out.add(new Problem(SEVERITY_ERROR, "rules.schema",
                        p.getFileName() + ": unsupported schemaVersion '" + schema + "'"));
            }
            byFile.put(p.getFileName().toString(), o);
            collectIds(out, p.getFileName().toString(), o, seenIds);
        }
        return byFile;
    }

    private static final String[][] RULE_LISTS = {
            {"fieldRedirects", "sourceOwner"},
            {"methodRedirects", "sourceOwner"},
            {"callSiteAdaptations", "sourceOwner"},
            {"callSiteAdaptations", "targetOwner"},
            {"bodyRedirects", "owner"},
            {"methodRenames", "owner"},
            {"superclassReplacements", "oldSuper"},
            {"superclassReplacements", "newSuper"},
            {"constructorRedirects", "owner"},
            {"signatureAdaptations", "targetClass"},
            {"mixinCallbackAdaptations", "mixinClass"},
            {"mixinClassReplacements", "targetClass"},
            {"mixinClassReplacements", "replacementClass"},
            {"mixinConfigAdditions", "mixinClass"},
            {"registrationKeys", "settingsClass"},
            {"registrationKeys", "setterOwner"},
            {"registrationKeys", "registryKeyOwner"},
            {"registrationKeys", "keyFactoryOwner"},
    };

    private void checkNamespaces(List<Problem> out, Map<String, JsonObject> rules) {
        String expectedNs = target.namespace;
        Set<String> offenders = new LinkedHashSet<>();
        for (Map.Entry<String, JsonObject> e : rules.entrySet()) {
            for (String[] spec : RULE_LISTS) {
                JsonElement list = e.getValue().get(spec[0]);
                if (list == null || !list.isJsonArray()) {
                    continue;
                }
                for (JsonElement el : list.getAsJsonArray()) {
                    if (!el.isJsonObject()) {
                        continue;
                    }
                    String cls = optString(el.getAsJsonObject(), spec[1]);
                    if (cls == null || cls.isBlank()) {
                        continue;
                    }
                    String ns = namespaceOf(cls);
                    if (ns != null && !ns.equals(expectedNs)) {
                        offenders.add(e.getKey() + " " + spec[0] + "." + spec[1] + " = " + cls
                                + " is " + ns);
                    }
                }
            }
        }
        if (!offenders.isEmpty()) {
            List<String> shown = new ArrayList<>(offenders);
            out.add(new Problem(SEVERITY_ERROR, "rules.namespace-mismatch",
                    "profile namespace is '" + expectedNs + "' but " + offenders.size()
                            + " rule reference(s) are written in another namespace: "
                            + String.join("; ", shown.subList(0, Math.min(3, shown.size())))
                            + (shown.size() > 3 ? "; ..." : "")));
        }
    }

    private static final Pattern INTERMEDIARY_MEMBER =
            Pattern.compile("\\b(class|method|field)_\\d+\\b");

    /**
     * Maps one class reference to the namespace it is written in, or null when it is neither
     * Minecraft's obfuscated (intermediary) nor deobfuscated (official) form.
     */
    static String namespaceOf(String raw) {
        String cls = raw.replace('.', '/');
        if (!cls.startsWith("net/minecraft/")) {
            return null;
        }
        Matcher m = INTERMEDIARY_MEMBER.matcher(cls);
        return m.find() ? "intermediary" : "official";
    }

    private void collectIds(List<Problem> out, String file, JsonObject o, Set<String> seen) {
        Set<String> handledLists = new LinkedHashSet<>();
        for (String[] spec : RULE_LISTS) {
            if (!handledLists.add(spec[0])) {
                continue; // the same list appears once per class-like field it references
            }
            JsonElement list = o.get(spec[0]);
            if (list == null || !list.isJsonArray()) {
                continue;
            }
            for (JsonElement el : list.getAsJsonArray()) {
                if (!el.isJsonObject()) {
                    continue;
                }
                String id = optString(el.getAsJsonObject(), "id");
                if (id == null || id.isBlank()) {
                    out.add(new Problem(SEVERITY_ERROR, "rules.id-missing",
                            file + " has a " + spec[0] + " entry without an id; an anonymous rule"
                                    + " cannot be reported, required or degraded"));
                    continue;
                }
                if (!seen.add(id)) {
                    out.add(new Problem(SEVERITY_WARNING, "rules.duplicate-id",
                            file + ": rule id '" + id + "' is also used by another rule file;"
                                    + " the per-id hit counts reported by patch will be merged"));
                }
            }
        }
    }

    private static final String[][] CONVERSION_LISTS = {
            {"fieldRedirects"},
            {"methodRedirects"},
            {"callSiteAdaptations"},
            {"bodyRedirects"},
            {"methodRenames"},
            {"superclassReplacements"},
            {"constructorRedirects"},
            {"signatureAdaptations"},
            {"mixinCallbackAdaptations"},
            {"mixinClassReplacements"},
            {"mixinConfigAdditions"},
            {"registrationKeys"},
    };

    /**
     * Every conversion rule must state what capability it provides, how risky it is and what
     * evidence justifies it. A rule that cannot answer those three is not a rule, it is a guess -
     * and {@code mixinStrips} is the one list allowed to answer with {@code reason} instead,
     * because a strip records a loss rather than claiming a conversion.
     */
    private void checkRuleMetadata(List<Problem> out, Map<String, JsonObject> rules) {
        for (Map.Entry<String, JsonObject> e : rules.entrySet()) {
            for (String[] spec : CONVERSION_LISTS) {
                JsonElement list = e.getValue().get(spec[0]);
                if (list == null || !list.isJsonArray()) {
                    continue;
                }
                for (JsonElement el : list.getAsJsonArray()) {
                    if (!el.isJsonObject()) {
                        continue;
                    }
                    JsonObject r = el.getAsJsonObject();
                    String id = optString(r, "id");
                    if (id == null) {
                        continue; // already reported by collectIds
                    }
                    for (String field : new String[]{"capability", "risk", "evidence"}) {
                        String v = optString(r, field);
                        if (v == null || v.isBlank()) {
                            out.add(new Problem(SEVERITY_ERROR, "rules.metadata-missing",
                                    e.getKey() + " rule '" + id + "' has no " + field
                                            + "; a conversion without declared capability/risk/evidence"
                                            + " must not be applied"));
                        }
                    }
                }
            }
            JsonElement strips = e.getValue().get("mixinStrips");
            if (strips != null && strips.isJsonArray()) {
                for (JsonElement el : strips.getAsJsonArray()) {
                    if (!el.isJsonObject()) {
                        continue;
                    }
                    JsonObject r = el.getAsJsonObject();
                    String id = optString(r, "id");
                    if (optString(r, "reason") == null) {
                        out.add(new Problem(SEVERITY_ERROR, "rules.strip-no-reason",
                                e.getKey() + " mixinStrip '" + id + "' has no reason; a silent"
                                        + " strip is indistinguishable from a crash that was hidden"));
                    }
                }
            }
        }
    }

    /**
     * The rule package has an order: rules that touch one member apply in the order they are read.
     * A caller may pass a subset (most pipelines only need a few packages), but it may not reorder
     * the profile's sequence, because that silently changes which rule wins.
     */
    private void checkRuleOrder(List<Problem> out, Map<String, JsonObject> rules) {
        if (pipeline.ruleOrder.isEmpty()) {
            return; // already reported in checkIdentity
        }
        Map<String, Integer> rank = new java.util.LinkedHashMap<>();
        for (int i = 0; i < pipeline.ruleOrder.size(); i++) {
            rank.put(normalizeRuleRef(pipeline.ruleOrder.get(i)), i);
        }
        int last = -1;
        for (String file : rules.keySet()) {
            Integer idx = rank.get(file);
            if (idx == null) {
                out.add(new Problem(SEVERITY_WARNING, "rules.not-in-profile",
                        file + " is not listed in pipeline.ruleOrder; the profile does not record"
                                + " where it applies, so this run cannot be reproduced from it"));
                continue;
            }
            if (idx < last) {
                out.add(new Problem(SEVERITY_ERROR, "rules.order-mismatch",
                        file + " appears before a rule the profile orders earlier"
                                + " (pipeline.ruleOrder index " + idx + " < previous " + last + ")"));
            }
            last = idx;
        }
    }

    private static String normalizeRuleRef(String ref) {
        String r = ref.replace('\\', '/');
        int slash = r.lastIndexOf('/');
        return slash >= 0 ? r.substring(slash + 1) : r;
    }

    private void checkIndices(List<Problem> out, Input in) throws IOException {
        List<Artifact> declared = new ArrayList<>();
        addIfPresent(declared, indices.bridgeStub);
        addIfPresent(declared, indices.clientJar);
        addIfPresent(declared, indices.mappings);
        addIfPresent(declared, indices.loader);
        if (indices.api != null) {
            indices.api.forEach(a -> addIfPresent(declared, a));
        }
        if (indices.libs != null) {
            indices.libs.forEach(a -> addIfPresent(declared, a));
        }
        addIfPresent(declared, indices.libClosure);
        for (Artifact a : declared) {
            Path p = resolve(in.root, a.path);
            if (!Files.isRegularFile(p)) {
                out.add(new Problem(in.allowMissingIndices ? SEVERITY_WARNING : SEVERITY_ERROR,
                        "indices.missing",
                        "index '" + a.role + "' at " + p + " does not exist; a target that cannot"
                                + " show its own index cannot verify what it converted against"));
                continue;
            }
            if (a.sha256 == null || a.sha256.isBlank()) {
                out.add(new Problem(SEVERITY_ERROR, "indices.no-hash",
                        "index '" + a.role + "' declares no sha256; an unpinned index is what makes a"
                                + " conversion irreproducible next month"));
                continue;
            }
            if (in.verifyIndexHashes) {
                String actual = sha256(p);
                if (!actual.equalsIgnoreCase(a.sha256)) {
                    out.add(new Problem(SEVERITY_ERROR, "indices.hash-mismatch",
                            "index '" + a.role + "' at " + p.getFileName() + " has sha256 "
                                    + actual.substring(0, 12) + " but the profile froze "
                                    + a.sha256.substring(0, Math.min(12, a.sha256.length()))
                                    + "; a different jar/mapping set silently changes every"
                                    + " member lookup"));
                }
            }
        }
        checkOverride(out, in, "clientJar", indices.clientJar, in.clientJar);
        checkOverride(out, in, "mappings", indices.mappings, in.mappings);
        for (int i = 0; i < in.apiJars.size(); i++) {
            Artifact a = (indices.api != null && i < indices.api.size()) ? indices.api.get(i) : null;
            checkOverride(out, in, "api[" + i + "]", a, in.apiJars.get(i));
        }
        for (int i = 0; i < in.libs.size(); i++) {
            Artifact a = (indices.libs != null && i < indices.libs.size()) ? indices.libs.get(i) : null;
            checkOverride(out, in, "libs[" + i + "]", a, in.libs.get(i));
        }
    }

    private void checkOverride(List<Problem> out, Input in, String role, Artifact declared, Path given)
            throws IOException {
        if (given == null) {
            return;
        }
        if (!Files.isRegularFile(given)) {
            out.add(new Problem(SEVERITY_ERROR, "indices.missing",
                    "--" + role + " " + given + " does not exist"));
            return;
        }
        if (declared == null || declared.sha256 == null) {
            out.add(new Problem(SEVERITY_WARNING, "indices.unpinned-override",
                    "--" + role + " " + given.getFileName() + " is not pinned by the profile;"
                            + " the run cannot be reproduced from this profile alone"));
            return;
        }
        if (in.verifyIndexHashes) {
            String actual = sha256(given);
            if (!actual.equalsIgnoreCase(declared.sha256)) {
                out.add(new Problem(SEVERITY_ERROR, "indices.hash-mismatch",
                        "--" + role + " " + given.getFileName() + " has sha256 "
                                + actual.substring(0, 12) + " but the profile froze "
                                + declared.sha256.substring(0, Math.min(12, declared.sha256.length()))));
            }
        }
    }

    private static void addIfPresent(List<Artifact> out, Artifact a) {
        if (a != null && a.path != null && !a.path.isBlank()) {
            out.add(a);
        }
    }

    /**
     * A bridge compiled for Java 21 must not land in a Java 17 target: the class verifier rejects
     * it at load time, after the artifact shipped. Checking the class file header here turns that
     * into a conversion-time failure.
     */
    private void checkBridgeClassVersions(List<Problem> out, Input in) throws IOException {
        int limit = target.classMajorMax;
        for (Path dir : in.bridgeDirs) {
            if (!Files.isDirectory(dir)) {
                out.add(new Problem(SEVERITY_ERROR, "bridge.dir-missing",
                        "--bridge-dir " + dir + " is not a directory"));
                continue;
            }
            List<Path> classes;
            try (var s = Files.walk(dir)) {
                classes = s.filter(Files::isRegularFile)
                        .filter(p -> p.toString().endsWith(".class"))
                        .sorted().toList();
            }
            int checked = 0;
            int bad = 0;
            String first = null;
            for (Path c : classes) {
                byte[] head = new byte[8];
                try (var is = Files.newInputStream(c)) {
                    int n = is.readNBytes(head, 0, 8);
                    if (n < 8) {
                        out.add(new Problem(SEVERITY_ERROR, "bridge.truncated",
                                c + " is shorter than a class file header"));
                        continue;
                    }
                }
                int major = ((head[6] & 0xFF) << 8) | (head[7] & 0xFF);
                checked++;
                if (major > limit) {
                    bad++;
                    if (first == null) {
                        first = dir.relativize(c).toString().replace('\\', '/') + " (major " + major + ")";
                    }
                }
            }
            if (bad > 0) {
                out.add(new Problem(SEVERITY_ERROR, "bridge.class-version",
                        bad + " of " + checked + " bridge class(es) in " + dir.getFileName()
                                + " are compiled above target class major " + limit + ", first "
                                + first + "; the target runtime cannot load them"));
            }
        }
    }

    private static Path resolve(Path root, String rel) {
        Path p = Path.of(rel.replace('\\', '/'));
        return p.isAbsolute() ? p : root.resolve(p);
    }

    static String sha256(Path p) throws IOException {
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            try (var in = Files.newInputStream(p)) {
                byte[] buf = new byte[1 << 20];
                int n;
                while ((n = in.read(buf)) > 0) {
                    md.update(buf, 0, n);
                }
            }
            StringBuilder sb = new StringBuilder();
            for (byte b : md.digest()) {
                sb.append(String.format(Locale.ROOT, "%02x", b));
            }
            return sb.toString();
        } catch (java.security.NoSuchAlgorithmException e) {
            throw new IOException("SHA-256 unavailable", e);
        }
    }

    private static String optString(JsonObject o, String key) {
        JsonElement e = o.get(key);
        if (e == null || e.isJsonNull() || !e.isJsonPrimitive()) {
            return null;
        }
        String v = e.getAsString();
        return v.isBlank() ? null : v;
    }

    /** Machine-readable summary for {@code profile-check --json}. */
    public JsonObject toJson() {
        JsonObject o = new JsonObject();
        o.addProperty("schemaVersion", schemaVersion);
        o.addProperty("profileId", profileId);
        o.addProperty("status", status);
        JsonObject t = new JsonObject();
        t.addProperty("id", target.id);
        t.addProperty("minecraft", target.minecraft);
        t.addProperty("loader", target.loader);
        t.addProperty("loaderVersion", target.loaderVersion);
        t.addProperty("fabricApi", target.fabricApi);
        t.addProperty("javaMajor", target.javaMajor);
        t.addProperty("classMajorMax", target.classMajorMax);
        t.addProperty("namespace", target.namespace);
        t.addProperty("namespaceStrategy", target.namespaceStrategy);
        o.add("target", t);
        JsonObject s = new JsonObject();
        s.addProperty("minecraft", source.minecraft);
        s.addProperty("loader", source.loader);
        s.addProperty("namespace", source.namespace);
        s.addProperty("javaMajor", source.javaMajor);
        s.addProperty("classMajorMax", source.classMajorMax);
        o.add("source", s);
        o.addProperty("bridgeAbi", pipeline.bridgeAbi);
        o.addProperty("ruleOrderEntries", pipeline.ruleOrder.size());
        if (pipeline.engine != null) {
            JsonObject eng = new JsonObject();
            eng.addProperty("name", pipeline.engine.name);
            eng.addProperty("commit", pipeline.engine.commit);
            eng.addProperty("artifactSha256", pipeline.engine.artifactSha256);
            o.add("engine", eng);
        }
        if (resources != null) {
            JsonObject r = new JsonObject();
            r.addProperty("dataVersion", resources.dataVersion);
            r.addProperty("resourcePackFormat", resources.resourcePackFormat);
            o.add("resources", r);
        }
        if (verification != null) {
            JsonObject v = new JsonObject();
            v.addProperty("fixtureVersion", verification.fixtureVersion);
            JsonArray scope = new JsonArray();
            (verification.testedScopes == null ? List.<String>of() : verification.testedScopes)
                    .forEach(scope::add);
            v.add("testedScopes", scope);
            JsonArray gaps = new JsonArray();
            (verification.knownGaps == null ? List.<String>of() : verification.knownGaps).forEach(gaps::add);
            v.add("knownGaps", gaps);
            o.add("verification", v);
        }
        JsonArray refuses = new JsonArray();
        refusesTargets.forEach(refuses::add);
        o.add("refusesTargets", refuses);
        return o;
    }
}
