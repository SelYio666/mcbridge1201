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

import net.minecraft.class_1799;
import net.minecraft.class_2487;
import net.minecraft.class_2499;
import net.minecraft.class_310;
import net.minecraft.class_5632;
import top.mcbridge1201.bridge.ShulkerBoxNbtBridge;

/**
 * Replacement wiring for the mixin the conversion had to drop: 1.21.1 no longer has the old
 * getTooltipData signature, so this companion supplies the mod's PreviewTooltipData from the current
 * no-argument ItemStack.getTooltipData(). The mod's still-active HandledScreen mixin then renders the
 * grid.
 */
@Mixin(class_1799.class)
public class PreviewTooltipDataMixin {
    @Inject(method = "method_32347", at = @At("HEAD"), cancellable = true)
    private void sbtpreview$inject(CallbackInfoReturnable<Optional<class_5632>> cir) {
        class_1799 stack = (class_1799) (Object) this;
        if (stack.method_7960()) {
            return;
        }
        PreviewProvider provider = PreviewProviderRegistry.getInstance().get(stack);
        Object component = stack.method_57379(net.minecraft.class_9334.field_49622, null);
        class_2487 tag = ShulkerBoxNbtBridge.legacyBlockEntityTag(stack, "BlockEntityTag");
        String items = "null-tag";
        if (tag != null) {
            Object list = tag.method_10580("Items");
            items = list instanceof class_2499 nl ? "list:" + nl.size() : String.valueOf(list);
        }
        System.out.println("SBT_COMPONENT " + component + " item=" + stack.method_7909()
                + " count=" + stack.method_7947() + " items=" + items);
        System.out.println("SBT_MAP " + stack.method_57380());
        var player = net.minecraft.class_310.method_1551().field_1724;
        if (player != null) {
            var held = player.method_31548().method_5438(player.method_31548().field_7545);
            System.out.println("SBT_INV " + (held == null ? "null" : held.method_57380())
                    + " same=" + (held == stack));
        }
        if (component instanceof net.minecraft.class_9288 c) {
            int iter = 0;
            for (var s : c.method_59714()) {
                if (!s.method_7960()) {
                    iter++;
                }
            }
            long raw1 = c.method_57489().count();
            long raw2 = c.method_59712().count();
            var first = c.method_59714().iterator();
            String head = "none";
            while (first.hasNext()) {
                var st = first.next();
                head = st.method_7909() + "x" + st.method_7947() + " empty=" + st.method_7960();
                break;
            }
            long stream1 = c.method_57489().filter(s -> !s.method_7960()).count();
            long stream2 = c.method_59712().filter(s -> !s.method_7960()).count();
            System.out.println("SBT_ITER raw1=" + raw1 + " raw2=" + raw2 + " head=" + head
                    + " stream1=" + stream1 + " stream2=" + stream2);
        }
        if (provider == null) {
            System.out.println("SBT_PREVIEW_NOPROVIDER " + stack.method_7909());
            return;
        }
        class_310 mc = class_310.method_1551();
        PreviewContext context = mc.field_1724 == null
                ? PreviewContext.of(stack)
                : PreviewContext.of(stack, mc.field_1724);
        boolean show = provider.shouldDisplay(context);
        int size = provider.getInventory(context).size();
        int nonAir = 0;
        for (var entry : provider.getInventory(context)) {
            if (!entry.method_7960()) {
                nonAir++;
            }
        }
        boolean showNoOwner = provider.shouldDisplay(PreviewContext.of(stack));
        System.out.println("SBT_PREVIEW provider=" + provider.getClass().getSimpleName()
                + " show=" + show + " showNoOwner=" + showNoOwner + " inv=" + size
                + " nonAir=" + nonAir + " stack=" + stack.method_7909());
        if (!show) {
            return;
        }
        if (size == 0) {
            return;
        }
        cir.setReturnValue(Optional.of(new PreviewTooltipData(provider, context)));
    }
}
