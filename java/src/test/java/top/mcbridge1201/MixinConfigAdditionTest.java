package top.mcbridge1201;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import org.junit.jupiter.api.Test;
import top.mcbridge1201.rules.JarPatcher;
import top.mcbridge1201.rules.RuleSet;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;
import java.util.zip.ZipOutputStream;

import static org.junit.jupiter.api.Assertions.*;

/** A stripped mixin must be re-enabled in its config, not only replaced on disk. */
class MixinConfigAdditionTest {

    private static void writeJar(Path path, Map<String, byte[]> entries) throws Exception {
        try (ZipOutputStream zos = new ZipOutputStream(Files.newOutputStream(path))) {
            for (var e : entries.entrySet()) {
                ZipEntry ze = new ZipEntry(e.getKey());
                ze.setTime(0L);
                zos.putNextEntry(ze);
                zos.write(e.getValue());
                zos.closeEntry();
            }
        }
    }

    @Test
    void addsMissingMixinClassToClientList() throws Exception {
        Path dir = Path.of("build", "test-tmp", "mixin-config-addition");
        Files.createDirectories(dir);
        Path in = dir.resolve("in.jar");
        Path out = dir.resolve("out.jar");
        String config = "{\"required\":true,\"package\":\"demo.mixin\",\"client\":[\"Kept\"]}";
        Map<String, byte[]> entries = new LinkedHashMap<>();
        entries.put("demo.mixins.json", config.getBytes(StandardCharsets.UTF_8));
        writeJar(in, entries);

        RuleSet rs = new RuleSet();
        RuleSet.MixinConfigAddition a = new RuleSet.MixinConfigAddition();
        a.id = "synthetic.readd-mixin";
        a.config = "demo.mixins.json";
        a.mixinClass = "Restored";
        rs.mixinConfigAdditions.add(a);

        JarPatcher.Result res = JarPatcher.patch(in, out, rs, null, null);
        assertEquals(1, res.applied().get(a.id));

        try (ZipFile zf = new ZipFile(out.toFile())) {
            String patched = new String(zf.getInputStream(zf.getEntry("demo.mixins.json")).readAllBytes(),
                    StandardCharsets.UTF_8);
            JsonObject root = JsonParser.parseString(patched).getAsJsonObject();
            var client = root.getAsJsonArray("client");
            assertEquals(2, client.size());
            assertEquals("Kept", client.get(0).getAsString());
            assertEquals("Restored", client.get(1).getAsString());
        }
    }

    @Test
    void doesNotDuplicateAnAlreadyListedClass() throws Exception {
        Path dir = Path.of("build", "test-tmp", "mixin-config-addition-idem");
        Files.createDirectories(dir);
        Path in = dir.resolve("in.jar");
        Path out = dir.resolve("out.jar");
        String config = "{\"client\":[\"Present\"]}";
        Map<String, byte[]> entries = new LinkedHashMap<>();
        entries.put("demo.mixins.json", config.getBytes(StandardCharsets.UTF_8));
        writeJar(in, entries);

        RuleSet rs = new RuleSet();
        RuleSet.MixinConfigAddition a = new RuleSet.MixinConfigAddition();
        a.id = "synthetic.readd-existing";
        a.config = "demo.mixins.json";
        a.mixinClass = "Present";
        rs.mixinConfigAdditions.add(a);

        JarPatcher.patch(in, out, rs, null, null);
        try (ZipFile zf = new ZipFile(out.toFile())) {
            JsonObject root = JsonParser.parseString(new String(
                    zf.getInputStream(zf.getEntry("demo.mixins.json")).readAllBytes(),
                    StandardCharsets.UTF_8)).getAsJsonObject();
            assertEquals(1, root.getAsJsonArray("client").size());
        }
    }
}
