package top.mcbridge1201.rules;

import org.objectweb.asm.ClassReader;
import org.objectweb.asm.ClassWriter;
import org.objectweb.asm.Opcodes;
import org.objectweb.asm.Type;
import org.objectweb.asm.tree.AbstractInsnNode;
import org.objectweb.asm.tree.AnnotationNode;
import org.objectweb.asm.tree.ClassNode;
import org.objectweb.asm.tree.FieldInsnNode;
import org.objectweb.asm.tree.InsnList;
import org.objectweb.asm.tree.LabelNode;
import org.objectweb.asm.tree.LocalVariableNode;
import org.objectweb.asm.tree.MethodInsnNode;
import org.objectweb.asm.tree.MethodNode;
import org.objectweb.asm.tree.ParameterNode;

import java.io.BufferedOutputStream;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.*;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;
import java.util.zip.ZipInputStream;
import java.util.zip.ZipOutputStream;

/**
 * Applies {@link RuleSet} rewrites to a jar (recursing into nested jars) and embeds the
 * referenced bridge classes. Deterministic output (fixed entry timestamps), no zipfs.
 */
public final class JarPatcher {
    public record Result(Map<String, Integer> applied, int classes, Set<String> bridges,
                         int nestedJars, Set<String> externalBridges) {}

    private static final class Stats {
        final Map<String, Integer> applied = new TreeMap<>();
        final Set<String> bridges = new TreeSet<>();
        final Set<String> external = new TreeSet<>();
        int classes;
        int nested;
    }

    public static Result patch(Path in, Path out, RuleSet rules) throws IOException {
        return patch(in, out, rules, null, Map.of());
    }

    /**
     * @param targetIndex optional 1.21.1 index; when present, method-reference constant kinds
     *                    are corrected (a class that became an interface needs an
     *                    InterfaceMethodref, otherwise the JVM throws IncompatibleClassChangeError:
     *                    observed for {@code com.mojang.serialization.DataResult} after 1.20.5).
     */
    public static Result patch(Path in, Path out, RuleSet rules,
                               top.mcbridge1201.index.TargetIndex targetIndex) throws IOException {
        return patch(in, out, rules, targetIndex, Map.of());
    }

    /**
     * @param bridgeClasses javac-compiled bridge classes keyed by internal name (e.g.
     *                      {@code top/mcbridge1201/bridge/Foo}). Used by call-site adaptations,
     *                      whose bridges are Java source compiled against the target stub rather
     *                      than generated as ASM. Nested classes named {@code Foo$Bar} are
     *                      embedded with their outer class.
     */
    public static Result patch(Path in, Path out, RuleSet rules,
                               top.mcbridge1201.index.TargetIndex targetIndex,
                               Map<String, byte[]> bridgeClasses) throws IOException {
        Map<String, byte[]> entries = new LinkedHashMap<>();
        try (ZipFile zf = new ZipFile(in.toFile())) {
            var en = zf.entries();
            while (en.hasMoreElements()) {
                var e = en.nextElement();
                if (e.isDirectory()) continue;
                entries.put(e.getName(), readAll(zf.getInputStream(e)));
            }
        }
        Stats st = new Stats();
        Map<String, byte[]> patched = patchEntries(entries, rules, targetIndex, st, true);
        // Bridges generated as ASM by the tool itself (existing rules).
        Set<String> generatedNames = new TreeSet<>();
        for (String name : st.bridges) {
            if (BridgeGenerator.isGenerated(name)) generatedNames.add(name);
        }
        for (var e : BridgeGenerator.generate(generatedNames).entrySet()) {
            patched.put(e.getKey() + ".class", e.getValue());
        }
        // Bridges compiled by javac (call-site adaptations). An unknown bridge is a hard error:
        // silently emitting a call to a missing class would defer the failure to server boot.
        for (String used : st.bridges) {
            if (BridgeGenerator.isGenerated(used)) continue;
            if (bridgeClasses == null || !bridgeClasses.containsKey(used)) {
                throw new IllegalArgumentException("bridge class " + used
                        + " is not generated and was not supplied (use --bridge-dir)");
            }
            boolean embedded = false;
            for (var e : bridgeClasses.entrySet()) {
                if (e.getKey().equals(used) || e.getKey().startsWith(used + "$")) {
                    patched.put(e.getKey() + ".class", e.getValue());
                    embedded = true;
                }
            }
            if (!embedded) {
                throw new IllegalArgumentException("compiled bridge class missing: " + used);
            }
            st.external.add(used);
        }
        Files.createDirectories(out.toAbsolutePath().getParent());
        writeZip(patched, out);
        return new Result(st.applied, st.classes, st.bridges, st.nested, st.external);
    }

    private static Map<String, byte[]> patchEntries(Map<String, byte[]> entries, RuleSet rules,
                                                    top.mcbridge1201.index.TargetIndex idx,
                                                    Stats st, boolean topLevel) {
        Map<String, byte[]> out = new LinkedHashMap<>();
        for (Map.Entry<String, byte[]> e : entries.entrySet()) {
            String name = e.getKey();
            if (name.startsWith("META-INF/") && (name.endsWith(".SF") || name.endsWith(".RSA")
                    || name.endsWith(".DSA") || name.endsWith(".EC"))) {
                continue; // patched content invalidates signatures
            }
            if (name.endsWith(".jar") && looksLikeZip(e.getValue())) {
                Map<String, byte[]> nested = readZip(e.getValue());
                Map<String, byte[]> fixed = patchEntries(nested, rules, idx, st, false);
                out.put(name, writeZipBytes(fixed));
                st.nested++;
                continue;
            }
            RuleSet.MixinStrip strip = rules.mixinStripFor(name);
            if (strip != null) {
                out.put(name, stripMixinConfig(e.getValue(), strip, st));
                continue;
            }
            List<RuleSet.MixinCallbackAdaptation> refmaps = rules.refmapAdaptationsFor(name);
            if (!refmaps.isEmpty()) {
                out.put(name, patchRefmap(e.getValue(), refmaps, st));
                continue;
            }
            if (!name.endsWith(".class")) {
                out.put(name, e.getValue());
                continue;
            }
            byte[] bytes = patchClass(e.getValue(), rules, idx, st);
            out.put(name, bytes);
        }
        return out;
    }

    private static byte[] patchClass(byte[] bytes, RuleSet rules,
                                     top.mcbridge1201.index.TargetIndex idx, Stats st) {
        ClassNode cn = new ClassNode();
        new ClassReader(bytes).accept(cn, 0);
        boolean changed = false;
        boolean framesAffected = false;
        if (applyMixinCallbackAdaptations(cn, rules, st)) {
            changed = true;
            framesAffected = true;
        }
        if (applySignatureAdaptations(cn, rules, st)) {
            changed = true;
            framesAffected = true;
        }
        for (MethodNode mn : cn.methods) {
            InsnList insns = mn.instructions;
            for (AbstractInsnNode insn = insns.getFirst(); insn != null; ) {
                AbstractInsnNode next = insn.getNext();
                if (insn instanceof MethodInsnNode m && m.getOpcode() == Opcodes.INVOKESPECIAL
                        && "<init>".equals(m.name)) {
                    RuleSet.ConstructorRedirect r = rules.matchConstructor(m.owner, m.desc);
                    if (r != null && rewriteConstructor(insns, m, r)) {
                        st.applied.merge(r.id, 1, Integer::sum);
                        st.bridges.add(r.bridgeClass);
                        changed = true;
                        framesAffected = true;
                    }
                }
                if (insn instanceof FieldInsnNode f && f.getOpcode() == Opcodes.GETSTATIC) {
                    RuleSet.FieldRedirect r = rules.matchGetStatic(f.owner, f.name, f.desc);
                    if (r != null) {
                        insns.set(insn, new MethodInsnNode(Opcodes.INVOKESTATIC,
                                r.bridgeClass, r.bridgeMethod, r.bridgeDesc, false));
                        st.applied.merge(r.id, 1, Integer::sum);
                        st.bridges.add(r.bridgeClass);
                        changed = true;
                    }
                } else if (insn instanceof MethodInsnNode m0) {
                    if (System.getenv("MCB_DEBUG_RULES") != null
                            && m0.desc.contains("JsonElement;)Lnet/minecraft/class_2073;")) {
                        System.out.printf("DEBUG invoke %d %s.%s%s%n", m0.getOpcode(), m0.owner, m0.name, m0.desc);
                    }
                    RuleSet.CallSiteAdaptation cs =
                            rules.matchCallSite(m0.owner, m0.name, m0.desc, m0.getOpcode());
                    if (cs != null) {
                        // The callee's arguments were replaced, not just renamed. Keep the old
                        // stack shape and hand it to a javac-compiled bridge.
                        insns.set(insn, new MethodInsnNode(Opcodes.INVOKESTATIC,
                                cs.bridgeClass, cs.bridgeMethod, cs.bridgeDesc, false));
                        st.applied.merge(cs.id, 1, Integer::sum);
                        st.bridges.add(cs.bridgeClass);
                        changed = true;
                    } else {
                        RuleSet.MethodRedirect r =
                                rules.matchInvoke(m0.owner, m0.name, m0.desc, m0.getOpcode());
                        if (r != null) {
                            insns.set(insn, new MethodInsnNode(Opcodes.INVOKESTATIC,
                                    r.bridgeClass, r.bridgeMethod, r.bridgeDesc, false));
                            st.applied.merge(r.id, 1, Integer::sum);
                            st.bridges.add(r.bridgeClass);
                            changed = true;
                        }
                    }
                }
                insn = next;
            }
            for (AbstractInsnNode insn = insns.getFirst(); insn != null; insn = insn.getNext()) {
                if (idx != null) {
                    if (insn instanceof MethodInsnNode m && fixKind(m, idx)) {
                        st.applied.merge("constant-kind-fix", 1, Integer::sum);
                        changed = true;
                    }
                    if (fixHandles(insn, idx)) {
                        st.applied.merge("constant-kind-fix-handle", 1, Integer::sum);
                        changed = true;
                    }
                }
                // Handles can carry a call-site adaptation even when no target index was
                // supplied; the rule itself is exact, so it is safe to apply unconditionally.
                if (applyHandleRules(insn, rules, st)) {
                    changed = true;
                }
            }
        }
        if (!changed) return bytes;
        // A constructor redirect removes NEW/DUP, so frames must be recomputed.
        ClassWriter cw = framesAffected ? new SafeClassWriter() : new ClassWriter(0);
        cn.accept(cw);
        st.classes++;
        return cw.toByteArray();
    }

    /**
     * Adapts a mixin callback whose target method gained parameters: the callback gains the
     * new parameter slots before {@code CallbackInfo}, and the {@code @Inject(method=...)}
     * string is rewritten to the target version's descriptor.
     */
    private static boolean applyMixinCallbackAdaptations(ClassNode cn, RuleSet rules, Stats st) {
        boolean any = false;
        for (RuleSet.MixinCallbackAdaptation a : rules.mixinAdaptationsFor(cn.name)) {
            for (MethodNode mn : cn.methods) {
                if (!mn.name.equals(a.callbackMethod) || !mn.desc.equals(a.oldCallbackDesc)) continue;
                if (a.replace) {
                    // The callback body only uses `this`; replace the captured target args with
                    // the target version's args and drop the now-stale debug metadata.
                    int oldArgSlots = Type.getArgumentsAndReturnSizes(a.oldCallbackDesc) >> 2;
                    for (AbstractInsnNode insn = mn.instructions.getFirst(); insn != null; insn = insn.getNext()) {
                        if (insn instanceof org.objectweb.asm.tree.VarInsnNode v
                                && v.var >= 1 && v.var < oldArgSlots) {
                            throw new IllegalArgumentException(a.id + ": replace mode cannot be used; "
                                    + "callback reads captured argument slot " + v.var);
                        }
                        if (insn instanceof org.objectweb.asm.tree.IincInsnNode i
                                && i.var >= 1 && i.var < oldArgSlots) {
                            throw new IllegalArgumentException(a.id + ": replace mode cannot be used; "
                                    + "callback increments captured argument slot " + i.var);
                        }
                    }
                    mn.desc = a.newCallbackDesc;
                    mn.maxLocals = Math.max(mn.maxLocals, Type.getArgumentsAndReturnSizes(a.newCallbackDesc) >> 2);
                    mn.parameters = null;
                    mn.localVariables = null;
                } else {
                    int delta = 0;
                    for (String d : a.addedParamDescs) delta += Type.getType(d).getSize();
                    if (delta == 0) continue;
                    shiftLocals(mn, a.insertSlot, delta);
                    mn.desc = a.newCallbackDesc;
                    mn.maxLocals += delta;
                    addMixinParameters(mn, a);
                }
                rewriteInjectTarget(mn, a.oldTargetDescriptor, a.newTargetDescriptor);
                st.applied.merge(a.id, 1, Integer::sum);
                any = true;
            }
        }
        return any;
    }

    private static void addMixinParameters(MethodNode mn, RuleSet.MixinCallbackAdaptation a) {
        if (mn.parameters != null && !mn.parameters.isEmpty()) {
            int at = Math.max(0, mn.parameters.size() - 1); // keep CallbackInfo last
            for (int i = 0; i < a.addedParamDescs.size(); i++) {
                String name = i < a.addedParamNames.size() ? a.addedParamNames.get(i) : "p" + i;
                mn.parameters.add(at + i, new ParameterNode(name, 0));
            }
        }
        if (mn.localVariables != null && !mn.localVariables.isEmpty()) {
            LabelNode start = null;
            LabelNode end = null;
            for (AbstractInsnNode insn = mn.instructions.getFirst(); insn != null; insn = insn.getNext()) {
                if (insn instanceof LabelNode l) {
                    if (start == null) start = l;
                    end = l;
                }
            }
            if (start != null) {
                int slot = a.insertSlot;
                for (int i = 0; i < a.addedParamDescs.size(); i++) {
                    String name = i < a.addedParamNames.size() ? a.addedParamNames.get(i) : "p" + i;
                    String desc = a.addedParamDescs.get(i);
                    mn.localVariables.add(new LocalVariableNode(name, desc, null, start, end, slot));
                    slot += Type.getType(desc).getSize();
                }
            }
        }
    }

    @SuppressWarnings("unchecked")
    private static void rewriteInjectTarget(MethodNode mn, String oldTarget, String newTarget) {
        if (oldTarget == null || newTarget == null) return;
        for (List<AnnotationNode> annotations : Arrays.asList(mn.visibleAnnotations, mn.invisibleAnnotations)) {
            if (annotations == null) continue;
            for (AnnotationNode an : annotations) {
                if (!"Lorg/spongepowered/asm/mixin/injection/Inject;".equals(an.desc) || an.values == null) {
                    continue;
                }
                for (int i = 0; i + 1 < an.values.size(); i += 2) {
                    if (!"method".equals(an.values.get(i))) continue;
                    Object value = an.values.get(i + 1);
                    if (value instanceof List<?> raw) {
                        List<Object> list = (List<Object>) raw;
                        for (int j = 0; j < list.size(); j++) {
                            if (oldTarget.equals(list.get(j))) list.set(j, newTarget);
                        }
                    } else if (value instanceof String s && oldTarget.equals(s)) {
                        an.values.set(i + 1, newTarget);
                    }
                }
            }
        }
    }

    /**
     * Appends a parameter to an override so it keeps overriding the target method, shifting
     * existing locals and forwarding the new argument to the listed calls.
     */
    private static boolean applySignatureAdaptations(ClassNode cn, RuleSet rules, Stats st) {
        boolean any = false;
        for (RuleSet.SignatureAdaptation a : rules.adaptationsFor(cn.name)) {
            for (MethodNode mn : cn.methods) {
                if (!mn.name.equals(a.methodName) || !mn.desc.equals(a.oldDesc)) continue;
                shiftLocals(mn, a.paramSlot, 1);
                mn.desc = a.newDesc;
                mn.maxLocals = Math.max(mn.maxLocals + 1, a.paramSlot + 1);
                for (AbstractInsnNode insn = mn.instructions.getFirst(); insn != null; insn = insn.getNext()) {
                    if (!(insn instanceof MethodInsnNode m)) continue;
                    for (RuleSet.CallRewrite cw : a.callRewrites) {
                        boolean ownerOk = cw.owner == null || cw.owner.equals(m.owner);
                        if (ownerOk && cw.name.equals(m.name) && cw.oldDesc.equals(m.desc)) {
                            m.desc = cw.newDesc;
                            mn.instructions.insertBefore(m,
                                    new org.objectweb.asm.tree.VarInsnNode(Opcodes.ALOAD, a.paramSlot));
                            st.applied.merge(a.id + "/call", 1, Integer::sum);
                            break;
                        }
                    }
                }
                st.applied.merge(a.id, 1, Integer::sum);
                any = true;
            }
        }
        return any;
    }

    private static void shiftLocals(MethodNode mn, int fromSlot, int delta) {
        for (AbstractInsnNode insn = mn.instructions.getFirst(); insn != null; insn = insn.getNext()) {
            if (insn instanceof org.objectweb.asm.tree.VarInsnNode v && v.var >= fromSlot) {
                v.var += delta;
            } else if (insn instanceof org.objectweb.asm.tree.IincInsnNode i && i.var >= fromSlot) {
                i.var += delta;
            }
        }
        if (mn.localVariables != null) {
            for (var lv : mn.localVariables) {
                if (lv.index >= fromSlot) lv.index += delta;
            }
        }
    }

    /**
     * Rewrites {@code NEW X; DUP; <pure pushes>; INVOKESPECIAL X.<init>} into
     * {@code <pure pushes>; INVOKESTATIC bridge}. Only used when the constructor became
     * private and a public factory exists (Identifier in 1.21).
     */
    private static boolean rewriteConstructor(InsnList insns, MethodInsnNode call,
                                              RuleSet.ConstructorRedirect r) {
        // walk back over the argument pushes to the DUP that follows NEW
        AbstractInsnNode dup = null;
        for (AbstractInsnNode p = call.getPrevious(); p != null; p = p.getPrevious()) {
            if (p instanceof org.objectweb.asm.tree.LabelNode
                    || p instanceof org.objectweb.asm.tree.JumpInsnNode) {
                return false; // control flow between allocation and call: do not touch
            }
            if (p instanceof org.objectweb.asm.tree.MethodInsnNode) return false;
            if (p instanceof FieldInsnNode f) {
                if (f.getOpcode() != Opcodes.GETSTATIC) return false;
                continue;
            }
            if (p instanceof org.objectweb.asm.tree.InsnNode i && i.getOpcode() == Opcodes.DUP) {
                dup = p;
                break;
            }
            if (!isPurePush(p.getOpcode())) return false;
        }
        if (dup == null) return false;
        AbstractInsnNode newInsn = dup.getPrevious();
        if (!(newInsn instanceof org.objectweb.asm.tree.TypeInsnNode t)
                || t.getOpcode() != Opcodes.NEW || !t.desc.equals(r.owner)) {
            return false;
        }
        insns.remove(newInsn);
        insns.remove(dup);
        insns.set(call, new MethodInsnNode(Opcodes.INVOKESTATIC, r.bridgeClass, r.bridgeMethod,
                r.bridgeDesc, false));
        return true;
    }

    private static boolean isPurePush(int opcode) {
        return switch (opcode) {
            case Opcodes.ALOAD, Opcodes.ILOAD, Opcodes.LLOAD, Opcodes.FLOAD, Opcodes.DLOAD,
                 Opcodes.LDC, Opcodes.ACONST_NULL, Opcodes.ICONST_M1, Opcodes.ICONST_0, Opcodes.ICONST_1,
                 Opcodes.ICONST_2, Opcodes.ICONST_3, Opcodes.ICONST_4, Opcodes.ICONST_5,
                 Opcodes.LCONST_0, Opcodes.LCONST_1, Opcodes.FCONST_0, Opcodes.FCONST_1, Opcodes.FCONST_2,
                 Opcodes.DCONST_0, Opcodes.DCONST_1, Opcodes.BIPUSH, Opcodes.SIPUSH -> true;
            default -> false;
        };
    }

    /** Frames are recomputed without resolving game types (not on this tool's classpath). */
    private static final class SafeClassWriter extends ClassWriter {
        SafeClassWriter() {
            super(ClassWriter.COMPUTE_FRAMES | ClassWriter.COMPUTE_MAXS);
        }

        @Override
        protected String getCommonSuperClass(String type1, String type2) {
            return "java/lang/Object";
        }
    }

    private static boolean fixKind(MethodInsnNode m, top.mcbridge1201.index.TargetIndex idx) {
        var info = idx.classes.get(m.owner);
        if (info == null) return false;
        int op = m.getOpcode();
        if (info.isInterface) {
            if (op == Opcodes.INVOKESTATIC && !m.itf) {
                m.itf = true;
                return true;
            }
            if (op == Opcodes.INVOKEVIRTUAL) {
                m.setOpcode(Opcodes.INVOKEINTERFACE);
                m.itf = true;
                return true;
            }
        } else if (m.itf && op != Opcodes.INVOKEINTERFACE) {
            m.itf = false;
            return true;
        }
        return false;
    }

    /**
     * Method handles carry their own kind bit; a REF_invokeStatic on an interface also needs
     * an InterfaceMethodref (observed in a MethodHandle bootstrap argument:
     * {@code ShapeTypes.decode} referenced {@code DataResult.success} through a handle).
     */
    /**
     * A method reference can also be a lambda implementation handle rather than a direct
     * instruction (observed: CenturyBridge's tombstone {@code t6(JsonElement)} was passed as a
     * MethodHandle to ResourcefulLib's passthrough). Handle matches are redirected like calls.
     */
    private static boolean applyHandleRules(AbstractInsnNode insn, RuleSet rules, Stats st) {
        if (insn instanceof org.objectweb.asm.tree.InvokeDynamicInsnNode indy) {
            boolean any = false;
            for (int i = 0; i < indy.bsmArgs.length; i++) {
                if (indy.bsmArgs[i] instanceof org.objectweb.asm.Handle h) {
                    var fixed = redirectHandle(h, rules, st);
                    if (fixed != null) {
                        indy.bsmArgs[i] = fixed;
                        any = true;
                    }
                }
            }
            return any;
        }
        if (insn instanceof org.objectweb.asm.tree.LdcInsnNode ldc
                && ldc.cst instanceof org.objectweb.asm.Handle h) {
            var fixed = redirectHandle(h, rules, st);
            if (fixed != null) {
                ldc.cst = fixed;
                return true;
            }
        }
        return false;
    }

    private static org.objectweb.asm.Handle redirectHandle(org.objectweb.asm.Handle h, RuleSet rules, Stats st) {
        int opcode = h.getTag() == Opcodes.H_INVOKESTATIC ? Opcodes.INVOKESTATIC
                : h.getTag() == Opcodes.H_INVOKEVIRTUAL ? Opcodes.INVOKEVIRTUAL : 0;
        if (opcode == 0) return null;
        RuleSet.CallSiteAdaptation cs = rules.matchCallSite(h.getOwner(), h.getName(), h.getDesc(), opcode);
        if (cs != null) {
            st.applied.merge(cs.id, 1, Integer::sum);
            st.bridges.add(cs.bridgeClass);
            return new org.objectweb.asm.Handle(Opcodes.H_INVOKESTATIC, cs.bridgeClass, cs.bridgeMethod,
                    cs.bridgeDesc, false);
        }
        RuleSet.MethodRedirect r = rules.matchInvoke(h.getOwner(), h.getName(), h.getDesc(), opcode);
        if (r == null) return null;
        st.applied.merge(r.id, 1, Integer::sum);
        st.bridges.add(r.bridgeClass);
        return new org.objectweb.asm.Handle(Opcodes.H_INVOKESTATIC, r.bridgeClass, r.bridgeMethod,
                r.bridgeDesc, false);
    }

    private static boolean fixHandles(AbstractInsnNode insn, top.mcbridge1201.index.TargetIndex idx) {
        if (insn instanceof org.objectweb.asm.tree.LdcInsnNode ldc) {
            Object v = ldc.cst;
            if (v instanceof org.objectweb.asm.Handle h) {
                var fixed = fixHandle(h, idx);
                if (fixed != null) {
                    ldc.cst = fixed;
                    return true;
                }
            }
        } else if (insn instanceof org.objectweb.asm.tree.InvokeDynamicInsnNode indy) {
            boolean any = false;
            for (int i = 0; i < indy.bsmArgs.length; i++) {
                if (indy.bsmArgs[i] instanceof org.objectweb.asm.Handle h) {
                    var fixed = fixHandle(h, idx);
                    if (fixed != null) {
                        indy.bsmArgs[i] = fixed;
                        any = true;
                    }
                }
            }
            return any;
        }
        return false;
    }

    private static org.objectweb.asm.Handle fixHandle(org.objectweb.asm.Handle h,
                                                      top.mcbridge1201.index.TargetIndex idx) {
        var info = idx.classes.get(h.getOwner());
        if (info == null || !info.isInterface) return null;
        if (h.getTag() == Opcodes.H_INVOKESTATIC && !h.isInterface()) {
            return new org.objectweb.asm.Handle(h.getTag(), h.getOwner(), h.getName(), h.getDesc(), true);
        }
        return null;
    }

    /** Removes explicitly degraded mixin entries from a config (recorded, never silent). */
    private static byte[] stripMixinConfig(byte[] json, RuleSet.MixinStrip strip, Stats st) {
        com.google.gson.JsonObject o;
        try {
            o = com.google.gson.JsonParser.parseString(new String(json, java.nio.charset.StandardCharsets.UTF_8)).getAsJsonObject();
        } catch (RuntimeException ex) {
            return json;
        }
        for (String side : new String[]{"mixins", "client", "server"}) {
            if (!o.has(side) || !o.get(side).isJsonArray()) continue;
            var arr = o.getAsJsonArray(side);
            for (int i = arr.size() - 1; i >= 0; i--) {
                String cls = arr.get(i).getAsString();
                if (strip.classes.contains(cls)) {
                    arr.remove(i);
                    st.applied.merge(strip.id, 1, Integer::sum);
                }
            }
        }
        return new com.google.gson.Gson().toJson(o).getBytes(java.nio.charset.StandardCharsets.UTF_8);
    }

    /** Rewrites a Mixin refmap entry that pins an old target descriptor. */
    private static byte[] patchRefmap(byte[] json, List<RuleSet.MixinCallbackAdaptation> adaptations, Stats st) {
        com.google.gson.JsonObject root;
        try {
            root = com.google.gson.JsonParser.parseString(
                    new String(json, java.nio.charset.StandardCharsets.UTF_8)).getAsJsonObject();
        } catch (RuntimeException ex) {
            throw new IllegalArgumentException("invalid mixin refmap JSON", ex);
        }
        com.google.gson.JsonObject mappings = root.getAsJsonObject("mappings");
        if (mappings == null) throw new IllegalArgumentException("mixin refmap has no 'mappings' object");
        for (RuleSet.MixinCallbackAdaptation a : adaptations) {
            if (a.refmapKey == null || a.refmapValue == null) continue;
            com.google.gson.JsonObject mixin = mappings.getAsJsonObject(a.mixinClass);
            if (mixin == null) {
                throw new IllegalArgumentException("refmap has no entry for mixin " + a.mixinClass);
            }
            mixin.addProperty(a.refmapKey, a.refmapValue);
            st.applied.merge(a.id + "/refmap", 1, Integer::sum);
        }
        return new com.google.gson.Gson().toJson(root).getBytes(java.nio.charset.StandardCharsets.UTF_8);
    }

    private static boolean looksLikeZip(byte[] b) {
        return b.length > 4 && b[0] == 'P' && b[1] == 'K';
    }

    private static Map<String, byte[]> readZip(byte[] bytes) {
        Map<String, byte[]> out = new LinkedHashMap<>();
        try (ZipInputStream zin = new ZipInputStream(new ByteArrayInputStream(bytes))) {
            ZipEntry e;
            while ((e = zin.getNextEntry()) != null) {
                if (e.isDirectory()) continue;
                out.put(e.getName(), readAll(zin));
            }
        } catch (IOException ex) {
            throw new RuntimeException(ex);
        }
        return out;
    }

    private static byte[] writeZipBytes(Map<String, byte[]> entries) {
        ByteArrayOutputStream bos = new ByteArrayOutputStream();
        try (ZipOutputStream zos = new ZipOutputStream(bos)) {
            for (var e : entries.entrySet()) {
                ZipEntry ze = new ZipEntry(e.getKey());
                ze.setTime(0L);
                zos.putNextEntry(ze);
                zos.write(e.getValue());
                zos.closeEntry();
            }
        } catch (IOException ex) {
            throw new RuntimeException(ex);
        }
        return bos.toByteArray();
    }

    private static void writeZip(Map<String, byte[]> entries, Path out) throws IOException {
        try (ZipOutputStream zos = new ZipOutputStream(new BufferedOutputStream(Files.newOutputStream(out)))) {
            for (var e : entries.entrySet()) {
                ZipEntry ze = new ZipEntry(e.getKey());
                ze.setTime(0L);
                zos.putNextEntry(ze);
                zos.write(e.getValue());
                zos.closeEntry();
            }
            zos.finish();
        }
    }

    private static byte[] readAll(InputStream in) throws IOException {
        ByteArrayOutputStream bos = new ByteArrayOutputStream();
        in.transferTo(bos);
        return bos.toByteArray();
    }
}
