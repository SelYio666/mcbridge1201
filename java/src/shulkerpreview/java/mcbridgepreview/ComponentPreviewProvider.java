package mcbridgepreview;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

import com.misterpemodder.shulkerboxtooltip.api.PreviewContext;
import com.misterpemodder.shulkerboxtooltip.api.color.ColorKey;
import com.misterpemodder.shulkerboxtooltip.api.provider.PreviewProvider;
import com.misterpemodder.shulkerboxtooltip.api.renderer.PreviewRenderer;

import net.minecraft.class_1799;
import net.minecraft.class_2561;
import net.minecraft.class_2960;
import net.minecraft.class_9288;
import net.minecraft.class_9334;

/**
 * Registry-level preview provider for shulker boxes. The converted mod's own ItemStackMixin
 * overrides the tooltip data with whatever PreviewProviderRegistry returns for the stack; for a
 * stack that carries only the modern CONTAINER component (client-side stacks, and server stacks
 * whose legacy tag did not survive) the registry answered EmptyPreviewProvider, so the grid
 * renderer merged an empty inventory and drew no icons (p187 GRID_SETRENDER provider=
 * EmptyPreviewProvider inv=0). This provider is registered over the mod's one for every shulker
 * item and answers from the component when it has content, falling back to the mod's provider
 * (legacy BlockEntityTag path) otherwise.
 */
public final class ComponentPreviewProvider implements PreviewProvider {
    private final PreviewProvider delegate;

    public ComponentPreviewProvider(PreviewProvider delegate) {
        this.delegate = delegate;
    }

    /** Component-first inventory: 27 slots from CONTAINER when it has content, else the delegate. */
    @Override
    public List<class_1799> getInventory(PreviewContext context) {
        List<class_1799> inventory = new ArrayList<>(Collections.nCopies(27, class_1799.field_8037));
        class_1799 live = context.stack();
        class_1799 snapshot = SnapshotStore.get(live);
        // The live stack keeps the CONTAINER component with its items; the tooltip-time copy
        // (ItemStack.copy) can lose the item list (p187: snapshot reads came back empty), so the
        // live stack is tried first and the snapshot is only a fallback.
        for (class_1799 candidate : new class_1799[]{live, snapshot}) {
            if (candidate == null || candidate.method_7960()) {
                continue;
            }
            // method_57379(type, value) is ItemStack.set and would clear the component; read
            // through getComponents() (method_57353) instead.
            Object component = candidate.method_57353().method_57829(class_9334.field_49622);
            if (component instanceof class_9288 container) {
                int slot = 0;
                for (class_1799 entry : container.method_59714()) {
                    if (slot >= 27) {
                        break;
                    }
                    inventory.set(slot++, entry);
                }
                for (class_1799 entry : inventory) {
                    if (!entry.method_7960()) {
                        return inventory;
                    }
                }
            }
        }
        return delegate.getInventory(context);
    }

    @Override
    public boolean shouldDisplay(PreviewContext context) {
        for (class_1799 stack : getInventory(context)) {
            if (!stack.method_7960()) {
                return true;
            }
        }
        return false;
    }

    @Override
    public int getInventoryMaxSize(PreviewContext context) {
        List<class_1799> inventory = getInventory(context);
        for (class_1799 stack : inventory) {
            if (!stack.method_7960()) {
                return 27;
            }
        }
        return delegate.getInventoryMaxSize(context);
    }

    /** Strictly above the mod's own provider so register() replaces it per item. */
    @Override
    public int getPriority() {
        return delegate.getPriority() + 1;
    }

    @Override
    public int getMaxRowSize(PreviewContext context) {
        return delegate.getMaxRowSize(context);
    }

    @Override
    public boolean isFullPreviewAvailable(PreviewContext context) {
        return delegate.isFullPreviewAvailable(context);
    }

    @Override
    public boolean showTooltipHints(PreviewContext context) {
        return delegate.showTooltipHints(context);
    }

    @Override
    public String getTooltipHintLangKey(PreviewContext context) {
        return delegate.getTooltipHintLangKey(context);
    }

    @Override
    public String getFullTooltipHintLangKey(PreviewContext context) {
        return delegate.getFullTooltipHintLangKey(context);
    }

    @Override
    public String getLockKeyTooltipHintLangKey(PreviewContext context) {
        return delegate.getLockKeyTooltipHintLangKey(context);
    }

    @Override
    public ColorKey getWindowColorKey(PreviewContext context) {
        return delegate.getWindowColorKey(context);
    }

    @Override
    public PreviewRenderer getRenderer() {
        return delegate.getRenderer();
    }

    @Override
    public List<class_2561> addTooltip(PreviewContext context) {
        return delegate.addTooltip(context);
    }

    @Override
    public void onInventoryAccessStart(PreviewContext context) {
        delegate.onInventoryAccessStart(context);
    }

    @Override
    public class_2960 getTextureOverride(PreviewContext context) {
        return delegate.getTextureOverride(context);
    }
}
