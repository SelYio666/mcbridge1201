package top.mcbridge1201.bridge;

import net.minecraft.class_310;
import net.minecraft.class_350;

/**
 * Keeps the 1.20.1 class_350 six-argument constructor alive for converted subclasses that extend
 * class_350 directly (e.g. Mod Menu's DescriptionListWidget).
 *
 * <p>1.21.1 changed the constructor to (client, width, height, y, itemHeight); the old top/bottom
 * pair became a height. The old protected geometry fields that mods read directly are re-declared
 * and initialised with the old constructor semantics.
 */
public abstract class LegacyParentWidget extends class_350 {
    protected final class_310 field_22740;
    protected int field_22741;
    protected int field_22742;
    protected int field_22743;
    protected int field_19085;
    protected int field_19086;
    protected int field_19087;
    protected int field_19088;
    protected int field_22748;

    protected LegacyParentWidget(class_310 client, int width, int height, int top, int bottom,
                                 int itemHeight) {
        super(client, width, bottom - top, top, itemHeight);
        this.field_22740 = client;
        this.field_22742 = width;
        this.field_22743 = height;
        this.field_19085 = top;
        this.field_19086 = bottom;
        this.field_22741 = itemHeight;
        this.field_19088 = 0;
        this.field_19087 = width;
    }

    /** 1.20.1 class_350.setLeftPos(int): shifts the row area horizontally. */
    public void method_25333(int left) {
        this.field_19088 = left;
        this.field_19087 = left + this.field_22742;
    }
}
