package sbtpreview;

import java.util.Optional;

import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

import com.misterpemodder.shulkerboxtooltip.api.PreviewContext;
import com.misterpemodder.shulkerboxtooltip.api.provider.PreviewProvider;
import com.misterpemodder.shulkerboxtooltip.api.provider.PreviewProviderRegistry;
import com.misterpemodder.shulkerboxtooltip.impl.tooltip.PreviewTooltipData;

import mcbridgepreview.ComponentPreviewProvider;
import mcbridgepreview.SnapshotStore;
import net.minecraft.class_1799;
import net.minecraft.class_310;
import net.minecraft.class_5632;
import net.minecraft.class_9288;
import net.minecraft.class_9334;

/**
 * Supplies the mod's PreviewTooltipData from ItemStack.getTooltipData. The conversion stripped the
 * mod's own ItemStackMixin entries (dead 1.21.1 targets), so with the vanilla method nothing ever
 * produces a preview component (p187: getTooltipData returned Optional.empty on every frame). The
 * companion builds the data itself: the component-first provider (registered into the mod's
 * registry by CompanionInit, wrapped again here so it also works when registration failed) reads
 * the CONTAINER component of the tooltip-time snapshot, falling back to the mod's provider legacy
 * path. No other mixin writes this method, so there is no injection-order race.
 */
@Mixin(class_1799.class)
public class PreviewTooltipDataMixin {
    @Inject(method = "method_7950", at = @At("HEAD"))
    private void sbtpreview$snapshot(net.minecraft.class_1792.class_9635 context,
                                     net.minecraft.class_1657 player, net.minecraft.class_1836 type,
                                     org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable<
                                             java.util.List<net.minecraft.class_2561>> cir) {
        class_1799 live = (class_1799) (Object) this;
        SnapshotStore.put(live, live.method_7972());
    }

    @Inject(method = "method_32347", at = @At("HEAD"), cancellable = true)
    private void sbtpreview$data(CallbackInfoReturnable<Optional<class_5632>> cir) {
        class_1799 live = (class_1799) (Object) this;
        if (live.method_7960()) {
            return;
        }
        PreviewProvider registryProvider = PreviewProviderRegistry.getInstance().get(live);
        if (registryProvider == null) {
            return;
        }
        class_1799 snapshot = SnapshotStore.get(live);
        class_1799 stack = snapshot != null ? snapshot : live;
        // method_57379(type, value) is ItemStack.set and would clear the component; read through
        // getComponents() (method_57353) instead.
        Object component = stack.method_57353().method_57829(class_9334.field_49622);
        if (!(component instanceof class_9288)) {
            // No modern container on this stack: leave the vanilla empty data alone; the mod's
            // own provider path (registered in the registry) serves the legacy-tag stacks.
            return;
        }
        ComponentPreviewProvider provider = new ComponentPreviewProvider(registryProvider);
        PreviewContext context = playerContext(live);
        if (!provider.shouldDisplay(context)) {
            return;
        }
        cir.setReturnValue(Optional.of(new PreviewTooltipData(provider, context)));
    }

    private static PreviewContext playerContext(class_1799 stack) {
        class_310 client = class_310.method_1551();
        return client.field_1724 == null
                ? PreviewContext.of(stack)
                : PreviewContext.of(stack, client.field_1724);
    }
}
