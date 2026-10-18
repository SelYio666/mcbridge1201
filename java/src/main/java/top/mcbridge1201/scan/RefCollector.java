package top.mcbridge1201.scan;

import org.objectweb.asm.AnnotationVisitor;
import org.objectweb.asm.ClassVisitor;
import org.objectweb.asm.ConstantDynamic;
import org.objectweb.asm.FieldVisitor;
import org.objectweb.asm.Handle;
import org.objectweb.asm.Label;
import org.objectweb.asm.MethodVisitor;
import org.objectweb.asm.Opcodes;
import org.objectweb.asm.Type;
import org.objectweb.asm.TypePath;
import org.objectweb.asm.signature.SignatureReader;
import org.objectweb.asm.signature.SignatureVisitor;

import java.util.ArrayList;
import java.util.List;
import java.util.function.Consumer;

/**
 * Collects every symbolic reference a class file can make: hierarchy, descriptors,
 * generic signatures, instructions, invokedynamic bootstrap data, annotations and
 * mixin-style annotation strings.
 */
public final class RefCollector extends ClassVisitor {
    private final Consumer<Ref> sink;
    private final String sourceClass;

    public RefCollector(Consumer<Ref> sink, String sourceClass) {
        super(Opcodes.ASM9);
        this.sink = sink;
        this.sourceClass = sourceClass;
    }

    public String sourceClass() {
        return sourceClass;
    }

    private void cls(String internalName) {
        if (internalName == null || internalName.isEmpty()) return;
        sink.accept(new Ref(RefKind.CLASS, internalName, null, null));
    }

    private void type(Type t) {
        if (t == null) return;
        switch (t.getSort()) {
            case Type.OBJECT -> cls(t.getInternalName());
            case Type.ARRAY -> type(t.getElementType());
            case Type.METHOD -> {
                for (Type a : t.getArgumentTypes()) type(a);
                type(t.getReturnType());
            }
            default -> { }
        }
    }

    private void desc(String d) {
        if (d == null || d.isEmpty()) return;
        if (d.charAt(0) == '(') {
            type(Type.getMethodType(d));
        } else {
            type(Type.getType(d));
        }
    }

    private void sig(String s) {
        if (s == null) return;
        try {
            new SignatureReader(s).accept(new SignatureVisitor(Opcodes.ASM9) {
                @Override
                public void visitClassType(String name) {
                    cls(name);
                }
            });
        } catch (RuntimeException ignored) {
            // malformed signatures are not our damage to report
        }
    }

    @Override
    public void visit(int version, int access, String name, String signature, String superName, String[] interfaces) {
        cls(superName);
        if (interfaces != null) for (String i : interfaces) cls(i);
        sig(signature);
    }

    @Override
    public FieldVisitor visitField(int access, String name, String descriptor, String signature, Object value) {
        desc(descriptor);
        sig(signature);
        if (value instanceof Type t && t.getSort() == Type.OBJECT) cls(t.getInternalName());
        return new FieldVisitor(Opcodes.ASM9) {
            @Override
            public AnnotationVisitor visitAnnotation(String d, boolean visible) {
                return annotation(d);
            }
        };
    }

    @Override
    public MethodVisitor visitMethod(int access, String name, String descriptor, String signature, String[] exceptions) {
        desc(descriptor);
        sig(signature);
        if (exceptions != null) for (String e : exceptions) cls(e);
        return new MethodVisitor(Opcodes.ASM9) {
            @Override
            public void visitTypeInsn(int opcode, String type) {
                cls(type);
            }

            @Override
            public void visitFieldInsn(int opcode, String owner, String n, String d) {
                sink.accept(new Ref(RefKind.FIELD, owner, n, d));
                desc(d);
            }

            @Override
            public void visitMethodInsn(int opcode, String owner, String n, String d, boolean isInterface) {
                sink.accept(new Ref(RefKind.METHOD, owner, n, d));
                desc(d);
            }

            @Override
            public void visitInvokeDynamicInsn(String n, String d, Handle bsm, Object... args) {
                desc(d);
                handle(bsm);
                for (Object a : args) constant(a);
            }

            @Override
            public void visitLdcInsn(Object value) {
                constant(value);
            }

            @Override
            public void visitMultiANewArrayInsn(String d, int dims) {
                desc(d);
            }

            @Override
            public void visitTryCatchBlock(Label start, Label end, Label handler, String type) {
                cls(type);
            }

            @Override
            public void visitLocalVariable(String n, String d, String s, Label start, Label end, int index) {
                desc(d);
                sig(s);
            }

            @Override
            public AnnotationVisitor visitAnnotation(String d, boolean visible) {
                return annotation(d);
            }

            @Override
            public AnnotationVisitor visitTypeAnnotation(int typeRef, TypePath typePath, String d, boolean visible) {
                return annotation(d);
            }

            @Override
            public AnnotationVisitor visitInsnAnnotation(int typeRef, TypePath typePath, String d, boolean visible) {
                return annotation(d);
            }

            @Override
            public AnnotationVisitor visitParameterAnnotation(int parameter, String d, boolean visible) {
                return annotation(d);
            }

            @Override
            public void visitFrame(int type, int numLocal, Object[] local, int numStack, Object[] stack) {
                // frames reference classes but are recomputed/derived; skip to avoid noise
            }
        };
    }

    @Override
    public AnnotationVisitor visitAnnotation(String descriptor, boolean visible) {
        return annotation(descriptor);
    }

    private void constant(Object value) {
        if (value instanceof Type t) {
            type(t);
        } else if (value instanceof Handle h) {
            handle(h);
        } else if (value instanceof ConstantDynamic cd) {
            desc(cd.getDescriptor());
            handle(cd.getBootstrapMethod());
            for (int i = 0; i < cd.getBootstrapMethodArgumentCount(); i++) constant(cd.getBootstrapMethodArgument(i));
        }
    }

    private void handle(Handle h) {
        cls(h.getOwner());
        desc(h.getDesc());
        if (h.getTag() <= Opcodes.H_PUTSTATIC) {
            sink.accept(new Ref(RefKind.FIELD, h.getOwner(), h.getName(), h.getDesc()));
        } else {
            sink.accept(new Ref(RefKind.METHOD, h.getOwner(), h.getName(), h.getDesc()));
        }
    }

    /** Annotation visitor that records class-valued values and mixin-style target strings. */
    private AnnotationVisitor annotation(String descriptor) {
        if (descriptor != null && descriptor.startsWith("L") && descriptor.endsWith(";")) {
            cls(descriptor.substring(1, descriptor.length() - 1));
        }
        return new AnnotationVisitor(Opcodes.ASM9) {
            @Override
            public void visit(String name, Object value) {
                if (value instanceof Type t && t.getSort() == Type.OBJECT) cls(t.getInternalName());
                else if (value instanceof String s) mixinTarget(s);
            }

            @Override
            public void visitEnum(String name, String d, String value) {
                if (d != null && d.startsWith("L")) cls(d.substring(1, d.length() - 1));
            }

            @Override
            public AnnotationVisitor visitAnnotation(String name, String d) {
                return annotation(d);
            }

            @Override
            public AnnotationVisitor visitArray(String name) {
                return this;
            }
        };
    }

    /** Mixin target selectors are plain (dot) class names or descriptors. */
    private void mixinTarget(String s) {
        if (s == null || s.isEmpty()) return;
        String t = s.trim();
        if (t.startsWith("L") && t.endsWith(";") && t.indexOf('/') > 0) {
            desc(t);
            return;
        }
        // only a plain fully-qualified class name; selectors like "foo.Bar;method(...)" are not classes
        if (t.matches("[A-Za-z_$][\\w$]*(\\.[A-Za-z_$][\\w$]*)+")
                && (t.startsWith("net.minecraft.") || t.startsWith("net.minecraftforge.") || t.startsWith("net.neoforged."))) {
            cls(t.replace('.', '/'));
        }
    }

    public static List<Ref> collect(byte[] classBytes, String sourceClass) {
        List<Ref> out = new ArrayList<>();
        new org.objectweb.asm.ClassReader(classBytes)
                .accept(new RefCollector(out::add, sourceClass), 0);
        return out;
    }
}
