package net.fabricmc.fabric.api.client.model;

import net.minecraft.class_1087;
import net.minecraft.class_1091;
import net.minecraft.class_1092;
import net.minecraft.class_2960;

/**
 * Compatibility shim for the Fabric API class that 1.20.1 IronChests linked against and 1.21.1
 * Fabric API removed. The old call is
 * {@code BakedModelManagerHelper.getModel(BakedModelManager, Identifier)} from
 * {@code IronChestsClientImpl.loadModel}; 1.21.1 exposes
 * {@code BakedModelManager.getModel(ModelIdentifier)} instead.
 */
public final class BakedModelManagerHelper {
    private BakedModelManagerHelper() {}

    public static class_1087 getModel(class_1092 manager, class_2960 id) {
        return manager.method_4742(class_1091.method_61078(id));
    }
}
