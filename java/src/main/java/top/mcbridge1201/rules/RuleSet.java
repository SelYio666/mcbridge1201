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

    /**
     * Retargets a converted class to a bridge superclass when a Minecraft superclass constructor
     * changed shape (e.g. EntryListWidget 1.20.1's six-argument constructor becoming the
     * five-argument one in 1.21.1). The bridge subclass keeps the old constructor signature.
     */
    /**
     * Replaces an entire method body with a call to a bridge method (the original body is dropped).
     * Used when the old body depends on APIs that cannot be bridged (e.g. removed RenderSystem
     * shader access in a custom list renderer).
     */
    public static final class BodyRedirect {
        public String id;
        public String owner;
        public String name;
        public String desc;
        public String bridgeClass;
        public String bridgeMethod;
        public String bridgeDesc;
        /**
         * When true the body is not dropped wholesale: everything before the block that opens the
         * removed-API tail is kept, and only that tail is replaced by the bridge call. The boundary
         * is the label of the block that contains the first reference to a tombstone stub
         * ({@code centurybridge/gen/}). This exists because some methods do their real work - state
         * updates, list rebuilds - in the same body that ends in removed drawing calls, so dropping
         * the body also drops the side effect (Mod Menu's description panel: the rows were built
         * before the shader tail and never appeared again).
         */
        public boolean keepPrefixBeforeTombstones;
        public String capability;
        public String risk;
        public String evidence;
    }

    public static final class SuperclassReplacement {
        public String id;
        public String oldSuper;
        public String newSuper;
        public String bridgeClass;
        public String capability;
        public String risk;
        public String evidence;
    }

    public final List<FieldRedirect> fieldRedirects = new ArrayList<>();
    public final List<MethodRedirect> methodRedirects = new ArrayList<>();
    public final List<MethodRename> methodRenames = new ArrayList<>();
    public final List<BodyRedirect> bodyRedirects = new ArrayList<>();
    public final List<SuperclassReplacement> superclassReplacements = new ArrayList<>();
    public final List<CallSiteAdaptation> callSiteAdaptations = new ArrayList<>();
    public final List<ConstructorRedirect> constructorRedirects = new ArrayList<>();
    public final List<SignatureAdaptation> signatureAdaptations = new ArrayList<>();
    public final List<MixinCallbackAdaptation> mixinCallbackAdaptations = new ArrayList<>();
    public final List<MixinClassReplacement> mixinClassReplacements = new ArrayList<>();
    public final List<MixinConfigAddition> mixinConfigAdditions = new ArrayList<>();
    public final List<MixinStrip> mixinStrips = new ArrayList<>();

    /**
     * Explicit, recorded degradation: removes mixin classes from a config whose injection
     * targets no longer exist. Disabling a mixin is never silent success; the patch report
     * and the compatibility profile must list it.
     */
    public static final class MixinStrip {
        public String id;
        public String config;
        public List<String> classes = new ArrayList<>();
        public String reason;
    }

    /** A call that must gain the extra argument introduced by a signature adaptation. */
    public static final class CallRewrite {
        public String owner;
        public String name;
        public String oldDesc;
        public String newDesc;
    }

    /**
     * Adapts a mixin callback to a target method whose descriptor gained parameters. The
     * callback keeps its body but gains the new parameter slots before {@code CallbackInfo};
     * the {@code @Inject(method=...)} string is rewritten at the same time. This is separate
     * from {@link SignatureAdaptation}: that one migrates an override in the mod, while this one
     * migrates a mixin's injection target and its callback signature.
     */
    public static final class MixinCallbackAdaptation {
        public String id;
        public String mixinClass;
        public String callbackMethod;
        public String oldCallbackDesc;
        public String newCallbackDesc;
        public int insertSlot;
        /** When true the callback's old target args are replaced by new args (body must not use them). */
        public boolean replace;
        public List<String> addedParamDescs = new ArrayList<>();
        public List<String> addedParamNames = new ArrayList<>();
        public String oldTargetDescriptor;
        public String newTargetDescriptor;
        public String refmap;
        public String refmapKey;
        public String refmapValue;
        public String capability;
        public String risk;
        public String evidence;
    }

    /**
     * Replaces a mixin implementation class with a javac-compiled port for the target version.
     * Used when the mixin body depends on an API whose shape changed (not just a descriptor).
     * The replacement keeps the original mixin class name so the mixin config remains valid.
     */
    public static final class MixinClassReplacement {
        public String id;
        public String targetClass;
        public String replacementClass;
        public List<String> alsoEmbed = new ArrayList<>();
        public String capability;
        public String risk;
        public String evidence;
    }

    /**
     * Re-enables a mixin class in its mixin config after a conversion stripped it.
     * Needed together with a {@link MixinClassReplacement}: the replacement class is
     * useless if the config no longer lists it. The class name may be simple
     * ("EntityRendererMixin") or dotted ("client.foo.Bar"), matching the config style.
     */
    public static final class MixinConfigAddition {
        public String id;
        public String config;
        public String mixinClass;
        public String capability;
        public String risk;
        public String evidence;
    }

    /**
     * Migrates an override to the target version's signature by appending a parameter
     * (e.g. BlockEntity NBT methods gained a RegistryWrapper.WrapperLookup in 1.20.5).
     * Without this the method no longer overrides and vanilla silently skips it.
     */
    public static final class SignatureAdaptation {
        public String id;
        public String targetClass;
        public String methodName;
        public String oldDesc;
        public String newDesc;
        public int paramSlot;
        public List<CallRewrite> callRewrites = new ArrayList<>();
        public String capability;
        public String risk;
        public String evidence;
    }

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
    /**
     * Renames a method declaration inside one class and (optionally) rewrites {@code invokespecial}
     * calls to it. Needed when a parent method became final and the child must override the new
     * render hook instead (e.g. ButtonWidget.render → renderWidget in 1.21.1).
     */
    public static final class MethodRename {
        public String id;
        public String owner;
        public String oldName;
        public String oldDesc;
        public String newName;
        public boolean rewriteSuperCalls;
        /**
         * Only rename in classes that are this type or inherit from it. A wildcard rename has to
         * know what it is renaming for: {@code method_25394} is final on {@code ClickableWidget},
         * so a subclass that declares it must be renamed, but a class that only implements
         * {@code Renderable} (Cloth Config's list widget extends {@code class_362}) still needs
         * {@code method_25394} to be called at all. Without this gate the rename turned a working
         * list into thirteen rows that never painted.
         */
        public String onlyIfExtends;
        /** If set, classes whose direct superclass equals this name are left untouched. */
        public String excludeSuper;
        public String capability;
        public String risk;
        public String evidence;
    }

    public static final class MethodRedirect {        public String id;
        public String sourceOwner;
        public String sourceName;
        public String sourceDesc;
        public int sourceOpcode; // 184 = INVOKESTATIC, 185 = INVOKEINTERFACE, 182 = INVOKEVIRTUAL
        public String bridgeClass;
        public String bridgeMethod;
        public String bridgeDesc;
        /** Extra classes to embed from --bridge-dir when this rule applies (e.g. API shims). */
        public List<String> extraBridgeClasses;
        public String capability;
        public String risk;
        public String evidence;
    }

    /**
     * A call-site signature adaptation: the callee's descriptor changed between versions
     * (arguments were replaced, not just renamed). The old call is redirected to a
     * javac-compiled bridge with the old descriptor; the bridge receives the old arguments and
     * implements the target-version equivalent. Matched exactly by owner + name + descriptor
     * (+ opcode).
     */
    public static final class CallSiteAdaptation {
        public String id;
        public String sourceOwner;
        public String sourceName;
        public String sourceDesc;
        public int sourceOpcode; // 184 = INVOKESTATIC by default
        public String targetOwner;
        public String targetName;
        public String targetDesc;
        public String bridgeClass;
        public String bridgeMethod;
        public String bridgeDesc;
        public String capability;
        public String risk;
        public String evidence;
    }

    /**
     * Injects a registry key into a settings object that was built without one.
     *
     * <p>1.21.2 made block/item settings carry their registry key before registration; a 1.20.1
     * source never calls the setter, so this is an <em>absent call</em>, not a wrong reference.
     * None of the other rule types can express it: there is no call site to rewrite, the key is
     * not a constructor argument, and replacing the body would drop the surrounding logic.
     *
     * <p>The rewrite is deliberately narrow. It fires only when, in the same method, an instance
     * of {@code settingsClass} is constructed, the two loads pushed most recently before it are
     * replayable (a registry and an id), and a register call follows within {@code maxDistance}
     * instructions. Anything else is left untouched rather than guessed at.
     */
    public static final class RegistrationKey {
        public String id;
        /** The register call that proves this is a registration site and not any settings use. */
        public String registerOwner;
        public String registerName;
        /** Settings class, e.g. {@code net/minecraft/class_1792$class_1793}. */
        public String settingsClass;
        /** Settings constructor descriptor, e.g. {@code ()V}. */
        public String settingsCtorDesc;
        /** The setter to inject, e.g. {@code method_63686} on the settings class. */
        public String setterOwner;
        public String setterName;
        public String setterDesc;
        /** {@code RegistryKey.of} on the ResourceKey class. */
        public String keyFactoryOwner;
        public String keyFactoryName;
        public String keyFactoryDesc;
        /** {@code Registry#registryKey()} — the ResourceKey of the registry instance. */
        public String registryKeyOwner;
        public String registryKeyName;
        public String registryKeyDesc;
        /** How far ahead to look for the register call; defaults to 40 instructions. */
        public int maxDistance;
        public String capability;
        public String risk;
        public String evidence;
    }

    /**
     * Inserts one bridge call immediately before a matched call.
     *
     * <p>This exists because some fixes are "tell the bridge something before the callee runs",
     * not "replace the callee". The concrete case: ResourcefulLib evaluates a mod's
     * {@code Supplier} inside {@code FabricRegistryEntry.of}, and the registry id is sitting in a
     * local variable at that moment - a bridge can cache it in a context so the lambda that builds
     * {@code Item.Settings} can key it (runs/p258).
     *
     * <p>Stack discipline: the matched call's arguments are already on the stack when the insertion
     * happens, so the injected sequence must be net-zero. {@code ALOAD slot} pushes the argument and
     * the bridge call consumes exactly it.
     */
    public static final class InsertBeforeCall {
        public String id;
        /** The call this inserts before; matched exactly (owner + name + descriptor + opcode). */
        public String matchOwner;
        public String matchName;
        public String matchDesc;
        public int matchOpcode;
        /** Local variable slot to push as the single bridge argument. */
        public int loadLocal = -1;
        /** How to push it: "aload" (reference) or "iload" (int). */
        public String loadKind = "aload";
        public String bridgeClass;
        public String bridgeMethod;
        public String bridgeDesc;
        public String capability;
        public String risk;
        public String evidence;
    }

    public final List<InsertBeforeCall> insertBeforeCalls = new ArrayList<>();
    public final List<RegistrationKey> registrationKeys = new ArrayList<>();
    public String version;
    public String target;

    /** Schema versions this build understands. */
    public static final java.util.Set<String> SUPPORTED_SCHEMAS = java.util.Set.of("0.1-draft");

    public static RuleSet load(Path json) throws IOException {
        JsonObject o = new Gson().fromJson(Files.readString(json, StandardCharsets.UTF_8), JsonObject.class);
        RuleSet rs = new RuleSet();
        rs.version = o.has("schemaVersion") ? o.get("schemaVersion").getAsString() : null;
        rs.target = o.has("target") ? o.get("target").getAsString() : null;
        if (rs.version == null || rs.version.isBlank()) {
            throw new IOException("rule file " + json + " has no schemaVersion");
        }
        if (!SUPPORTED_SCHEMAS.contains(rs.version)) {
            throw new IOException("unsupported schemaVersion '" + rs.version + "' in " + json
                    + " (supported: " + SUPPORTED_SCHEMAS + ")");
        }
        if (rs.target == null || rs.target.isBlank()) {
            throw new IOException("rule file " + json + " has no target");
        }
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
        if (o.has("methodRenames")) {
            for (var el : o.getAsJsonArray("methodRenames")) {
                rs.methodRenames.add(new Gson().fromJson(el, MethodRename.class));
            }
        }
        if (o.has("bodyRedirects")) {
            for (var el : o.getAsJsonArray("bodyRedirects")) {
                rs.bodyRedirects.add(new Gson().fromJson(el, BodyRedirect.class));
            }
        }
        if (o.has("superclassReplacements")) {
            for (var el : o.getAsJsonArray("superclassReplacements")) {
                rs.superclassReplacements.add(new Gson().fromJson(el, SuperclassReplacement.class));
            }
        }
        if (o.has("callSiteAdaptations")) {
            for (var el : o.getAsJsonArray("callSiteAdaptations")) {
                rs.callSiteAdaptations.add(new Gson().fromJson(el, CallSiteAdaptation.class));
            }
        }
        if (o.has("constructorRedirects")) {
            for (var el : o.getAsJsonArray("constructorRedirects")) {
                rs.constructorRedirects.add(new Gson().fromJson(el, ConstructorRedirect.class));
            }
        }
        if (o.has("signatureAdaptations")) {
            for (var el : o.getAsJsonArray("signatureAdaptations")) {
                rs.signatureAdaptations.add(new Gson().fromJson(el, SignatureAdaptation.class));
            }
        }
        if (o.has("mixinCallbackAdaptations")) {
            for (var el : o.getAsJsonArray("mixinCallbackAdaptations")) {
                rs.mixinCallbackAdaptations.add(new Gson().fromJson(el, MixinCallbackAdaptation.class));
            }
        }
        if (o.has("mixinClassReplacements")) {
            for (var el : o.getAsJsonArray("mixinClassReplacements")) {
                rs.mixinClassReplacements.add(new Gson().fromJson(el, MixinClassReplacement.class));
            }
        }
        if (o.has("mixinConfigAdditions")) {
            for (var el : o.getAsJsonArray("mixinConfigAdditions")) {
                rs.mixinConfigAdditions.add(new Gson().fromJson(el, MixinConfigAddition.class));
            }
        }
        if (o.has("mixinStrips")) {
            for (var el : o.getAsJsonArray("mixinStrips")) {
                rs.mixinStrips.add(new Gson().fromJson(el, MixinStrip.class));
            }
        }
        if (o.has("insertBeforeCalls")) {
            for (var el : o.getAsJsonArray("insertBeforeCalls")) {
                rs.insertBeforeCalls.add(new Gson().fromJson(el, InsertBeforeCall.class));
            }
        }
        if (o.has("registrationKeys")) {
            for (var el : o.getAsJsonArray("registrationKeys")) {
                rs.registrationKeys.add(new Gson().fromJson(el, RegistrationKey.class));
            }
        }
        return rs;
    }

    public MixinStrip mixinStripFor(String entryName) {
        for (MixinStrip s : mixinStrips) {
            if (entryName.equals(s.config) || entryName.endsWith("/" + s.config)) return s;
        }
        return null;
    }

    public List<SignatureAdaptation> adaptationsFor(String internalClass) {
        List<SignatureAdaptation> out = new ArrayList<>();
        for (SignatureAdaptation a : signatureAdaptations) {
            if (ownerMatches(a.targetClass, internalClass)) out.add(a);
        }
        return out;
    }

    /** Mixin callback adaptations target one exact mixin class; no wildcards. */
    public List<MixinCallbackAdaptation> mixinAdaptationsFor(String internalClass) {
        List<MixinCallbackAdaptation> out = new ArrayList<>();
        for (MixinCallbackAdaptation a : mixinCallbackAdaptations) {
            if (a.mixinClass.equals(internalClass)) out.add(a);
        }
        return out;
    }

    /** Refmap entries that must be rewritten together with a mixin callback adaptation. */
    public List<MixinCallbackAdaptation> refmapAdaptationsFor(String entryName) {
        List<MixinCallbackAdaptation> out = new ArrayList<>();
        for (MixinCallbackAdaptation a : mixinCallbackAdaptations) {
            if (a.refmap != null && a.refmap.equals(entryName)) out.add(a);
        }
        return out;
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

    /**
     * Exact match only: call-site adaptations change the meaning of the call, so there is no
     * wildcard owner and no descriptor-prefix matching here.
     */
    public CallSiteAdaptation matchCallSite(String owner, String name, String desc, int opcode) {
        for (CallSiteAdaptation r : callSiteAdaptations) {
            if (!r.sourceOwner.equals(owner)) continue;
            if (!r.sourceName.equals(name)) continue;
            if (!r.sourceDesc.equals(desc)) continue;
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
