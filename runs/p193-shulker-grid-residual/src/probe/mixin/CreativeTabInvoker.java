package probe.mixin;

import net.minecraft.class_1761;
import net.minecraft.class_481;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Invoker;

/** Test-only invoker for the creative screen's private tab setter (method_2466). */
@Mixin(class_481.class)
public interface CreativeTabInvoker {
    @Invoker("method_2466")
    void mcbridge$selectTab(class_1761 tab);
}
