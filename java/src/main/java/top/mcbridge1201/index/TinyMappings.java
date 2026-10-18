package top.mcbridge1201.index;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;

/**
 * Parser for Fabric intermediary tiny v2 mappings (namespaces: official, intermediary).
 *
 * <p>Descriptors in tiny v2 are written in the <em>first</em> namespace (official /
 * obfuscated), so member keys must be built from the raw text and descriptors must be
 * translated through the class map before they can be compared with mod bytecode
 * (which is in intermediary for Minecraft types).
 */
public final class TinyMappings {
    public final Map<String, String> classMap = new HashMap<>();      // official -> intermediary
    public final Map<String, String> methodNames = new HashMap<>();   // ownerObf + "#" + name + "#" + desc(obf) -> intermediary
    public final Map<String, String> fieldNames = new HashMap<>();

    private String currentClass;

    public static TinyMappings read(InputStream in) throws IOException {
        TinyMappings m = new TinyMappings();
        try (BufferedReader r = new BufferedReader(new InputStreamReader(in, StandardCharsets.UTF_8))) {
            String header = r.readLine();
            if (header == null || !header.startsWith("tiny\t2")) {
                throw new IOException("not a tiny v2 mappings file");
            }
            String[] hp = header.split("\t");
            if (hp.length < 5 || !"official".equals(hp[3]) || !"intermediary".equals(hp[4])) {
                throw new IOException("expected namespaces official/intermediary, got " + java.util.Arrays.toString(hp));
            }
            String line;
            while ((line = r.readLine()) != null) {
                if (line.isEmpty() || line.startsWith("#")) {
                    continue;
                }
                if (line.charAt(0) == 'c') {
                    String[] p = line.split("\t", -1);
                    if (p.length >= 3 && !p[1].isEmpty() && !p[2].isEmpty()) {
                        m.classMap.put(p[1], p[2]);
                    }
                    m.currentClass = p.length >= 2 ? p[1] : null;
                } else if (line.charAt(0) == '\t') {
                    // member line: \t m|f <desc> <obfName> <interName>
                    if (m.currentClass == null) continue;
                    int pos = 1;
                    char kind = line.charAt(pos++);
                    if (kind != 'm' && kind != 'f') continue;
                    if (line.charAt(pos) != '\t') continue;
                    pos++;
                    int t1 = line.indexOf('\t', pos);
                    if (t1 < 0) continue;
                    int t2 = line.indexOf('\t', t1 + 1);
                    if (t2 < 0) continue;
                    String desc = line.substring(pos, t1);
                    String obfName = line.substring(t1 + 1, t2);
                    String interName = line.substring(t2 + 1);
                    String key = m.currentClass + "#" + obfName + "#" + desc;
                    if (kind == 'm') m.methodNames.put(key, interName);
                    else m.fieldNames.put(key, interName);
                }
            }
        }
        return m;
    }

    /** Translate every {@code L<class>;} in a descriptor through the class map. */
    public String remapDesc(String desc) {
        if (desc == null || desc.isEmpty()) return desc;
        StringBuilder out = new StringBuilder(desc.length() + 16);
        int i = 0;
        while (i < desc.length()) {
            char c = desc.charAt(i);
            if (c == 'L') {
                int end = desc.indexOf(';', i);
                if (end < 0) {
                    out.append(desc, i, desc.length());
                    break;
                }
                String cls = desc.substring(i + 1, end);
                out.append('L').append(classMap.getOrDefault(cls, cls)).append(';');
                i = end + 1;
            } else {
                out.append(c);
                i++;
            }
        }
        return out.toString();
    }

    public String className(String official) {
        return classMap.getOrDefault(official, official);
    }
}
