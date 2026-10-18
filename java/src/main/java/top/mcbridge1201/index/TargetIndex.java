package top.mcbridge1201.index;

import java.util.*;

/** Namespace-aware lookup over an index of classes and their declared members. */
public final class TargetIndex {
    public enum Kind { OK, MISSING_CLASS, MISSING_MEMBER, DESC_MISMATCH, UNKNOWN, NOT_INDEXED_NAMESPACE }

    private static final java.util.Set<String> JDK_INHERITED = java.util.Set.of(
            "toString", "equals", "hashCode", "getClass", "clone", "finalize", "notify", "notifyAll", "wait",
            "ordinal", "name", "compareTo", "getDeclaringClass", "values", "valueOf", "canEqual");

    public record Resolution(Kind kind, String declaredIn, String actualDesc) {}

    public final Map<String, ClassInfo> classes = new HashMap<>();
    public final String namespace;

    public TargetIndex(String namespace) {
        this.namespace = namespace;
    }

    public boolean hasClass(String internalName) {
        return classes.containsKey(internalName);
    }

    public boolean inScope(String owner) {
        return owner.startsWith("net/minecraft/") || owner.startsWith("net/fabricmc/")
                || owner.startsWith("com/mojang/") || owner.startsWith("net/neoforged/")
                || classes.containsKey(owner);
    }

    /** Walk the hierarchy (owner, superclasses, interfaces) looking for the exact member. */
    public Resolution resolveMethod(String owner, String name, String desc) {
        if (!owner.startsWith("net/") && !owner.startsWith("com/") && !classes.containsKey(owner)) {
            return new Resolution(Kind.NOT_INDEXED_NAMESPACE, null, null);
        }
        if (!classes.containsKey(owner)) {
            return new Resolution(Kind.MISSING_CLASS, null, null);
        }
        Deque<String> queue = new ArrayDeque<>();
        Set<String> seen = new HashSet<>();
        queue.add(owner);
        boolean nameSeen = false;
        boolean unindexedAncestor = false;
        String anyDesc = null;
        String where = null;
        while (!queue.isEmpty()) {
            String cur = queue.poll();
            if (!seen.add(cur)) continue;
            ClassInfo ci = classes.get(cur);
            if (ci == null) {
                if (!cur.equals(owner) && !isObject(cur)) unindexedAncestor = true;
                continue;
            }
            Set<String> descs = ci.methods.get(name);
            if (descs != null) {
                if (descs.contains(desc)) {
                    return new Resolution(Kind.OK, cur, desc);
                }
                nameSeen = true;
                anyDesc = descs.iterator().next();
                where = cur;
            }
            if (ci.superName != null) queue.add(ci.superName);
            queue.addAll(ci.interfaces);
        }
        if (!nameSeen && JDK_INHERITED.contains(name)) {
            return new Resolution(Kind.OK, "java/lang/Object", desc);
        }
        if (nameSeen) return new Resolution(Kind.DESC_MISMATCH, where, anyDesc);
        return unindexedAncestor ? new Resolution(Kind.UNKNOWN, null, null)
                : new Resolution(Kind.MISSING_MEMBER, null, null);
    }

    public Resolution resolveField(String owner, String name, String desc) {
        if (!classes.containsKey(owner)) {
            if (inScope(owner)) return new Resolution(Kind.MISSING_CLASS, null, null);
            return new Resolution(Kind.NOT_INDEXED_NAMESPACE, null, null);
        }
        Deque<String> queue = new ArrayDeque<>();
        Set<String> seen = new HashSet<>();
        queue.add(owner);
        boolean nameSeen = false;
        boolean unindexedAncestor = false;
        String anyDesc = null;
        String where = null;
        while (!queue.isEmpty()) {
            String cur = queue.poll();
            if (!seen.add(cur)) continue;
            ClassInfo ci = classes.get(cur);
            if (ci == null) {
                // JDK ancestors are complete from the analyzer's point of view: a field
                // cannot be inherited from java.util.function.Predicate, so do not let an
                // unindexed JDK interface mask a genuinely removed field
                // (ItemPredicate.field_9640 was missed this way until a real crash exposed it).
                if (!cur.equals(owner) && !isJdk(cur)) unindexedAncestor = true;
                continue;
            }
            Set<String> descs = ci.fields.get(name);
            if (descs != null) {
                if (descs.contains(desc)) return new Resolution(Kind.OK, cur, desc);
                nameSeen = true;
                anyDesc = descs.iterator().next();
                where = cur;
            }
            if (ci.superName != null) queue.add(ci.superName);
            queue.addAll(ci.interfaces);
        }
        if (nameSeen) return new Resolution(Kind.DESC_MISMATCH, where, anyDesc);
        return unindexedAncestor ? new Resolution(Kind.UNKNOWN, null, null)
                : new Resolution(Kind.MISSING_MEMBER, null, null);
    }

    /**
     * java/lang/Object is the universal root: its members are covered by JDK_INHERITED,
     * so an unresolved member there is a real absence. Any other out-of-index ancestor
     * (including java.util.AbstractList) may legitimately supply the member.
     */
    private static boolean isObject(String owner) {
        return "java/lang/Object".equals(owner);
    }

    private static boolean isJdk(String owner) {
        return owner.startsWith("java/") || owner.startsWith("javax/") || owner.startsWith("jdk/")
                || owner.startsWith("sun/") || owner.startsWith("com/sun/");
    }

    public int classCount() {
        return classes.size();
    }

    public int methodCount() {
        int n = 0;
        for (ClassInfo c : classes.values()) for (Set<String> d : c.methods.values()) n += d.size();
        return n;
    }
}
