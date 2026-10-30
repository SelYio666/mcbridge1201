package top.mcbridge1201.bridge;

import net.minecraft.class_1799;
import net.minecraft.class_1887;
import net.minecraft.class_2561;
import net.minecraft.class_287;
import net.minecraft.class_289;
import net.minecraft.class_332;
import net.minecraft.class_342;

/**
 * Neutralises Cloth Config 11.1.136's immediate-mode drawing helpers, which 1.21.1 deleted (p210).
 *
 * <p>Cloth paints its list with the pre-1.21 model: take the shared
 * {@code VertexConsumerProvider.Immediate} ({@code class_289.method_1348}), ask it for a
 * {@code BufferBuilder} ({@code method_1349}), call {@code begin(DrawMode, VertexFormat)}
 * ({@code class_287.method_1328}), emit vertices, close each one ({@code class_4588.method_1344}),
 * then {@code Immediate.draw()} ({@code method_1350}). 1.21.1 removed all five entry points and
 * replaced the model with {@code RenderLayer} + a single {@code VertexConsumer} per layer, so there
 * is no call-site bridge that keeps them working: {@code begin} no longer exists as a concept.
 * {@code runs/p210-cloth-config/scan_tombstones.py} lists the 7 classes that still reach them.
 *
 * <p>What makes the screen recoverable is where those calls sit. {@code renderList} opens with
 * {@code vcp = Immediate.getInstance(); bb = t0(vcp)} and then <em>never reads either slot</em> -
 * the loop below it draws selection bars through {@code class_332.method_25294} and hands every row
 * to {@code renderItem(DrawContext, Entry, ...)}, which takes no {@code BufferBuilder} at all. So
 * the only barrier between 13 constructed rows and a drawn list is that dead preamble. {@link
 * #buffer} returns {@code null} and the rows appear; nothing downstream dereferences it.
 *
 * <p>The rest of the deleted calls sit in decoration that the screen survives without: the tiled
 * background behind the list, the vignette above and below it, the tab shade gradient and the
 * dropdown drop shadow. Those are replaced body-for-body by the no-op stubs below. This is a
 * recorded degradation, not a silent one - every stub is listed in
 * {@code rules/fabric-1.21.1/cloth-config-render.json} with its own risk note, and the
 * verification run asserts the count of each.
 *
 * <p>Compiled against the 1.21.1 intermediary stub only. The Cloth-owned types these methods used
 * to touch ({@code Matrix4f}, Cloth's {@code Rectangle}, the widget instance) are taken as
 * {@code Object} so this class carries no dependency on Cloth's class hierarchy.
 */
public final class ClothRenderBridge {
    private ClothRenderBridge() {
    }

    /**
     * Stand-in for {@code class_289.method_1349()} ({@code Immediate.getBuffer}).
     *
     * <p>Returns {@code null} deliberately. 1.21.1 has no argument-less buffer accessor - {@code
     * method_60827(RenderLayer)} replaced it - and the only call sites that survive in this jar are
     * the dead preambles of {@code renderList} / {@code method_25394}, where the value is stored and
     * never read. Returning a real buffer would not help either: it would be un-begun, because
     * {@code begin} is gone too. The build asserts that every remaining {@code t0} call site is
     * covered by a rule, so "returns null" cannot silently become a live dereference.
     */
    public static class_287 buffer(class_289 immediate) {
        return null;
    }

    /**
     * Stand-in for {@code class_342.method_1865()} ({@code TextFieldWidget.tick}), called from
     * {@code AbstractConfigScreen.method_25393} for every text field child.
     *
     * <p>1.21.1's text field has no per-tick hook; the caret blink is driven inside the widget's own
     * render. An empty body is the correct translation, not a workaround: the parent screen's own
     * {@code method_25393} still runs, and {@code TickableWidget.tick()} children are still ticked
     * by the loop that follows this call.
     */
    public static void textFieldTick(class_342 widget) {
    }

    /** Replaces {@code DynamicEntryListWidget.renderBackBackground} (tiled list backdrop). */
    public static void listBackdrop(Object self, class_332 context, class_287 buffer,
                                    class_289 immediate) {
    }

    /** Replaces {@code DynamicEntryListWidget.renderHoleBackground} (vignette above/below the list). */
    public static void listVignette(Object self, class_332 context, int x1, int y1, int x2, int y2) {
    }

    /** Replaces {@code AbstractConfigScreen.overlayBackground} (screen-wide dim layer). */
    public static void screenOverlay(Object self, Object matrix, Object rectangle, int x1, int y1,
                                     int x2, int y2, int argb) {
    }

    /** Replaces {@code ClothConfigScreen.drawTabsShades} (shade under the tab strip). */
    public static void tabShades(Object self, Object matrix, int mouseX, int mouseY) {
    }

    /** Replaces {@code ClothConfigScreen$ListWidget.fillGradient} (per-row gradient helper). */
    public static void fillGradient(Object matrix, class_287 buffer, double x1, double y1, double x2,
                                    double y2, int colorTop, int colorBottom, int argb) {
    }

    /** Replaces {@code DropdownBoxEntry$DefaultDropdownMenuElement.lateRender} (drop shadow). */
    public static void dropdownShadow(Object self, class_332 context, int mouseX, int mouseY,
                                      float delta) {
    }

    /**
     * Stand-in for {@code class_1799.method_7977} ({@code ItemStack.setCustomName}), used by Cloth's
     * own demo screen to label the sample items.
     *
     * <p>1.20.5 moved item naming onto the data-component system, so the old mutator is gone. The
     * stack is returned unchanged: the demo items keep their default names, and the screen still
     * opens. This one is only reached through Cloth Config's own Mod Menu entry - opening the mod
     * list calls every entry's config factory, so leaving it as a stub made the mod list log
     * "Error from mod 'cloth-config'" on every visit even when AppleSkin's screen was fine
     * (runs/p210-cloth-config/after2/client.log:138).
     */
    public static class_1799 keepStackName(class_1799 stack, class_2561 name) {
        return stack;
    }

    /**
     * Stand-in for {@code class_1893.field_9131} ({@code Enchantments.<id>}), the enchantment Cloth's
     * demo screen puts on its sample item.
     *
     * <p>The field name survives into 1.21.1 but its type does not: it became
     * {@code RegistryKey<Enchantment>} ({@code class_5321<class_1887>}) because enchantments moved
     * into a registry. Turning that key back into an {@code Enchantment} needs a
     * {@code Registry<Enchantment>}, and 1.21.1 exposes none statically - the client's registry
     * holder ({@code class_7923}) declares 75 {@code class_2378} fields and not one of them is the
     * enchantment registry, which is only reachable through the per-world
     * {@code DynamicRegistryManager}. This lambda has no world in scope.
     *
     * <p>Returns {@code null} on purpose; {@link #demoAddEnchantment} is its only consumer and both
     * halves are replaced together (cloth-config-render.json). Degradation: the demo's sample item
     * is not enchanted. It is still shown, and AppleSkin's own screen never reaches this path.
     */
    public static class_1887 demoEnchantment() {
        return null;
    }

    /**
     * Stand-in for {@code class_1799.method_7978(Enchantment,int)} ({@code ItemStack.addEnchantment}),
     * which 1.21.1 widened to {@code RegistryEntry<Enchantment>} ({@code class_6880<class_1887>}).
     *
     * <p>Empty rather than a rewrite: the only value this jar can push here comes from
     * {@link #demoEnchantment}, which cannot be resolved (see above), so there is nothing to add.
     * The signature keeps the stack shape identical to the removed call, which is why the site can
     * be retargeted without touching the surrounding bytecode.
     */
    public static void demoAddEnchantment(class_1799 stack, class_1887 enchantment, int level) {
    }
}
