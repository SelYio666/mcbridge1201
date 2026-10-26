package probe.mixin;

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
import net.minecraft.class_332;
import net.minecraft.class_327;

/**
 * p187 diagnostic mixin: traces the converted mod's BasePreviewRenderer draw pipeline so we can
 * see where the diamond disappears between the wrapper inventory (p186: nonAir=1) and the missing
 * grid icons. All targets are mod classes, so remap stays off; logging is rate-limited because
 * setPreview/drawItems run every frame while the tooltip is shown.
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
    private void probe$setPreview(PreviewContext context, PreviewProvider provider, CallbackInfo ci) {
        if (setPreviewLogs++ >= 3 && setPreviewLogs % 200 != 0) {
            return;
        }
        List<class_1799> inventory = provider.getInventory(context);
        int nonAir = 0;
        String head = "none";
        for (class_1799 stack : inventory) {
            if (!stack.method_7960()) {
                nonAir++;
                if (head.equals("none")) {
                    head = stack.method_7909() + "x" + stack.method_7947();
                }
            }
        }
        System.out.println("GRID_SETRENDER call=" + setPreviewLogs
                + " provider=" + provider.getClass().getName()
                + " inv=" + inventory.size() + " nonAir=" + nonAir + " head=" + head);
    }

    @Inject(method = "drawItems", at = @At("HEAD"), remap = false)
    private void probe$drawItems(int x, int y, class_332 context, class_327 textRenderer,
                                 CallbackInfo ci) {
        if (drawItemsLogs++ >= 3 && drawItemsLogs % 200 != 0) {
            return;
        }
        String first = "empty";
        if (items != null && !items.isEmpty()) {
            Object entry = items.get(0);
            if (entry instanceof MergedItemStack merged) {
                class_1799 stack = merged.get();
                first = stack.method_7909() + "x" + stack.method_7947()
                        + " empty=" + stack.method_7960();
            } else {
                first = entry.getClass().getName();
            }
        }
        System.out.println("GRID_DRAWITEMS call=" + drawItemsLogs
                + " type=" + previewType + " items=" + (items == null ? "null" : items.size())
                + " first=" + first);
    }

    @Inject(method = "drawItem", at = @At("HEAD"), remap = false)
    private void probe$drawItem(class_1799 stack, int x, int y, class_332 context,
                                class_327 textRenderer, int index, boolean shortCounts,
                                CallbackInfo ci) {
        if (drawItemLogs++ >= 3) {
            return;
        }
        System.out.println("GRID_DRAWITEM call=" + drawItemLogs
                + " stack=" + stack.method_7909() + " count=" + stack.method_7947()
                + " empty=" + stack.method_7960() + " x=" + x + " y=" + y
                + " short=" + shortCounts);
    }
}
