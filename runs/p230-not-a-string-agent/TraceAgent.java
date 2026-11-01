package mcbridge.agent;

import java.lang.instrument.ClassFileTransformer;
import java.lang.instrument.Instrumentation;
import java.security.ProtectionDomain;

import org.objectweb.asm.ClassReader;
import org.objectweb.asm.ClassVisitor;
import org.objectweb.asm.ClassWriter;
import org.objectweb.asm.Label;
import org.objectweb.asm.MethodVisitor;
import org.objectweb.asm.Opcodes;

/**
 * Prints a stack trace whenever something logs exactly "Not a string".
 * Used by p229/p230 to find the call site of a stackless vanilla log line.
 */
public final class TraceAgent {
    public static void premain(String args, Instrumentation inst) {
        inst.addTransformer(new ClassFileTransformer() {
            @Override
            public byte[] transform(ClassLoader loader, String className, Class<?> redefined,
                                    ProtectionDomain pd, byte[] bytes) {
                if (!"org/apache/logging/slf4j/Log4jLogger".equals(className)) {
                    return null;
                }
                ClassReader cr = new ClassReader(bytes);
                ClassWriter cw = new ClassWriter(ClassWriter.COMPUTE_FRAMES);
                ClassVisitor cv = new ClassVisitor(Opcodes.ASM9, cw) {
                    @Override
                    public MethodVisitor visitMethod(int access, String name, String desc,
                                                     String sig, String[] exceptions) {
                        MethodVisitor mv = super.visitMethod(access, name, desc, sig, exceptions);
                        if (!"error".equals(name) || !"(Ljava/lang/String;)V".equals(desc)) {
                            return mv;
                        }
                        return new MethodVisitor(Opcodes.ASM9, mv) {
                            @Override
                            public void visitCode() {
                                super.visitCode();
                                super.visitLdcInsn("Not a string");
                                super.visitVarInsn(Opcodes.ALOAD, 1);
                                super.visitMethodInsn(Opcodes.INVOKEVIRTUAL, "java/lang/String",
                                        "equals", "(Ljava/lang/Object;)Z", false);
                                Label skip = new Label();
                                super.visitJumpInsn(Opcodes.IFEQ, skip);
                                super.visitTypeInsn(Opcodes.NEW, "java/lang/Exception");
                                super.visitInsn(Opcodes.DUP);
                                super.visitLdcInsn("TRACE Not a string");
                                super.visitMethodInsn(Opcodes.INVOKESPECIAL, "java/lang/Exception",
                                        "<init>", "(Ljava/lang/String;)V", false);
                                super.visitMethodInsn(Opcodes.INVOKEVIRTUAL, "java/lang/Throwable",
                                        "printStackTrace", "()V", false);
                                super.visitLabel(skip);
                            }
                        };
                    }
                };
                cr.accept(cv, 0);
                return cw.toByteArray();
            }
        });
    }
}

