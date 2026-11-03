package mcbfixture;

import net.minecraft.class_2561;
import net.minecraft.class_332;
import net.minecraft.class_437;

/**
 * GUI: a Screen subclass overriding the pre-1.21.2 render hook. 1.21.6 splits extraction from
 * drawing, so a converter has to decide per call whether it still paints immediately.
 */
public class FixtureScreen extends class_437 {
    public FixtureScreen(class_2561 title) {
        super(title);
    }

    @Override
    public void method_25394(class_332 context, int mouseX, int mouseY, float delta) {
        super.method_25394(context, mouseX, mouseY, delta);
        context.method_25294(0, 0, 16, 16, 0xFF204060);
    }
}
