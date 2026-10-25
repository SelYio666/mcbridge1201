package probe.mixin;

import net.blay09.mods.trashslot.network.MessageDeleteFromSlot;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Accessor;

@Mixin(MessageDeleteFromSlot.class)
public interface MessageDeleteAccessorMixin {
    @Accessor("slotNumber")
    int mcbridge$slotNumber();

    @Accessor("isDeleteAll")
    boolean mcbridge$isDeleteAll();
}
