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
    public final List<MethodRedirect> methodRedirects = new ArrayList<>();
    public final List<ConstructorRedirect> constructorRedirects = new ArrayList<>();

    /**
     * Replaces {@code new X(a,b) + invokespecial X.<init>(a,b)} with a static factory call.
     * Needed when a constructor became private (e.g. {@code new Identifier(ns, path)} in 1.21.1).
     */
    public static final class ConstructorRedirect {
        public String id;
        public String owner;
        public String desc;
        public String bridgeClass;
        public String bridgeMethod;
        public String bridgeDesc;
        public String capability;
        public String risk;
        public String evidence;
    }

    /** Rewrites an interface/static call to a bridge method that adapts the callee's shape. */
    public static final class MethodRedirect {
        public String id;
        public String sourceOwner;
        public String sourceName;
        public String sourceDesc;
        public int sourceOpcode; // 184 = INVOKESTATIC, 185 = INVOKEINTERFACE, 182 = INVOKEVIRTUAL
        public String bridgeClass;
        public String bridgeMethod;
        public String bridgeDesc;
        public String capability;
        public String risk;
        public String evidence;
    }
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
        if (o.has("methodRedirects")) {
            for (var el : o.getAsJsonArray("methodRedirects")) {
                rs.methodRedirects.add(new Gson().fromJson(el, MethodRedirect.class));
            }
        }
        if (o.has("constructorRedirects")) {
            for (var el : o.getAsJsonArray("constructorRedirects")) {
                rs.constructorRedirects.add(new Gson().fromJson(el, ConstructorRedirect.class));
            }
        }
        return rs;
    }

    public ConstructorRedirect matchConstructor(String owner, String desc) {
        for (ConstructorRedirect r : constructorRedirects) {
            if (ownerMatches(r.owner, owner) && r.desc.equals(desc)) {
                return r;
            }
        }
        return null;
    }

    public MethodRedirect matchInvoke(String owner, String name, String desc, int opcode) {
        for (MethodRedirect r : methodRedirects) {
            if (!ownerMatches(r.sourceOwner, owner)) continue;
            if (r.sourceName != null && !r.sourceName.isEmpty() && !r.sourceName.equals(name)) continue;
            if (r.sourceDesc != null && !r.sourceDesc.equals(desc)) continue;
            if (r.sourceOpcode != 0 && r.sourceOpcode != opcode) continue;
            return r;
        }
        return null;
    }

    /** A trailing '*' allows matching generated helper classes (e.g. tombstone stubs). */
    private static boolean ownerMatches(String pattern, String owner) {
        if (pattern.endsWith("*")) {
            return owner.startsWith(pattern.substring(0, pattern.length() - 1));
        }
        return pattern.equals(owner);
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
