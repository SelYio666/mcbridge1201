package p204probe.mixin;

import net.minecraft.class_342;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

/**
 * The keyboard channel, at the point that matters: what the TEXT FIELD receives.
 *
 * Screen.keyPressed/charTyped only dispatch to the focused child, so a line from here means the
 * window delivered a real key (GLFW key/char callback -> Screen -> focused widget) and the widget
 * took it. A forged InputConstants poll (the p197/p202 style) can never produce these lines,
 * because it answers a poll instead of delivering an event.
 */
@Mixin(class_342.class)
public class TextFieldMixin {
    @Inject(method = "method_25400", at = @At("HEAD"))
    private void p204$charTyped(char chr, int modifiers, CallbackInfoReturnable<Boolean> cir) {
        p204probe.WheelProbe.noteChar(chr);
    }

    @Inject(method = "method_25404", at = @At("HEAD"))
    private void p204$keyPressed(int keyCode, int scanCode, int modifiers,
                                 CallbackInfoReturnable<Boolean> cir) {
        p204probe.WheelProbe.noteKey(keyCode, scanCode);
    }
}
