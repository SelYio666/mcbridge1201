package probe.mixin;

import net.minecraft.class_312;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Invoker;

/** Test-only invoker for the private GLFW mouse-button callback (real event path). */
@Mixin(class_312.class)
public interface MouseInvoker {
    @Invoker("method_1601")
    void mcbridge$onMouseButton(long window, int button, int action, int mods);
}
