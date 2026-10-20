package top.mcbridge1201.bridge;

import net.minecraft.class_310;
import net.minecraft.class_4280;

/**
 * Keeps the 1.20.1 EntryListWidget shape alive for converted subclasses.
 *
 * <p>1.21.1 changed {@code EntryListWidget(MinecraftClient, width, height, top, bottom, itemHeight)}
 * to {@code (MinecraftClient, width, height, y, itemHeight)}; the old top/bottom pair became a
 * height. Converted subclasses are retargeted to this class by the superclassReplacements rule, so
 * their {@code super(...)} calls keep working while the drawing code stays untouched.
 *
 * <p>1.21.1 also removed the old protected geometry fields of class_350 that mods read directly
 * (left/right/top/bottom/bounds). They are re-declared here and initialised with the old constructor
 * semantics so field resolution from subclasses keeps working. Values written by the mod itself stay
 * local to these fields; 1.21.1 internals compute their own geometry, so scrollbar placement can
 * differ slightly from 1.20.1.
 */
public abstract class LegacyEntryListWidget extends class_4280 {
    protected final class_310 field_22740;
    protected int field_22741;
    protected int field_22742;
    protected int field_22743;
    protected int field_19085;
    protected int field_19086;
    protected int field_19087;
    protected int field_19088;
    protected int field_22748;

    protected LegacyEntryListWidget(class_310 client, int width, int height, int top, int bottom,
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

    /** 1.20.1 EntryListWidget.setLeftPos(int): shifts the row area horizontally. */
    public void method_25333(int left) {
        this.field_19088 = left;
        this.field_19087 = left + this.field_22742;
    }
}
