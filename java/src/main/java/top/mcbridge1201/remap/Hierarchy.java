package top.mcbridge1201.remap;

import java.util.*;

/**
 * Class hierarchy collected from a jar, used to propagate interface/override member
 * names the way TinyRemapper does.
 *
 * <p>Intermediary does not always list every implementation: a server-only override can
 * be absent from the merged mapping while its interface is mapped. Without propagation
 * the override keeps its obfuscated name and the JVM throws AbstractMethodError at
 * runtime (observed for {@code net.minecraft.class_3797.class_6489.method_48019}).
 *
 * <p>Propagation must not touch static/private methods: they do not override, and
 * intermediary names are derived from (name, descriptor) only, so mapping a private
 * helper to an interface method's name creates a duplicate method and a
 * {@code ClassFormatError} (observed for {@code net.minecraft.class_5912}).
 */
public final class Hierarchy {
    public static final class Node {
        public final String name;
        public String superName;
        public List<String> interfaces = List.of();
        public final Map<String, Integer> methods = new HashMap<>(); // name+desc -> access
        public final Set<String> fields = new HashSet<>();

        Node(String name) {
            this.name = name;
        }
    }

    public final Map<String, Node> nodes = new HashMap<>();
    /** owner#name#desc -> final name (direct map, or propagated for virtual methods). */
    public final Map<String, String> resolvedMethods = new HashMap<>();
    /** (implOwner#name#desc) -> mapped SAM name, collected from invokedynamic bootstrap args. */
    public final Map<String, String> lambdaNames = new HashMap<>();
    /** iface + "#" + indyName -> mapped SAM name (used to rename the invokedynamic site). */
    public final Map<String, String> indyNames = new HashMap<>();
    /** {implOwner, implName, implDesc, iface, samName, samDesc} pending mapping resolution. */
    public final List<String[]> pendingLambdas = new ArrayList<>();

    public Node get(String name) {
        return nodes.get(name);
    }

    public void add(String name, String superName, String[] interfaces) {
        Node n = nodes.computeIfAbsent(name, Node::new);
        n.superName = superName;
        if (interfaces != null && interfaces.length > 0) n.interfaces = List.of(interfaces);
    }

    public void addMethod(String owner, String name, String desc, int access) {
        nodes.computeIfAbsent(owner, Node::new).methods.put(name + " " + desc, access);
    }

    public void addField(String owner, String name, String desc) {
        nodes.computeIfAbsent(owner, Node::new).fields.add(name + desc);
    }

    /** Visits the owner, then superclasses and interfaces breadth-first. */
    public List<String> supertypes(String owner) {
        List<String> out = new ArrayList<>();
        Set<String> seen = new HashSet<>();
        Deque<String> q = new ArrayDeque<>();
        q.add(owner);
        while (!q.isEmpty()) {
            String cur = q.poll();
            if (cur == null || !seen.add(cur)) continue;
            out.add(cur);
            Node n = nodes.get(cur);
            if (n == null) continue;
            if (n.superName != null) q.add(n.superName);
            q.addAll(n.interfaces);
        }
        return out;
    }
}
