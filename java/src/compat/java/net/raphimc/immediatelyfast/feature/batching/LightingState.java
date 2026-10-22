package net.raphimc.immediatelyfast.feature.batching;

import com.mojang.blaze3d.systems.RenderSystem;
import java.lang.reflect.Field;
import java.util.Stack;
import org.joml.Vector3f;

/**
 * 1.21.1 port of ImmediatelyFast's item-lighting snapshot. RenderSystem.shaderLightDirections
 * is private (upstream uses an access widener), so read it via cached reflection.
 */
public record LightingState(Vector3f light0, Vector3f light1) {

    private static final Stack<LightingState> STACK = new Stack<>();
    private static final Field LIGHTS;

    static {
        try {
            LIGHTS = RenderSystem.class.getDeclaredField("shaderLightDirections");
            LIGHTS.setAccessible(true);
        } catch (ReflectiveOperationException exc) {
            throw new ExceptionInInitializerError(exc);
        }
    }

    public static LightingState current() {
        try {
            Vector3f[] dirs = (Vector3f[]) LIGHTS.get(null);
            return new LightingState(dirs[0], dirs[1]);
        } catch (ReflectiveOperationException exc) {
            throw new RuntimeException("cannot read shader light directions", exc);
        }
    }

    public void saveAndApply() {
        STACK.push(current());
        this.apply();
    }

    public void revert() {
        STACK.pop().apply();
    }

    public void apply() {
        RenderSystem.setShaderLights(this.light0, this.light1);
    }
}
