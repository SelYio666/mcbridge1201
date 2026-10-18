package top.mcbridge1201.rules;

import com.google.gson.Gson;
import com.google.gson.JsonObject;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

/**
 * Versioned transform rules. Each rule has an explicit match (owner/name/descriptor),
 * an action, a required capability and a risk note; nothing is matched by name alone.
 */
public final class RuleSet {
    public static final class FieldRedirect {
        public String id;
        public String sourceOwner;
        public String sourceName;
        public String sourceDesc;
        public String bridgeClass;
        public String bridgeMethod;
        public String bridgeDesc;
        public String capability;
        public String risk;
        public String evidence;
    }

    public final List<FieldRedirect> fieldRedirects = new ArrayList<>();
    public String version;
    public String target;

    public static RuleSet load(Path json) throws IOException {
        JsonObject o = new Gson().fromJson(Files.readString(json, StandardCharsets.UTF_8), JsonObject.class);
        RuleSet rs = new RuleSet();
        rs.version = o.has("schemaVersion") ? o.get("schemaVersion").getAsString() : null;
        rs.target = o.has("target") ? o.get("target").getAsString() : null;
        if (o.has("fieldRedirects")) {
            for (var el : o.getAsJsonArray("fieldRedirects")) {
                rs.fieldRedirects.add(new Gson().fromJson(el, FieldRedirect.class));
            }
        }
        return rs;
    }

    public FieldRedirect matchGetStatic(String owner, String name, String desc) {
        for (FieldRedirect r : fieldRedirects) {
            if (r.sourceOwner.equals(owner) && r.sourceName.equals(name)
                    && (r.sourceDesc == null || r.sourceDesc.equals(desc))) {
                return r;
            }
        }
        return null;
    }
}
