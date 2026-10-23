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
 * The converted mod's ShulkerBoxPreviewProvider reads the legacy BlockEntityTag.Items through the
 * bridge; when a stack carries only the modern CONTAINER component that path can disagree with the
 * component (p186: SBT_ITER raw=1, provider nonAir=0). This wrapper keeps the mod's renderer and
 * hints but supplies the inventory directly from the ContainerComponent.
 */
public final class ComponentPreviewProvider implements PreviewProvider {
    private final PreviewProvider delegate;
    private final class_9288 component;

    public ComponentPreviewProvider(PreviewProvider delegate, class_9288 component) {
        this.delegate = delegate;
        this.component = component;
    }

    @Override
    public List<class_1799> getInventory(PreviewContext context) {
        List<class_1799> inventory = new ArrayList<>(Collections.nCopies(27, class_1799.field_8037));
        if (component != null) {
            int slot = 0;
            for (class_1799 stack : component.method_59714()) {
                if (slot >= 27) {
                    break;
                }
                inventory.set(slot++, stack);
            }
        }
        return inventory;
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
        return 27;
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

    @Override
    public int getPriority() {
        return delegate.getPriority();
    }
}
