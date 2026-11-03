package top.mcbridge1201;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import top.mcbridge1201.profile.TargetProfile;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * The target gate must fail for the reasons it claims to fail for.
 *
 * <p>These tests are the executable form of A02's acceptance: a wrong target, a wrong namespace,
 * a missing or substituted index, a bridge compiled above the target Java level and a reordered
 * rule package all stop before a jar is written. The positive case runs against the real frozen
 * profile and the real rule package, so the gate is also a regression test for the baseline.
 */
class TargetProfileValidationTest {
    @TempDir
    Path tmp;

    // --- positive ----------------------------------------------------------------------------

    @Test
    void frozenProfileAcceptsTheRealRulePackage() throws IOException {
        Path root = repoRoot();
        if (root == null) {
            return; // running outside the repository checkout: nothing to freeze-test
        }
        TargetProfile p = TargetProfile.load(root.resolve("targets/fabric-1.21.1.json"));
        TargetProfile.Input in = new TargetProfile.Input();
        in.root = root;
        in.allowMissingIndices = true; // work/ is gitignored; a clone has no index jars
        for (String rel : p.pipeline.ruleOrder) {
            in.ruleFiles.add(root.resolve(rel));
        }
        List<TargetProfile.Problem> problems = p.validate(in);
        List<String> errors = new ArrayList<>();
        for (TargetProfile.Problem pr : problems) {
            if (pr.isError()) {
                errors.add(pr.toString());
            }
        }
        assertTrue(errors.isEmpty(), "the frozen profile must accept its own rule package: " + errors);
        assertEquals("fabric-1.21.1", p.target.id);
        assertEquals("intermediary", p.target.namespace);
        assertEquals(TargetProfile.BRIDGE_ABI, p.pipeline.bridgeAbi);
        assertEquals(65, p.target.classMajorMax);
        assertEquals("mcbridge-bridge-1", p.pipeline.bridgeAbi);
    }

    @Test
    void everyConversionRuleInTheRealPackageDeclaresCapabilityRiskEvidence() throws IOException {
        Path root = repoRoot();
        if (root == null) {
            return;
        }
        TargetProfile p = TargetProfile.load(root.resolve("targets/fabric-1.21.1.json"));
        TargetProfile.Input in = new TargetProfile.Input();
        in.root = root;
        in.allowMissingIndices = true;
        for (String rel : p.pipeline.ruleOrder) {
            in.ruleFiles.add(root.resolve(rel));
        }
        Set<String> codes = codes(p.validate(in));
        assertFalse(codes.contains("rules.metadata-missing"),
                "a rule without capability/risk/evidence must not be in the frozen package");
        assertFalse(codes.contains("rules.id-missing"));
        assertFalse(codes.contains("rules.strip-no-reason"));
        assertFalse(codes.contains("rules.order-mismatch"));
    }

    // --- negatives: the four A02 acceptance cases ---------------------------------------------

    @Test
    void wrongTargetIsRejected() throws IOException {
        Path rules = writeRule("rules-other-target.json", "fabric-1.21.4", "net/minecraft/class_1", true);
        TargetProfile p = profile("fabric-1.21.1", "intermediary", 21, 65, TargetProfile.BRIDGE_ABI,
                List.of(rules.getFileName().toString()), null);
        Set<String> codes = codes(p.validate(inputWith(rules)));
        assertTrue(codes.contains("rules.target-mismatch"), "codes=" + codes);
    }

    @Test
    void wrongNamespaceIsRejected() throws IOException {
        // Official (deobfuscated) names against an intermediary profile.
        Path rules = writeRule("rules-official-ns.json", "fabric-1.21.1", "net/minecraft/world/entity/Entity", true);
        TargetProfile p = profile("fabric-1.21.1", "intermediary", 21, 65, TargetProfile.BRIDGE_ABI,
                List.of(rules.getFileName().toString()), null);
        Set<String> codes = codes(p.validate(inputWith(rules)));
        assertTrue(codes.contains("rules.namespace-mismatch"), "codes=" + codes);
    }

    @Test
    void missingIndexIsRejected() throws IOException {
        Path rules = writeRule("rules-ok.json", "fabric-1.21.1", "net/minecraft/class_1", true);
        TargetProfile p = profile("fabric-1.21.1", "intermediary", 21, 65, TargetProfile.BRIDGE_ABI,
                List.of(rules.getFileName().toString()),
                new IndexSpec("does/not/exist.jar", "0".repeat(64)));
        Set<String> codes = codes(p.validate(inputWith(rules)));
        assertTrue(codes.contains("indices.missing"), "codes=" + codes);
    }

    @Test
    void indexWithWrongHashIsRejected() throws IOException {
        Path index = tmp.resolve("client.jar");
        Files.write(index, "not the frozen jar".getBytes(StandardCharsets.UTF_8));
        Path rules = writeRule("rules-ok.json", "fabric-1.21.1", "net/minecraft/class_1", true);
        TargetProfile p = profile("fabric-1.21.1", "intermediary", 21, 65, TargetProfile.BRIDGE_ABI,
                List.of(rules.getFileName().toString()),
                new IndexSpec(index.getFileName().toString(), "f".repeat(64)));
        TargetProfile.Input in = inputWith(rules);
        in.root = tmp; // resolve the index relative to the temp dir
        Set<String> codes = codes(p.validate(in));
        assertTrue(codes.contains("indices.hash-mismatch"), "codes=" + codes);
    }

    @Test
    void indexWithCorrectHashPasses() throws IOException {
        Path index = tmp.resolve("client.jar");
        Files.write(index, "frozen bytes".getBytes(StandardCharsets.UTF_8));
        Path rules = writeRule("rules-ok.json", "fabric-1.21.1", "net/minecraft/class_1", true);
        TargetProfile p = profile("fabric-1.21.1", "intermediary", 21, 65, TargetProfile.BRIDGE_ABI,
                List.of(rules.getFileName().toString()),
                new IndexSpec(index.getFileName().toString(), sha256(index)));
        TargetProfile.Input in = inputWith(rules);
        in.root = tmp;
        Set<String> codes = codes(p.validate(in));
        assertFalse(codes.contains("indices.hash-mismatch"), "codes=" + codes);
        assertFalse(codes.contains("indices.missing"), "codes=" + codes);
    }

    // --- further gate behaviour --------------------------------------------------------------

    @Test
    void bridgeCompiledAboveTargetJavaIsRejected() throws IOException {
        Path rules = writeRule("rules-ok.json", "fabric-1.21.1", "net/minecraft/class_1", true);
        TargetProfile p = profile("fabric-1.21.1", "intermediary", 21, 65, TargetProfile.BRIDGE_ABI,
                List.of(rules.getFileName().toString()), null);
        Path bridges = tmp.resolve("bridges");
        Files.createDirectories(bridges);
        // Class file header only: magic + minor + major 69 (Java 25).
        Files.write(bridges.resolve("TooNew.class"), new byte[]{
                (byte) 0xCA, (byte) 0xFE, (byte) 0xBA, (byte) 0xBE, 0, 0, 0, 69});
        TargetProfile.Input in = inputWith(rules);
        in.bridgeDirs.add(bridges);
        Set<String> codes = codes(p.validate(in));
        assertTrue(codes.contains("bridge.class-version"), "codes=" + codes);
    }

    @Test
    void bridgeAtTargetJavaLevelPasses() throws IOException {
        Path rules = writeRule("rules-ok.json", "fabric-1.21.1", "net/minecraft/class_1", true);
        TargetProfile p = profile("fabric-1.21.1", "intermediary", 21, 65, TargetProfile.BRIDGE_ABI,
                List.of(rules.getFileName().toString()), null);
        Path bridges = tmp.resolve("bridges-ok");
        Files.createDirectories(bridges);
        Files.write(bridges.resolve("Fine.class"), new byte[]{
                (byte) 0xCA, (byte) 0xFE, (byte) 0xBA, (byte) 0xBE, 0, 0, 0, 65});
        TargetProfile.Input in = inputWith(rules);
        in.bridgeDirs.add(bridges);
        Set<String> codes = codes(p.validate(in));
        assertFalse(codes.contains("bridge.class-version"), "codes=" + codes);
    }

    @Test
    void reorderedRulePackageIsRejected() throws IOException {
        Path a = writeRule("a-rules.json", "fabric-1.21.1", "net/minecraft/class_1", true);
        Path b = writeRule("b-rules.json", "fabric-1.21.1", "net/minecraft/class_2", true);
        TargetProfile p = profile("fabric-1.21.1", "intermediary", 21, 65, TargetProfile.BRIDGE_ABI,
                List.of(a.getFileName().toString(), b.getFileName().toString()), null);
        TargetProfile.Input in = new TargetProfile.Input();
        in.root = tmp;
        in.allowMissingIndices = true;
        in.ruleFiles.add(b); // profile says a then b
        in.ruleFiles.add(a);
        Set<String> codes = codes(p.validate(in));
        assertTrue(codes.contains("rules.order-mismatch"), "codes=" + codes);
    }

    @Test
    void ruleWithoutCapabilityIsRejected() throws IOException {
        Path rules = writeRule("rules-nocap.json", "fabric-1.21.1", "net/minecraft/class_1", false);
        TargetProfile p = profile("fabric-1.21.1", "intermediary", 21, 65, TargetProfile.BRIDGE_ABI,
                List.of(rules.getFileName().toString()), null);
        Set<String> codes = codes(p.validate(inputWith(rules)));
        assertTrue(codes.contains("rules.metadata-missing"), "codes=" + codes);
    }

    @Test
    void emptyRuleOrderIsRejected() throws IOException {
        Path rules = writeRule("rules-ok.json", "fabric-1.21.1", "net/minecraft/class_1", true);
        TargetProfile p = profile("fabric-1.21.1", "intermediary", 21, 65, TargetProfile.BRIDGE_ABI,
                List.of(), null);
        Set<String> codes = codes(p.validate(inputWith(rules)));
        assertTrue(codes.contains("pipeline.rule-order-empty"), "codes=" + codes);
    }

    @Test
    void bridgeAbiMismatchIsRejected() throws IOException {
        Path rules = writeRule("rules-ok.json", "fabric-1.21.1", "net/minecraft/class_1", true);
        TargetProfile p = profile("fabric-1.21.1", "intermediary", 21, 65, "mcbridge-bridge-0",
                List.of(rules.getFileName().toString()), null);
        Set<String> codes = codes(p.validate(inputWith(rules)));
        assertTrue(codes.contains("pipeline.bridge-abi"), "codes=" + codes);
    }

    @Test
    void classMajorMustMatchTheDeclaredJavaLevel() throws IOException {
        Path rules = writeRule("rules-ok.json", "fabric-1.21.1", "net/minecraft/class_1", true);
        // Java 21 produces class major 65; claiming 61 means the profile would accept Java 17 classes
        // as if they were the target level.
        TargetProfile p = profile("fabric-1.21.1", "intermediary", 21, 61, TargetProfile.BRIDGE_ABI,
                List.of(rules.getFileName().toString()), null);
        Set<String> codes = codes(p.validate(inputWith(rules)));
        assertTrue(codes.contains("target.class-major-inconsistent"), "codes=" + codes);
    }

    @Test
    void profileWithoutTargetIdIsNotLoadable() {
        String json = """
                {"schemaVersion":"target-profile-1","profileId":"x",
                 "source":{},"target":{"minecraft":"1.21.1","loader":"fabric","namespace":"intermediary",
                 "javaMajor":21,"classMajorMax":65},
                 "indices":{},"pipeline":{"bridgeAbi":"mcbridge-bridge-1"}}
                """;
        IOException e = assertThrows(IOException.class, () -> TargetProfile.fromJson(json, "inline"));
        assertTrue(e.getMessage().contains("target.id"), e.getMessage());
    }

    @Test
    void unknownSchemaIsNotLoadable() {
        String json = """
                {"schemaVersion":"target-profile-99","profileId":"x","source":{},"target":{"id":"fabric-1.21.1"},
                 "indices":{},"pipeline":{"bridgeAbi":"mcbridge-bridge-1"}}
                """;
        IOException e = assertThrows(IOException.class, () -> TargetProfile.fromJson(json, "inline"));
        assertTrue(e.getMessage().contains("unsupported schemaVersion"), e.getMessage());
    }

    // --- helpers -----------------------------------------------------------------------------

    private record IndexSpec(String path, String sha256) {
    }

    private TargetProfile.Input inputWith(Path rule) {
        TargetProfile.Input in = new TargetProfile.Input();
        in.root = tmp;
        in.allowMissingIndices = true;
        in.ruleFiles.add(rule);
        return in;
    }

    private static Set<String> codes(List<TargetProfile.Problem> problems) {
        Set<String> out = new LinkedHashSet<>();
        for (TargetProfile.Problem p : problems) {
            out.add(p.code);
        }
        return out;
    }

    private Path writeRule(String name, String target, String owner, boolean withMetadata) throws IOException {
        String meta = withMetadata
                ? "\"capability\":\"c\",\"risk\":\"low\",\"evidence\":\"e\""
                : "\"risk\":\"low\",\"evidence\":\"e\"";
        String json = """
                {"schemaVersion":"0.1-draft","target":"%s",
                 "fieldRedirects":[{"id":"r1","sourceOwner":"%s","sourceName":"field_1",
                   "bridgeClass":"top/mcbridge1201/bridge/B","bridgeMethod":"m","bridgeDesc":"()V",%s}]}
                """.formatted(target, owner, meta);
        Path p = tmp.resolve(name);
        Files.writeString(p, json, StandardCharsets.UTF_8);
        return p;
    }

    private TargetProfile profile(String targetId, String namespace, int javaMajor, int classMajorMax,
                                  String abi, List<String> ruleOrder, IndexSpec index) throws IOException {
        String idx = index == null
                ? ""
                : ",\"clientJar\":{\"role\":\"target client\",\"path\":\"" + index.path()
                  + "\",\"sha256\":\"" + index.sha256() + "\"}";
        String order = String.join(",", ruleOrder.stream().map(r -> "\"" + r + "\"").toList());
        String json = """
                {"schemaVersion":"target-profile-1","profileId":"test",
                 "source":{"minecraft":"1.20.1","loader":"fabric","namespace":"intermediary",
                           "javaMajor":17,"classMajorMax":61},
                 "target":{"id":"%s","minecraft":"1.21.1","loader":"fabric","loaderVersion":"0.19.5",
                           "fabricApi":"0.102.0+1.21.1","javaMajor":%d,"classMajorMax":%d,
                           "namespace":"%s","namespaceStrategy":"version_specific_mapping_and_index"},
                 "indices":{"api":[]%s},
                 "pipeline":{"bridgeAbi":"%s","ruleOrder":[%s]},
                 "verification":{}}
                """.formatted(targetId, javaMajor, classMajorMax, namespace, idx, abi, order);
        Path p = tmp.resolve("target-profile.json");
        Files.writeString(p, json, StandardCharsets.UTF_8);
        return TargetProfile.load(p);
    }

    private static String sha256(Path p) throws IOException {
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            return HexFormat.of().formatHex(md.digest(Files.readAllBytes(p)));
        } catch (java.security.NoSuchAlgorithmException e) {
            throw new IOException(e);
        }
    }

    /** Walk up from the working directory until the frozen profile is found. */
    private static Path repoRoot() {
        Path cur = Path.of("").toAbsolutePath();
        for (int i = 0; i < 4 && cur != null; i++) {
            if (Files.isRegularFile(cur.resolve("targets/fabric-1.21.1.json"))) {
                return cur;
            }
            cur = cur.getParent();
        }
        return null;
    }
}
