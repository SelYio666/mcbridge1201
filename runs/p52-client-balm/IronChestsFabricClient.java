package tech.thatgravyboat.ironchests.client.fabric;

import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.model.loading.v1.ModelLoadingPlugin;
import net.minecraft.class_2960;
import tech.thatgravyboat.ironchests.api.chesttype.ChestBlockType;
import tech.thatgravyboat.ironchests.api.chesttype.ChestType;
import tech.thatgravyboat.ironchests.client.IronChestsClient;
import tech.thatgravyboat.ironchests.common.registry.custom.ChestTypeRegistry;
import top.mcbridge1201.bridge.IdentifierFactory;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

/** 1.21.1 model-loading replacement for the removed ModelLoadingRegistry path. */
public class IronChestsFabricClient implements ClientModInitializer {
    @Override
    public void onInitializeClient() {
        IronChestsClient.init();
        ModelLoadingPlugin.register(context -> {
            List<class_2960> ids = new ArrayList<>();
            ids.add(IdentifierFactory.of("ironchests", "block/locked"));
            ids.add(IdentifierFactory.of("ironchests", "block/unlocked"));
            for (ChestType type : ChestTypeRegistry.INSTANCE.getChests().values()) {
                if (type.blockType() != ChestBlockType.CHEST) continue;
                String name = type.name().toLowerCase(Locale.ROOT);
                ids.add(IdentifierFactory.of("ironchests", "block/chests/" + name + "_chest_lid"));
                ids.add(IdentifierFactory.of("ironchests", "block/chests/" + name + "_chest_base"));
            }
            context.addModels(ids);
        });
    }
}
