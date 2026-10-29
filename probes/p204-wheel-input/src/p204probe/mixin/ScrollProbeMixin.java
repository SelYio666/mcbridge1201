package p204probe.mixin;

import net.minecraft.class_312;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/**
 * The scroll equivalent of p202's P202_CURSOR: log every scroll event the WINDOW delivers, before
 * the game does anything with it (Mouse.onMouseScroll is the GLFW scroll callback body).
 *
 * This is what separates "the list scrolled" from "the list scrolled because of a real wheel":
 * a probe that wrote the scroll amount would produce no such line. Every notch sent by the harness
 * has to show up here with dy=-1.0, and the control phase (wheel with the cursor outside the game
 * window) has to produce none.
 */
@Mixin(class_312.class)
public class ScrollProbeMixin {
    @Inject(method = "method_1598", at = @At("HEAD"))
    private void p204$onScroll(long window, double xOffset, double yOffset, CallbackInfo ci) {
        p204probe.WheelProbe.noteScroll(xOffset, yOffset);
    }
}
