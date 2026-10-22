package net.raphimc.immediatelyfast.feature.batching;

import com.mojang.blaze3d.platform.GlStateManager;
import com.mojang.blaze3d.systems.RenderSystem;
import java.lang.reflect.Field;
import java.util.Stack;

/**
 * 1.21.1 port of ImmediatelyFast's blend/depth state snapshot. GlStateManager's nested state
 * fields are private in 1.21.1 (upstream uses an access widener); this port reads them via
 * cached reflection.
 */
public record BlendFuncDepthFuncState(boolean blend, boolean depthTest, int srcRgb, int srcAlpha,
                                      int dstRgb, int dstAlpha, int depthFunc) {

    private static final Stack<BlendFuncDepthFuncState> STACK = new Stack<>();
    private static final Field GL_BLEND;
    private static final Field GL_DEPTH;

    static {
        try {
            GL_BLEND = GlStateManager.class.getDeclaredField("BLEND");
            GL_BLEND.setAccessible(true);
            GL_DEPTH = GlStateManager.class.getDeclaredField("DEPTH");
            GL_DEPTH.setAccessible(true);
        } catch (ReflectiveOperationException exc) {
            throw new ExceptionInInitializerError(exc);
        }
    }

    public static BlendFuncDepthFuncState current() {
        try {
            Object blend = GL_BLEND.get(null);
            Object depth = GL_DEPTH.get(null);
            return new BlendFuncDepthFuncState(
                    readBool(blend, "field_5045", "field_5051"),
                    readBool(depth, "field_5074", "field_5051"),
                    readInt(blend, "field_5049"),
                    readInt(blend, "field_5047"),
                    readInt(blend, "field_5048"),
                    readInt(blend, "field_5046"),
                    readInt(depth, "field_5075"));
        } catch (ReflectiveOperationException exc) {
            throw new RuntimeException("cannot read GlStateManager blend/depth state", exc);
        }
    }

    private static Object nested(Object owner, String name) throws ReflectiveOperationException {
        Field field = owner.getClass().getDeclaredField(name);
        field.setAccessible(true);
        return field.get(owner);
    }

    private static boolean readBool(Object owner, String outer, String inner)
            throws ReflectiveOperationException {
        Object state = nested(owner, outer);
        Field field = state.getClass().getDeclaredField(inner);
        field.setAccessible(true);
        return field.getBoolean(state);
    }

    private static int readInt(Object owner, String name) throws ReflectiveOperationException {
        Field field = owner.getClass().getDeclaredField(name);
        field.setAccessible(true);
        return field.getInt(owner);
    }

    public void saveAndApply() {
        STACK.push(current());
        this.apply();
    }

    public void revert() {
        STACK.pop().apply();
    }

    public void apply() {
        if (this.blend) {
            RenderSystem.enableBlend();
        } else {
            RenderSystem.disableBlend();
        }
        RenderSystem.blendFuncSeparate(this.srcRgb, this.dstRgb, this.srcAlpha, this.dstAlpha);
        if (this.depthTest) {
            RenderSystem.enableDepthTest();
        } else {
            RenderSystem.disableDepthTest();
        }
        RenderSystem.depthFunc(this.depthFunc);
    }
}
