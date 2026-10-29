package p204probe.mixin;

import net.minecraft.class_339;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Accessor;

/**
 * Read-only geometry of any ClickableWidget (the mod list and the search box are both class_339).
 * Four getters, no setters: the probe must not be able to move a widget, or "the pointer was over
 * the list" would be the probe's own doing rather than the window's.
 *
 * The field order is the one class_339's constructor writes (verified from its bytecode):
 *   (int x, int y, int width, int height) -> field_22760, field_22761, field_22758, field_22759
 * The first p204 run assumed 22758=x and reported a zero-width list; it aimed the cursor at the
 * right pane instead, which is why the wheel produced events (P204_SCROLL) while the list stayed
 * at 0.0. Guessing field meaning is exactly how a run turns green for the wrong reason, so this
 * mapping is pinned here.
 */
@Mixin(class_339.class)
public interface WidgetAccessor {
    @Accessor("field_22760")
    int p204$x();

    @Accessor("field_22761")
    int p204$y();

    @Accessor("field_22758")
    int p204$width();

    @Accessor("field_22759")
    int p204$height();
}
