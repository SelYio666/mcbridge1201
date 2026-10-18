package top.mcbridge1201.scan;

/** A single symbolic reference found in a class file. */
public record Ref(RefKind kind, String owner, String name, String desc) {
    public String key() {
        return kind + "\u0000" + owner + "\u0000" + (name == null ? "" : name) + "\u0000" + (desc == null ? "" : desc);
    }
}
