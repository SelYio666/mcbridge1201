package top.mcbridge1201.index;

import java.util.*;

/**
 * One class in an index. Names are internal (slash separated) and already in
 * the namespace the analyzer compares against (intermediary for Minecraft,
 * plain names for Fabric API).
 */
public final class ClassInfo {
    public final String name;
    public String superName;
    public List<String> interfaces = List.of();
    /** member name -> descriptors */
    public final Map<String, Set<String>> methods = new HashMap<>();
    public final Map<String, Set<String>> fields = new HashMap<>();
    public boolean isInterface;
    public boolean syntheticMissingMapping;

    public ClassInfo(String name) {
        this.name = name;
    }

    public void addMethod(String name, String desc) {
        methods.computeIfAbsent(name, k -> new HashSet<>()).add(desc);
    }

    public void addField(String name, String desc) {
        fields.computeIfAbsent(name, k -> new HashSet<>()).add(desc);
    }
}
