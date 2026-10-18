package top.mcbridge1201.analyze;

import top.mcbridge1201.index.TargetIndex;
import top.mcbridge1201.scan.ArtifactScanner;
import top.mcbridge1201.scan.Ref;
import top.mcbridge1201.scan.RefKind;

import java.util.*;

/**
 * Compares a 1.20.1 artifact's symbolic references with a target-version index.
 *
 * <p>Only references we can actually judge are reported as damage:
 * <ul>
 *   <li>intermediary-named Minecraft references are resolved against the 1.21.1
 *       class/member index built from the official client jar + intermediary mappings;</li>
 *   <li>Fabric API references are resolved against the 1.21.1 Fabric API bundle;</li>
 *   <li>Mojang-named / SRG-named Minecraft references are counted separately and marked
 *       unmapped instead of being guessed, because that needs a second namespace index.</li>
 * </ul>
 */
public final class Analyzer {
    private static final int MAX_ITEMS = 400;

    public enum Verdict { CLEAN_STATIC, BLOCKED_STATIC, NEEDS_DEPENDENCY, WRONG_LOADER, NEEDS_NAMESPACE_INDEX }

    public static final class Item {
        public String owner;
        public String name;
        public String desc;
        public String kind;
        public int refCount;
        public List<String> sources;
        public String note;
        /** true when the same reference resolved against the 1.20.1 source index (guards against mapping noise). */
        public Boolean presentInSource;
    }

    public static final class Result {
        public String verdict = Verdict.CLEAN_STATIC.name().toLowerCase(Locale.ROOT);
        public final Map<String, Integer> counts = new LinkedHashMap<>();
        public final List<Item> missingClass = new ArrayList<>();
        public final List<Item> missingMember = new ArrayList<>();
        public final List<Item> descMismatch = new ArrayList<>();
        public final List<Item> missingApiClass = new ArrayList<>();
        public final List<Item> missingApiMember = new ArrayList<>();
        public final List<Item> wrongLoader = new ArrayList<>();
        public final List<Item> unmappedNamespace = new ArrayList<>();
        public final List<Item> external = new ArrayList<>();
        public final List<String> unresolvedMixinTargets = new ArrayList<>();
        public final List<String> unresolvedMixinInjections = new ArrayList<>();
        public int mixinClassCount;
        public int mixinInjectionCount;
        public int mixinAtTargetCount;
        public final List<String> notes = new ArrayList<>();
        public boolean truncated;
    }

    private final TargetIndex mc;
    private final TargetIndex api;
    private final String targetLoader;
    private final TargetIndex source;
    private final TargetIndex sourceApi;

    public Analyzer(TargetIndex mc, TargetIndex api, String targetLoader) {
        this(mc, api, targetLoader, null, null);
    }

    public Analyzer(TargetIndex mc, TargetIndex api, String targetLoader, TargetIndex source) {
        this(mc, api, targetLoader, source, null);
    }

    public Analyzer(TargetIndex mc, TargetIndex api, String targetLoader, TargetIndex source, TargetIndex sourceApi) {
        this.mc = mc;
        this.api = api;
        this.targetLoader = targetLoader;
        this.source = source;
        this.sourceApi = sourceApi;
    }

    /** Intermediary names are class_<id>/comp_<id>; anything else under net/minecraft is Mojang/SRG. */
    static boolean isIntermediaryName(String owner) {
        return owner.startsWith("net/minecraft/class_") || owner.startsWith("net/minecraft/comp_")
                || owner.contains("/class_") || owner.contains("/comp_");
    }

    public Result analyze(ArtifactScanner.Artifact a) {
        Result r = new Result();
        Map<String, Item> missClass = new LinkedHashMap<>();
        Map<String, Item> missMember = new LinkedHashMap<>();
        Map<String, Item> mismatch = new LinkedHashMap<>();
        Map<String, Item> missApi = new LinkedHashMap<>();
        Map<String, Item> missApiMember = new LinkedHashMap<>();
        Map<String, Item> wrong = new LinkedHashMap<>();
        Map<String, Item> unmapped = new LinkedHashMap<>();
        Map<String, Integer> externalPkgs = new TreeMap<>();

        for (ArtifactScanner.RefAgg agg : a.refs.values()) {
            Ref ref = agg.ref;
            String owner = ref.owner();
            if (owner == null || owner.isEmpty()) continue;
            if (a.ownClasses.contains(owner)) continue;
            if (isJdk(owner)) continue;

            if (owner.startsWith("net/minecraft/")) {
                if (!isIntermediaryName(owner)) {
                    // Mojang-named (mixin target strings, dev-time code) or SRG-named (Forge).
                    add(unmapped, ref, agg);
                    continue;
                }
                if (ref.kind() == RefKind.CLASS) {
                    if (!mc.hasClass(owner)) add(missClass, ref, agg);
                    continue;
                }
                TargetIndex.Resolution res = ref.kind() == RefKind.METHOD
                        ? mc.resolveMethod(owner, ref.name(), ref.desc())
                        : mc.resolveField(owner, ref.name(), ref.desc());
                apply(r, missClass, missMember, mismatch, ref, agg, res);
            } else if (owner.startsWith("net/fabricmc/")) {
                if (ref.kind() == RefKind.CLASS) {
                    if (!api.hasClass(owner)) add(missApi, ref, agg);
                    continue;
                }
                TargetIndex.Resolution res = ref.kind() == RefKind.METHOD
                        ? api.resolveMethod(owner, ref.name(), ref.desc())
                        : api.resolveField(owner, ref.name(), ref.desc());
                if (res.kind() == TargetIndex.Kind.MISSING_CLASS) add(missApi, ref, agg);
                else if (res.kind() == TargetIndex.Kind.MISSING_MEMBER || res.kind() == TargetIndex.Kind.DESC_MISMATCH)
                    add(missApiMember, ref, agg);
            } else if (owner.startsWith("net/minecraftforge/") || owner.startsWith("cpw/mods/")
                    || owner.startsWith("net/neoforged/")) {
                if ("fabric".equals(targetLoader)) add(wrong, ref, agg);
                else add(missClass, ref, agg);
            } else {
                String pkg = owner.contains("/") ? owner.substring(0, owner.indexOf('/')) : owner;
                externalPkgs.merge(pkg, 1, Integer::sum);
            }
        }

        for (ArtifactScanner.MixinInfo mi : a.mixins) {
            r.mixinClassCount++;
            for (String t : mi.targets) {
                if (isIntermediaryName(t) && !mc.hasClass(t)) {
                    r.unresolvedMixinTargets.add(mi.configName + " -> " + t);
                } else if ((t.startsWith("net/minecraftforge/") || t.startsWith("net/neoforged/"))
                        && "fabric".equals(targetLoader)) {
                    r.unresolvedMixinTargets.add(mi.configName + " -> " + t + " (forge namespace)");
                }
            }
            for (ArtifactScanner.Injection inj : mi.injections) {
                r.mixinInjectionCount++;
                if (inj.targetName == null) continue;
                boolean constructor = "<init>".equals(inj.targetName) || "<clinit>".equals(inj.targetName);
                if (!inj.targetName.startsWith("method_") && !constructor) continue;
                List<String> owners = inj.targetOwner != null
                        ? List.of(inj.targetOwner) : mi.targets;
                for (String t : owners) {
                    if (!isIntermediaryName(t) || !mc.hasClass(t)) continue;
                    String desc = inj.targetDesc == null ? "" : inj.targetDesc;
                    TargetIndex.Resolution res = mc.resolveMethod(t, inj.targetName, desc);
                    boolean missing = inj.targetDesc == null
                            ? res.kind() == TargetIndex.Kind.MISSING_MEMBER
                            : res.kind() == TargetIndex.Kind.MISSING_MEMBER
                                    || res.kind() == TargetIndex.Kind.DESC_MISMATCH;
                    if (missing) {
                        r.unresolvedMixinInjections.add(mi.configName + " -> " + t + "."
                                + inj.targetName + desc + " (" + inj.annotation + ")");
                    }
                }
                if (inj.atTargetOwner != null && inj.atTargetName != null
                        && isIntermediaryName(inj.atTargetOwner) && mc.hasClass(inj.atTargetOwner)) {
                    r.mixinAtTargetCount++;
                    boolean field = inj.atTargetField || "FIELD".equals(inj.atValue);
                    boolean method = !field && (inj.atValue == null || "INVOKE".equals(inj.atValue));
                    String n = inj.atTargetName;
                    if ((field && n.startsWith("field_")) || (method
                            && (n.startsWith("method_") || n.equals("<init>") || n.equals("<clinit>")))) {
                        String desc = inj.atTargetDesc == null ? "" : inj.atTargetDesc;
                        TargetIndex.Resolution res = field
                                ? mc.resolveField(inj.atTargetOwner, n, desc)
                                : mc.resolveMethod(inj.atTargetOwner, n, desc);
                        boolean missing = inj.atTargetDesc == null
                                ? res.kind() == TargetIndex.Kind.MISSING_MEMBER
                                : res.kind() == TargetIndex.Kind.MISSING_MEMBER
                                        || res.kind() == TargetIndex.Kind.DESC_MISMATCH;
                        if (missing) {
                            r.unresolvedMixinInjections.add(mi.configName + " -> @At "
                                    + inj.atValue + " " + inj.atTargetOwner + "." + n + desc
                                    + " (" + inj.annotation + ")");
                        }
                    }
                }
            }
        }

        r.missingClass.addAll(trim(missClass, r));
        r.missingMember.addAll(trim(missMember, r));
        r.descMismatch.addAll(trim(mismatch, r));
        r.missingApiClass.addAll(trim(missApi, r));
        r.missingApiMember.addAll(trim(missApiMember, r));
        r.wrongLoader.addAll(trim(wrong, r));
        r.unmappedNamespace.addAll(trim(unmapped, r));
        for (var e : externalPkgs.entrySet()) {
            Item it = new Item();
            it.owner = e.getKey();
            it.kind = "package";
            it.refCount = e.getValue();
            r.external.add(it);
        }

        r.counts.put("missingClass", missClass.size());
        r.counts.put("missingMember", missMember.size());
        r.counts.put("descMismatch", mismatch.size());
        r.counts.put("missingApiClass", missApi.size());
        r.counts.put("missingApiMember", missApiMember.size());
        r.counts.put("wrongLoaderNamespace", wrong.size());
        r.counts.put("unmappedNamespaceRefs", unmapped.values().stream().mapToInt(i -> i.refCount).sum());
        r.counts.put("mixins", a.mixins.size());
        r.counts.put("mixinTargetsUnresolved", r.unresolvedMixinTargets.size());
        r.counts.put("mixinInjections", r.mixinInjectionCount);
        r.counts.put("mixinAtTargets", r.mixinAtTargetCount);
        r.counts.put("mixinInjectionsUnresolved", r.unresolvedMixinInjections.size());
        int confirmed = 0;
        for (List<Item> l : List.of(r.missingClass, r.missingMember, r.descMismatch, r.missingApiClass, r.missingApiMember)) {
            for (Item i : l) if (Boolean.TRUE.equals(i.presentInSource)) confirmed++;
        }
        r.counts.put("missingConfirmedInSource", confirmed);

        int hard = missClass.size() + missMember.size() + mismatch.size() + missApi.size() + missApiMember.size();
        if (a.errorCount() > 0) r.notes.add("class scan errors: " + a.errorCount());
        if (!wrong.isEmpty() && "fabric".equals(targetLoader)) {
            r.verdict = Verdict.WRONG_LOADER.name().toLowerCase(Locale.ROOT);
        } else if (!"fabric".equals(a.loader) && !"neoforge".equals(targetLoader) && !wrong.isEmpty()) {
            r.verdict = Verdict.WRONG_LOADER.name().toLowerCase(Locale.ROOT);
        } else if (hard > 0 || !r.unresolvedMixinTargets.isEmpty()
                || !r.unresolvedMixinInjections.isEmpty()) {
            r.verdict = Verdict.BLOCKED_STATIC.name().toLowerCase(Locale.ROOT);
        } else if (!unmapped.isEmpty() && missClass.isEmpty() && missMember.isEmpty()) {
            r.verdict = Verdict.NEEDS_NAMESPACE_INDEX.name().toLowerCase(Locale.ROOT);
        } else if (!r.external.isEmpty()) {
            r.verdict = Verdict.NEEDS_DEPENDENCY.name().toLowerCase(Locale.ROOT);
        }
        r.notes.add("static analysis only: a clean result is not a runtime or gameplay pass (stage ANALYZED)");
        return r;
    }

    private void apply(Result r, Map<String, Item> missClass, Map<String, Item> missMember,
                       Map<String, Item> mismatch, Ref ref, ArtifactScanner.RefAgg agg,
                       TargetIndex.Resolution res) {
        switch (res.kind()) {
            case MISSING_CLASS -> add(missClass, ref, agg);
            case MISSING_MEMBER -> add(missMember, ref, agg);
            case DESC_MISMATCH -> {
                Item it = add(mismatch, ref, agg);
                it.note = "target has same name in " + res.declaredIn() + " with desc " + res.actualDesc();
            }
            case UNKNOWN -> r.counts.merge("unresolvedDueToHierarchy", agg.count, Integer::sum);
            default -> { }
        }
    }

    private static boolean isJdk(String owner) {
        return owner.startsWith("java/") || owner.startsWith("javax/") || owner.startsWith("jdk/")
                || owner.startsWith("sun/") || owner.startsWith("com/sun/");
    }

    private Item add(Map<String, Item> map, Ref ref, ArtifactScanner.RefAgg agg) {
        Item it = map.computeIfAbsent(ref.key(), k -> {
            Item i = new Item();
            i.owner = ref.owner();
            i.name = ref.name();
            i.desc = ref.desc();
            i.kind = ref.kind().name().toLowerCase(Locale.ROOT);
            i.presentInSource = source == null ? null : resolvesInSource(ref);
            return i;
        });
        it.refCount += agg.count;
        if (it.sources == null) it.sources = new ArrayList<>();
        for (String s : agg.sources) if (it.sources.size() < 3 && !it.sources.contains(s)) it.sources.add(s);
        return it;
    }

    private boolean resolvesInSource(Ref ref) {
        if (ref.kind() == RefKind.CLASS) {
            if (ref.owner().startsWith("net/fabricmc/")) return sourceApi != null && sourceApi.hasClass(ref.owner());
            return source != null && source.hasClass(ref.owner());
        }
        TargetIndex idx = ref.owner().startsWith("net/fabricmc/") ? sourceApi : source;
        if (idx == null) return false;
        TargetIndex.Resolution res = ref.kind() == RefKind.METHOD
                ? idx.resolveMethod(ref.owner(), ref.name(), ref.desc())
                : idx.resolveField(ref.owner(), ref.name(), ref.desc());
        return res.kind() == TargetIndex.Kind.OK;
    }

    private List<Item> trim(Map<String, Item> map, Result r) {
        List<Item> all = new ArrayList<>(map.values());
        all.sort((x, y) -> Integer.compare(y.refCount, x.refCount));
        if (all.size() > MAX_ITEMS) {
            r.truncated = true;
            return new ArrayList<>(all.subList(0, MAX_ITEMS));
        }
        return all;
    }
}
