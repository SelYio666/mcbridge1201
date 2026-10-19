package probe.mixin;

import net.blay09.mods.balm.api.event.client.screen.ScreenMouseEvent;
import net.blay09.mods.balm.mixin.AbstractContainerScreenAccessor;
import net.blay09.mods.trashslot.client.ContainerSettings;
import net.blay09.mods.trashslot.client.TrashSlotGuiHandler;
import net.blay09.mods.trashslot.client.TrashSlotSlot;
import net.blay09.mods.trashslot.config.TrashSlotConfig;
import net.minecraft.class_310;
import net.minecraft.class_465;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(targets = "net.blay09.mods.trashslot.client.TrashSlotGuiHandler", remap = false)
public class TrashGuiDebugMixin {
    @Shadow
    private static ContainerSettings currentContainerSettings;

    @Inject(method = "onMouseClick", at = @At("HEAD"), remap = false, require = 0)
    private static void debugClick(ScreenMouseEvent.Click.Pre event, CallbackInfo ci) {
        var player = class_310.method_1551().field_1724;
        boolean hovering = false;
        TrashSlotSlot trash = TrashSlotGuiHandler.getTrashSlot();
        if (player != null && class_310.method_1551().field_1755 instanceof class_465<?> screen
                && trash != null) {
            hovering = ((AbstractContainerScreenAccessor) screen)
                    .callIsHovering(trash, event.getMouseX(), event.getMouseY());
            System.out.println("DEBUG_CLICK button=" + event.getButton()
                    + " x=" + event.getMouseX() + " y=" + event.getMouseY()
                    + " hovering=" + hovering
                    + " carried=" + player.field_7512.method_34255()
                    + " trash=" + trash.method_7677()
                    + " settings=" + currentContainerSettings
                    + " enabled=" + (currentContainerSettings != null
                            && currentContainerSettings.isEnabled())
                    + " provider=" + TrashSlotConfig.getDeletionProvider());
        } else {
            System.out.println("DEBUG_CLICK no screen/player button=" + event.getButton()
                    + " x=" + event.getMouseX() + " y=" + event.getMouseY());
        }
    }
}
