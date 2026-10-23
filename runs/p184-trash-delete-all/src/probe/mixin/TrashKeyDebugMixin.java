package probe.mixin;

import net.blay09.mods.balm.api.event.client.screen.ScreenKeyEvent;
import net.minecraft.class_3675;
import net.minecraft.class_437;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

@Mixin(targets = "net.blay09.mods.trashslot.client.TrashSlotGuiHandler", remap = false)
public class TrashKeyDebugMixin {
    @Inject(method = "onKeyPress", at = @At("HEAD"), remap = false, require = 0)
    private static void keyHead(ScreenKeyEvent.Press.Post event, CallbackInfo ci) {
        System.out.println("DEBUG_KEY key=" + event.getKey()
                + " scan=" + event.getScanCode()
                + " mods=" + event.getModifiers()
                + " screen=" + event.getScreen());
    }

    @Inject(method = "runKeyBindings", at = @At("HEAD"), remap = false, require = 0)
    private static void runHead(class_437 screen, class_3675.class_307 input,
                                int key, int scan, int mods, CallbackInfoReturnable<Boolean> cir) {
        System.out.println("DEBUG_RUN key=" + key + " scan=" + scan
                + " mods=" + mods + " type=" + input + " screen=" + screen);
    }

    @Inject(method = "runKeyBindings", at = @At("RETURN"), remap = false, require = 0)
    private static void runReturn(class_437 screen, class_3675.class_307 input,
                                  int key, int scan, int mods, CallbackInfoReturnable<Boolean> cir) {
        System.out.println("DEBUG_RUN_RETURN=" + cir.getReturnValue());
    }
}
