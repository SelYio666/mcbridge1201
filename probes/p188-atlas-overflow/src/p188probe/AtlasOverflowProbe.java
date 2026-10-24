package p188probe;

import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.minecraft.class_1011;
import net.minecraft.class_22;
import net.minecraft.class_310;
import net.minecraft.class_330;
import net.minecraft.class_638;
import net.minecraft.class_3620;
import net.minecraft.class_9209;

import p188probe.mixin.DrawContextConsumersAccessor;

/**
 * Test-only client probe for the p188 atlas overflow scene.
 *
 * <p>Once the server has sent the real MapState of map 1 (the player spawns holding it), the probe
 * drives the public update path 1026 times with ids 1..1026 while reusing that one MapState. The
 * first 1024 ids fill atlas 0; id 1025/1026 overflow into a freshly created atlas 1, which is the
 * path that had never been exercised (p181 note: "Atlas overflow (1024 maps) is still untested").
 * Every assignment logs the port's map-atlas markers, and map 1024's texture constructor must bind
 * {@code immediatelyfast:map_atlas/1}.
 *
 * <p>The datapack then swaps the held item to filled_map[map_id=1024]; once the client receives
 * that map's own MapState the probe updates it again, so the held-map draw uploads into atlas 1
 * (bind + update markers with map=1024). After 60 s the probe requests the normal client stop
 * (p181 pattern), letting the runner verify {@code map-atlas clear atlases=2} on a real exit.
 */
public final class AtlasOverflowProbe implements ClientModInitializer {
    private static final int FIRST_OVERFLOW_ID = 1025;
    private static final int LAST_ID = 1026;
    private static final long EXIT_DELAY_MS = 60_000L;

    private boolean assigned;
    private boolean drawn;
    private boolean pixelChecked;

    @Override
    public void onInitializeClient() {
        net.fabricmc.fabric.api.client.rendering.v1.HudRenderCallback.EVENT.register(
                (context, tickCounter) -> drawOverflowMap(context));
        ClientTickEvents.END_CLIENT_TICK.register(this::tick);
        Thread stopper = new Thread(() -> {
            try {
                Thread.sleep(EXIT_DELAY_MS);
            } catch (InterruptedException ignored) {
                return;
            }
            class_310 client = class_310.method_1551();
            System.out.println("[p188-probe] requesting client stop");
            client.method_18859(client::method_1592);
        }, "p188-stop");
        stopper.setDaemon(true);
        stopper.start();
    }

    /**
     * Draws the first overflow map (1025, atlas 1 tile 0) through the public MapRenderer.draw on
     * every HUD frame once the overflow assignment has run. This drives the real bind + atlas
     * upload path for the second atlas; the quad itself lands near the HUD origin, which does not
     * matter - the markers and the screenshot are the evidence.
     */
    private void drawOverflowMap(net.minecraft.class_332 context) {
        class_310 client = class_310.method_1551();
        class_638 world = client.field_1687;
        if (!assigned || pixelChecked || world == null || client.field_1724 == null) {
            return;
        }
        class_22 state1 = world.method_17891(new class_9209(1));
        if (state1 == null) {
            return;
        }
        if (!drawn) {
            drawn = true;
            class_330 mapRenderer = client.field_1773.method_3194();
            net.minecraft.class_4597.class_4598 consumers =
                    ((p188probe.mixin.DrawContextConsumersAccessor) (Object) context).mcbridge$field_44658();
            mapRenderer.method_1773(context.method_51448(), consumers,
                    new class_9209(FIRST_OVERFLOW_ID), state1, true, 15728880);
            System.out.println("[p188-probe] drew map 1025 through MapRenderer.draw (atlas 1)");
            return;
        }
        // Second HUD frame: read the atlas 1 NativeImage back and compare sampled pixels with the
        // MapState colors, so the upload into the OVERFLOW atlas is proven at pixel level (the
        // update marker is rate-limited and this map's upload was beyond its first three lines).
        pixelChecked = true;
        net.raphimc.immediatelyfast.injection.interfaces.IMapRenderer hooks =
                (net.raphimc.immediatelyfast.injection.interfaces.IMapRenderer) client.field_1773.method_3194();
        net.raphimc.immediatelyfast.feature.map_atlas_generation.MapAtlasTexture atlas1 =
                hooks.immediatelyFast$getMapAtlasTexture(1);
        if (atlas1 == null) {
            System.out.println("[p188-probe] pixel-check FAILED: atlas 1 missing");
            return;
        }
        class_1011 image = atlas1.getTexture().method_4525();
        if (image == null) {
            System.out.println("[p188-probe] pixel-check FAILED: atlas 1 image not allocated");
            return;
        }
        byte[] colors = state1.field_122;
        int mismatches = 0;
        int[] probes = {0 + 0 * 128, 64 + 64 * 128, 127 + 127 * 128, 32 + 96 * 128};
        StringBuilder report = new StringBuilder();
        for (int i : probes) {
            int x = i % 128;
            int y = i / 128;
            int expected = class_3620.method_38480(colors[i] & 0xFF);
            int actual = image.method_4315(x, y);
            boolean ok = actual == expected;
            if (!ok) {
                mismatches++;
            }
            report.append(" (").append(x).append(',').append(y)
                    .append(')').append(ok ? "ok" : "exp=" + expected + " act=" + actual);
        }
        System.out.println("[p188-probe] atlas1-pixel-check mismatches=" + mismatches
                + report);
    }

    private void tick(class_310 client) {
        class_638 world = client.field_1687;
        if (world == null || client.field_1724 == null || assigned) {
            return;
        }
        class_22 state1 = world.method_17891(new class_9209(1));
        if (state1 == null) {
            return;
        }
        assigned = true;
        class_330 mapRenderer = client.field_1773.method_3194();
        for (int id = 1; id <= LAST_ID; id++) {
            mapRenderer.method_1769(new class_9209(id), state1);
        }
        net.raphimc.immediatelyfast.injection.interfaces.IMapRenderer hooks =
                (net.raphimc.immediatelyfast.injection.interfaces.IMapRenderer) mapRenderer;
        System.out.println("[p188-probe] assigned 1026 map ids (reusing map 1's MapState)"
                + " mapping1024=" + hooks.immediatelyFast$getAtlasMapping(1024)
                + " mapping1025=" + hooks.immediatelyFast$getAtlasMapping(FIRST_OVERFLOW_ID)
                + " mapping1026=" + hooks.immediatelyFast$getAtlasMapping(LAST_ID)
                + " atlasOf1025=" + (hooks.immediatelyFast$getAtlasMapping(FIRST_OVERFLOW_ID) >> 16)
                + " atlasOf1026=" + (hooks.immediatelyFast$getAtlasMapping(LAST_ID) >> 16));
    }
}
