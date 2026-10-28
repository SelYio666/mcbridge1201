package p202probe.mixin;

import java.util.List;

import com.misterpemodder.shulkerboxtooltip.api.PreviewContext;
import com.misterpemodder.shulkerboxtooltip.api.PreviewType;
import com.misterpemodder.shulkerboxtooltip.api.provider.PreviewProvider;
import com.misterpemodder.shulkerboxtooltip.impl.util.MergedItemStack;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

import net.minecraft.class_1799;
import net.minecraft.class_327;
import net.minecraft.class_332;

/**
 * Traces the converted mod's draw pipeline. p202 needs one thing p196/p197 did not log: the
 * identity of EVERY drawn stack, not just the first, because the claim is "27 cells, 27 different
 * NBT payloads". drawItem receives the stack and its grid index, so the log line pairs a cell with
 * the exact component map that was handed to the renderer.
 */
@Mixin(com.misterpemodder.shulkerboxtooltip.impl.renderer.BasePreviewRenderer.class)
public abstract class PreviewDrawProbeMixin {
    @Shadow(remap = false)
    private List<?> items;

    @Shadow(remap = false)
    private PreviewType previewType;

    private static int setPreviewLogs;
    private static int drawItemsLogs;
    private static int drawItemLogs;

    @Inject(method = "setPreview", at = @At("RETURN"), remap = false)
    private void p202$setPreview(PreviewContext context, PreviewProvider provider,
                                 CallbackInfo ci) {
        int call = ++setPreviewLogs;
        if (call > 3 && call % 200 != 0) {
            return;
        }
        List<class_1799> inventory = provider.getInventory(context);
        int nonAir = 0;
        for (class_1799 stack : inventory) {
            if (!stack.method_7960()) {
                nonAir++;
            }
        }
        System.out.println("P202_SETRENDER call=" + call
                + " provider=" + provider.getClass().getName()
                + " inv=" + inventory.size() + " nonAir=" + nonAir);
    }

    @Inject(method = "drawItems", at = @At("HEAD"), remap = false)
    private void p202$drawItems(int x, int y, class_332 context, class_327 textRenderer,
                                CallbackInfo ci) {
        int call = ++p202probe.Counters.DRAW_ITEMS_CALLS;
        p202probe.Counters.LAST_TYPE = String.valueOf(previewType);
        if (call > 3 && call % 200 != 0) {
            return;
        }
        String first = "empty";
        if (items != null && !items.isEmpty()) {
            Object entry = items.get(0);
            if (entry instanceof MergedItemStack merged) {
                class_1799 stack = merged.get();
                first = stack.method_7909() + "x" + stack.method_7947();
            } else {
                first = entry.getClass().getName();
            }
        }
        System.out.println("P202_DRAWITEMS call=" + call
                + " type=" + previewType + " items=" + (items == null ? "null" : items.size())
                + " x=" + x + " y=" + y
                + " first=" + first);
    }

    @Inject(method = "drawItem", at = @At("HEAD"), remap = false)
    private void p202$drawItem(class_1799 stack, int x, int y, class_332 context,
                               class_327 textRenderer, int index, boolean shortCounts,
                               CallbackInfo ci) {
        int call = ++p202probe.Counters.DRAW_ITEM_CALLS;
        String comps = String.valueOf(stack.method_57353()).replace('\n', ' ');
        p202probe.Counters.DRAWN_DISTINCT.add(comps);
        if (!stack.method_7960()) {
            p202probe.Counters.DRAWN_DISTINCT_NONAIR.add(comps);
            p202probe.Counters.DRAWN_ITEMS.add(String.valueOf(stack.method_7909()));
        }
        p202probe.Counters.DRAWN_KEYS.add(index + "|" + stack.method_7909() + "|"
                + stack.method_7947() + "|" + comps);
        if (p202probe.Counters.DRAWN_ORDER.size() < 40) {
            p202probe.Counters.DRAWN_ORDER.add(index + ":" + stack.method_7909()
                    + "x" + stack.method_7947());
        }
        if (call > 40) {
            return;
        }
        System.out.println("P202_DRAWITEM call=" + call + " index=" + index
                + " item=" + stack.method_7909() + " count=" + stack.method_7947()
                + " x=" + x + " y=" + y + " short=" + shortCounts
                + " comps=" + (comps.length() <= 200 ? comps : comps.substring(0, 197) + "..."));
    }
}
