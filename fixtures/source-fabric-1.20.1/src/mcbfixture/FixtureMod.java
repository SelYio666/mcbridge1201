package mcbfixture;

import net.fabricmc.api.ModInitializer;

/** Entry point: touching registration from {@code onInitialize} is the shape real mods use. */
public final class FixtureMod implements ModInitializer {
    @Override
    public void onInitialize() {
        FixtureRegistry.bootstrap();
    }
}
