package p203.mixin;

import net.blay09.mods.trashslot.TrashHelper;
import net.fabricmc.api.EnvType;
import net.fabricmc.loader.api.FabricLoader;
import net.minecraft.class_1657;
import net.minecraft.class_1799;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/**
 * Stamps the trash state mutation itself.
 *
 * <p>The first attempt hooked {@code ServerPlayNetworkHandler.onCustomPayload} and produced zero
 * lines even though both trash operations clearly reached the server (A's trash went 5 -> empty and
 * B's 4 -> 3 on the server side within the same second). Rather than argue about which dispatch
 * path the Balm bridge uses, the stamp moved to the place the claim is actually about: the moment
 * the per-player trash value is written. Two different players writing in the same stamped tick is
 * exactly "the two operations were applied concurrently".
 *
 * <p>{@code TrashHelper.setTrashItem} writes the stack into the player's persistent NBT, so it runs
 * on both sides; the side and the thread are printed to keep them apart.
 */
@Mixin(TrashHelper.class)
public class TrashHelperMixin {
    @Inject(method = "setTrashItem", at = @At("HEAD"))
    private static void p203$stampSet(class_1657 player, class_1799 stack, CallbackInfo ci) {
        boolean server = FabricLoader.getInstance().getEnvironmentType() == EnvType.SERVER;
        p203.ConcurrentProbe.noteTrashMutation(
                server ? "SERVER" : "CLIENT",
                player == null ? "?" : player.method_7334().getName(),
                stack,
                System.currentTimeMillis());
    }
}
